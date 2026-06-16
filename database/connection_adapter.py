"""
PostgreSQL connection adapter for psycopg3.

Provides a sqlite3.Connection-compatible interface so all existing repositories
work unchanged with both backends. Used by get_connection() when IS_POSTGRES=True.
"""
from __future__ import annotations

import re
from datetime import datetime, date
from decimal import Decimal
from typing import Any

_INSERT_RE = re.compile(r'^\s*INSERT\s+', re.IGNORECASE)
_RETURNING_RE = re.compile(r'\bRETURNING\b', re.IGNORECASE)
_INSERT_OR_IGNORE_RE = re.compile(r'\bINSERT\s+OR\s+IGNORE\s+INTO\b', re.IGNORECASE)
_INSERT_TABLE_RE = re.compile(r'INSERT\s+(?:OR\s+IGNORE\s+)?INTO\s+(\w+)', re.IGNORECASE)

# Tables that have no 'id' column — RETURNING id must not be appended to INSERTs.
_TABLES_WITHOUT_ID = frozenset({'schema_migrations'})


def _sqlite_to_pg(sql: str) -> str:
    """Translate SQLite SQL to PostgreSQL SQL.

    - ? positional placeholders → %s
    - INSERT OR IGNORE INTO → INSERT INTO … ON CONFLICT DO NOTHING
    """
    sql = sql.replace('?', '%s')
    if _INSERT_OR_IGNORE_RE.search(sql):
        sql = _INSERT_OR_IGNORE_RE.sub('INSERT INTO', sql)
        if 'ON CONFLICT' not in sql.upper():
            sql = sql.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    return sql


def _table_from_insert(sql: str) -> str | None:
    """Extract the target table name from an INSERT statement (lowercased)."""
    m = _INSERT_TABLE_RE.search(sql)
    return m.group(1).lower() if m else None


def _normalize_value(v: Any) -> Any:
    """Convert PostgreSQL-native types to the plain Python types sqlite3 returns."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(v, date):
        return v.isoformat()
    return v


def _normalize_row(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {k: _normalize_value(v) for k, v in row.items()}


def _split_sql(script: str) -> list[str]:
    """Split a SQL script on semicolons, ignoring those inside -- comments or '...' literals.

    Handles:
    - ``--`` single-line comments (skipped entirely, not added to any statement)
    - ``'...'`` string literals including ``''`` escaped quotes
    - Semicolons as statement terminators only when outside the above contexts
    """
    statements: list[str] = []
    buf: list[str] = []
    i, n = 0, len(script)
    while i < n:
        ch = script[i]
        if ch == '-' and i + 1 < n and script[i + 1] == '-':
            # Skip single-line comment up to (but not including) the newline
            while i < n and script[i] != '\n':
                i += 1
        elif ch == "'":
            buf.append(ch)
            i += 1
            while i < n:
                c = script[i]
                buf.append(c)
                i += 1
                if c == "'":
                    if i < n and script[i] == "'":
                        # Escaped quote '' inside string literal
                        buf.append(script[i])
                        i += 1
                    else:
                        break
        elif ch == ';':
            stmt = ''.join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
        else:
            buf.append(ch)
            i += 1
    stmt = ''.join(buf).strip()
    if stmt:
        statements.append(stmt)
    return statements


class PgCursorAdapter:
    """Wraps a psycopg3 cursor to mimic sqlite3.Cursor."""

    def __init__(self, cursor, captured_lastrowid: int | None = None):
        self._cursor = cursor
        self._lastrowid = captured_lastrowid

    @property
    def lastrowid(self) -> int | None:
        return self._lastrowid

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def fetchone(self) -> dict | None:
        return _normalize_row(self._cursor.fetchone())

    def fetchall(self) -> list[dict]:
        return [_normalize_row(r) for r in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield _normalize_row(row)

    # Allow subscript on result rows in loop: for row in cursor; row["col"]
    def __getitem__(self, key):
        return self._cursor[key]


class PgConnectionAdapter:
    """
    Wraps a psycopg3 connection with a sqlite3.Connection-compatible interface.

    Key translations:
    - ? placeholders  →  %s
    - INSERT OR IGNORE INTO  →  INSERT INTO … ON CONFLICT DO NOTHING
    - INSERT statements receive ``RETURNING id`` only when the target table has an id
      column.  Tables listed in ``_TABLES_WITHOUT_ID`` (e.g. schema_migrations) are
      excluded unconditionally.  Any other table that turns out to have no id column
      is handled via a savepoint: if PostgreSQL raises undefined_column (pgcode 42703)
      the statement is retried without RETURNING and lastrowid is set to None.
    - RETURNING is always appended *after* ON CONFLICT DO NOTHING (correct PG syntax).
      When a conflict fires, fetchone() returns None and lastrowid is silently None.
    - executescript() splits on ``;`` using a state machine that ignores semicolons
      inside ``--`` comments and ``'...'`` string literals.
    - Row results are normalised (Decimal→float, datetime→str).
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=None) -> PgCursorAdapter:
        pg_sql = _sqlite_to_pg(sql)
        is_insert = bool(_INSERT_RE.match(pg_sql.lstrip()))
        last_id: int | None = None

        if is_insert and not _RETURNING_RE.search(pg_sql):
            table = _table_from_insert(pg_sql)
            if table in _TABLES_WITHOUT_ID:
                # Known id-less table: skip RETURNING entirely.
                cursor = self._conn.execute(pg_sql, params or ())
            else:
                # Optimistically append RETURNING id.  Use a savepoint so that an
                # undefined_column error does not abort the surrounding transaction.
                pg_sql_ret = pg_sql.rstrip().rstrip(';') + ' RETURNING id'
                try:
                    self._conn.execute('SAVEPOINT _pg_ret')
                    cursor = self._conn.execute(pg_sql_ret, params or ())
                    row = cursor.fetchone()
                    self._conn.execute('RELEASE SAVEPOINT _pg_ret')
                    if row:
                        last_id = row.get('id') if isinstance(row, dict) else row[0]
                except Exception as exc:
                    # pgcode 42703 = undefined_column — table has no 'id' column.
                    if getattr(exc, 'pgcode', '') == '42703':
                        self._conn.execute('ROLLBACK TO SAVEPOINT _pg_ret')
                        self._conn.execute('RELEASE SAVEPOINT _pg_ret')
                        cursor = self._conn.execute(pg_sql, params or ())
                    else:
                        raise
        else:
            cursor = self._conn.execute(pg_sql, params or ())
            if is_insert:
                # SQL already carries RETURNING — consume the id row.
                row = cursor.fetchone()
                if row:
                    last_id = row.get('id') if isinstance(row, dict) else row[0]

        return PgCursorAdapter(cursor, captured_lastrowid=last_id)

    def executemany(self, sql: str, seq_of_params) -> PgCursorAdapter:
        """Batch-execute sql for each parameter tuple — mirrors sqlite3.Connection.executemany."""
        pg_sql = _sqlite_to_pg(sql)
        cursor = self._conn.executemany(pg_sql, list(seq_of_params))
        return PgCursorAdapter(cursor)

    def executescript(self, sql: str) -> None:
        """Execute multiple SQL statements separated by semicolons.

        Uses ``_split_sql`` to correctly handle semicolons inside ``--`` comments
        and ``'...'`` string literals.  The schema passed to this method must contain
        only plain CREATE/INSERT/ALTER statements — dollar-quoted strings and block
        comments (``/* */``) are not handled.
        """
        for stmt in _split_sql(sql):
            self._conn.execute(stmt)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        pass  # Pool manages the connection lifecycle

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

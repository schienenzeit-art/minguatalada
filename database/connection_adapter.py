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
    - INSERT statements automatically receive RETURNING id; lastrowid is captured
    - executescript() splits on ; and executes each statement
    - Row results are normalised (Decimal→float, datetime→str)
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=None) -> PgCursorAdapter:
        pg_sql = _sqlite_to_pg(sql)
        is_insert = bool(_INSERT_RE.match(pg_sql.lstrip()))

        if is_insert and not _RETURNING_RE.search(pg_sql):
            pg_sql = pg_sql.rstrip().rstrip(';') + ' RETURNING id'

        cursor = self._conn.execute(pg_sql, params or ())

        last_id: int | None = None
        if is_insert:
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
        """Execute multiple semicolon-separated SQL statements (psycopg3 compat)."""
        for stmt in sql.split(';'):
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
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

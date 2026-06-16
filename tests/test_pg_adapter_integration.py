"""
Integration tests for PgConnectionAdapter — require a real PostgreSQL database.

Set TEST_DATABASE_URL=postgresql://user:pass@host/db to run.
Skipped automatically when the env var is absent.

Scenarios:
  1. INSERT into a table WITH 'id' column  →  lastrowid is a positive int
  2. INSERT into a table WITHOUT 'id' column (schema_migrations-style)  →  no crash, lastrowid is None
  3. INSERT OR IGNORE that hits a unique conflict  →  no crash, lastrowid is None
"""
import os

import pytest

TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL', '')
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason='TEST_DATABASE_URL not set — skipping Postgres adapter integration tests',
)


@pytest.fixture(scope='module')
def pg_adapter():
    """PgConnectionAdapter backed by a real Postgres connection with two temp tables."""
    psycopg = pytest.importorskip('psycopg')
    from psycopg.rows import dict_row
    from database.connection_adapter import PgConnectionAdapter

    conn = psycopg.connect(TEST_DATABASE_URL, row_factory=dict_row)

    # Table WITH id column
    conn.execute("""
        CREATE TEMP TABLE _pg_adp_with_id (
            id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)
    # Table WITHOUT id column (mirrors schema_migrations)
    conn.execute("""
        CREATE TEMP TABLE _pg_adp_no_id (
            version INTEGER PRIMARY KEY,
            note    TEXT NOT NULL
        )
    """)
    # Seed a row to guarantee a conflict in test 3
    conn.execute("INSERT INTO _pg_adp_with_id (name) VALUES ('existing_row')")
    conn.commit()

    yield PgConnectionAdapter(conn)

    conn.execute('DROP TABLE IF EXISTS _pg_adp_with_id')
    conn.execute('DROP TABLE IF EXISTS _pg_adp_no_id')
    conn.commit()
    conn.close()


def test_insert_with_id_column_sets_lastrowid(pg_adapter):
    """INSERT into a table with an id column must return a positive integer lastrowid."""
    cur = pg_adapter.execute(
        "INSERT INTO _pg_adp_with_id (name) VALUES (?)", ("new_row",)
    )
    assert cur.lastrowid is not None, "lastrowid must not be None for a table with id"
    assert isinstance(cur.lastrowid, int)
    assert cur.lastrowid > 0


def test_insert_no_id_column_no_crash(pg_adapter):
    """INSERT into a table without an id column must not raise; lastrowid must be None."""
    cur = pg_adapter.execute(
        "INSERT INTO _pg_adp_no_id (version, note) VALUES (?, ?)", (1, "first")
    )
    assert cur.lastrowid is None


def test_insert_or_ignore_conflict_no_crash(pg_adapter):
    """INSERT OR IGNORE that hits a unique conflict must not raise; lastrowid must be None."""
    # 'existing_row' was seeded in the fixture — this insert must conflict silently.
    cur = pg_adapter.execute(
        "INSERT OR IGNORE INTO _pg_adp_with_id (name) VALUES (?)", ("existing_row",)
    )
    assert cur.lastrowid is None

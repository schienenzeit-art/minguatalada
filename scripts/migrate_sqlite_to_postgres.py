"""
Einmalige Datenmigration: SQLite → PostgreSQL

Ablauf:
  1. SQLite READ-ONLY öffnen (Quelldaten nicht verändern)
  2. PostgreSQL-Schema initialisieren (schema_postgres.sql)
  3. Alle Tabellen in FK-sicherer Reihenfolge übertragen
  4. Sequenzen auf MAX(id)+1 setzen

Verwendung:
  python scripts/migrate_sqlite_to_postgres.py \
      --sqlite data/system.db \
      --pg postgresql://user:password@100.x.y.z:5432/minguatalada

Optionen:
  --dry-run   Alles prüfen, aber nichts in PostgreSQL schreiben
  --force     Bestehende Daten in PostgreSQL überschreiben (TRUNCATE)
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("migrate")

# Reihenfolge: abhängige Tabellen NACH ihren Eltern
_TABLE_ORDER = [
    "locations",
    "roles",
    "categories",
    "mandants",
    "users",
    "settings",
    "persons",
    "claims",
    "claim_history",
    "claim_notes",
    "incomes",
    "expenses",
    "cards",
    "document_types",
    "documents",
    "document_templates",
    "tasks",
    "audit_logs",
    "notifications",
    "appointments",
    "archive_rules",
    "person_notes",
    "approval_requests",
    "household_members",
    "age_alerts",
    "re_evaluation_requests",
    "user_mail_configs",
    "wiedervorlagen",
    "checklist_templates",
    "checklist_items",
    "claim_checklist_items",
    "update_history",
    "update_migrations",
    "filter_presets",
    "schema_migrations",
]

# Spalten die in SQLite 0/1 sind und in PG als BOOLEAN behandelt werden
_BOOL_COLS: dict[str, set[str]] = {
    "locations":             {"is_active"},
    "roles":                 {"is_active"},
    "mandants":              {"is_active"},
    "users":                 {"is_active", "must_change_password"},
    "settings":              {"editable_by_admin"},
    "categories":            set(),
    "claims":                {"has_housing_benefit"},
    "expenses":              {"has_proof"},
    "cards":                 set(),
    "document_types":        {"is_active"},
    "documents":             {"is_deleted"},
    "document_templates":    {"is_active"},
    "tasks":                 {"is_system_task"},
    "notifications":         {"is_read"},
    "archive_rules":         {"is_active"},
    "household_members":     {"is_primary"},
    "age_alerts":            {"is_resolved"},
    "checklist_items":       {"is_required"},
    "claim_checklist_items": {"is_required", "is_checked"},
    "user_mail_configs":     {"use_tls", "is_active"},
    "wiedervorlagen":        {"is_done"},
}


def _open_sqlite(path: Path) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists_sqlite(src: sqlite3.Connection, table: str) -> bool:
    row = src.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _columns_sqlite(src: sqlite3.Connection, table: str) -> list[str]:
    rows = src.execute(f"PRAGMA table_info({table})").fetchall()
    return [r[1] for r in rows]


def _migrate_table(
    src: sqlite3.Connection,
    pg,
    table: str,
    dry_run: bool,
    force: bool,
) -> int:
    if not _table_exists_sqlite(src, table):
        log.info("  %-30s  NICHT IN SQLITE — übersprungen", table)
        return 0

    rows = src.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        log.info("  %-30s  leer", table)
        return 0

    cols = _columns_sqlite(src, table)
    bool_cols = _BOOL_COLS.get(table, set())

    if force and not dry_run:
        pg.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")

    count = 0
    for row in rows:
        values = []
        for col in cols:
            v = row[col]
            # 0/1 integer → Python bool for BOOLEAN columns in PG
            if col in bool_cols and v is not None:
                v = bool(int(v))
            # Compact JSON blobs stay as text
            values.append(v)

        placeholders = ", ".join(["%s"] * len(cols))
        col_list = ", ".join(cols)
        sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
            f" ON CONFLICT DO NOTHING"
        )
        if not dry_run:
            pg.execute(sql, values)
        count += 1

    if not dry_run:
        pg.commit()

    log.info("  %-30s  %d Zeilen", table, count)
    return count


def _reset_sequences(pg) -> None:
    """IDENTITY-Sequenzen auf MAX(id)+1 setzen, damit neue INSERTs keine PK-Konflikte erzeugen."""
    tables_with_identity = [t for t in _TABLE_ORDER if t != "schema_migrations"]
    for table in tables_with_identity:
        try:
            row = pg.execute(f"SELECT MAX(id) FROM {table}").fetchone()
            max_id = (row or {}).get("max", None) if isinstance(row, dict) else (row[0] if row else None)
            if max_id is not None:
                pg.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), %s)",
                    (int(max_id),),
                )
        except Exception as e:
            log.warning("Sequenz-Reset für %s fehlgeschlagen: %s", table, e)
    pg.commit()
    log.info("Sequenzen zurückgesetzt.")


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL Datenmigration")
    parser.add_argument("--sqlite", required=True, help="Pfad zur SQLite-Datenbankdatei")
    parser.add_argument("--pg", required=True, help="PostgreSQL-Connection-URL")
    parser.add_argument("--dry-run", action="store_true", help="Nichts schreiben, nur prüfen")
    parser.add_argument("--force", action="store_true", help="TRUNCATE vor dem Einfügen")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite)
    if not sqlite_path.exists():
        log.error("SQLite-Datei nicht gefunden: %s", sqlite_path)
        sys.exit(1)

    log.info("Quelle:  %s", sqlite_path)
    log.info("Ziel:    %s", args.pg.split("@")[-1])
    log.info("Dry-run: %s", args.dry_run)
    log.info("Force:   %s", args.force)

    # ── PostgreSQL-Schema initialisieren ────────────────────────────────────
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        log.error("psycopg3 nicht installiert: pip install 'psycopg[binary]'")
        sys.exit(1)

    if not args.dry_run:
        schema_path = Path(__file__).parent.parent / "database" / "schema_postgres.sql"
        schema_sql = schema_path.read_text(encoding="utf-8")
        with psycopg.connect(args.pg, row_factory=dict_row) as pg_conn:
            for stmt in schema_sql.split(';'):
                stmt = stmt.strip()
                if stmt and not stmt.startswith('--'):
                    try:
                        pg_conn.execute(stmt)
                    except Exception as e:
                        log.warning("Schema-Statement übersprungen: %s", e)
            pg_conn.commit()
        log.info("PostgreSQL-Schema initialisiert.")

    # ── Daten übertragen ────────────────────────────────────────────────────
    src = _open_sqlite(sqlite_path)

    total = 0
    with psycopg.connect(args.pg, row_factory=dict_row, autocommit=False) as pg_conn:
        from database.connection_adapter import PgConnectionAdapter
        pg = PgConnectionAdapter(pg_conn)

        log.info("Beginne Datentransfer...")
        for table in _TABLE_ORDER:
            try:
                count = _migrate_table(src, pg, table, dry_run=args.dry_run, force=args.force)
                total += count
            except Exception as e:
                log.error("Fehler bei Tabelle '%s': %s", table, e)
                sys.exit(1)

        if not args.dry_run:
            _reset_sequences(pg)

    src.close()

    if args.dry_run:
        log.info("DRY-RUN abgeschlossen. %d Zeilen würden übertragen.", total)
    else:
        log.info("Migration abgeschlossen. %d Zeilen übertragen.", total)


if __name__ == "__main__":
    main()

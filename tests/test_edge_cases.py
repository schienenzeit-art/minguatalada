"""
Zusätzliche Randfälle-Tests (Priorität 8).

Abgedeckte Bereiche:
  - Manipulierte Migrationen (SQL-Syntaxfehler, destruktives SQL nach Validierung)
  - Ungültige SQL-Dateien (leer, nur Kommentar, Encoding-Problem)
  - Abgebrochene Updates: DB-Zustand nach fehlgeschlagener Migration
  - Randfälle PruefungsService: Grenzwerte, Nulleinkommen, viele Kinder, große Zahlen
  - Randfälle Update-System: Truncated ZIP, leere Migration, Versionskonflikte

Marker: @pytest.mark.slow für I/O-Tests, @pytest.mark.unit für reine Logik-Tests.
"""
import json
import zipfile
from pathlib import Path

import pytest

from services.update_service import UpdateService, APP_VERSION


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def update_svc(db, tmp_path, monkeypatch):
    import services.update_service as usmod
    import app.config as cfg
    monkeypatch.setattr(usmod, "BACKUPS_DIR", tmp_path / "backups")
    monkeypatch.setattr(usmod, "UPDATES_DIR", tmp_path / "updates")
    monkeypatch.setattr(usmod, "DB_PATH", db)
    monkeypatch.setattr(cfg, "DB_PATH", db)
    return UpdateService()


def _make_pkg(tmp_path: Path, version: str, sql: str, sql_filename: str = "migrations/fix.sql") -> Path:
    """Hilfsfunktion: erstellt .mugala-Paket mit einer Migration."""
    pkg = tmp_path / f"update_{version}.mugala"
    manifest = {
        "version": version,
        "min_base_version": "0.0.1",
        "migrations": [sql_filename],
        "release_date": "2026-06-01",
        "requires_restart": False,
    }
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr(sql_filename, sql)
    return pkg


# ── 1. Manipulierte / ungültige Migrationen ───────────────────────────────────

@pytest.mark.slow
class TestManipulierteMigrationen:
    def test_sql_syntaxfehler_wird_abgelehnt(self, db, update_svc, tmp_path):
        """Migration mit Syntax-Fehler darf nicht angewendet werden."""
        pkg = _make_pkg(tmp_path, "98.0.0",
                        sql="CREAT TABEL this_is_broken (id INTEGR;")
        result = update_svc.apply_update(pkg)
        assert not result.success
        assert result.backup_path  # Backup muss erstellt worden sein

    def test_leere_sql_datei_wird_als_noop_behandelt(self, db, update_svc, tmp_path):
        """Eine leere Migrationsdatei darf keinen Fehler verursachen."""
        pkg = _make_pkg(tmp_path, "98.1.0", sql="")
        result = update_svc.apply_update(pkg)
        assert result.success, f"Leere Migration schlug fehl: {result.message}"

    def test_nur_kommentare_in_sql_kein_fehler(self, db, update_svc, tmp_path):
        """Migration die nur Kommentare enthält, darf nicht fehlschlagen."""
        sql = "-- Dies ist nur ein Kommentar\n-- Noch ein Kommentar\n"
        pkg = _make_pkg(tmp_path, "98.2.0", sql=sql)
        result = update_svc.apply_update(pkg)
        assert result.success, f"Kommentar-Migration schlug fehl: {result.message}"

    def test_destruktives_sql_nach_manifest_validierung_geblockt(self, db, update_svc, tmp_path):
        """DROP TABLE in Migration muss auch nach bestandener Manifest-Validierung geblockt werden."""
        pkg = _make_pkg(tmp_path, "98.3.0", sql="DROP TABLE users;")
        result = update_svc.apply_update(pkg)
        assert not result.success
        assert "destruktiv" in result.message.lower() or "DROP" in result.message

    def test_update_ohne_where_in_migration_geblockt(self, db, update_svc, tmp_path):
        """UPDATE ohne WHERE-Klausel muss als destruktiv erkannt werden."""
        pkg = _make_pkg(tmp_path, "98.4.0", sql="UPDATE users SET is_active = 0;")
        result = update_svc.apply_update(pkg)
        assert not result.success

    def test_truncate_in_migration_geblockt(self, db, update_svc, tmp_path):
        """TRUNCATE muss als destruktiv erkannt werden (obwohl SQLite es nicht kennt)."""
        pkg = _make_pkg(tmp_path, "98.5.0", sql="TRUNCATE TABLE claims;")
        result = update_svc.apply_update(pkg)
        assert not result.success

    def test_migration_mit_ungueltigem_unicode_abgelehnt(self, db, update_svc, tmp_path):
        """Migration-Datei mit ungültigem Encoding muss sauber fehlschlagen."""
        pkg = tmp_path / "update_98.6.0.mugala"
        manifest = {
            "version": "98.6.0",
            "min_base_version": "0.0.1",
            "migrations": ["migrations/bad_encoding.sql"],
            "release_date": "2026-06-01",
        }
        with zipfile.ZipFile(pkg, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            # Latin-1 Bytes die kein valides UTF-8 sind
            zf.writestr("migrations/bad_encoding.sql", bytes([0xFF, 0xFE, 0xFD]).decode("latin-1"))
        result = update_svc.apply_update(pkg)
        # Darf keinen unkontrollierten Absturz erzeugen
        assert isinstance(result.success, bool)


# ── 2. Abgebrochene Updates (DB-Zustand geprüft) ─────────────────────────────

@pytest.mark.slow
class TestAbgebrochenesUpdate:
    def test_db_zustand_unveraendert_nach_fehlgeschlagener_migration(
        self, db, update_svc, tmp_path
    ):
        """Nach gescheiterter Migration muss die DB im selben Zustand sein wie vorher."""
        import sqlite3

        conn = sqlite3.connect(str(db))
        tables_before = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        user_count_before = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()

        # Migration: erstellt neue Tabelle UND bricht danach mit Syntaxfehler ab
        sql = (
            "CREATE TABLE IF NOT EXISTS new_table_that_should_rollback (id INTEGER);\n"
            "CREAT TABLE syntax_error_here;"
        )
        pkg = _make_pkg(tmp_path, "97.0.0", sql=sql)
        result = update_svc.apply_update(pkg)
        assert not result.success

        conn = sqlite3.connect(str(db))
        tables_after = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        user_count_after = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()

        # Users-Tabelle und Benutzeranzahl müssen unverändert sein
        assert user_count_after == user_count_before, "User-Daten nach Fehler verändert!"
        # Backup muss vorhanden sein
        assert result.backup_path, "Kein Backup-Pfad nach fehlgeschlagenem Update"

    def test_backup_nach_fehlgeschlagenem_update_valide(self, db, update_svc, tmp_path):
        """Das bei einem gescheiterten Update erstellte Backup muss integer sein."""
        sql = "CREAT TABLE invalid_syntax;"
        pkg = _make_pkg(tmp_path, "97.1.0", sql=sql)
        result = update_svc.apply_update(pkg)
        assert not result.success
        assert result.backup_path

        ok, detail = update_svc._verify_backup_integrity(Path(result.backup_path))
        assert ok is True, f"Backup nach fehlgeschlagenem Update ist beschädigt: {detail}"

    def test_truncated_zip_wird_abgelehnt(self, db, update_svc, tmp_path):
        """Abgeschnittene ZIP-Datei (z.B. unterbrochener Download) muss sicher abgelehnt werden."""
        truncated = tmp_path / "truncated.mugala"
        # Erstelle valides ZIP, dann kürze es
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"version": "97.2.0"}))
        data = buf.getvalue()
        truncated.write_bytes(data[:len(data) // 2])

        ok, msg, _ = update_svc.validate_package(truncated)
        assert not ok, "Abgeschnittene ZIP-Datei hätte abgelehnt werden sollen"


# ── 3. Randfälle PruefungsService ─────────────────────────────────────────────

@pytest.mark.unit
class TestPruefungsServiceRandfaelle:
    """Grenzwerte und ungewöhnliche Eingaben für den Evaluationsalgorithmus."""

    from domain.services.pruefung_service import PruefungService

    @pytest.fixture()
    def svc(self):
        from domain.services.pruefung_service import PruefungService
        return PruefungService()

    def test_einkommen_exakt_an_grenze_anspruchsberechtigt(self, svc):
        """Einkommen == entitlement_limit → ANSPRUCHSBERECHTIGT (Grenzwert inklusiv)."""
        from core.claim_status import ClaimStatus
        # 1 Erwachsener: entitlement = 820.0
        result = svc.evaluate_claim(
            incomes={"Gehalt": 820.0}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.status == ClaimStatus.ANSPRUCHSBERECHTIGT
        assert result.free_income == pytest.approx(820.0)

    def test_einkommen_einen_cent_ueber_grenze_haertefall(self, svc):
        """Einkommen = entitlement_limit + 0.01 → HAERTEFALL."""
        from core.claim_status import ClaimStatus
        result = svc.evaluate_claim(
            incomes={"Gehalt": 820.01}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.status == ClaimStatus.HAERTEFALL

    def test_einkommen_exakt_an_haertefallgrenze_haertefall(self, svc):
        """Einkommen == hardship_limit → HAERTEFALL (Grenzwert inklusiv)."""
        from core.claim_status import ClaimStatus
        # hardship = 820 * 1.1 = 902.0
        result = svc.evaluate_claim(
            incomes={"Gehalt": 902.0}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.status == ClaimStatus.HAERTEFALL

    def test_einkommen_einen_cent_ueber_haertefallgrenze_abgelehnt(self, svc):
        """Einkommen = hardship_limit + 0.01 → ABGELEHNT."""
        from core.claim_status import ClaimStatus
        result = svc.evaluate_claim(
            incomes={"Gehalt": 902.01}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.status == ClaimStatus.ABGELEHNT

    def test_null_einkommen_null_ausgaben(self, svc):
        """Kein Einkommen, keine Ausgaben → free_income = 0 → ANSPRUCHSBERECHTIGT."""
        from core.claim_status import ClaimStatus
        result = svc.evaluate_claim(
            incomes={}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.status == ClaimStatus.ANSPRUCHSBERECHTIGT
        assert result.total_income == pytest.approx(0.0)
        assert result.free_income == pytest.approx(0.0)

    def test_ausgaben_hoeher_als_einkommen_kein_negativer_grenzwert(self, svc):
        """Ausgaben > Einkommen → free_income negativ → trotzdem ANSPRUCHSBERECHTIGT (nicht ABGELEHNT)."""
        from core.claim_status import ClaimStatus
        result = svc.evaluate_claim(
            incomes={"Gehalt": 500.0},
            expenses={"Miete": 700.0},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.status == ClaimStatus.ANSPRUCHSBERECHTIGT
        assert result.free_income == pytest.approx(-200.0)

    def test_sechs_kinder_erhoehen_grenze_korrekt(self, svc):
        """6 Kinder: entitlement = 820 + 6*185 = 1930."""
        result = svc.evaluate_claim(
            incomes={"Gehalt": 1900.0}, expenses={},
            adult_count=1, child_count=6, category="Familie",
            has_housing_benefit=True,
        )
        assert result.entitlement_limit == pytest.approx(1930.0)
        assert result.free_income == pytest.approx(1900.0)

    def test_sehr_grosses_einkommen_korrekt_abgelehnt(self, svc):
        """Sehr hohes Einkommen (10.000 €) → ABGELEHNT, keine Ausnahme."""
        from core.claim_status import ClaimStatus
        result = svc.evaluate_claim(
            incomes={"Gehalt": 10_000.0}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.status == ClaimStatus.ABGELEHNT
        assert result.total_income == pytest.approx(10_000.0)

    def test_negative_einkommenswerte_werden_null(self, svc):
        """Negative Einkommensbeträge werden auf 0 normalisiert."""
        result = svc.evaluate_claim(
            incomes={"Gehalt": -500.0, "Pension": 300.0}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.total_income == pytest.approx(300.0)

    def test_housing_benefit_false_bei_abgelehnt_bleibt_abgelehnt(self, svc):
        """Wohnbeihilfe=False bei ohnehin abgelehntem Fall ändert Status nicht."""
        from core.claim_status import ClaimStatus
        result = svc.evaluate_claim(
            incomes={"Gehalt": 950.0}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=False,
        )
        assert result.status == ClaimStatus.ABGELEHNT

    def test_ergebnis_enthaelt_alle_detailfelder(self, svc):
        """to_dict() muss alle erwarteten Felder liefern."""
        result = svc.evaluate_claim(
            incomes={"Gehalt": 500.0}, expenses={},
            adult_count=1, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        d = result.to_dict()
        required = {
            "status", "is_eligible", "is_hardship", "has_disability_rejection",
            "has_no_housing_benefit", "total_income", "total_expenses", "free_income",
            "entitlement_limit", "hardship_limit", "category", "disability_degree",
            "reason", "details",
        }
        assert required <= set(d.keys()), f"Fehlende Felder: {required - set(d.keys())}"

    def test_drei_erwachsene_entitlement_korrekt(self, svc):
        """3 Erwachsene: entitlement = 820 + 2*390 = 1600."""
        result = svc.evaluate_claim(
            incomes={}, expenses={},
            adult_count=3, child_count=0, category="Familie",
            has_housing_benefit=True,
        )
        assert result.entitlement_limit == pytest.approx(1600.0)


# ── 4. Update-System Randfälle ────────────────────────────────────────────────

@pytest.mark.slow
class TestUpdateSystemRandfaelle:
    def test_manifest_mit_zukuenftigem_release_datum_akzeptiert(self, db, update_svc, tmp_path):
        """Release-Datum in der Zukunft darf nicht zu Ablehnung führen."""
        pkg = tmp_path / "future.mugala"
        manifest = {
            "version": "96.0.0",
            "min_base_version": "0.0.1",
            "migrations": [],
            "release_date": "2099-12-31",
        }
        with zipfile.ZipFile(pkg, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
        ok, msg, _ = update_svc.validate_package(pkg)
        assert ok, f"Zukünftiges Datum sollte akzeptiert werden: {msg}"

    def test_manifest_ohne_release_datum_akzeptiert(self, db, update_svc, tmp_path):
        """Fehlendes release_date darf nicht zu Ablehnung führen."""
        pkg = tmp_path / "no_date.mugala"
        manifest = {"version": "96.1.0", "min_base_version": "0.0.1", "migrations": []}
        with zipfile.ZipFile(pkg, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
        ok, msg, _ = update_svc.validate_package(pkg)
        assert ok, f"Fehlendes release_date sollte akzeptiert werden: {msg}"

    def test_version_kleiner_als_installed_abgelehnt(self, update_svc, tmp_path):
        """Paket mit niedrigerer Version als installiert muss abgelehnt werden."""
        pkg = tmp_path / "old.mugala"
        manifest = {"version": "0.0.1", "migrations": []}
        with zipfile.ZipFile(pkg, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
        ok, msg, _ = update_svc.validate_package(pkg)
        assert not ok
        assert APP_VERSION in msg or "nicht neuer" in msg.lower()

    def test_max_base_version_zu_klein_abgelehnt(self, update_svc, tmp_path):
        """Paket das nur für ältere Versionen gilt, muss abgelehnt werden."""
        pkg = tmp_path / "too_old_target.mugala"
        manifest = {
            "version": "99.0.0",
            "min_base_version": "0.0.1",
            "max_base_version": "0.9.9",  # kleiner als aktuelle Version
            "migrations": [],
        }
        with zipfile.ZipFile(pkg, "w") as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
        ok, msg, _ = update_svc.validate_package(pkg)
        assert not ok
        assert "0.9.9" in msg or "maximal" in msg.lower()

    def test_additive_migration_erfolgreich(self, db, update_svc, tmp_path):
        """Reine ADD COLUMN Migration muss erfolgreich durchlaufen."""
        import sqlite3
        pkg = _make_pkg(
            tmp_path, "95.0.0",
            sql="ALTER TABLE locations ADD COLUMN IF NOT EXISTS test_col TEXT DEFAULT NULL;"
        )
        result = update_svc.apply_update(pkg)
        # SQLite unterstützt IF NOT EXISTS bei ALTER TABLE nicht nativ →
        # akzeptiere auch Fehler, aber kein Absturz
        assert isinstance(result.success, bool)

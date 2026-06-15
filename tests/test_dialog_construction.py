"""
Tests für die Konstruktion der Haupt-Dialoge ohne vorinjizierte Services.

Reproduziert den Crash aus Issue "Prüfung starten" – die Fallback-Konstruktoren
der drei Services in ClaimEvaluationDialog fehlten zuvor Pflichtargumente.

Umgebung: offscreen (kein Display nötig), pytest-qt NICHT vorausgesetzt.
"""
import os

import pytest

# Überspringen wenn PyQt6 nicht installiert ist (z.B. CI-Ubuntu ohne GUI-Abhängigkeiten)
pytest.importorskip("PyQt6")

# Offscreen-Rendering erzwingen bevor PyQt6 initialisiert wird
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ─── Gemeinsame Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    """Gemeinsame QApplication-Instanz für alle UI-Tests in diesem Modul."""
    from PyQt6.QtWidgets import QApplication
    existing = QApplication.instance()
    if existing is not None:
        return existing
    app = QApplication([])
    return app


@pytest.fixture()
def claim_id(db, db_conn, as_admin):
    """Legt einen minimalen Testantrag an und gibt die id zurück."""
    from tests.conftest import create_test_claim
    return create_test_claim(db_conn)


# ─── ClaimEvaluationDialog ────────────────────────────────────────────────────

class TestClaimEvaluationDialogConstruction:
    """Dialog darf ohne injizierte Services instanziiert werden."""

    def test_ohne_services_und_ohne_claim_id(self, db, qapp, as_admin):
        """Konstruktor ohne claim_id und ohne Services schlägt nicht fehl."""
        from ui.pages.claim_evaluation_dialog import ClaimEvaluationDialog
        dlg = ClaimEvaluationDialog(claim_id=None)
        assert dlg is not None
        if dlg._autosave_timer:
            dlg._autosave_timer.stop()
        dlg.deleteLater()

    def test_mit_claim_id_ohne_services(self, db, qapp, as_admin, claim_id):
        """Konstruktor mit claim_id=<existierend> und ohne Services schlägt nicht fehl."""
        from ui.pages.claim_evaluation_dialog import ClaimEvaluationDialog
        dlg = ClaimEvaluationDialog(claim_id=claim_id)
        assert dlg is not None
        if dlg._autosave_timer:
            dlg._autosave_timer.stop()
        dlg.deleteLater()

    def test_alle_drei_services_werden_gebaut(self, db, qapp, as_admin):
        """claim_service, checklist_service und re_evaluation_service sind nach __init__ gesetzt."""
        from ui.pages.claim_evaluation_dialog import ClaimEvaluationDialog
        from services.claim_service import ClaimService
        from services.checklist_service import ChecklistService
        from services.re_evaluation_service import ReEvaluationService
        dlg = ClaimEvaluationDialog(claim_id=None)
        assert isinstance(dlg.claim_service, ClaimService)
        assert isinstance(dlg.checklist_service, ChecklistService)
        assert isinstance(dlg.re_evaluation_service, ReEvaluationService)
        if dlg._autosave_timer:
            dlg._autosave_timer.stop()
        dlg.deleteLater()


# ─── CaseCreateDialog ─────────────────────────────────────────────────────────

class TestCaseCreateDialogConstruction:
    """CaseCreateDialog darf ohne injizierte Services instanziiert werden."""

    def test_ohne_services(self, db, qapp, as_admin):
        """Konstruktor ohne Argumente schlägt nicht fehl."""
        from ui.pages.case_create_page import CaseCreateDialog
        dlg = CaseCreateDialog()
        assert dlg is not None
        dlg.deleteLater()

    def test_claim_service_wird_gebaut(self, db, qapp, as_admin):
        """claim_service ist nach __init__ ein vollständiger ClaimService."""
        from ui.pages.case_create_page import CaseCreateDialog
        from services.claim_service import ClaimService
        dlg = CaseCreateDialog()
        assert isinstance(dlg.claim_service, ClaimService)
        dlg.deleteLater()

    def test_on_start_evaluation_ohne_fall_zeigt_warnung(self, db, qapp, as_admin, monkeypatch):
        """on_start_evaluation ohne angelegten Fall darf nicht crashen."""
        from ui.pages.case_create_page import CaseCreateDialog
        warned = []

        # QMessageBox.warning abfangen statt echten Dialog anzeigen
        monkeypatch.setattr(
            "ui.pages.case_create_page.QMessageBox.warning",
            lambda *a, **kw: warned.append(True),
        )
        dlg = CaseCreateDialog()
        dlg.on_start_evaluation()
        assert warned, "Warnung wurde nicht angezeigt"
        dlg.deleteLater()

"""
Unit-Tests für ClaimStatus: Übergänge, Rollenlogik, Display-Namen.

Reine Unit-Tests — keine Datenbank, keine I/O.
Sichern das rollenbasierte Berechtigungsmodell als Regression ab.
"""
import pytest

from core.claim_status import ClaimStatus

pytestmark = pytest.mark.unit


# ─── Basis ────────────────────────────────────────────────────────────────────

def test_alle_statuses_sind_valide():
    for s in ClaimStatus.ALL_STATUSES:
        assert ClaimStatus.is_valid_status(s)


def test_unbekannter_status_ist_invalide():
    assert not ClaimStatus.is_valid_status("FANTASIESTATUS")
    assert not ClaimStatus.is_valid_status("")


def test_display_names_vollstaendig():
    for s in ClaimStatus.ALL_STATUSES:
        display = ClaimStatus.get_display(s)
        assert display, f"Kein Display-Name für Status: {s}"
        assert display != s, f"Display-Name ist identisch mit Key, vermutlich fehlt ein Eintrag: {s}"


def test_unbekannter_status_gibt_rohwert_zurueck():
    assert ClaimStatus.get_display("UNBEKANNT") == "UNBEKANNT"


# ─── can_transition ───────────────────────────────────────────────────────────

class TestMitarbeiterTransitionen:
    """Mitarbeiter hat eingeschränkte Übergangsrechte."""

    def test_kann_in_pruefung_zu_anspruchsberechtigt(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.IN_PRUEFUNG, ClaimStatus.ANSPRUCHSBERECHTIGT, "Mitarbeiter"
        )

    def test_kann_in_pruefung_zu_abgelehnt(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.IN_PRUEFUNG, ClaimStatus.ABGELEHNT, "Mitarbeiter"
        )

    def test_kann_in_pruefung_zu_haertefall(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.IN_PRUEFUNG, ClaimStatus.HAERTEFALL, "Mitarbeiter"
        )

    def test_kann_anspruchsberechtigt_zu_freigabe_karte(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.ANSPRUCHSBERECHTIGT, ClaimStatus.FREIGABE_KARTE, "Mitarbeiter"
        )

    def test_kann_nicht_direkt_archivieren(self):
        # Mitarbeiter darf nicht archivieren
        assert not ClaimStatus.can_transition(
            ClaimStatus.ABGELEHNT, ClaimStatus.ARCHIVIERT, "Mitarbeiter"
        )

    def test_kann_nicht_von_archiviert_wechseln(self):
        # Mitarbeiter hat keine Transition aus ARCHIVIERT
        assert not ClaimStatus.can_transition(
            ClaimStatus.ARCHIVIERT, ClaimStatus.IN_PRUEFUNG, "Mitarbeiter"
        )

    def test_kann_nicht_freigabe_karte_zu_abgelehnt(self):
        # Mitarbeiter hat keine FREIGABE_KARTE-Transitions
        assert not ClaimStatus.can_transition(
            ClaimStatus.FREIGABE_KARTE, ClaimStatus.ABGELEHNT, "Mitarbeiter"
        )


class TestSupervisorTransitionen:
    """Supervisor hat erweiterte Rechte, darf archivieren und Widersprüche bearbeiten."""

    def test_kann_anspruchsberechtigt_archivieren(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.ANSPRUCHSBERECHTIGT, ClaimStatus.ARCHIVIERT, "Supervisor"
        )

    def test_kann_widerspruch_zu_in_pruefung(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.WIDERSPRUCH, ClaimStatus.IN_PRUEFUNG, "Supervisor"
        )

    def test_kann_haertefall_zu_anspruchsberechtigt(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.HAERTEFALL, ClaimStatus.ANSPRUCHSBERECHTIGT, "Supervisor"
        )

    def test_kann_vorlaefig_abgelehnt_zu_abgelehnt(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.VORLAEFIG_ABGELEHNT, ClaimStatus.ABGELEHNT, "Supervisor"
        )


class TestAdminTransitionen:
    """Admin darf alle sinnvollen Übergänge."""

    def test_admin_darf_jeden_validen_uebergang_aus_in_pruefung(self):
        erlaubt = ClaimStatus.get_allowed_transitions(ClaimStatus.IN_PRUEFUNG, "Admin")
        # Admin sollte alle anderen Statuses erreichen können
        assert ClaimStatus.ANSPRUCHSBERECHTIGT in erlaubt
        assert ClaimStatus.ABGELEHNT in erlaubt
        assert ClaimStatus.ARCHIVIERT in erlaubt
        assert ClaimStatus.WIDERSPRUCH in erlaubt

    def test_admin_darf_aus_archiviert_zurueck(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.ARCHIVIERT, ClaimStatus.IN_PRUEFUNG, "Admin"
        )

    def test_admin_darf_archiviert_zu_anspruchsberechtigt(self):
        assert ClaimStatus.can_transition(
            ClaimStatus.ARCHIVIERT, ClaimStatus.ANSPRUCHSBERECHTIGT, "Admin"
        )


class TestUnbekannteRolle:
    """Unbekannte Rollen haben keine Rechte."""

    def test_unbekannte_rolle_hat_keine_transitionen(self):
        ergebnis = ClaimStatus.get_allowed_transitions(ClaimStatus.IN_PRUEFUNG, "Praktikant")
        assert ergebnis == []

    def test_unbekannte_rolle_kann_nicht_uebergehen(self):
        assert not ClaimStatus.can_transition(
            ClaimStatus.IN_PRUEFUNG, ClaimStatus.ABGELEHNT, "Praktikant"
        )


# ─── Genehmigungspflichtige Statuses ─────────────────────────────────────────

def test_haertefall_erfordert_genehmigung():
    assert ClaimStatus.requires_approval(ClaimStatus.HAERTEFALL)


def test_vorlaefig_abgelehnt_erfordert_genehmigung():
    assert ClaimStatus.requires_approval(ClaimStatus.VORLAEFIG_ABGELEHNT)


def test_anspruchsberechtigt_erfordert_keine_genehmigung():
    assert not ClaimStatus.requires_approval(ClaimStatus.ANSPRUCHSBERECHTIGT)


def test_abgelehnt_erfordert_keine_genehmigung():
    assert not ClaimStatus.requires_approval(ClaimStatus.ABGELEHNT)


# ─── Parameterisierte Vollständigkeitsprüfung ─────────────────────────────────

@pytest.mark.parametrize("role", ["Mitarbeiter", "Standortleitung", "Supervisor", "Admin"])
def test_alle_rollen_haben_mindestens_einen_uebergang(role):
    """Regression: jede definierte Rolle hat zumindest einen erlaubten Übergang."""
    hat_uebergang = any(
        ClaimStatus.get_allowed_transitions(s, role)
        for s in ClaimStatus.ALL_STATUSES
    )
    assert hat_uebergang, f"Rolle {role} hat überhaupt keine definierten Übergänge"


@pytest.mark.parametrize("status,expected_display", [
    (ClaimStatus.IN_PRUEFUNG, "In Prüfung"),
    (ClaimStatus.ANSPRUCHSBERECHTIGT, "Anspruchsberechtigt"),
    (ClaimStatus.HAERTEFALL, "Härtefall"),
    (ClaimStatus.ABGELEHNT, "Abgelehnt"),
    (ClaimStatus.ARCHIVIERT, "Archiviert"),
    (ClaimStatus.WIDERSPRUCH, "Widerspruch"),
])
def test_display_names_exakt(status, expected_display):
    assert ClaimStatus.get_display(status) == expected_display

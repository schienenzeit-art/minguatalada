"""
Tests für HouseholdService: Haushaltsmitglieder hinzufügen, aktualisieren,
entfernen — besonders die neue Kategorie-Funktion für Erwachsene.

Regression für: Kategorien für alle Haushaltsmitglieder auswählbar.
"""
import pytest

from tests.conftest import create_test_claim

pytestmark = pytest.mark.integration


@pytest.fixture()
def household_svc(db):
    from services.household_service import HouseholdService
    return HouseholdService()


@pytest.fixture()
def claim_id(db, db_conn, as_admin):
    return create_test_claim(db_conn)


@pytest.fixture()
def category_id(db_conn) -> int:
    """Gibt die ID der Kategorie 'Pensionist' aus der DB zurück."""
    row = db_conn.execute(
        "SELECT id FROM categories WHERE name='Pensionist'"
    ).fetchone()
    assert row, "Kategorie 'Pensionist' nicht gefunden — Seed-Problem?"
    return row[0]


# ─── Mitglied hinzufügen ──────────────────────────────────────────────────────

def test_mitglied_hinzufuegen_gibt_id_zurueck(db, as_admin, household_svc, claim_id):
    mid = household_svc.add_member(
        claim_id=claim_id,
        first_name="Anna",
        last_name="Muster",
        birth_date="1985-03-15",
        relationship="Ehepartner",
    )
    assert isinstance(mid, int)
    assert mid > 0


def test_mitglied_mit_kategorie_hinzufuegen(
    db, as_admin, household_svc, claim_id, category_id
):
    mid = household_svc.add_member(
        claim_id=claim_id,
        first_name="Kurt",
        last_name="Muster",
        birth_date="1950-01-01",
        relationship="Ehepartner",
        category_id=category_id,
    )
    assert mid is not None
    members = household_svc.get_members(claim_id)
    member = next((m for m in members if m["id"] == mid), None)
    assert member is not None
    assert member["category_id"] == category_id
    assert member["category_name"] == "Pensionist"


def test_kind_hat_keine_kategorie(db, as_admin, household_svc, claim_id):
    """Kinder erhalten typischerweise keine Erwachsenen-Kategorie."""
    mid = household_svc.add_member(
        claim_id=claim_id,
        first_name="Lena",
        last_name="Muster",
        birth_date="2015-06-10",
        relationship="Kind",
        category_id=None,
    )
    members = household_svc.get_members(claim_id)
    kind = next((m for m in members if m["id"] == mid), None)
    assert kind["category_id"] is None
    assert kind["category_name"] is None


def test_mehrere_mitglieder_mit_verschiedenen_kategorien(
    db, db_conn, as_admin, household_svc, claim_id
):
    cat_pensionist = db_conn.execute(
        "SELECT id FROM categories WHERE name='Pensionist'"
    ).fetchone()[0]
    cat_sozial = db_conn.execute(
        "SELECT id FROM categories WHERE name='Sozialhilfebezieher'"
    ).fetchone()[0]

    mid1 = household_svc.add_member(
        claim_id=claim_id, first_name="A", last_name="B",
        birth_date="1950-01-01", relationship="Ehepartner",
        category_id=cat_pensionist,
    )
    mid2 = household_svc.add_member(
        claim_id=claim_id, first_name="C", last_name="D",
        birth_date="1975-05-05", relationship="Lebenspartner",
        category_id=cat_sozial,
    )

    members = {m["id"]: m for m in household_svc.get_members(claim_id)}
    assert members[mid1]["category_name"] == "Pensionist"
    assert members[mid2]["category_name"] == "Sozialhilfebezieher"


# ─── Mitglied aktualisieren ───────────────────────────────────────────────────

def test_mitglied_aktualisieren_aendert_daten(db, as_admin, household_svc, claim_id):
    mid = household_svc.add_member(
        claim_id=claim_id, first_name="Alt", last_name="Name",
        birth_date="1970-01-01", relationship="Ehepartner",
    )
    ok = household_svc.update_member(
        member_id=mid, first_name="Neu", last_name="Name",
        birth_date="1970-01-01", relationship="Lebenspartner",
    )
    assert ok
    members = household_svc.get_members(claim_id)
    updated = next((m for m in members if m["id"] == mid), None)
    assert updated["first_name"] == "Neu"
    assert updated["relationship"] == "Lebenspartner"


def test_mitglied_kategorie_aktualisieren(
    db, db_conn, as_admin, household_svc, claim_id, category_id
):
    mid = household_svc.add_member(
        claim_id=claim_id, first_name="Max", last_name="M",
        birth_date="1960-07-07", relationship="Ehepartner",
    )
    # Kategorie nachträglich setzen
    household_svc.update_member(
        member_id=mid, first_name="Max", last_name="M",
        birth_date="1960-07-07", relationship="Ehepartner",
        category_id=category_id,
    )
    members = household_svc.get_members(claim_id)
    member = next((m for m in members if m["id"] == mid), None)
    assert member["category_id"] == category_id


def test_mitglied_kategorie_entfernen(
    db, db_conn, as_admin, household_svc, claim_id, category_id
):
    mid = household_svc.add_member(
        claim_id=claim_id, first_name="Eva", last_name="M",
        birth_date="1955-01-01", relationship="Ehepartner",
        category_id=category_id,
    )
    # Kategorie wieder entfernen
    household_svc.update_member(
        member_id=mid, first_name="Eva", last_name="M",
        birth_date="1955-01-01", relationship="Ehepartner",
        category_id=None,
    )
    members = household_svc.get_members(claim_id)
    member = next((m for m in members if m["id"] == mid), None)
    assert member["category_id"] is None


# ─── Mitglied entfernen ───────────────────────────────────────────────────────

def test_mitglied_entfernen(db, as_admin, household_svc, claim_id):
    mid = household_svc.add_member(
        claim_id=claim_id, first_name="Weg", last_name="Damit",
        birth_date="2000-01-01", relationship="Kind",
    )
    ok = household_svc.remove_member(mid)
    assert ok
    members = household_svc.get_members(claim_id)
    assert not any(m["id"] == mid for m in members)


def test_nicht_vorhandenes_mitglied_entfernen_gibt_false(db, as_admin, household_svc):
    ok = household_svc.remove_member(member_id=999999)
    assert not ok


# ─── Beziehungstypen ─────────────────────────────────────────────────────────

def test_get_relationships_gibt_liste_zurueck(db, household_svc):
    rels = household_svc.get_relationships()
    assert isinstance(rels, list)
    assert len(rels) >= 3
    assert "Kind" in rels
    assert "Ehepartner" in rels


# ─── Alle Kategorien aus Domain verfügbar ────────────────────────────────────

def test_alle_domain_kategorien_in_db_vorhanden(db, db_conn):
    from domain.categories import CATEGORIES
    db_cats = {
        r[0] for r in db_conn.execute("SELECT name FROM categories").fetchall()
    }
    for cat in CATEGORIES:
        assert cat in db_cats, f"Kategorie '{cat}' fehlt in der DB"

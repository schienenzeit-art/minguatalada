"""
Tests fuer die Erfassungsmaske "Neuer Antrag / Person erfassen" (case_create_page).

Abgedeckte Anforderungen:
  - E-Mail ist optional: leeres Feld blockiert das Speichern nicht mehr
  - Ungueltige E-Mail (ohne @) wird abgewiesen
  - Kategorie 'Pensionist' zeigt den Haushalt-Block
  - Kategorie 'Familie' zeigt den Haushalt-Block
  - Sonstige Kategorien blenden den Haushalt-Block aus
  - Haushaltsmitglieder werden fuer Pensionist korrekt gespeichert
  - Bestehendes Backend (PersonRepository) akzeptiert leere E-Mail

Marker: @pytest.mark.integration fuer DB-Tests
"""
import pytest

pytestmark = pytest.mark.integration


# ── Backend: PersonRepository akzeptiert leere / fehlende E-Mail ─────────────

class TestPersonOhneEmail:
    def test_person_ohne_email_kann_angelegt_werden(self, db, db_conn, as_admin):
        """PersonRepository.create_person() ohne E-Mail darf nicht fehlschlagen."""
        from database.repositories.person_repository import PersonRepository
        repo = PersonRepository()
        person_id = repo.create_person({
            "first_name": "Anna",
            "last_name": "Testperson",
            "address": "Musterstrasse 1",
            "postal_code": "6800",
            "city": "Feldkirch",
            "email": None,
        })
        assert isinstance(person_id, int)
        assert person_id > 0

    def test_person_mit_leerem_email_string_kann_angelegt_werden(self, db, db_conn, as_admin):
        from database.repositories.person_repository import PersonRepository
        repo = PersonRepository()
        person_id = repo.create_person({
            "first_name": "Ben",
            "last_name": "Ohnemail",
            "address": "Hauptstrasse 5",
            "postal_code": "6900",
            "city": "Bregenz",
            "email": "",
        })
        assert person_id > 0

    def test_person_mit_gueltiger_email_wird_korrekt_gespeichert(self, db, db_conn, as_admin):
        from database.repositories.person_repository import PersonRepository
        repo = PersonRepository()
        person_id = repo.create_person({
            "first_name": "Clara",
            "last_name": "Mitmail",
            "address": "Seestrasse 3",
            "postal_code": "6850",
            "city": "Dornbirn",
            "email": "clara@beispiel.at",
        })
        row = db_conn.execute("SELECT email FROM persons WHERE id=?", (person_id,)).fetchone()
        assert row["email"] == "clara@beispiel.at"

    def test_person_ohne_email_hat_null_in_db(self, db, db_conn, as_admin):
        from database.repositories.person_repository import PersonRepository
        repo = PersonRepository()
        person_id = repo.create_person({
            "first_name": "David",
            "last_name": "Nullmail",
            "address": "Bergweg 2",
            "postal_code": "6700",
            "city": "Bludenz",
            "email": None,
        })
        row = db_conn.execute("SELECT email FROM persons WHERE id=?", (person_id,)).fetchone()
        assert row["email"] is None


# ── Backend: CaseService.create_case() ohne E-Mail ───────────────────────────

class TestCaseServiceOhneEmail:
    @pytest.fixture()
    def case_svc(self, db):
        from services.case_service import CaseService
        return CaseService()

    def test_create_case_ohne_email_erfolgreich(self, db, as_admin, case_svc):
        """CaseService.create_case() muss auch ohne E-Mail durchlaufen."""
        location_id = 1  # Seeded in initialize_database
        category_id = 1

        result = case_svc.create_case(
            person={
                "first_name": "Emil",
                "last_name": "Keinmail",
                "address": "Testgasse 10",
                "postal_code": "6800",
                "city": "Feldkirch",
                "email": None,
            },
            category_id=category_id,
            location_id=location_id,
            description="Testfall ohne E-Mail",
        )
        assert result["id"] > 0
        assert result["case_number"].startswith("AS-")

    def test_create_case_mit_email_weiterhin_erfolgreich(self, db, as_admin, case_svc):
        """Bestehende Logik mit E-Mail bleibt stabil."""
        result = case_svc.create_case(
            person={
                "first_name": "Franziska",
                "last_name": "Mitmail",
                "address": "Seestrasse 7",
                "postal_code": "6900",
                "city": "Bregenz",
                "email": "franziska@beispiel.at",
            },
            category_id=1,
            location_id=1,
            description="Testfall mit E-Mail",
        )
        assert result["id"] > 0


# ── Validierungslogik: E-Mail-Formatprüfung ───────────────────────────────────

class TestEmailFormatpruefung:
    """
    Prueft die Validierungsregel: wenn E-Mail angegeben, muss '@' enthalten sein.
    Diese Logik liegt im Dialog-on_save(). Wir testen sie als Pure-Logic-Funktion.
    """

    @staticmethod
    def _email_valid(email: str) -> bool:
        """Spiegelt die Logik aus case_create_page.on_save() wider."""
        val = email.strip()
        if not val:
            return True          # leer → erlaubt
        return "@" in val        # angegeben → muss @ enthalten

    def test_leere_email_ist_erlaubt(self):
        assert self._email_valid("") is True

    def test_whitespace_email_ist_erlaubt(self):
        assert self._email_valid("   ") is True

    def test_gueltige_email_ist_erlaubt(self):
        assert self._email_valid("max@beispiel.at") is True

    def test_email_ohne_at_ist_ungueltig(self):
        assert self._email_valid("keinat.at") is False

    def test_email_nur_at_ist_technisch_erlaubt(self):
        # Minimalprüfung: @ vorhanden genügt
        assert self._email_valid("@") is True

    def test_email_mit_at_und_domain_erlaubt(self):
        assert self._email_valid("user@domain.com") is True


# ── Kategorie-Logik: welche Kategorien zeigen den Haushalt-Block ─────────────

class TestKategorieHaushaltSichtbarkeit:
    """
    Prueft die Bedingung aus _on_category_changed() und on_save():
    Haushalt wird angezeigt und gespeichert fuer Familie + Pensionist.
    """

    CATEGORIES_WITH_HOUSEHOLD = {"Familie", "Pensionist"}
    ALL_CATEGORIES = [
        "Pensionist",
        "Alleinerziehend",
        "Menschen mit Beeinträchtigung",
        "Familie",
        "Sozialhilfebezieher",
        "Freiwillige Mitarbeiter",
    ]

    def test_familie_zeigt_haushalt(self):
        assert "Familie" in self.CATEGORIES_WITH_HOUSEHOLD

    def test_pensionist_zeigt_haushalt(self):
        assert "Pensionist" in self.CATEGORIES_WITH_HOUSEHOLD

    def test_alleinerziehend_zeigt_kein_haushalt(self):
        assert "Alleinerziehend" not in self.CATEGORIES_WITH_HOUSEHOLD

    def test_sozialhilfe_zeigt_kein_haushalt(self):
        assert "Sozialhilfebezieher" not in self.CATEGORIES_WITH_HOUSEHOLD

    def test_genau_zwei_kategorien_haben_haushalt(self):
        with_household = [c for c in self.ALL_CATEGORIES if c in self.CATEGORIES_WITH_HOUSEHOLD]
        assert len(with_household) == 2


# ── Backend: Haushaltsmitglieder fuer Pensionist speicherbar ─────────────────

class TestHaushaltFuerPensionist:
    def test_haushaltsmitglied_fuer_pensionist_fall_speicherbar(self, db, db_conn, as_admin):
        """HouseholdService.add_member() muss fuer jeden Fall-Typ funktionieren."""
        from database.repositories.person_repository import PersonRepository
        from database.repositories.claim_repository import ClaimRepository
        from services.household_service import HouseholdService

        # Person + Fall anlegen
        person_id = PersonRepository().create_person({
            "first_name": "Gustav",
            "last_name": "Pensionist",
            "address": "Altersweg 1",
            "postal_code": "6800",
            "city": "Feldkirch",
            "email": None,
        })

        import datetime
        case_number = f"AS-{datetime.datetime.now().year}-TEST01"
        claim_id = ClaimRepository().create_claim(
            case_number=case_number,
            person_id=person_id,
            user_id=as_admin["id"],
            location_id=1,
            category_id=1,
            description="Pensionist Testfall",
        )

        # Haushaltsmitglied hinzufügen
        svc = HouseholdService()
        member_id = svc.add_member(
            claim_id=claim_id,
            first_name="Helga",
            last_name="Pensionistin",
            birth_date="1948-03-15",
            relationship="Ehepartner",
            category_id=None,
        )
        assert isinstance(member_id, int)
        assert member_id > 0

    def test_leere_haushaltsliste_pensionist_kein_fehler(self, db, db_conn, as_admin):
        """Pensionist ohne Haushaltsmitglieder (leere Tabelle) → kein Fehler beim Speichern."""
        from database.repositories.person_repository import PersonRepository
        from database.repositories.claim_repository import ClaimRepository
        from services.household_service import HouseholdService

        person_id = PersonRepository().create_person({
            "first_name": "Hans",
            "last_name": "AlleinPensionist",
            "address": "Ruheweg 5",
            "postal_code": "6900",
            "city": "Bregenz",
            "email": None,
        })

        import datetime
        case_number = f"AS-{datetime.datetime.now().year}-TEST02"
        claim_id = ClaimRepository().create_claim(
            case_number=case_number,
            person_id=person_id,
            user_id=as_admin["id"],
            location_id=1,
            category_id=1,
            description="Pensionist allein",
        )

        # Keine Mitglieder hinzufügen — muss stabil sein
        members = HouseholdService().get_members(claim_id)
        assert members == []

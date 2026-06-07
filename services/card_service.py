from typing import Optional, Dict
from datetime import datetime, timedelta

from database.repositories.card_repository import CardRepository
from database.repositories.claim_repository import ClaimRepository
from core.claim_status import ClaimStatus
from core.card_status import CardStatus

# Rollen mit Recht zur Kartenerstellung (Anforderung 9)
CARD_CREATE_ROLES = {"Standortleitung", "Supervisor", "Admin"}


class CardService:
    """
    Service für Kartenverwaltung.
    
    Verantwortlichkeiten:
    - Kartenerstellung (mit Validierung)
    - Kartenstatus und Ablauflogik
    - Kartenlisten und Filterung
    """

    # Schwellwert für "bald ablaufend" (Tage)
    EXPIRY_THRESHOLD_DAYS = 30

    def __init__(self):
        self.card_repository = CardRepository()
        self.claim_repository = ClaimRepository()

    def can_create_card_for_role(self, role_name: str) -> tuple[bool, str]:
        """Prüft ob die Rolle Kartenerstellung erlaubt (Anforderung 9: Mitarbeiter darf nicht)."""
        if role_name not in CARD_CREATE_ROLES:
            return False, f"Rolle '{role_name}' hat keine Berechtigung zur Kartenerstellung. Nur Standortleitung/Supervisor/Admin."
        return True, ""

    def can_create_card_for_claim(self, claim_id: int) -> tuple[bool, str]:
        """
        Prüft, ob für einen Fall eine Karte erstellt werden darf.
        
        Fachliche Regel:
        - Karte nur für ANSPRUCHSBERECHTIGT oder HAERTEFALL
        - Nicht für ABGELEHNT, IN_PRUEFUNG, etc.
        
        Returns:
            (erlaubt: bool, begründung: str)
        """
        claim = self.claim_repository.get_claim_by_id(claim_id)

        if not claim:
            return False, "Fall nicht gefunden"

        if claim["status"] == ClaimStatus.ABGELEHNT:
            return False, "Karte kann nicht für abgelehnten Fall erstellt werden"

        if claim["status"] not in [ClaimStatus.ANSPRUCHSBERECHTIGT, ClaimStatus.HAERTEFALL]:
            return False, f"Fallstatus muss {ClaimStatus.ANSPRUCHSBERECHTIGT} oder {ClaimStatus.HAERTEFALL} sein, ist aber {claim['status']}"

        # Prüfe ob bereits eine aktive Karte existiert
        existing = self.card_repository.get_cards_by_claim(claim_id)
        active_cards = [c for c in existing if c["status"] not in [CardStatus.ABGELAUFEN, CardStatus.ARCHIVIERT]]
        
        if active_cards:
            return False, "Für diesen Fall existiert bereits eine aktive Karte"

        return True, ""

    def create_card(
        self,
        claim_id: int,
        created_by: int,
        issue_date: Optional[str] = None,
        expiry_date: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Erstellt eine neue Karte für einen Fall.
        
        Args:
            claim_id: Zugehöriger Fall
            created_by: Benutzer-ID des Erstellers
            issue_date: Ausstellungsdatum (optional, default: heute)
            expiry_date: Ablaufdatum (optional, default: heute + 365 Tage)
            note: Optionale Bemerkung
            
        Returns:
            Neue Karte als dict oder None
        """
        can_create, reason = self.can_create_card_for_claim(claim_id)
        if not can_create:
            print(f"Kartenerstellung nicht möglich: {reason}")
            return None

        claim = self.claim_repository.get_claim_by_id(claim_id)

        # Standardwerte setzen
        if issue_date is None:
            issue_date = datetime.now().strftime("%Y-%m-%d")

        if expiry_date is None:
            expiry_dt = datetime.now() + timedelta(days=365)
            expiry_date = expiry_dt.strftime("%Y-%m-%d")

        # Kartennummer nach Standort-Nummernkreis generieren
        location_id = claim.get("location_id")
        location_name = claim.get("location_name")
        is_staff = False
        # Kategorie "Freiwillige Mitarbeiter" → Staff-Nummernkreis
        if claim.get("category_name") == "Freiwillige Mitarbeiter":
            is_staff = True
        card_number = self.card_repository.get_next_card_number(
            location_name=location_name,
            is_staff=is_staff,
        )

        # Karte erstellen
        card_id = self.card_repository.create_card(
            card_number=card_number,
            claim_id=claim_id,
            person_id=claim["person_id"],
            location_id=claim["location_id"],
            issue_date=issue_date,
            expiry_date=expiry_date,
            created_by=created_by,
            note=note,
        )

        if card_id is None:
            print("Fehler beim Erstellen der Karte in der Datenbank")
            return None

        return self.card_repository.get_card_by_id(card_id)

    def get_card(self, card_id: int) -> Optional[Dict]:
        """Holt eine Karte und prüft Ablaufstatus."""
        card = self.card_repository.get_card_by_id(card_id)
        if card:
            # Ablaufstatus aktualisieren
            self.card_repository.check_and_update_expiry_status(
                card_id,
                days_threshold=self.EXPIRY_THRESHOLD_DAYS
            )
            card = self.card_repository.get_card_by_id(card_id)
        return card

    def get_cards_for_claim(self, claim_id: int) -> list[Dict]:
        """Holt alle Karten für einen Fall."""
        cards = self.card_repository.get_cards_by_claim(claim_id)
        # Ablaufstatus für alle prüfen und aktualisieren
        for card in cards:
            self.card_repository.check_and_update_expiry_status(
                card["id"],
                days_threshold=self.EXPIRY_THRESHOLD_DAYS
            )
        # Neu laden nach Status-Update
        return self.card_repository.get_cards_by_claim(claim_id)

    def get_cards_for_person(self, person_id: int) -> list[Dict]:
        """Holt alle Karten für eine Person."""
        cards = self.card_repository.get_cards_by_person(person_id)
        for card in cards:
            self.card_repository.check_and_update_expiry_status(
                card["id"],
                days_threshold=self.EXPIRY_THRESHOLD_DAYS
            )
        return self.card_repository.get_cards_by_person(person_id)

    def list_cards(
        self,
        location_id: Optional[int] = None,
        status: Optional[str] = None,
        person_id: Optional[int] = None,
        search_text: Optional[str] = None,
    ) -> list[Dict]:
        """
        Holt gefilterte Kartenliste.
        Aktualisiert automatisch Ablaufstatus.
        """
        cards = self.card_repository.get_cards(
            location_id=location_id,
            status=status,
            person_id=person_id,
            search_text=search_text,
        )

        # Ablaufstatus für alle aktualisieren
        for card in cards:
            self.card_repository.check_and_update_expiry_status(
                card["id"],
                days_threshold=self.EXPIRY_THRESHOLD_DAYS
            )

        # Neu laden nach Updates
        return self.card_repository.get_cards(
            location_id=location_id,
            status=status,
            person_id=person_id,
            search_text=search_text,
        )

    def lock_card(self, card_id: int, block_reason: str | None = None) -> bool:
        """Sperrt eine Karte (optional mit Sperrgrund)."""
        return self.card_repository.update_card_status_with_reason(card_id, CardStatus.GESPERRT, block_reason)

    def get_card_stats(self, location_id: int | None = None) -> dict:
        """Gibt Karten-Statistiken pro Standort zurück."""
        return self.card_repository.get_card_stats_by_location(location_id)

    def archive_card(self, card_id: int) -> bool:
        """Archiviert eine Karte."""
        return self.card_repository.update_card_status(card_id, CardStatus.ARCHIVIERT)

    def get_expiring_cards(self, days: int = 30) -> list[Dict]:
        """
        Holt Karten die in den nächsten Tagen ablaufen.
        Wird verwendet für Warnungen in der Admin-Ansicht.
        """
        return self.card_repository.get_expiring_cards(days=days)

    def get_card_status_display(self, status: str) -> str:
        """Gibt die deutsche Beschreibung des Kartenstatus zurück."""
        return CardStatus.get_status_display_name(status)

    def get_all_card_statuses(self) -> list[str]:
        """Gibt alle möglichen Kartenstatus zurück."""
        return CardStatus.ALL_STATUSES

    def count_cards(
        self,
        status: str | None = None,
        statuses: list[str] | None = None,
        location_id: int | None = None,
    ) -> int:
        return self.card_repository.count_cards(
            status=status,
            statuses=statuses,
            location_id=location_id,
        )

    def count_expiring_cards(self, days: int = 30) -> int:
        return self.card_repository.count_expiring_cards(days=days)

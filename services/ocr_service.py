"""
OCR-Service – Architektur-Vorbereitung für gescannte Antragsformulare.

Voraussetzungen für Produktivbetrieb:
    pip install pytesseract pillow
    Tesseract-OCR Binary installieren: https://github.com/UB-Mannheim/tesseract/wiki

Aktueller Status: Stub – kein Tesseract konfiguriert.
Die Schnittstelle ist jedoch vollständig definiert und AuditLog-fähig.
"""
from pathlib import Path

from database.repositories.audit_repository import AuditRepository
from core.session import Session


class OcrService:
    """OCR-gestützter Intake-Prozess für Antragsformulare (Anforderung 9)."""

    def __init__(self):
        self.audit_repo = AuditRepository()

    def is_available(self) -> bool:
        """Prüft ob Tesseract installiert und konfiguriert ist."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text(self, image_path: str | Path) -> str:
        """
        Extrahiert Text aus Bild/PDF-Seite.
        Erfordert pytesseract + Tesseract-Binary.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {image_path}")

        self.audit_repo.log(
            user_id=Session.get_user_id(),
            action="OCR_SCAN_GESTARTET",
            object_type="document",
            object_id=None,
            details=f"Datei: {image_path.name}",
        )

        try:
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang="deu")
            self.audit_repo.log(
                user_id=Session.get_user_id(),
                action="OCR_SCAN_ABGESCHLOSSEN",
                object_type="document",
                object_id=None,
                details=f"Datei: {image_path.name}, Zeichen erkannt: {len(text)}",
            )
            return text
        except ImportError:
            raise RuntimeError(
                "OCR nicht verfügbar. Bitte installieren:\n"
                "  pip install pytesseract pillow\n"
                "  Tesseract-Binary: https://github.com/UB-Mannheim/tesseract/wiki"
            )

    def parse_intake_form(self, image_path: str | Path) -> dict:
        """
        Versucht ein Antragsformular zu erkennen und strukturiert auszulesen.

        Rückgabe-Schema (alle Felder optional, soweit erkannt):
        {
            "last_name": str | None,
            "first_name": str | None,
            "birth_date": str | None,   # YYYY-MM-DD
            "address": str | None,
            "postal_code": str | None,
            "city": str | None,
            "has_housing_benefit": bool | None,
            "raw_text": str,
            "confidence": float,  # 0.0–1.0
        }
        """
        raw_text = self.extract_text(image_path)

        # TODO: feldbasierte Extraktion via Regex-Muster für standardisiertes Formular
        # Aktuell: Rohtext zurückgeben, manuelle Nachbearbeitung durch Mitarbeiter
        result = {
            "last_name": None,
            "first_name": None,
            "birth_date": None,
            "address": None,
            "postal_code": None,
            "city": None,
            "has_housing_benefit": None,
            "raw_text": raw_text,
            "confidence": 0.0,
        }

        self.audit_repo.log(
            user_id=Session.get_user_id(),
            action="OCR_FORMULAR_GEPARST",
            object_type="document",
            object_id=None,
            details=f"Datei: {Path(image_path).name}",
        )

        return result

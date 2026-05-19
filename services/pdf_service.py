"""PDF generation helpers using ReportLab.

This module provides `PDFService` used by the UI to generate various
PDF documents. It is kept minimal and uses services to fetch data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
from reportlab.platypus.tables import TableStyle

from services.claim_service import ClaimService
from services.card_service import CardService
from services.report_service import ReportService


PDF_ROOT = Path("data") / "pdfs"


class PDFService:
    def __init__(
        self,
        claim_service: ClaimService | None = None,
        card_service: CardService | None = None,
        report_service: ReportService | None = None,
    ):
        self.claim_service = claim_service or ClaimService()
        self.card_service = card_service or CardService()
        self.report_service = report_service or ReportService()

        self.styles = getSampleStyleSheet()
        self.heading_style = ParagraphStyle(
            "Heading",
            parent=self.styles["Heading1"],
            fontSize=16,
            leading=20,
        )
        self.section_style = ParagraphStyle(
            "Section",
            parent=self.styles["Heading2"],
            fontSize=12,
            leading=14,
        )
        self.normal_style = ParagraphStyle(
            "Normal",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=12,
        )

        # ensure pdf dir exists
        Path(PDF_ROOT).mkdir(parents=True, exist_ok=True)

    def _build_document(self, file_path: Path, story: list) -> str:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(str(file_path), pagesize=A4)
        doc.build(story)
        return str(file_path)

    def _format_table(self, data: list[list[str | int]], col_widths: list[float] | None = None) -> Table:
        table = Table(data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ]
            )
        )
        return table

    def generate_claim_evaluation_pdf(
        self,
        claim_id: int,
        file_path: Optional[str] = None,
    ) -> str:
        claim = self.claim_service.get_claim_by_id(claim_id)
        if claim is None:
            raise ValueError("Anspruch nicht gefunden.")

        if file_path is None:
            filename = f"Pruefungsprotokoll_{claim_id}.pdf"
            file_path = str(PDF_ROOT / filename)

        story: list = []
        story.append(Paragraph("Prüfungsprotokoll", self.heading_style))
        story.append(Paragraph(f"Fallnummer: {claim.get('case_number', '-')}", self.normal_style))
        story.append(Paragraph(f"Person: {claim.get('person_display_name', '-')}", self.normal_style))
        story.append(Paragraph(f"Standort: {claim.get('location_name', '-')}", self.normal_style))
        story.append(Paragraph(f"Kategorie: {claim.get('category_name', '-')}", self.normal_style))
        story.append(Paragraph(f"Status: {claim.get('status', '-')}", self.normal_style))
        story.append(Paragraph(f"Prüfer: {claim.get('examiner_name', '-')}", self.normal_style))
        story.append(Paragraph(f"Prüfdatum: {claim.get('evaluation_date', '-')}", self.normal_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Stammdaten", self.section_style))
        story.append(Paragraph(claim.get('description', '-') or '-', self.normal_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Haushaltsdaten", self.section_style))
        incomes = claim.get('incomes') or []
        expenses = claim.get('expenses') or []
        income_rows = [["Typ", "Betrag (€)"]] + [[i.get('type', '-'), f"{i.get('amount', 0):.2f}"] for i in incomes]
        expense_rows = [["Typ", "Betrag (€)", "Nachweis"]] + [[e.get('type', '-'), f"{e.get('amount', 0):.2f}", "Ja" if e.get('has_proof') else "Nein"] for e in expenses]

        if len(income_rows) > 1:
            story.append(Paragraph("Einnahmen", self.section_style))
            story.append(self._format_table(income_rows))
            story.append(Spacer(1, 6))

        if len(expense_rows) > 1:
            story.append(Paragraph("Ausgaben", self.section_style))
            story.append(self._format_table(expense_rows))
            story.append(Spacer(1, 6))

        free_income = claim.get('free_income')
        entitlement_limit = claim.get('entitlement_limit')
        hardship_limit = claim.get('hardship_limit')

        story.append(Paragraph(f"Status: {claim.get('status', '-')}", self.normal_style))
        story.append(Paragraph(f"Begründung: {claim.get('evaluation_reason', '-')}", self.normal_style))
        if free_income is not None:
            story.append(Paragraph(f"Frei verfügbar: {free_income:.2f} €", self.normal_style))
        if entitlement_limit is not None:
            story.append(Paragraph(f"Anspruchsgrenze: {entitlement_limit:.2f} €", self.normal_style))
        if hardship_limit is not None:
            story.append(Paragraph(f"Härtefallgrenze: {hardship_limit:.2f} €", self.normal_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Freigabe / Abschluss", self.section_style))
        story.append(Paragraph(f"Prüfer-ID: {claim.get('examiner_id', '-')}", self.normal_style))
        story.append(Paragraph(f"Evaluierung abgeschlossen am: {claim.get('evaluation_date', '-')}", self.normal_style))

        return self._build_document(Path(file_path), story)

    def generate_case_summary_pdf(
        self,
        claim_id: int,
        file_path: Optional[str] = None,
    ) -> str:
        claim = self.claim_service.get_claim_by_id(claim_id)
        if claim is None:
            raise ValueError("Anspruch nicht gefunden.")

        if file_path is None:
            filename = f"Fallzusammenfassung_{claim_id}.pdf"
            file_path = str(PDF_ROOT / filename)

        story: list = []
        story.append(Paragraph("Fallzusammenfassung", self.heading_style))
        story.append(Paragraph(f"Fallnummer: {claim.get('case_number', '-')}", self.normal_style))
        story.append(Paragraph(f"Person: {claim.get('person_display_name', '-')}", self.normal_style))
        story.append(Paragraph(f"Standort: {claim.get('location_name', '-')}", self.normal_style))
        story.append(Paragraph(f"Status: {claim.get('status', '-')}", self.normal_style))
        story.append(Paragraph(f"Begründung: {claim.get('evaluation_reason', '-')}", self.normal_style))

        return self._build_document(Path(file_path), story)

    def generate_card_print_pdf(
        self,
        card_id: int,
        file_path: Optional[str] = None,
    ) -> str:
        card = self.card_service.get_card(card_id)
        if card is None:
            raise ValueError("Karte nicht gefunden.")

        if file_path is None:
            filename = f"Kartenausdruck_{card_id}.pdf"
            file_path = str(PDF_ROOT / filename)

        story: list = []
        story.append(Paragraph("Kartenausdruck", self.heading_style))
        story.append(Paragraph(f"Kartennummer: {card.get('card_number', '-')}", self.normal_style))
        story.append(Paragraph(f"Fallnummer: {card.get('case_number', '-')}", self.normal_style))
        person_name = f"{card.get('person_first_name', '-') } {card.get('person_last_name', '-') }"
        story.append(Paragraph(f"Person: {person_name}", self.normal_style))

        return self._build_document(Path(file_path), story)

    def generate_location_report_pdf(
        self,
        location_id: Optional[int] = None,
    ) -> str:
        report = self.report_service.get_location_report(location_id)
        if location_id is None:
            filename = "Standortreport_alle.pdf"
        else:
            filename = f"Standortreport_{location_id}.pdf"

        file_path = str(PDF_ROOT / filename)

        story: list = []
        story.append(Paragraph("Standortreport", self.heading_style))
        story.append(Paragraph(f"Standort: {report.get('location_name', '-')}", self.normal_style))
        story.append(Spacer(1, 12))

        claim_rows = [["Status", "Anzahl"]] + [[item['status'], str(item['count'])] for item in report['claim_status_counts']]
        card_rows = [["Status", "Anzahl"]] + [[item['status'], str(item['count'])] for item in report['card_status_counts']]

        story.append(Paragraph("Anspruchsstatus", self.section_style))
        story.append(self._format_table(claim_rows))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Kartenstatus", self.section_style))
        story.append(self._format_table(card_rows))

        return self._build_document(Path(file_path), story)
        story.append(Paragraph(
            f"Begründung: {claim.get('evaluation_reason', '-')}", self.normal_style
        ))

        return self._build_document(Path(file_path), story)

    def generate_card_print_pdf(
        self,
        card_id: int,
        file_path: Optional[str] = None,
    ) -> str:
        card = self.card_service.get_card(card_id)
        if card is None:
            raise ValueError("Karte nicht gefunden.")

        if file_path is None:
            filename = f"Kartenausdruck_{card_id}.pdf"
            file_path = str(PDF_ROOT / filename)

        story: list = []
        story.append(Paragraph("Kartenausdruck", self.heading_style))
        story.append(Paragraph(
            f"Kartennummer: {card.get('card_number', '-')}", self.normal_style
        ))
        story.append(Paragraph(
            f"Fallnummer: {card.get('case_number', '-')}", self.normal_style
        ))
        story.append(Paragraph(
            f"Person: {card.get('person_first_name', '-') } {card.get('person_last_name', '-')}", self.normal_style
        ))
        story.append(Paragraph(
            f"Standort: {card.get('location_name', '-')}", self.normal_style
        ))
        story.append(Paragraph(
            f"Ausgestellt: {card.get('issue_date', '-')}", self.normal_style
        ))
        story.append(Paragraph(
            f"Ablauf: {card.get('expiry_date', '-')}", self.normal_style
        ))
        story.append(Paragraph(
            f"Status: {card.get('status', '-')}", self.normal_style
        ))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Hinweise", self.section_style))
        story.append(Paragraph(card.get("note", "-"), self.normal_style))

        return self._build_document(Path(file_path), story)

    def generate_location_report_pdf(
        self,
        location_id: Optional[int] = None,
        file_path: Optional[str] = None,
    ) -> str:
        report = self.report_service.get_location_report(location_id)
        if file_path is None:
            location_part = report["location_name"].replace(" ", "_")
            file_path = str(PDF_ROOT / f"Standortreport_{location_part}.pdf")

        story: list = []
        story.append(Paragraph("Standortreport", self.heading_style))
        story.append(Paragraph(
            f"Standort: {report['location_name']}", self.normal_style
        ))
        story.append(Paragraph(
            f"Anträge insgesamt: {report['total_claims']}", self.normal_style
        ))
        story.append(Paragraph(
            f"Karten insgesamt: {report['total_cards']}", self.normal_style
        ))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Anspruchsstatus", self.section_style))
        claim_rows = [["Status", "Anzahl"]] + [[item["status"], str(item["count"])] for item in report["claim_status_counts"]]
        story.append(self._format_table(claim_rows, [8 * cm, 8 * cm]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Kartenstatus", self.section_style))
        card_rows = [["Status", "Anzahl"]] + [[item["status"], str(item["count"])] for item in report["card_status_counts"]]
        story.append(self._format_table(card_rows, [8 * cm, 8 * cm]))

        return self._build_document(Path(file_path), story)

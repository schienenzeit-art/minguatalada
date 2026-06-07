"""PDF generation helpers using ReportLab.

This module provides `PDFService` used by the UI to generate various
PDF documents. It is kept minimal and uses services to fetch data.
"""

from __future__ import annotations

from datetime import datetime, date as _date
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, Frame
from reportlab.platypus.tables import TableStyle

from app.config import DATA_DIR
from core.claim_status import ClaimStatus
from core.card_status import CardStatus
from services.claim_service import ClaimService
from services.card_service import CardService
from services.document_service import DocumentService
from services.report_service import ReportService
from database.repositories.person_repository import PersonRepository


PDF_ROOT = DATA_DIR / "pdfs"

# ── Absender (fest hinterlegt, kann über Mandant überschrieben werden) ────────
_ABSENDER_NAME   = "Verein Tischlein Deck Dich Vorarlberg"
_ABSENDER_STR    = "Ladritschweg 10c"
_ABSENDER_PLZORT = "6773 Vandans"
_ABSENDER_EMAIL  = "info@tischleindeckdich-vbg.at"
_ABSENDER_CITY   = "Vandans"


class PDFService:
    def __init__(
        self,
        claim_service: ClaimService,
        card_service: CardService | None = None,
        document_service: DocumentService | None = None,
        report_service: ReportService | None = None,
    ):
        self.document_service = document_service or DocumentService()
        self.person_repository = PersonRepository()
        self.claim_service = claim_service
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
        story.append(Paragraph(f"Status: {ClaimStatus.get_display(claim.get('status') or '')  or '-'}", self.normal_style))
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

        story.append(Paragraph(f"Status: {ClaimStatus.get_display(claim.get('status') or '') or '-'}", self.normal_style))
        story.append(Paragraph(f"Begründung: {claim.get('evaluation_reason') or '-'}", self.normal_style))
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

    def generate_person_dossier_pdf(
        self,
        person_id: int,
        file_path: Optional[str] = None,
    ) -> str:
        person = self.person_repository.get_person_by_id(person_id)
        if person is None:
            raise ValueError("Person nicht gefunden.")

        claims = self.claim_service.list_claims(person_id=person_id)
        documents = self.document_service.list_documents(person_id=person_id)

        if file_path is None:
            file_path = str(PDF_ROOT / f"Dossier_Person_{person_id}.pdf")

        story: list = []
        story.append(Paragraph("Personendossier", self.heading_style))
        story.append(Paragraph(f"Name: {person.get('first_name','-')} {person.get('last_name','-')}", self.normal_style))
        story.append(Paragraph(f"Adresse: {person.get('address','-')}", self.normal_style))
        story.append(Paragraph(f"Ort: {person.get('postal_code','-')} {person.get('city','-')}", self.normal_style))
        story.append(Paragraph(f"E-Mail: {person.get('email','-')}", self.normal_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Fälle", self.section_style))
        if claims:
            claim_rows = [["Fallnummer", "Status", "Kategorie", "Standort"]]
            for claim in claims:
                claim_rows.append([
                    claim.get("case_number", "-"),
                    ClaimStatus.get_display(claim.get("status") or "") or "-",
                    claim.get("category_name", "-"),
                    claim.get("location_name", "-"),
                ])
            story.append(self._format_table(claim_rows, [120, 110, 110, 110]))
        else:
            story.append(Paragraph("Keine zugeordneten Fälle.", self.normal_style))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Dokumente", self.section_style))
        if documents:
            doc_rows = [["Titel", "Typ", "Hochgeladen", "Status"]]
            for doc in documents:
                doc_rows.append([
                    doc.get("title", "-"),
                    doc.get("document_type_name", "-"),
                    doc.get("uploaded_at", "-"),
                    doc.get("status", "-"),
                ])
            story.append(self._format_table(doc_rows, [160, 120, 120, 100]))
        else:
            story.append(Paragraph("Keine Dokumente vorhanden.", self.normal_style))

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
        story.append(Paragraph(f"Status: {ClaimStatus.get_display(claim.get('status') or '') or '-'}", self.normal_style))
        story.append(Paragraph(f"Begründung: {claim.get('evaluation_reason') or '-'}", self.normal_style))

        return self._build_document(Path(file_path), story)

    def generate_customer_report_pdf(
        self,
        location_id: Optional[int],
        year: int,
        month: int,
        file_path: Optional[str] = None,
    ) -> str:
        report = self.report_service.get_customer_monthly_report(location_id, year, month)
        location_part = report["location_name"].replace(" ", "_")
        if file_path is None:
            file_path = str(PDF_ROOT / f"Kundenbestand_{location_part}_{year}_{month:02d}.pdf")

        story: list = []
        story.append(Paragraph("Monatsreport Kundenbestand", self.heading_style))
        story.append(Paragraph(f"Standort: {report['location_name']}", self.normal_style))
        story.append(Paragraph(f"Monat: {report['report_month']}", self.normal_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Neukunden im Monat", self.section_style))
        story.append(Paragraph(str(report["new_customers"]), self.normal_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Gesamtbestand Kunden", self.section_style))
        story.append(Paragraph(str(report["total_customers"]), self.normal_style))

        return self._build_document(Path(file_path), story)

    def generate_period_report_pdf(
        self,
        location_id: Optional[int],
        start_date: str,
        end_date: str,
        selected_metrics: list[str] | None = None,
        file_path: Optional[str] = None,
    ) -> str:
        report = self.report_service.get_period_report(start_date, end_date, location_id)
        if file_path is None:
            location_part = report["location_name"].replace(" ", "_")
            file_path = str(PDF_ROOT / f"Zeitraumreport_{location_part}_{start_date}_{end_date}.pdf")

        if selected_metrics is None:
            selected_metrics = [
                "applications",
                "evaluations",
                "approved",
                "rejected",
                "hardship",
                "cards",
            ]

        story: list = []
        story.append(Paragraph("Zeitraumreport", self.heading_style))
        story.append(Paragraph(f"Standort: {report['location_name']}", self.normal_style))
        story.append(Paragraph(f"Zeitraum: {report['start_date']} bis {report['end_date']}", self.normal_style))
        story.append(Spacer(1, 12))

        metric_rows = [["Kennzahl", "Wert"]]
        if "applications" in selected_metrics:
            metric_rows.append(["Anträge", str(report["total_applications"])])
        if "evaluations" in selected_metrics:
            metric_rows.append(["Prüfungen", str(report["total_evaluations"])])
        if "approved" in selected_metrics:
            metric_rows.append(["anspruchsberechtigte", str(report["approved_claims"])])
        if "rejected" in selected_metrics:
            metric_rows.append(["abgelehnte", str(report["rejected_claims"])])
        if "hardship" in selected_metrics:
            metric_rows.append(["Härtefälle", str(report["hardship_claims"])])

        if len(metric_rows) > 1:
            story.append(self._format_table(metric_rows))
            story.append(Spacer(1, 12))

        if "cards" in selected_metrics and report["cards_by_location"]:
            story.append(Paragraph("Kundenstamm pro Laden", self.section_style))
            card_rows = [["Standort", "Karten im Zeitraum"]]
            for item in report["cards_by_location"]:
                card_rows.append([item.get("location_name", "-"), str(item.get("card_count", 0))])
            story.append(self._format_table(card_rows))

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
            f"Status: {CardStatus.get_status_display_name(card.get('status') or '') or '-'}", self.normal_style
        ))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Hinweise", self.section_style))
        story.append(Paragraph(card.get("note") or "-", self.normal_style))

        return self._build_document(Path(file_path), story)

    # ── Fensterbrief (Brief / Bescheid nach österreichischem Standard) ────────
    def generate_letter_pdf(
        self,
        template_id: int,
        context: dict,
        file_path: Optional[str] = None,
    ) -> str:
        """Generiert einen druckfertigen Bescheid/Brief als Fensterbrief-PDF.

        Adressblock liegt im österreichischen Sichtfensterbereich
        (ca. 20–95 mm von links, 40–80 mm von oben) für DL-Umschläge.
        """
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.styles import ParagraphStyle as PS

        from services.document_template_service import DocumentTemplateService
        svc = DocumentTemplateService()
        rendered = svc.render(template_id, context)

        if file_path is None:
            tpl = svc.get_template(template_id)
            safe = (tpl.get("name") or "Brief").replace(" ", "_")
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = str(PDF_ROOT / f"Brief_{safe}_{ts}.pdf")

        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        w, h = A4   # 595.28 pt × 841.89 pt
        c = rl_canvas.Canvas(str(file_path), pagesize=A4)

        # ── Trennlinie Adressfenster (unsichtbar für Druck, Hilfsline deaktiviert) ─

        # ── Absender-Rücksendevermerklinie (8pt, grau, über Empfängerfenster) ──
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.45, 0.45, 0.45)
        c.drawString(
            20*mm, h - 36*mm,
            f"{_ABSENDER_NAME} · {_ABSENDER_STR} · {_ABSENDER_PLZORT}",
        )

        # ── Empfänger-Adressblock (Fensterzone: x=20–95mm, y=40–80mm von oben) ─
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 11)
        addr_lines = [
            f"{context.get('VORNAME','')} {context.get('NACHNAME','')}".strip(),
            context.get("ADRESSE", ""),
            f"{context.get('PLZ','')} {context.get('ORT','')}".strip(),
        ]
        y_addr = h - 50*mm
        for line in addr_lines:
            line = line.strip()
            if line:
                c.drawString(20*mm, y_addr, line)
                y_addr -= 6.5*mm

        # ── Absender-Block rechts ─────────────────────────────────────────────
        c.setFont("Helvetica-Bold", 10)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(120*mm, h - 22*mm, _ABSENDER_NAME)
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawString(120*mm, h - 28*mm, _ABSENDER_STR)
        c.drawString(120*mm, h - 33.5*mm, _ABSENDER_PLZORT)
        c.drawString(120*mm, h - 39*mm, _ABSENDER_EMAIL)

        # ── Ort und Datum (rechtsbündig) ──────────────────────────────────────
        datum = context.get("DATUM", _date.today().strftime("%d.%m.%Y"))
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0, 0, 0)
        c.drawRightString(190*mm, h - 96*mm, f"{_ABSENDER_CITY}, {datum}")

        # ── Aktenzeichen / Betreff ────────────────────────────────────────────
        betreff = context.get("BETREFF", context.get("AKTENZEICHEN", ""))
        if betreff:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(20*mm, h - 108*mm, f"Betreff: {betreff}")

        # ── Brieftext (mit automatischem Zeilenumbruch via Platypus Frame) ─────
        body_style = PS(
            "LetterBody",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            spaceAfter=10,
        )
        text_frame = Frame(
            20*mm,          # x
            28*mm,          # y (Unterkante)
            170*mm,         # Breite
            h - 120*mm - 28*mm,  # Höhe (von Unterkante bis Textstart)
            showBoundary=0,
        )
        story = []
        for para in rendered.split("\n\n"):
            para = para.strip()
            if para:
                # HTML-Sonderzeichen escapen, Zeilenumbrüche als <br/>
                para = (para
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace("\n", "<br/>"))
                story.append(Paragraph(para, body_style))
        text_frame.addFromList(story, c)

        c.save()
        return str(file_path)

    def generate_serial_letters_pdf(
        self,
        template_id: int,
        contexts: list[dict],
        file_path: Optional[str] = None,
    ) -> str:
        """Generiert ein Sammel-PDF mit mehreren Briefen (ein Brief pro Seite)."""
        from reportlab.pdfgen import canvas as rl_canvas
        from services.document_template_service import DocumentTemplateService

        svc = DocumentTemplateService()
        if file_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = str(PDF_ROOT / f"Serienbriefe_{ts}.pdf")

        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        w, h = A4
        c = rl_canvas.Canvas(str(file_path), pagesize=A4)

        for i, ctx in enumerate(contexts):
            rendered = svc.render(template_id, ctx)
            self._draw_letter_page(c, ctx, rendered, w, h)
            if i < len(contexts) - 1:
                c.showPage()

        c.save()
        return str(file_path)

    def _draw_letter_page(self, c, context: dict, rendered_text: str, w: float, h: float) -> None:
        """Zeichnet eine Briefseite auf den übergebenen Canvas."""
        from reportlab.lib.styles import ParagraphStyle as PS

        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.45, 0.45, 0.45)
        c.drawString(20*mm, h - 36*mm,
            f"{_ABSENDER_NAME} · {_ABSENDER_STR} · {_ABSENDER_PLZORT}")

        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 11)
        addr_lines = [
            f"{context.get('VORNAME','')} {context.get('NACHNAME','')}".strip(),
            context.get("ADRESSE", ""),
            f"{context.get('PLZ','')} {context.get('ORT','')}".strip(),
        ]
        y_addr = h - 50*mm
        for line in addr_lines:
            line = line.strip()
            if line:
                c.drawString(20*mm, y_addr, line)
                y_addr -= 6.5*mm

        c.setFont("Helvetica-Bold", 10)
        c.drawString(120*mm, h - 22*mm, _ABSENDER_NAME)
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawString(120*mm, h - 28*mm, _ABSENDER_STR)
        c.drawString(120*mm, h - 33.5*mm, _ABSENDER_PLZORT)
        c.drawString(120*mm, h - 39*mm, _ABSENDER_EMAIL)

        datum = context.get("DATUM", _date.today().strftime("%d.%m.%Y"))
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0, 0, 0)
        c.drawRightString(190*mm, h - 96*mm, f"{_ABSENDER_CITY}, {datum}")

        betreff = context.get("BETREFF", context.get("AKTENZEICHEN", ""))
        if betreff:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(20*mm, h - 108*mm, f"Betreff: {betreff}")

        body_style = PS("LetterBody", fontName="Helvetica", fontSize=10, leading=15, spaceAfter=10)
        text_frame = Frame(20*mm, 28*mm, 170*mm, h - 120*mm - 28*mm, showBoundary=0)
        story = []
        for para in rendered_text.split("\n\n"):
            para = para.strip()
            if para:
                para = (para.replace("&", "&amp;").replace("<", "&lt;")
                            .replace(">", "&gt;").replace("\n", "<br/>"))
                story.append(Paragraph(para, body_style))
        text_frame.addFromList(story, c)

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
        claim_rows = [["Status", "Anzahl"]] + [[ClaimStatus.get_display(item["status"]) or item["status"], str(item["count"])] for item in report["claim_status_counts"]]
        story.append(self._format_table(claim_rows))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Kartenstatus", self.section_style))
        card_rows = [["Status", "Anzahl"]] + [[CardStatus.get_status_display_name(item["status"]) or item["status"], str(item["count"])] for item in report["card_status_counts"]]
        story.append(self._format_table(card_rows))

        return self._build_document(Path(file_path), story)

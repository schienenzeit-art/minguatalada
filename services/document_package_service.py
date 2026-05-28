"""DocumentPackageService — baut Dokumentpakete aus Brief + Prüfprotokoll.

Regel:
  Ablehnung (ABGELEHNT, VORLAEFIG_ABGELEHNT) → Bescheid + Prüfprotokoll
  Alle anderen Status → nur Bescheid

Gibt eine geordnete Liste von PDF-Pfaden zurück.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.claim_status import ClaimStatus
from services.document_template_service import DocumentTemplateService, build_claim_context


_STATUS_NEEDS_PROTOCOL = frozenset({
    ClaimStatus.ABGELEHNT,
    ClaimStatus.VORLAEFIG_ABGELEHNT,
    ClaimStatus.HAERTEFALL,
})


class DocumentPackageService:
    """Zentrale Logik für Dokumentpakete: Brief + optionales Prüfprotokoll."""

    def __init__(
        self,
        pdf_service=None,
        template_service: DocumentTemplateService | None = None,
    ):
        self._pdf = pdf_service
        self._tpl = template_service or DocumentTemplateService()

    def _get_pdf(self):
        if self._pdf is None:
            from services.pdf_service import PDFService
            self._pdf = PDFService()
        return self._pdf

    # ── Statusabhängige Vorlage finden ────────────────────────────────────────
    def find_default_template(self, status: str, template_type: str = "BESCHEID") -> dict | None:
        """Findet die Standard-Vorlage für den gegebenen Status."""
        templates = self._tpl.list_templates(include_inactive=False)
        # Zuerst: status_trigger-Match
        for tpl in templates:
            if (tpl.get("status_trigger") == status
                    and tpl.get("template_type") == template_type):
                return tpl
        # Fallback: passende Vorlage per Name
        display = ClaimStatus.get_display(status).lower()
        for tpl in templates:
            if (display in tpl.get("name", "").lower()
                    and tpl.get("template_type") == template_type):
                return tpl
        # Letzter Fallback: erste aktive Vorlage des Typs
        for tpl in templates:
            if tpl.get("template_type") == template_type:
                return tpl
        return None

    # ── Dokumentpaket erstellen ───────────────────────────────────────────────
    def build_package(
        self,
        claim: dict,
        template_id: int | None = None,
        include_protocol: bool | None = None,
    ) -> list[str]:
        """Gibt eine Liste von PDF-Pfaden zurück (Brief + ggf. Prüfprotokoll).

        include_protocol=None → auto-Entscheid basierend auf Status.
        """
        paths: list[str] = []

        ctx    = build_claim_context(claim)
        status = claim.get("status", "")

        # Vorlage
        if template_id is None:
            tpl = self.find_default_template(status)
            if tpl:
                template_id = tpl["id"]

        # Brief-PDF
        if template_id:
            letter_path = self._get_pdf().generate_letter_pdf(template_id, ctx)
            paths.append(letter_path)

        # Prüfprotokoll automatisch beilegen?
        if include_protocol is None:
            include_protocol = status in _STATUS_NEEDS_PROTOCOL

        if include_protocol:
            claim_id = claim.get("id")
            if claim_id:
                try:
                    protocol_path = self._get_pdf().generate_claim_evaluation_pdf(claim_id)
                    paths.append(protocol_path)
                except Exception:
                    pass

        return paths

    def build_package_for_claim_id(
        self,
        claim_id: int,
        claim_service=None,
        template_id: int | None = None,
        include_protocol: bool | None = None,
    ) -> list[str]:
        if claim_service is None:
            from services.claim_service import ClaimService
            claim_service = ClaimService()
        claim = claim_service.get_claim_by_id(claim_id)
        if not claim:
            raise ValueError(f"Antrag {claim_id} nicht gefunden.")
        return self.build_package(claim, template_id, include_protocol)

    # ── Sammel-PDF ───────────────────────────────────────────────────────────
    def merge_pdfs(self, pdf_paths: list[str], output_path: str) -> str:
        """Führt mehrere PDFs zu einem Dokument zusammen (via PyPDF2 oder Fallback)."""
        try:
            from pypdf import PdfWriter
            writer = PdfWriter()
            for p in pdf_paths:
                writer.append(p)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                writer.write(f)
            return output_path
        except ImportError:
            # Fallback: einfach erstes PDF zurückgeben
            return pdf_paths[0] if pdf_paths else ""

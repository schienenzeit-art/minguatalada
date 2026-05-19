from typing import Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGridLayout,
    QScrollArea,
    QInputDialog,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from services.pdf_service import PDFService
from ui.components.page_header import PageHeader
from ui.components.empty_state import EmptyState


class DocumentsPage(QWidget):
    def __init__(self, pdf_service: PDFService | None = None):
        super().__init__()
        self.pdf_service = pdf_service or PDFService()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("documentsPage")
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = PageHeader(
            title="Dokumente",
            subtitle="Erzeugen Sie PDF-Dokumente für Prüfungen, Fallzusammenfassungen und Kartenausdrucke.",
            action_text="PDF erzeugen",
            action_callback=self.open_generate_pdf_menu,
        )
        layout.addWidget(header)

        self.button_grid = QGridLayout()
        self.button_grid.setSpacing(16)

        self._add_document_card(
            0,
            "Prüfungsprotokoll",
            "Erzeugt das Prüfungsprotokoll für einen bestehenden Anspruch.",
            self.on_generate_evaluation_pdf,
        )
        self._add_document_card(
            1,
            "Fallzusammenfassung",
            "Erzeugt eine kompakte Zusammenfassung des Anspruchs.",
            self.on_generate_summary_pdf,
        )
        self._add_document_card(
            2,
            "Kartenausdruck",
            "Erzeugt einen Druck für die Karte eines Anspruchs.",
            self.on_generate_card_pdf,
        )
        self._add_document_card(
            3,
            "Standortreport",
            "Erzeugt einen PDF-Report zu Standortstatistiken.",
            self.on_generate_location_report_pdf,
        )

        content_box = QWidget()
        content_box_layout = QVBoxLayout()
        content_box_layout.setContentsMargins(0, 0, 0, 0)
        content_box_layout.addLayout(self.button_grid)
        content_box_layout.addStretch()
        content_box.setLayout(content_box_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_box)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def _add_document_card(self, index: int, title: str, subtitle: str, callback) -> None:
        card = QWidget()
        card.setObjectName("pageSection")
        card_layout = QVBoxLayout()
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("color: #6b6b6b; font-size: 12px;")

        generate_button = QPushButton("PDF erzeugen")
        generate_button.setObjectName("secondaryButton")
        generate_button.clicked.connect(callback)

        card_layout.addWidget(title_label)
        card_layout.addWidget(subtitle_label)
        card_layout.addStretch()
        card_layout.addWidget(generate_button)
        card.setLayout(card_layout)
        self.button_grid.addWidget(card, index // 2, index % 2)

    def open_generate_pdf_menu(self) -> None:
        QMessageBox.information(
            self,
            "PDF erzeugen",
            "Wählen Sie eine Aktion: Prüfungsprotokoll, Fallzusammenfassung, Kartenausdruck oder Standortreport.",
        )

    def _pick_save_path(self, default_name: str) -> Optional[str]:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "PDF speichern",
            default_name,
            "PDF-Dateien (*.pdf)",
        )
        return file_path if file_path else None

    def on_generate_evaluation_pdf(self) -> None:
        claim_id, ok = QInputDialog.getInt(self, "Prüfungsprotokoll", "Anspruchs-ID:", min=1)
        if not ok:
            return
        file_path = self._pick_save_path(f"Pruefungsprotokoll_{claim_id}.pdf")
        if not file_path:
            return

        try:
            output_path = self.pdf_service.generate_claim_evaluation_pdf(claim_id=claim_id, file_path=file_path)
            QMessageBox.information(self, "PDF erstellt", f"PDF wurde erstellt: {output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"PDF konnte nicht erstellt werden: {e}")

    def on_generate_summary_pdf(self) -> None:
        claim_id, ok = QInputDialog.getInt(self, "Fallzusammenfassung", "Anspruchs-ID:", min=1)
        if not ok:
            return
        file_path = self._pick_save_path(f"Fallzusammenfassung_{claim_id}.pdf")
        if not file_path:
            return

        try:
            output_path = self.pdf_service.generate_case_summary_pdf(claim_id=claim_id, file_path=file_path)
            QMessageBox.information(self, "PDF erstellt", f"PDF wurde erstellt: {output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"PDF konnte nicht erstellt werden: {e}")

    def on_generate_card_pdf(self) -> None:
        card_id, ok = QInputDialog.getInt(self, "Kartenausdruck", "Karten-ID:", min=1)
        if not ok:
            return
        file_path = self._pick_save_path(f"Kartenausdruck_{card_id}.pdf")
        if not file_path:
            return

        try:
            output_path = self.pdf_service.generate_card_print_pdf(card_id=card_id, file_path=file_path)
            QMessageBox.information(self, "PDF erstellt", f"PDF wurde erstellt: {output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"PDF konnte nicht erstellt werden: {e}")

    def on_generate_location_report_pdf(self) -> None:
        location_id, ok = QInputDialog.getInt(self, "Standortreport", "Standort-ID (0 für alle):", value=0, min=0)
        if not ok:
            return
        file_path = self._pick_save_path(f"Standortreport_{location_id or 'Alle'}.pdf")
        if not file_path:
            return

        try:
            output_path = self.pdf_service.generate_location_report_pdf(
                location_id=None if location_id == 0 else location_id,
                file_path=file_path,
            )
            QMessageBox.information(self, "PDF erstellt", f"PDF wurde erstellt: {output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"PDF konnte nicht erstellt werden: {e}")

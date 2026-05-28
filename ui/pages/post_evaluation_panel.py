"""PostEvaluationPanel — Nächste-Schritte-Dialog direkt nach abgeschlossener Prüfung.

Wird nach erfolgreichem `ClaimEvaluationDialog.apply_status()` geöffnet.
Zeigt statusabhängige Aktionen: Drucken, PDF, E-Mail, Karte, Wiedervorlage.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QMessageBox, QSizePolicy, QFrame,
)

from core.claim_status import ClaimStatus


def _open_file(path: str) -> None:
    """Öffnet eine Datei mit dem Standard-Programm des Betriebssystems."""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        import subprocess
        subprocess.Popen(["open", path])
    else:
        import subprocess
        subprocess.Popen(["xdg-open", path])


def _print_file(path: str) -> None:
    """Druckt eine Datei über den Standarddrucker."""
    if sys.platform == "win32":
        os.startfile(path, "print")
    else:
        _open_file(path)


class PostEvaluationPanel(QDialog):
    """Dialog für Folgeaktionen nach abgeschlossener Prüfung."""

    def __init__(
        self,
        claim: dict,
        claim_service=None,
        pdf_service=None,
        card_service=None,
        wiedervorlage_service=None,
        user_mail_service=None,
        document_package_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self._claim   = claim
        self._cs      = claim_service
        self._pdf     = pdf_service
        self._cards   = card_service
        self._wv      = wiedervorlage_service
        self._mail    = user_mail_service
        self._pkg     = document_package_service
        self._pdfs: list[str] = []

        status = ClaimStatus.get_display(claim.get("status", ""))
        self.setWindowTitle(f"Prüfung abgeschlossen – {status}")
        self.setMinimumWidth(540)
        flags = self.windowFlags() | Qt.WindowType.Window
        self.setWindowFlags(flags)
        self._setup_ui()
        self._auto_build_pdfs()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # ── Status-Badge ──────────────────────────────────────────────────────
        status_raw = self._claim.get("status", "")
        status_lbl = ClaimStatus.get_display(status_raw)
        colors = {
            ClaimStatus.ANSPRUCHSBERECHTIGT: ("#e8f8ed", "#1a8f4a", "#b7e4cf"),
            ClaimStatus.HAERTEFALL:          ("#fff7e6", "#9a6700", "#f7d9a3"),
            ClaimStatus.ABGELEHNT:           ("#fdeaea", "#c0362a", "#f5c2c0"),
            ClaimStatus.VORLAEFIG_ABGELEHNT: ("#fdf6e3", "#b8860b", "#f0d9a0"),
        }
        bg, fg, border = colors.get(status_raw, ("#eef3f7", "#334e68", "#d8e2ec"))

        header = QLabel(
            f"<b>Prüfungsergebnis: {status_lbl}</b><br>"
            f"<span style='font-size:12px;color:#555;'>"
            f"Fall: {self._claim.get('case_number','–')} · "
            f"Person: {self._claim.get('person_first_name','')} "
            f"{self._claim.get('person_last_name','')}"
            f"</span>"
        )
        header.setStyleSheet(
            f"background:{bg}; color:{fg}; border:1px solid {border}; "
            f"border-radius:8px; padding:12px 16px;"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # ── Druck- und PDF-Aktionen ────────────────────────────────────────────
        print_box = QGroupBox("Drucken & PDF")
        print_layout = QHBoxLayout(print_box)
        print_layout.setSpacing(10)

        self._btn_print_letter = self._action_btn("Bescheid drucken", self._print_letter)
        self._btn_save_pdf     = self._action_btn("Als PDF speichern", self._save_pdf)
        self._btn_open_pdf     = self._action_btn("PDF öffnen", self._open_pdf)
        self._btn_print_proto  = self._action_btn("Prüfprotokoll drucken", self._print_protocol)

        for btn in [self._btn_print_letter, self._btn_save_pdf,
                    self._btn_open_pdf, self._btn_print_proto]:
            print_layout.addWidget(btn)
        layout.addWidget(print_box)

        # ── Kommunikation ─────────────────────────────────────────────────────
        comm_box = QGroupBox("Kommunikation")
        comm_layout = QHBoxLayout(comm_box)
        comm_layout.setSpacing(10)

        email = self._claim.get("person_email", "") or ""
        self._btn_send_mail = self._action_btn("Per E-Mail senden", self._send_email)
        self._btn_send_mail.setEnabled(bool(email))
        self._btn_send_mail.setToolTip(
            f"An: {email}" if email else "Keine E-Mail-Adresse hinterlegt"
        )
        comm_layout.addWidget(self._btn_send_mail)
        comm_layout.addStretch()
        layout.addWidget(comm_box)

        # ── Folgeaktionen ─────────────────────────────────────────────────────
        follow_box = QGroupBox("Folgeaktionen")
        follow_layout = QHBoxLayout(follow_box)
        follow_layout.setSpacing(10)

        eligible = self._claim.get("status", "") in (
            ClaimStatus.ANSPRUCHSBERECHTIGT, ClaimStatus.HAERTEFALL
        )
        self._btn_create_card = self._action_btn("Karte erstellen", self._create_card)
        self._btn_create_card.setEnabled(eligible)
        self._btn_create_card.setToolTip(
            "Karte erstellen" if eligible else "Nur für Anspruchsberechtigte und Härtefälle"
        )

        self._btn_wiedervorlage = self._action_btn("Wiedervorlage setzen", self._set_wiedervorlage)

        for btn in [self._btn_create_card, self._btn_wiedervorlage]:
            follow_layout.addWidget(btn)
        follow_layout.addStretch()
        layout.addWidget(follow_box)

        # ── Schließen ─────────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton("Schließen")
        close_btn.setObjectName("SoftButton")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

    @staticmethod
    def _action_btn(label: str, slot) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("SoftButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(slot)
        return btn

    # ── PDF-Vorbereitung ──────────────────────────────────────────────────────
    def _auto_build_pdfs(self) -> None:
        """Baut automatisch das Dokumentpaket (Brief + ggf. Protokoll)."""
        try:
            if self._pkg:
                self._pdfs = self._pkg.build_package(self._claim)
            elif self._pdf:
                claim_id = self._claim.get("id")
                if claim_id:
                    self._pdfs = [self._pdf.generate_claim_evaluation_pdf(claim_id)]
        except Exception:
            pass

    def _get_pdf(self):
        if self._pdf is None:
            from services.pdf_service import PDFService
            self._pdf = PDFService()
        return self._pdf

    def _ensure_pdfs(self) -> bool:
        if not self._pdfs:
            self._auto_build_pdfs()
        if not self._pdfs:
            QMessageBox.warning(self, "Keine PDFs", "Keine PDF-Dokumente konnten erstellt werden.")
            return False
        return True

    # ── Aktionen ──────────────────────────────────────────────────────────────
    def _print_letter(self):
        if not self._ensure_pdfs():
            return
        try:
            _print_file(self._pdfs[0])
        except Exception as exc:
            QMessageBox.critical(self, "Druckfehler", str(exc))

    def _print_protocol(self):
        try:
            claim_id = self._claim.get("id")
            if not claim_id:
                return
            path = self._get_pdf().generate_claim_evaluation_pdf(claim_id)
            _print_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Druckfehler", str(exc))

    def _open_pdf(self):
        if not self._ensure_pdfs():
            return
        try:
            _open_file(self._pdfs[0])
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", str(exc))

    def _save_pdf(self):
        from PyQt6.QtWidgets import QFileDialog
        if not self._ensure_pdfs():
            return
        case_number = self._claim.get("case_number", "Brief").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF speichern",
            f"Bescheid_{case_number}.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return
        import shutil
        shutil.copy2(self._pdfs[0], path)
        if len(self._pdfs) > 1:
            # Prüfprotokoll ebenfalls speichern
            proto_path = path.replace(".pdf", "_Pruefprotokoll.pdf")
            shutil.copy2(self._pdfs[1], proto_path)
            QMessageBox.information(self, "Gespeichert",
                f"Bescheid: {path}\nPrüfprotokoll: {proto_path}")
        else:
            QMessageBox.information(self, "Gespeichert", f"Gespeichert unter:\n{path}")

    def _send_email(self):
        email = self._claim.get("person_email", "") or ""
        if not email:
            QMessageBox.warning(self, "Keine E-Mail", "Keine E-Mail-Adresse für diese Person hinterlegt.")
            return
        if not self._ensure_pdfs():
            return
        try:
            svc = self._mail
            if svc is None:
                from services.user_mail_service import UserMailService
                svc = UserMailService()
            name = f"{self._claim.get('person_first_name','')} {self._claim.get('person_last_name','')}".strip()
            status_display = ClaimStatus.get_display(self._claim.get("status", ""))
            svc.send_document_mail(
                to_email=email,
                person_name=name,
                subject=f"Bescheid – Antrag {self._claim.get('case_number','')}: {status_display}",
                html_body=(
                    f"<p>Sehr geehrte/r {name},</p>"
                    f"<p>anbei erhalten Sie den Bescheid zu Ihrem Antrag "
                    f"(Aktenzeichen: {self._claim.get('case_number','')}).</p>"
                    f"<p>Ergebnis: <strong>{status_display}</strong></p>"
                ),
                pdf_paths=self._pdfs,
            )
            QMessageBox.information(self, "Gesendet", f"E-Mail erfolgreich an {email} gesendet.")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"E-Mail konnte nicht gesendet werden:\n{exc}")

    def _create_card(self):
        from PyQt6.QtWidgets import QInputDialog
        from datetime import date, timedelta
        claim_id = self._claim.get("id")
        if not claim_id:
            return
        # Standardmäßig 1 Jahr Gültigkeit vorschlagen
        default_expiry = (date.today() + timedelta(days=365)).strftime("%d.%m.%Y")
        expiry, ok = QInputDialog.getText(
            self, "Karte erstellen",
            "Ablaufdatum der Karte (TT.MM.JJJJ):",
            text=default_expiry,
        )
        if not ok:
            return
        try:
            from datetime import datetime
            expiry_iso = datetime.strptime(expiry.strip(), "%d.%m.%Y").strftime("%Y-%m-%d")
            from core.session import Session
            cards = self._cards
            if cards is None:
                from services.card_service import CardService
                cards = CardService()
            cards.create_card(
                claim_id=claim_id,
                person_id=self._claim.get("person_id"),
                location_id=self._claim.get("location_id"),
                issue_date=date.today().strftime("%Y-%m-%d"),
                expiry_date=expiry_iso,
                created_by=Session.get_user_id() or 0,
            )
            QMessageBox.information(self, "Karte erstellt", f"Kundenkarte bis {expiry} erstellt.")
        except ValueError:
            QMessageBox.warning(self, "Fehler", "Ungültiges Datum. Bitte TT.MM.JJJJ eingeben.")
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Karte konnte nicht erstellt werden:\n{exc}")

    def _set_wiedervorlage(self):
        from ui.dialogs.wiedervorlage_dialog import WiedervorlageDialog
        dlg = WiedervorlageDialog(
            claim_id=self._claim.get("id"),
            case_number=self._claim.get("case_number", ""),
            wiedervorlage_service=self._wv,
            parent=self,
        )
        dlg.exec()

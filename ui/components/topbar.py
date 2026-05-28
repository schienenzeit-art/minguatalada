from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMenu, QFrame, QVBoxLayout, QScrollArea, QSizePolicy,
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QTimer


class TopBar(QWidget):
    user_changed      = pyqtSignal(dict)
    search_requested  = pyqtSignal(str)
    notification_read = pyqtSignal(int)

    def __init__(self, title: str = "Dashboard", current_user: dict | None = None):
        super().__init__()
        self.title           = title
        self.current_user    = current_user
        self.available_users = []
        self._notification_service   = None
        self._doc_claim_service      = None
        self._doc_template_service   = None
        self._doc_pdf_service        = None
        self._unread_count   = 0
        self.setup_ui()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────────
    def setup_ui(self):
        self.setObjectName("topBar")
        self.setMinimumHeight(58)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 20, 10)
        layout.setSpacing(10)

        self.page_title = QLabel(self.title)
        self.page_title.setObjectName("pageTitle")
        self.page_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Suche …")
        self.search_input.setObjectName("topbarSearch")
        self.search_input.setMaximumWidth(300)
        self.search_input.returnPressed.connect(self._on_search)

        # ── Benachrichtigungs-Bell mit Badge-Overlay ───────────────────────────
        # Container hält Bell-Button + Badge als überlagerte Widgets
        self._bell_container = QWidget()
        self._bell_container.setFixedSize(44, 44)
        self._bell_container.setStyleSheet("background: transparent;")

        self.bell_button = QPushButton("🔔", self._bell_container)
        self.bell_button.setObjectName("bellButton")
        self.bell_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bell_button.setFixedSize(36, 36)
        self.bell_button.move(0, 8)
        self.bell_button.setToolTip("Benachrichtigungen")
        self.bell_button.clicked.connect(self._show_notifications)
        self.bell_button.setStyleSheet(
            "QPushButton#bellButton { background: transparent; border: none; "
            "font-size: 20px; padding: 0px; }"
            "QPushButton#bellButton:hover { background: rgba(0,0,0,0.06); border-radius: 8px; }"
        )

        self._badge = QLabel(self._bell_container)
        self._badge.setFixedSize(18, 18)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setStyleSheet(
            "background: #e53935; color: #fff; border-radius: 9px; "
            "font-size: 9px; font-weight: 800; border: 2px solid #fff;"
        )
        self._badge.move(22, 0)
        self._badge.hide()
        self._badge.raise_()

        # ── Dokument-Button ────────────────────────────────────────────────────
        self._doc_button = QPushButton("Dokument")
        self._doc_button.setObjectName("topbarButton")
        self._doc_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._doc_button.setToolTip("Brief, Bescheid oder Sonstiges erstellen")
        self._doc_button.clicked.connect(self._show_document_menu)

        # ── Benutzer-Button ────────────────────────────────────────────────────
        self.avatar_button = QPushButton(self._get_user_display_name())
        self.avatar_button.setObjectName("topbarButton")
        self.avatar_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_button.clicked.connect(self._show_user_menu)

        layout.addWidget(self.page_title)
        layout.addStretch()
        layout.addWidget(self.search_input)
        layout.addWidget(self._doc_button)
        layout.addWidget(self._bell_container)
        layout.addWidget(self.avatar_button)

    # ── Dokument-Services binden ──────────────────────────────────────────────
    def set_document_services(self, claim_service=None, template_service=None, pdf_service=None) -> None:
        self._doc_claim_service    = claim_service
        self._doc_template_service = template_service
        self._doc_pdf_service      = pdf_service

    def _show_document_menu(self) -> None:
        from core.case_context import CaseContext
        menu = QMenu(self)
        menu.setMinimumWidth(240)

        # ── Aktuelle-Fall-Aktionen (nur wenn Fall aktiv) ──────────────────────
        if CaseContext.is_active():
            case_no = CaseContext.get_case_number()
            header = menu.addAction(f"Aktueller Fall: {case_no}")
            header.setEnabled(False)
            menu.addSeparator()
            menu.addAction("Drucken …").triggered.connect(self._print_current_claim)
            menu.addAction("Wiedervorlage setzen …").triggered.connect(self._set_wiedervorlage)
            menu.addAction("Karte erstellen …").triggered.connect(self._create_card_for_claim)
            menu.addAction("Per E-Mail senden …").triggered.connect(self._mail_current_claim)
            menu.addSeparator()

        menu.addAction("Bescheid erstellen …").triggered.connect(
            lambda: self._open_letter_wizard("BESCHEID"))
        menu.addAction("Brief erstellen …").triggered.connect(
            lambda: self._open_letter_wizard("BRIEF"))
        menu.addAction("Sonstiges Dokument …").triggered.connect(
            lambda: self._open_letter_wizard(None))
        menu.addSeparator()
        menu.addAction("Serienbriefe …").triggered.connect(self._open_serial_letters)
        menu.exec(self._doc_button.mapToGlobal(self._doc_button.rect().bottomLeft()))

    def _print_current_claim(self) -> None:
        from core.case_context import CaseContext
        claim = CaseContext.get_claim()
        if not claim:
            return
        try:
            from services.document_package_service import DocumentPackageService
            import os, sys
            pkgs = DocumentPackageService().build_package(claim)
            for p in pkgs:
                if sys.platform == "win32":
                    os.startfile(p, "print")
                else:
                    os.startfile(p) if hasattr(os, "startfile") else None
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", str(exc))

    def _set_wiedervorlage(self) -> None:
        from core.case_context import CaseContext
        from ui.dialogs.wiedervorlage_dialog import WiedervorlageDialog
        dlg = WiedervorlageDialog(
            claim_id=CaseContext.get_claim_id(),
            case_number=CaseContext.get_case_number(),
            parent=self,
        )
        dlg.exec()

    def _create_card_for_claim(self) -> None:
        from core.case_context import CaseContext
        claim = CaseContext.get_claim()
        if not claim:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Hinweis", "Kein aktiver Fall.")
            return
        try:
            from ui.pages.post_evaluation_panel import PostEvaluationPanel
            panel = PostEvaluationPanel(claim=claim, parent=self)
            panel._create_card()
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", str(exc))

    def _mail_current_claim(self) -> None:
        from core.case_context import CaseContext
        claim = CaseContext.get_claim()
        if not claim:
            return
        email = claim.get("person_email", "") or ""
        from PyQt6.QtWidgets import QInputDialog
        to, ok = QInputDialog.getText(self, "E-Mail senden",
                                       "Empfänger-E-Mail:", text=email)
        if not ok or not to.strip():
            return
        try:
            from services.document_package_service import DocumentPackageService
            from services.user_mail_service import UserMailService
            pkgs = DocumentPackageService().build_package(claim)
            name = f"{claim.get('person_first_name','')} {claim.get('person_last_name','')}".strip()
            UserMailService().send_document_mail(
                to_email=to.strip(), person_name=name,
                subject=None, html_body=None, pdf_paths=pkgs,
            )
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Gesendet", f"E-Mail an {to.strip()} gesendet.")
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Fehler", str(exc))

    def _open_letter_wizard(self, template_type: str | None) -> None:
        from ui.dialogs.letter_wizard_dialog import LetterWizardDialog
        from core.case_context import CaseContext
        dlg = LetterWizardDialog(
            template_type=template_type,
            claim_service=self._doc_claim_service,
            template_service=self._doc_template_service,
            pdf_service=self._doc_pdf_service,
            initial_claim=CaseContext.get_claim(),   # aktuellen Fall vorausfüllen
            parent=self,
        )
        dlg.exec()

    def _open_serial_letters(self) -> None:
        try:
            from ui.pages.serial_letters_page import SerialLettersDialog
            dlg = SerialLettersDialog(
                claim_service=self._doc_claim_service,
                template_service=self._doc_template_service,
                pdf_service=self._doc_pdf_service,
                parent=self,
            )
            dlg.exec()
        except Exception as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", str(exc))

    # ── Notification-Service binden ───────────────────────────────────────────
    def set_notification_service(self, svc) -> None:
        self._notification_service = svc
        # Poll für Badge-Update alle 60 Sekunden
        timer = QTimer(self)
        timer.timeout.connect(self._refresh_badge)
        timer.start(60_000)
        self._refresh_badge()

    def _refresh_badge(self) -> None:
        if self._notification_service is None:
            return
        try:
            count = self._notification_service.count_unread()
        except Exception:
            count = 0
        self._unread_count = count
        if count > 0:
            text = str(count) if count <= 99 else "99+"
            self._badge.setText(text)
            self._badge.show()
            self._badge.raise_()
        else:
            self._badge.hide()

    # ── Notifications-Dropdown ────────────────────────────────────────────────
    def _show_notifications(self) -> None:
        menu = QMenu(self)
        menu.setMinimumWidth(340)

        if self._notification_service is None:
            menu.addAction("Kein Benachrichtigungsdienst verfügbar").setEnabled(False)
            menu.exec(self._bell_container.mapToGlobal(self._bell_container.rect().bottomLeft()))
            return

        notifications = self._notification_service.get_notifications(limit=20)
        if not notifications:
            menu.addAction("Keine Benachrichtigungen").setEnabled(False)
        else:
            for n in notifications:
                text  = n.get("title", "")
                msg   = n.get("message", "")
                label = f"{text}" + (f"\n  {msg}" if msg else "")
                is_read = bool(n.get("is_read"))
                action = QAction(label, menu)
                if not is_read:
                    font = action.font()
                    font.setBold(True)
                    action.setFont(font)
                nid = n["id"]
                action.triggered.connect(
                    lambda checked=False, _id=nid: self._on_notification_click(_id)
                )
                menu.addAction(action)

            menu.addSeparator()
            mark_all = menu.addAction("Alle als gelesen markieren")
            mark_all.triggered.connect(self._mark_all_read)

        menu.exec(self._bell_container.mapToGlobal(self._bell_container.rect().bottomLeft()))

    def _on_notification_click(self, notification_id: int) -> None:
        if self._notification_service:
            self._notification_service.mark_read(notification_id)
            self._refresh_badge()
        self.notification_read.emit(notification_id)

    def _mark_all_read(self) -> None:
        if self._notification_service:
            self._notification_service.mark_all_read()
            self._refresh_badge()

    # ── Benutzerverwaltung (kein Wechsel – nur Abmelden) ─────────────────────
    def _get_user_display_name(self) -> str:
        if self.current_user:
            return self.current_user.get("full_name", "Benutzer")[:22]
        return "Benutzer"

    def set_current_user(self, user: dict) -> None:
        self.current_user = user
        self.avatar_button.setText(self._get_user_display_name())

    def set_available_users(self, users: list[dict]) -> None:
        # Benutzerwechsel ist deaktiviert — diese Methode ist ein No-op.
        pass

    def _show_user_menu(self) -> None:
        """Zeigt nur Benutzerinfo und Abmelden — kein Benutzerwechsel erlaubt."""
        menu = QMenu(self)
        user = self.current_user or {}
        role = user.get("role_name", "")
        location = user.get("location_name", "")

        info = menu.addAction(f"{user.get('full_name','–')}  ·  {role}")
        info.setEnabled(False)
        if location:
            loc_action = menu.addAction(f"Standort: {location}")
            loc_action.setEnabled(False)
        menu.addSeparator()
        menu.addAction("Abmelden").triggered.connect(self._on_logout)
        menu.exec(self.avatar_button.mapToGlobal(self.avatar_button.rect().bottomLeft()))

    def _on_logout(self) -> None:
        self.user_changed.emit({"logout": True})

    def _on_search(self) -> None:
        text = self.search_input.text().strip()
        if text:
            self.search_requested.emit(text)

    def set_title(self, title: str) -> None:
        self.page_title.setText(title)

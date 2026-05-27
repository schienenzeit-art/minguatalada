from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

from services.auth_service import AuthService
from services.user_service import UserService
from core.session import Session

# Pfad zum Logo (relativ zum Projektstamm, funktioniert auch im PyInstaller-Bundle)
def _logo_path() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        import sys as _sys
        base = Path(_sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "assets" / "logo.png"


class LoginWindow(QDialog):
    def __init__(self, auth_service: AuthService | None = None, user_service: UserService | None = None):
        super().__init__()
        self.auth_service = auth_service or AuthService()
        self.user_service = user_service or UserService()
        self.current_user = None
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("loginDialog")
        self.setWindowTitle("Min Guata Lada — Anmeldung")
        self.setMinimumSize(460, 560)
        self.setModal(True)

        # App-Icon im Fenster-Titelbereich
        icon_path = _logo_path()
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(0)

        card = QFrame()
        card.setObjectName("LoginCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(16)

        # ── Logo ──────────────────────────────────────────────────────────────
        logo_container = QHBoxLayout()
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(
                220, 110,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(pix)
        else:
            # Fallback: Textlogo wenn Bild fehlt
            logo_label.setText("MIN GUATA LADA")
            logo_label.setStyleSheet(
                "font-size: 22px; font-weight: 900; color: #c0392b; letter-spacing: -0.02em;"
            )
        logo_container.addWidget(logo_label)
        card_layout.addLayout(logo_container)

        # ── Trennlinie ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #ebebea; border: none; max-height: 1px; margin: 4px 0;")
        card_layout.addWidget(sep)

        # ── Titel ─────────────────────────────────────────────────────────────
        title_label = QLabel("Willkommen zurück")
        title_label.setObjectName("PageTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Tischlein Deck Dich Vorarlberg — Anspruchsverwaltung")
        subtitle_label.setObjectName("PageSubtitle")
        subtitle_label.setWordWrap(True)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title_label)
        card_layout.addWidget(subtitle_label)

        # ── Felder ────────────────────────────────────────────────────────────
        user_lbl = QLabel("Benutzername")
        user_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #4a4845;")
        self.username_input = QLineEdit()
        self.username_input.setObjectName("loginInput")
        self.username_input.setPlaceholderText("Benutzername eingeben")
        self.username_input.returnPressed.connect(self.on_login_clicked)

        pw_lbl = QLabel("Passwort")
        pw_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #4a4845;")
        self.password_input = QLineEdit()
        self.password_input.setObjectName("loginInput")
        self.password_input.setPlaceholderText("Passwort eingeben")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.on_login_clicked)

        self.login_button = QPushButton("Anmelden")
        self.login_button.setObjectName("PrimaryButton")
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.setMinimumHeight(46)
        self.login_button.clicked.connect(self.on_login_clicked)

        card_layout.addWidget(user_lbl)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(pw_lbl)
        card_layout.addWidget(self.password_input)
        card_layout.addSpacing(4)
        card_layout.addWidget(self.login_button)

        # ── Fusszeile ─────────────────────────────────────────────────────────
        footer = QLabel("Min Guata Lada · Tischlein Deck Dich Vorarlberg")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #c0bebb; font-size: 11px; margin-top: 8px;")
        card_layout.addWidget(footer)

        root_layout.addStretch()
        root_layout.addWidget(card)
        root_layout.addStretch()

        self.setLayout(root_layout)

    def on_login_clicked(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Eingabe fehlt", "Bitte Benutzername und Passwort eingeben.")
            return

        result = self.auth_service.login(username, password)

        if not result["success"]:
            QMessageBox.warning(self, "Anmeldung fehlgeschlagen", result["message"])
            return

        self.current_user = result["user"]
        Session.set_user(result["user"])

        if result.get("must_change_password"):
            from ui.dialogs.force_password_dialog import ForcePasswordDialog
            dlg = ForcePasswordDialog(user_id=result["user"]["id"], user_service=self.user_service)
            dlg.exec()

        self.accept()

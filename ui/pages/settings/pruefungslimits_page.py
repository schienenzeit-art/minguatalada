from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFormLayout, QDoubleSpinBox,
    QFrame, QScrollArea, QMessageBox,
)

from core.session import Session
from services.settings_service import SettingsService
from ui.components.page_header import PageHeader


class PruefungslimitsPage(QWidget):
    """Dedizierte Seite für Anspruchsgrenzen und Härtefallberechnung."""

    def __init__(self, settings_service: SettingsService | None = None):
        super().__init__()
        self._svc = settings_service or SettingsService()
        self._fields: dict[str, QDoubleSpinBox] = {}
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        layout.addWidget(PageHeader(
            title="Prüfungslimits",
            subtitle="Anspruchsgrenzen und Härtefallmultiplikator für die Anspruchsprüfung.",
        ))

        is_admin = Session.is_admin()

        if not is_admin:
            banner = QLabel(
                "Ansichtsmodus — nur Administratoren dürfen diese Werte ändern."
            )
            banner.setStyleSheet(
                "background: #fff8e1; color: #7a5c00; border: 1px solid #ffe082; "
                "border-radius: 6px; padding: 8px 14px; font-size: 12px;"
            )
            layout.addWidget(banner)

        # ── Anspruchsgrenzen ──────────────────────────────────────────────────
        grp_limits = QGroupBox("Anspruchsgrenzen")
        form_limits = QFormLayout(grp_limits)
        form_limits.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_limits.setHorizontalSpacing(32)
        form_limits.setVerticalSpacing(14)

        self._fields["BASE_LIMIT"] = self._euro_box(0, 9999, is_admin)
        form_limits.addRow("Basisgrenze (€):", self._fields["BASE_LIMIT"])
        form_limits.addRow(
            "",
            self._hint("Grenzwert für eine einzelne erwachsene Person."),
        )

        self._fields["ADDITIONAL_ADULT_LIMIT"] = self._euro_box(0, 9999, is_admin)
        form_limits.addRow("Zuschlag weitere Erwachsene (€):", self._fields["ADDITIONAL_ADULT_LIMIT"])
        form_limits.addRow(
            "",
            self._hint("Wird je weiterer erwachsener Person im Haushalt addiert."),
        )

        self._fields["CHILD_LIMIT"] = self._euro_box(0, 9999, is_admin)
        form_limits.addRow("Zuschlag Kinder (€):", self._fields["CHILD_LIMIT"])
        form_limits.addRow(
            "",
            self._hint("Wird je minderjährigem Kind im Haushalt addiert."),
        )

        layout.addWidget(grp_limits)

        # ── Härtefall ─────────────────────────────────────────────────────────
        grp_hardship = QGroupBox("Härtefallberechnung")
        form_hs = QFormLayout(grp_hardship)
        form_hs.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_hs.setHorizontalSpacing(32)
        form_hs.setVerticalSpacing(14)

        self._fields["HARDSHIP_FACTOR"] = self._factor_box(1.0, 3.0, is_admin)
        form_hs.addRow("Härtefall-Multiplikator:", self._fields["HARDSHIP_FACTOR"])
        form_hs.addRow(
            "",
            self._hint(
                "Die berechnete Anspruchsgrenze wird mit diesem Faktor multipliziert, "
                "um die Härtefallgrenze zu ermitteln."
            ),
        )

        layout.addWidget(grp_hardship)

        # ── Beispielberechnung ────────────────────────────────────────────────
        self._example_frame = QFrame()
        self._example_frame.setObjectName("Card")
        example_layout = QVBoxLayout(self._example_frame)
        example_layout.setContentsMargins(16, 14, 16, 14)
        example_layout.setSpacing(6)

        title_lbl = QLabel("Beispielberechnung (1 Erwachsene + 1 Kind)")
        title_lbl.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        example_layout.addWidget(title_lbl)

        self._lbl_example = QLabel()
        self._lbl_example.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px; color: #444;"
        )
        example_layout.addWidget(self._lbl_example)

        layout.addWidget(self._example_frame)

        # Aktualisierung bei Wertänderung
        for box in self._fields.values():
            box.valueChanged.connect(self._update_example)

        layout.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_reset = QPushButton("Zurücksetzen")
        btn_reset.setObjectName("SoftButton")
        btn_reset.setToolTip("Gespeicherte Werte neu laden")
        btn_reset.clicked.connect(self._load)

        btn_save = QPushButton("Speichern")
        btn_save.setObjectName("PrimaryButton")
        btn_save.setEnabled(is_admin)
        btn_save.clicked.connect(self._save)

        btn_row.addWidget(btn_reset)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Hilfsmethoden ─────────────────────────────────────────────────────────

    @staticmethod
    def _euro_box(min_val: float, max_val: float, enabled: bool) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(min_val, max_val)
        box.setDecimals(2)
        box.setSuffix(" €")
        box.setSingleStep(10.0)
        box.setMinimumWidth(140)
        box.setEnabled(enabled)
        return box

    @staticmethod
    def _factor_box(min_val: float, max_val: float, enabled: bool) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(min_val, max_val)
        box.setDecimals(2)
        box.setSingleStep(0.05)
        box.setMinimumWidth(140)
        box.setEnabled(enabled)
        return box

    @staticmethod
    def _hint(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 11px; color: #888;")
        return lbl

    # ── Daten laden / speichern ───────────────────────────────────────────────

    def _load(self) -> None:
        defaults = {
            "BASE_LIMIT": 820.0,
            "ADDITIONAL_ADULT_LIMIT": 390.0,
            "CHILD_LIMIT": 185.0,
            "HARDSHIP_FACTOR": 1.1,
        }
        for key, default in defaults.items():
            try:
                raw = self._svc.get(key, default)
                self._fields[key].setValue(float(raw))
            except Exception:
                self._fields[key].setValue(default)
        self._update_example()

    def _save(self) -> None:
        if not Session.is_admin():
            QMessageBox.warning(
                self, "Keine Berechtigung",
                "Nur Administratoren dürfen Prüfungslimits ändern."
            )
            return

        changed: list[str] = []
        for key, box in self._fields.items():
            new_val = box.value()
            current = self._svc.get(key)
            try:
                if abs(float(current) - new_val) > 0.001:
                    self._svc.update_setting(key, new_val)
                    changed.append(key)
            except Exception as e:
                QMessageBox.critical(
                    self, "Fehler",
                    f"Einstellung '{key}' konnte nicht gespeichert werden:\n{e}"
                )
                return

        if not changed:
            QMessageBox.information(self, "Keine Änderungen", "Es wurden keine Werte geändert.")
        else:
            QMessageBox.information(
                self, "Gespeichert",
                f"Folgende Einstellungen wurden aktualisiert:\n{', '.join(changed)}"
            )
        self._load()

    def _update_example(self) -> None:
        try:
            base   = self._fields["BASE_LIMIT"].value()
            adult  = self._fields["ADDITIONAL_ADULT_LIMIT"].value()
            child  = self._fields["CHILD_LIMIT"].value()
            factor = self._fields["HARDSHIP_FACTOR"].value()

            # 1 Erwachsene + 1 Kind
            limit = base + child
            hardship = limit * factor

            self._lbl_example.setText(
                f"  Anspruchsgrenze:   {base:.2f} + {child:.2f} = {limit:.2f} €\n"
                f"  Härtefallgrenze:   {limit:.2f} × {factor:.2f} = {hardship:.2f} €\n"
                f"\n"
                f"  2 Erw. + 2 Kinder: {base:.2f} + {adult:.2f} + 2×{child:.2f} = "
                f"{base + adult + 2 * child:.2f} €"
            )
        except Exception:
            pass

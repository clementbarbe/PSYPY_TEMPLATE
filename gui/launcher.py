"""
Minimal experiment menu — sober design.

Flow:
    1. User fills in config (name, session, screen, etc.)
    2. Goes to the task tab
    3. Clicks a design button -> experiment launches directly

No experimental logic here. Only parameter collection.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QSpinBox, QComboBox,
    QCheckBox, QGroupBox, QTabWidget, QPushButton, QMessageBox,
)
from PyQt6.QtGui import QFont

from config.settings import ExperimentSettings
from gui.styles import STYLESHEET
from gui.task_panels import get_registered_panels


class ExperimentMenu(QMainWindow):
    """Main configuration menu."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Experimentale")
        self.setFont(QFont("Segoe UI", 12))
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(600)

        self.final_config = None
        self._build_ui()

    # ═════════════════════════════════════════════════════════════════
    # UI
    # ═════════════════════════════════════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        self._build_config(main)
        self._build_tabs(main)

    def _build_config(self, parent):
        group = QGroupBox("Configuration")
        grid = QGridLayout(group)
        grid.setSpacing(8)
        grid.setContentsMargins(12, 16, 12, 12)

        # ── Row 0: Nom, Session, Ecran, Mode ────────────────────────
        grid.addWidget(QLabel("Nom:"), 0, 0)
        self.txt_nom = QLineEdit()
        self.txt_nom.setPlaceholderText("ID participant")
        self.txt_nom.setFixedWidth(150)
        grid.addWidget(self.txt_nom, 0, 1)

        grid.addWidget(QLabel("Session:"), 0, 2)
        self.spin_session = QSpinBox()
        self.spin_session.setRange(1, 20)
        self.spin_session.setValue(1)
        self.spin_session.setFixedWidth(60)
        grid.addWidget(self.spin_session, 0, 3)

        grid.addWidget(QLabel("Ecran:"), 0, 4)
        self.spin_screen = QSpinBox()
        self.spin_screen.setRange(0, len(QApplication.screens()) - 1)
        self.spin_screen.setValue(0)
        self.spin_screen.setFixedWidth(60)
        grid.addWidget(self.spin_screen, 0, 5)

        grid.addWidget(QLabel("Mode:"), 0, 6)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["PC", "fMRI"])
        self.combo_mode.setFixedWidth(80)
        grid.addWidget(self.combo_mode, 0, 7)

        # ── Row 1: Checkboxes ────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(20)

        self.chk_save = QCheckBox("Enregistrer")
        self.chk_save.setChecked(True)
        row1.addWidget(self.chk_save)

        self.chk_parport = QCheckBox("Port Parallele")
        row1.addWidget(self.chk_parport)

        sep = QLabel("|")
        sep.setStyleSheet("color: #a0a0a0;")
        row1.addWidget(sep)

        self.chk_eyetracker = QCheckBox("Eye Tracker")
        row1.addWidget(self.chk_eyetracker)

        self.btn_et_reset = QPushButton("Force Reset")
        self.btn_et_reset.setObjectName("resetBtn")
        self.btn_et_reset.setFixedWidth(90)
        self.btn_et_reset.clicked.connect(self._force_reset_eyetracker)
        row1.addWidget(self.btn_et_reset)

        row1.addStretch()
        grid.addLayout(row1, 1, 0, 1, 8)

        parent.addWidget(group)

    def _build_tabs(self, parent):
        self.tabs = QTabWidget()

        panels = get_registered_panels()
        if not panels:
            lbl = QLabel("Aucune tache enregistree.")
            lbl.setStyleSheet("padding: 20px; color: #808080;")
            w = QWidget()
            lo = QVBoxLayout(w)
            lo.addWidget(lbl)
            self.tabs.addTab(w, "Vide")
        else:
            for name, panel_cls in panels.items():
                panel = panel_cls(self)
                self.tabs.addTab(panel, name)

        parent.addWidget(self.tabs)

    # ═════════════════════════════════════════════════════════════════
    # Validation + Launch
    # ═════════════════════════════════════════════════════════════════

    def validate_config(self) -> ExperimentSettings | None:
        nom = self.txt_nom.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Nom du participant requis.")
            return None

        # Sanitize
        safe_nom = ''.join(
            c for c in nom if c.isalnum() or c in '-_'
        )
        if not safe_nom:
            QMessageBox.warning(self, "Erreur", "Nom invalide.")
            return None

        mode = self.combo_mode.currentText().lower()

        return ExperimentSettings(
            participant_id=safe_nom,
            session=f"{self.spin_session.value():02d}",
            scanner_name='pc',
            mode=mode,
            fullscreen=(mode == 'fmri'),
            screen_index=self.spin_screen.value(),
            eyetracker_enabled=self.chk_eyetracker.isChecked(),
            trigger_output_enabled=self.chk_parport.isChecked(),
            save_data=self.chk_save.isChecked(),
        )

    def run_experiment(self, task_params: dict):
        """Called by task panels when a design button is clicked."""
        settings = self.validate_config()
        if settings is None:
            return

        self.final_config = {
            'settings': settings,
            'task_name': task_params['task_name'],
            'design_id': task_params.get('design_id', 1),
            'extra_params': task_params.get('extra_params', {}),
        }

        self.close()
        app = QApplication.instance()
        if app:
            app.quit()

    def get_config(self) -> dict | None:
        return self.final_config

    # ═════════════════════════════════════════════════════════════════
    # Eye Tracker Force Reset
    # ═════════════════════════════════════════════════════════════════

    def _force_reset_eyetracker(self):
        """Force reset a stuck EyeLink tracker."""
        reply = QMessageBox.question(
            self, "Force Reset",
            "Reinitialiser l'eye-tracker ?\n"
            "Ceci ferme toute connexion active et reconnecte.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from hardware.eyetracker import EyeTracker
        success, msg = EyeTracker.force_reset()

        if success:
            QMessageBox.information(self, "Eye Tracker", msg)
        else:
            QMessageBox.warning(self, "Eye Tracker", msg)


def show_menu() -> dict | None:
    """
    Show the configuration menu. Block until closed.

    Returns:
        dict with 'settings', 'task_name', 'design_id', 'extra_params'
        or None if user closed without launching.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    menu = ExperimentMenu()
    menu.show()
    app.exec()
    return menu.get_config()
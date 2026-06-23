"""
Minimal experiment menu.

One window, one config group, one tab per task.
Click a design button -> experiment starts.
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QSpinBox, QComboBox,
    QCheckBox, QGroupBox, QTabWidget, QPushButton, QMessageBox,
)

from config.settings import ExperimentSettings
from gui.styles import STYLESHEET
from gui.task_panels import get_registered_panels


class ExperimentMenu(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuration Experimentale")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(520)
        self.final_config = None
        self._build()

    def _build(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Config ───────────────────────────────────────────────────
        cfg = QGroupBox("Configuration")
        g = QGridLayout(cfg)
        g.setSpacing(6)

        g.addWidget(QLabel("Participant :"), 0, 0)
        self.txt_nom = QLineEdit()
        self.txt_nom.setPlaceholderText("ID")
        self.txt_nom.setFixedWidth(130)
        g.addWidget(self.txt_nom, 0, 1)

        g.addWidget(QLabel("Session :"), 0, 2)
        self.spin_ses = QSpinBox()
        self.spin_ses.setRange(1, 20)
        self.spin_ses.setValue(1)
        self.spin_ses.setFixedWidth(55)
        g.addWidget(self.spin_ses, 0, 3)

        g.addWidget(QLabel("Ecran :"), 0, 4)
        self.spin_scr = QSpinBox()
        self.spin_scr.setRange(0, max(0, len(QApplication.screens()) - 1))
        self.spin_scr.setValue(0)
        self.spin_scr.setFixedWidth(55)
        g.addWidget(self.spin_scr, 0, 5)

        g.addWidget(QLabel("Mode :"), 0, 6)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["PC", "fMRI"])
        self.combo_mode.setFixedWidth(70)
        g.addWidget(self.combo_mode, 0, 7)

        row1 = QHBoxLayout()
        row1.setSpacing(16)
        self.chk_save = QCheckBox("Save")
        self.chk_save.setChecked(True)
        row1.addWidget(self.chk_save)

        self.chk_parport = QCheckBox("Port parallele")
        row1.addWidget(self.chk_parport)

        self.chk_et = QCheckBox("Eye-tracker")
        row1.addWidget(self.chk_et)

        self.btn_reset = QPushButton("Force Reset")
        self.btn_reset.setObjectName("resetBtn")
        self.btn_reset.setFixedWidth(85)
        self.btn_reset.clicked.connect(self._reset_et)
        row1.addWidget(self.btn_reset)

        row1.addStretch()
        g.addLayout(row1, 1, 0, 1, 8)

        root.addWidget(cfg)

        # ── Tabs ─────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        panels = get_registered_panels()
        for name, cls in panels.items():
            self.tabs.addTab(cls(self), name)
        root.addWidget(self.tabs)

    # ── Validation + launch ──────────────────────────────────────────

    def validate(self) -> ExperimentSettings | None:
        nom = self.txt_nom.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Nom du participant requis.")
            return None
        safe = ''.join(c for c in nom if c.isalnum() or c in '-_')
        if not safe:
            QMessageBox.warning(self, "Erreur", "Nom invalide.")
            return None
        mode = self.combo_mode.currentText().lower()
        return ExperimentSettings(
            participant_id=safe,
            session=f"{self.spin_ses.value():02d}",
            mode=mode,
            fullscreen=(mode == 'fmri'),
            screen_index=self.spin_scr.value(),
            eyetracker_enabled=self.chk_et.isChecked(),
            trigger_output_enabled=self.chk_parport.isChecked(),
            save_data=self.chk_save.isChecked(),
        )

    def run_experiment(self, task_params: dict):
        settings = self.validate()
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

    def get_config(self):
        return self.final_config

    def _reset_et(self):
        reply = QMessageBox.question(
            self, "Force Reset",
            "Reinitialiser l'eye-tracker ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from hardware.eyetracker import EyeTracker
        ok, msg = EyeTracker.force_reset()
        if ok:
            QMessageBox.information(self, "Eye Tracker", msg)
        else:
            QMessageBox.warning(self, "Eye Tracker", msg)


def show_menu() -> dict | None:
    app = QApplication.instance() or QApplication(sys.argv)
    menu = ExperimentMenu()
    menu.show()
    app.exec()
    return menu.get_config()
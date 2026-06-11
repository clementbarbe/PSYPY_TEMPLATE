"""
PyQt6 experiment launcher with auto-discovered task tabs.

PsychoPy is NOT imported in this module.
Tasks are discovered via the lazy registry (no heavy imports).
"""

from __future__ import annotations

import sys
from typing import Callable

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QLineEdit, QComboBox, QCheckBox,
    QGroupBox, QTabWidget, QPushButton, QStatusBar, QFrame,
    QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize

from config.settings import ExperimentSettings
from config.scanners import list_scanners
from tasks.registry import list_tasks          # no PsychoPy triggered
from gui.styles import DARK_STYLESHEET
from gui.task_panels import get_panel_builder, TaskPanel


class ExperimentLauncher(QMainWindow):
    """
    Main launcher window.

    Collects session parameters, then calls on_start(settings, task, design, params).
    """

    def __init__(
        self,
        on_start: Callable[[ExperimentSettings, str, int, dict], None],
    ):
        super().__init__()
        self._on_start = on_start
        self._task_panels: dict[str, TaskPanel] = {}

        self.setWindowTitle("fMRI Experiment Framework")
        self.setMinimumSize(QSize(620, 580))
        self.setStyleSheet(DARK_STYLESHEET)

        self._build_ui()
        self._center_on_screen()

    # ═════════════════════════════════════════════════════════════════
    # UI Construction
    # ═════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 16, 20, 12)
        main_layout.setSpacing(12)

        # ── Header ───────────────────────────────────────────────────
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        title = QLabel("fMRI Experiment Framework")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        subtitle = QLabel("Multi-scanner cognitive neuroscience toolkit")
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle)

        main_layout.addLayout(header_layout)

        # Separator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        main_layout.addWidget(sep)

        # ── Session parameters ───────────────────────────────────────
        session_group = QGroupBox("Session Parameters")
        sg_layout = QGridLayout(session_group)
        sg_layout.setSpacing(10)

        # Row 0: Participant + Session
        sg_layout.addWidget(
            QLabel("Participant ID:"), 0, 0, Qt.AlignmentFlag.AlignRight
        )
        self._pid_edit = QLineEdit("01")
        self._pid_edit.setMaximumWidth(160)
        self._pid_edit.setPlaceholderText("e.g. 01, P001")
        sg_layout.addWidget(self._pid_edit, 0, 1)

        sg_layout.addWidget(
            QLabel("Session:"), 0, 2, Qt.AlignmentFlag.AlignRight
        )
        self._ses_edit = QLineEdit("01")
        self._ses_edit.setMaximumWidth(80)
        sg_layout.addWidget(self._ses_edit, 0, 3)

        # Row 1: Scanner + Mode
        sg_layout.addWidget(
            QLabel("Scanner:"), 1, 0, Qt.AlignmentFlag.AlignRight
        )
        self._scanner_combo = QComboBox()
        self._scanner_combo.addItems(list_scanners())
        self._scanner_combo.setCurrentText('pc')
        self._scanner_combo.setMaximumWidth(160)
        sg_layout.addWidget(self._scanner_combo, 1, 1)

        sg_layout.addWidget(
            QLabel("Mode:"), 1, 2, Qt.AlignmentFlag.AlignRight
        )
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(['pc', 'fmri'])
        self._mode_combo.setMaximumWidth(100)
        self._scanner_combo.currentTextChanged.connect(
            self._on_scanner_changed
        )
        sg_layout.addWidget(self._mode_combo, 1, 3)

        # Row 2: Hardware flags
        hw_layout = QHBoxLayout()
        hw_layout.setSpacing(30)
        self._et_check = QCheckBox("Eye-tracker")
        self._trigger_check = QCheckBox("TTL triggers")
        hw_layout.addWidget(self._et_check)
        hw_layout.addWidget(self._trigger_check)
        hw_layout.addStretch()
        sg_layout.addLayout(hw_layout, 2, 0, 1, 4)

        main_layout.addWidget(session_group)

        # ── Task tabs ────────────────────────────────────────────────
        self._tab_widget = QTabWidget()
        available_tasks = list_tasks()

        if not available_tasks:
            empty_label = QLabel(
                "No tasks registered.\n"
                "Add register_lazy() calls in tasks/__init__.py."
            )
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_widget = QWidget()
            el = QVBoxLayout(empty_widget)
            el.addWidget(empty_label)
            self._tab_widget.addTab(empty_widget, "No Tasks")
        else:
            for task_name in available_tasks:
                self._add_task_tab(task_name)

        main_layout.addWidget(self._tab_widget, stretch=1)

        # ── Buttons ──────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        quit_btn = QPushButton("Quit")
        quit_btn.setObjectName("quitBtn")
        quit_btn.clicked.connect(self.close)
        btn_layout.addWidget(quit_btn)

        launch_btn = QPushButton("Launch Task")
        launch_btn.setObjectName("launchBtn")
        launch_btn.clicked.connect(self._launch)
        btn_layout.addWidget(launch_btn)

        main_layout.addLayout(btn_layout)

        # ── Status bar ───────────────────────────────────────────────
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage(
            "Ready - select a task and press Launch"
        )

    # ═════════════════════════════════════════════════════════════════
    # Task tabs
    # ═════════════════════════════════════════════════════════════════

    def _add_task_tab(self, task_name: str) -> None:
        builder = get_panel_builder(task_name)
        if builder is not None:
            panel = builder(self._tab_widget, task_name)
        else:
            panel = TaskPanel(self._tab_widget, task_name)

        self._task_panels[task_name] = panel
        display_name = task_name.replace('_', ' ').title()
        self._tab_widget.addTab(panel, f"  {display_name}  ")

    # ═════════════════════════════════════════════════════════════════
    # Callbacks
    # ═════════════════════════════════════════════════════════════════

    def _on_scanner_changed(self, scanner_name: str) -> None:
        if scanner_name.lower() != 'pc':
            self._mode_combo.setCurrentText('fmri')
            self._trigger_check.setChecked(True)
        else:
            self._mode_combo.setCurrentText('pc')
            self._trigger_check.setChecked(False)

    def _get_selected_task_name(self) -> str | None:
        available = list_tasks()
        if not available:
            return None
        idx = self._tab_widget.currentIndex()
        if 0 <= idx < len(available):
            return available[idx]
        return None

    # ═════════════════════════════════════════════════════════════════
    # Launch
    # ═════════════════════════════════════════════════════════════════

    def _launch(self) -> None:
        pid = self._pid_edit.text().strip()
        if not pid:
            QMessageBox.warning(self, "Warning", "Participant ID is required.")
            return

        task_name = self._get_selected_task_name()
        if not task_name:
            QMessageBox.warning(self, "Warning", "No task selected.")
            return

        panel = self._task_panels.get(task_name)
        design_id = panel.selected_design_id if panel else 1
        extra_params = panel.get_extra_params() if panel else {}

        mode = self._mode_combo.currentText()

        settings = ExperimentSettings(
            participant_id=pid,
            session=self._ses_edit.text().strip() or '01',
            scanner_name=self._scanner_combo.currentText(),
            mode=mode,
            fullscreen=(mode == 'fmri'),
            eyetracker_enabled=self._et_check.isChecked(),
            trigger_output_enabled=self._trigger_check.isChecked(),
        )

        confirm = QMessageBox.question(
            self, "Confirm Launch",
            f"Participant: {pid}\n"
            f"Session: {settings.session}\n"
            f"Scanner: {settings.scanner_name}\n"
            f"Mode: {mode}\n"
            f"Task: {task_name}\n"
            f"Design: {design_id}\n\n"
            f"Launch experiment?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._status_bar.showMessage(
            f"Launching {task_name} (design {design_id}) for sub-{pid}..."
        )

        self.close()
        QApplication.processEvents()
        self._on_start(settings, task_name, design_id, extra_params)

    # ═════════════════════════════════════════════════════════════════
    # Helpers
    # ═════════════════════════════════════════════════════════════════

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)


def run_launcher(
    on_start: Callable[[ExperimentSettings, str, int, dict], None],
) -> None:
    """Create QApplication, show launcher, block until closed."""
    app = QApplication(sys.argv)
    app.setApplicationName("fMRI Experiment Framework")
    launcher = ExperimentLauncher(on_start)
    launcher.show()
    app.exec()
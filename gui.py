"""
GUI PyQt6 compact.

- Tâches détectées automatiquement.
- Un onglet par tâche.
- Un bouton direct par design.
- Session toujours "01".
- Plein écran toujours activé.
- Attente trigger toujours activée.
- Écran maximal sélectionné par défaut.
- Seuls l'écran maximal et l'écran précédent sont proposés.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from experiment import sanitize_id
from tasks import list_tasks, load_task_config


STYLESHEET = """
QMainWindow, QWidget#central {
    background-color: #1e1e1e;
}

QGroupBox {
    color: #cccccc;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 10px;
    padding: 12px 8px 8px 8px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}

QLabel {
    color: #cccccc;
}

QLineEdit, QComboBox {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 4px 6px;
    selection-background-color: #264f78;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #0078d4;
}

QCheckBox {
    color: #cccccc;
    spacing: 6px;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
}

QTabWidget::pane {
    border: 1px solid #3c3c3c;
    background-color: #1e1e1e;
    top: -1px;
}

QTabBar::tab {
    background-color: #2d2d2d;
    color: #999999;
    padding: 8px 18px;
    border: 1px solid #3c3c3c;
    border-bottom: none;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 1px;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #e0e0e0;
}

QTabBar::tab:hover:!selected {
    background-color: #252525;
}

QPushButton {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    padding: 5px 14px;
}

QPushButton:hover {
    background-color: #353535;
    border-color: #4c4c4c;
}

QPushButton:pressed {
    background-color: #1a1a1a;
}

QPushButton#run {
    background-color: #0e639c;
    border-color: #1177bb;
    color: white;
    font-weight: bold;
    padding: 6px 18px;
    min-height: 28px;
}

QPushButton#run:hover {
    background-color: #1177bb;
}

QPushButton#run:pressed {
    background-color: #0e639c;
}

QLabel#taskDescription {
    color: #808080;
    font-size: 11px;
    padding: 4px;
}
"""


def available_screen_indices() -> list[int]:
    """
    Retourne uniquement les deux plus grands index des écrans disponibles.

    1 écran  -> [0]
    2 écrans -> [0, 1]
    3 écrans -> [1, 2]
    """
    app = QApplication.instance()

    if app is None:
        return [0]

    count = len(app.screens())

    if count <= 1:
        return [0]

    maximum = count - 1
    return [maximum - 1, maximum]


class TaskPanel(QWidget):
    """Onglet générique créé automatiquement depuis config.yaml."""

    def __init__(self, menu: "ExperimentMenu", task_name: str):
        super().__init__()

        self.menu = menu
        self.task_name = task_name
        self.config = load_task_config(task_name)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        description = self.config.get("description", "")

        if description:
            label = QLabel(description)
            label.setObjectName("taskDescription")
            label.setWordWrap(True)
            layout.addWidget(label)

        group = QGroupBox("Designs")
        grid = QGridLayout(group)
        grid.setSpacing(6)

        designs = self.config.get("designs", {})

        for index, (design_id, design) in enumerate(sorted(designs.items())):
            name = design.get("name", f"Design {design_id}")

            button = QPushButton(f"Design {design_id}")
            button.setObjectName("run")
            button.setToolTip(name)

            button.clicked.connect(
                lambda _checked=False, did=design_id: self.launch(did)
            )

            grid.addWidget(button, index // 2, index % 2)

        layout.addWidget(group)

        summary_lines = []

        for design_id, design in sorted(designs.items()):
            name = design.get("name", f"Design {design_id}")
            blocks = design.get("blocks", [])
            n_blocks = len(blocks)
            n_trials = sum(int(block.get("n_trials", 0)) for block in blocks)

            summary_lines.append(
                f"D{design_id}: {name} — "
                f"{n_blocks} bloc(s), {n_trials} essai(s)"
            )

        if summary_lines:
            summary = QLabel("\n".join(summary_lines))
            summary.setObjectName("taskDescription")
            summary.setWordWrap(True)
            layout.addWidget(summary)

        layout.addStretch()

    def launch(self, design_id: int) -> None:
        self.menu.run_experiment(self.task_name, design_id)


class ExperimentMenu(QMainWindow):
    def __init__(self, settings_path: Path):
        super().__init__()

        self.settings_path = settings_path
        self.final_config: dict | None = None

        self.setWindowTitle("Configuration expérimentale")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(580)
        self.setMinimumHeight(390)

        self._build()

    def _build(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # --------------------------------------------------------------
        # Configuration générale
        # --------------------------------------------------------------

        cfg = QGroupBox("Configuration")
        grid = QGridLayout(cfg)
        grid.setSpacing(6)

        grid.addWidget(QLabel("Participant :"), 0, 0)

        self.participant_input = QLineEdit()
        self.participant_input.setPlaceholderText("ID")
        self.participant_input.setFixedWidth(150)
        grid.addWidget(self.participant_input, 0, 1)

        grid.addWidget(QLabel("Écran :"), 0, 2)

        self.screen_combo = QComboBox()
        self.screen_combo.setFixedWidth(165)
        self._populate_screens()
        grid.addWidget(self.screen_combo, 0, 3)

        options = QHBoxLayout()
        options.setSpacing(16)

        self.save_checkbox = QCheckBox("Sauvegarder")
        self.save_checkbox.setChecked(True)
        options.addWidget(self.save_checkbox)

        self.markers_checkbox = QCheckBox("Marqueurs")
        self.markers_checkbox.setChecked(False)
        options.addWidget(self.markers_checkbox)

        options.addStretch()
        grid.addLayout(options, 1, 0, 1, 4)

        hint = QLabel(
            "Session fixe : 01   |   "
            "Plein écran et attente du trigger activés systématiquement."
        )
        hint.setObjectName("taskDescription")
        grid.addWidget(hint, 2, 0, 1, 4)

        root.addWidget(cfg)

        # --------------------------------------------------------------
        # Onglets de tâches
        # --------------------------------------------------------------

        self.tabs = QTabWidget()

        display_names = {
            "flanker": "Flanker",
            "nback": "N-Back",
            "oddball": "Oddball",
            "stroop": "Stroop",
        }

        for task_name in list_tasks():
            tab_name = display_names.get(task_name, task_name.title())
            self.tabs.addTab(TaskPanel(self, task_name), tab_name)

        root.addWidget(self.tabs)

    def _populate_screens(self) -> None:
        indices = available_screen_indices()
        maximum = max(indices)

        for index in indices:
            label = (
                f"Écran {index} (max)"
                if index == maximum
                else f"Écran {index} (précédent)"
            )

            self.screen_combo.addItem(label, userData=index)

        position = self.screen_combo.findData(maximum)

        if position >= 0:
            self.screen_combo.setCurrentIndex(position)

    def validate(self) -> dict | None:
        try:
            participant = sanitize_id(self.participant_input.text())

        except Exception as exc:
            QMessageBox.warning(self, "Participant invalide", str(exc))
            return None

        screen = self.screen_combo.currentData()

        if screen is None:
            QMessageBox.warning(
                self,
                "Écran invalide",
                "Veuillez sélectionner un écran.",
            )
            return None

        return {
            "participant": participant,
            "session": "01",
            "screen": int(screen),

            # Paramètres imposés, volontairement absents du GUI.
            "fullscreen": True,
            "wait_trigger": True,

            "markers_enabled": self.markers_checkbox.isChecked(),
            "save_data": self.save_checkbox.isChecked(),
        }

    def run_experiment(self, task_name: str, design_id: int) -> None:
        config = self.validate()

        if config is None:
            return

        self.final_config = {
            **config,
            "task": task_name,
            "design": design_id,
        }

        # Le menu disparaît avant ouverture de la fenêtre PsychoPy.
        self.close()

        app = QApplication.instance()

        if app is not None:
            app.quit()

    def closeEvent(self, event) -> None:
        event.accept()


def show_gui(settings_path: Path) -> dict | None:
    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv)

    menu = ExperimentMenu(settings_path)
    menu.show()

    app.exec()

    return menu.final_config
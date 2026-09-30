"""Menu PyQt6 de configuration et lancement des tâches fMRI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread
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

from core.config import sanitize_id, sanitize_run, sanitize_session
from gui.worker import ExperimentWorker
from tasks import list_tasks, load_task_config


# Le style visuel d'origine est conservé strictement.
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
    """Retourne au plus les deux écrans d'index le plus élevé."""
    app = QApplication.instance()
    if app is None:
        return [0]
    count = len(app.screens())
    if count <= 1:
        return [0]
    maximum = count - 1
    return [maximum - 1, maximum]


class TaskPanel(QWidget):
    """Onglet générique construit automatiquement depuis ``config.yaml``."""

    def __init__(self, menu: "ExperimentMenu", task_name: str) -> None:
        """Crée les boutons de designs d'une tâche détectée."""
        super().__init__()
        self.menu = menu
        self.task_name = task_name
        self.config = load_task_config(task_name)
        self.design_buttons: list[tuple[QPushButton, str]] = []

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
            paradigm = str(design.get("paradigm", "block")).lower()
            button = QPushButton(f"Design {design_id}")
            button.setObjectName("run")
            button.setToolTip(f"{name} — {paradigm}")
            button.clicked.connect(
                lambda _checked=False, did=design_id: self.launch(did)
            )
            grid.addWidget(button, index // 2, index % 2)
            self.design_buttons.append((button, paradigm))
        layout.addWidget(group)

        summary_lines = []
        for design_id, design in sorted(designs.items()):
            name = design.get("name", f"Design {design_id}")
            paradigm = str(design.get("paradigm", "block"))
            blocks = design.get("blocks", [])
            n_trials = sum(int(block.get("n_trials", 0)) for block in blocks)
            summary_lines.append(
                f"D{design_id}: {name} — {paradigm}, "
                f"{len(blocks)} bloc(s), {n_trials} essai(s)"
            )
        if summary_lines:
            summary = QLabel("\n".join(summary_lines))
            summary.setObjectName("taskDescription")
            summary.setWordWrap(True)
            layout.addWidget(summary)
        layout.addStretch()

    def launch(self, design_id: int) -> None:
        """Demande au menu principal de lancer un design précis."""
        self.menu.run_experiment(self.task_name, design_id)

    def refresh_paradigm(self, selected: str) -> None:
        """Affiche uniquement les designs Bloc ou Event demandés."""
        selected = selected.lower()
        for button, paradigm in self.design_buttons:
            button.setVisible(selected == "all" or paradigm == selected)


class ExperimentMenu(QMainWindow):
    """Fenêtre principale ; elle reste réactive pendant l'acquisition."""

    def __init__(self, settings_path: Path) -> None:
        """Construit la fenêtre et garde les références du worker QThread."""
        super().__init__()
        self.settings_path = Path(settings_path)
        self.thread: QThread | None = None
        self.worker: ExperimentWorker | None = None
        self.setWindowTitle("Configuration expérimentale")
        self.setStyleSheet(STYLESHEET)
        self.setMinimumWidth(620)
        self.setMinimumHeight(450)
        self._build()

    def _build(self) -> None:
        """Construit les métadonnées, toggles hardware et onglets de tâches."""
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        cfg = QGroupBox("Configuration")
        grid = QGridLayout(cfg)
        grid.setSpacing(6)

        grid.addWidget(QLabel("Participant :"), 0, 0)
        self.participant_input = QLineEdit()
        self.participant_input.setPlaceholderText("ID")
        self.participant_input.setFixedWidth(120)
        grid.addWidget(self.participant_input, 0, 1)

        grid.addWidget(QLabel("Session :"), 0, 2)
        self.session_input = QLineEdit("01")
        self.session_input.setFixedWidth(70)
        grid.addWidget(self.session_input, 0, 3)

        grid.addWidget(QLabel("Run :"), 0, 4)
        self.run_input = QLineEdit()
        self.run_input.setPlaceholderText("auto")
        self.run_input.setFixedWidth(70)
        grid.addWidget(self.run_input, 0, 5)

        grid.addWidget(QLabel("Écran :"), 1, 0)
        self.screen_combo = QComboBox()
        self.screen_combo.setFixedWidth(150)
        self._populate_screens()
        grid.addWidget(self.screen_combo, 1, 1)

        grid.addWidget(QLabel("Paradigme :"), 1, 2)
        self.paradigm_combo = QComboBox()
        self.paradigm_combo.addItem("Tous", userData="all")
        self.paradigm_combo.addItem("Bloc", userData="block")
        self.paradigm_combo.addItem("Event-related", userData="event")
        self.paradigm_combo.setFixedWidth(140)
        grid.addWidget(self.paradigm_combo, 1, 3, 1, 2)

        options = QHBoxLayout()
        options.setSpacing(14)
        self.save_checkbox = QCheckBox("Sauvegarder")
        self.save_checkbox.setChecked(True)
        options.addWidget(self.save_checkbox)
        self.trigger_checkbox = QCheckBox("Triggers")
        self.trigger_checkbox.setChecked(True)
        options.addWidget(self.trigger_checkbox)
        self.markers_checkbox = QCheckBox("Marqueurs")
        self.markers_checkbox.setChecked(False)
        options.addWidget(self.markers_checkbox)
        self.eyetracker_checkbox = QCheckBox("Eye-tracker")
        self.eyetracker_checkbox.setChecked(False)
        options.addWidget(self.eyetracker_checkbox)
        self.mock_checkbox = QCheckBox("Mode Mock")
        self.mock_checkbox.setChecked(False)
        options.addWidget(self.mock_checkbox)
        options.addStretch()
        grid.addLayout(options, 2, 0, 1, 6)

        hint = QLabel(
            "L'expérience PsychoPy s'exécute dans un QThread dédié ; "
            "le GUI reste réactif pendant l'acquisition."
        )
        hint.setObjectName("taskDescription")
        grid.addWidget(hint, 3, 0, 1, 6)
        root.addWidget(cfg)

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
        self.paradigm_combo.currentIndexChanged.connect(self._refresh_paradigm)
        root.addWidget(self.tabs)

        self.status_label = QLabel("Prêt.")
        self.status_label.setObjectName("taskDescription")
        root.addWidget(self.status_label)

    def _populate_screens(self) -> None:
        """Liste les deux écrans les plus probables pour la stimulation."""
        indices = available_screen_indices()
        maximum = max(indices)
        for index in indices:
            label = f"Écran {index} (max)" if index == maximum else f"Écran {index} (précédent)"
            self.screen_combo.addItem(label, userData=index)
        position = self.screen_combo.findData(maximum)
        if position >= 0:
            self.screen_combo.setCurrentIndex(position)

    def _refresh_paradigm(self) -> None:
        """Propage le filtre de paradigme à tous les onglets."""
        selected = str(self.paradigm_combo.currentData() or "all")
        for index in range(self.tabs.count()):
            panel = self.tabs.widget(index)
            if isinstance(panel, TaskPanel):
                panel.refresh_paradigm(selected)

    def validate(self) -> dict | None:
        """Valide les métadonnées de session et retourne les options de lancement."""
        try:
            participant = sanitize_id(self.participant_input.text())
            session = sanitize_session(self.session_input.text())
            run = sanitize_run(self.run_input.text())
        except Exception as exc:
            QMessageBox.warning(self, "Métadonnées invalides", str(exc))
            return None
        screen = self.screen_combo.currentData()
        if screen is None:
            QMessageBox.warning(self, "Écran invalide", "Veuillez sélectionner un écran.")
            return None
        return {
            "participant": participant,
            "session": session,
            "run": run,
            "screen": int(screen),
            "fullscreen": True,
            "trigger_enabled": self.trigger_checkbox.isChecked(),
            "markers_enabled": self.markers_checkbox.isChecked(),
            "eyetracker_enabled": self.eyetracker_checkbox.isChecked(),
            "mock_mode": self.mock_checkbox.isChecked(),
            "save_data": self.save_checkbox.isChecked(),
        }

    def run_experiment(self, task_name: str, design_id: int) -> None:
        """Lance un worker QThread sans bloquer la boucle événementielle Qt."""
        if self.thread is not None and self.thread.isRunning():
            QMessageBox.information(self, "Acquisition en cours", "Une tâche est déjà en cours.")
            return
        config = self.validate()
        if config is None:
            return
        launch_config = {**config, "task": task_name, "design": int(design_id), "seed": None}
        self.status_label.setText(f"En cours : {task_name}, design {design_id}…")
        self.tabs.setEnabled(False)

        self.thread = QThread(self)
        self.worker = ExperimentWorker(self.settings_path, launch_config)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_worker)
        self.thread.start()

    def _on_finished(self, saved_path: str) -> None:
        """Réactive le menu après un run terminé normalement."""
        self.tabs.setEnabled(True)
        self.status_label.setText("Run terminé.")
        if saved_path:
            QMessageBox.information(self, "Run terminé", f"Données sauvegardées :\n{saved_path}")

    def _on_failed(self, message: str) -> None:
        """Affiche une erreur remontée depuis le worker."""
        self.tabs.setEnabled(True)
        self.status_label.setText("Erreur pendant le run.")
        QMessageBox.critical(self, "Erreur expérimentale", message)

    def _cleanup_worker(self) -> None:
        """Libère les objets Qt du worker après arrêt du thread."""
        if self.worker is not None:
            self.worker.deleteLater()
        if self.thread is not None:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None

    def closeEvent(self, event: Any) -> None:
        """Empêche la fermeture du GUI au milieu d'une acquisition."""
        if self.thread is not None and self.thread.isRunning():
            QMessageBox.warning(
                self,
                "Acquisition en cours",
                "Terminez ou interrompez la tâche PsychoPy avant de fermer le menu.",
            )
            event.ignore()
            return
        event.accept()


def show_gui(settings_path: Path) -> int:
    """Affiche le menu et retourne le code de sortie de l'application Qt."""
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    menu = ExperimentMenu(settings_path)
    menu.show()
    if owns_app:
        return int(app.exec())
    return 0

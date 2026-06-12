"""
Per-task panels with direct-launch design buttons.

Each panel class provides design buttons that directly launch
the experiment when clicked. Close to the original tab design.

To add a panel for a new task:
    1. Create a class inheriting QWidget
    2. Register with @register_panel('task_name')
    3. It receives parent_menu in constructor
    4. Call self.parent_menu.run_experiment(params) on button click
"""

from __future__ import annotations

from typing import Type

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QSpinBox,
)

from config.tasks_config import load_task_config

# ═════════════════════════════════════════════════════════════════════
# Registry
# ═════════════════════════════════════════════════════════════════════

_PANELS: dict[str, Type] = {}


def register_panel(name: str):
    """Class decorator: register a task panel."""
    def decorator(cls):
        _PANELS[name] = cls
        return cls
    return decorator


def get_registered_panels() -> dict[str, Type]:
    """Return {name: panel_class} dict."""
    return dict(_PANELS)


# ═════════════════════════════════════════════════════════════════════
# Flanker Panel
# ═════════════════════════════════════════════════════════════════════

@register_panel('Flanker')
class FlankerPanel(QWidget):
    TASK_NAME = 'flanker'

    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.config = load_task_config(self.TASK_NAME)
        self.designs = self.config.get('designs', {})
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Design buttons ───────────────────────────────────────────
        design_group = QGroupBox("Designs fMRI")
        dg = QGridLayout(design_group)
        dg.setSpacing(8)

        for i, (did, dconf) in enumerate(sorted(self.designs.items())):
            name = dconf.get('name', f'Design {did}')
            btn = QPushButton(f"  Design {did}")
            btn.setObjectName("designBtn")
            btn.setToolTip(name)
            btn.clicked.connect(lambda _, d=did: self._run_design(d))
            dg.addWidget(btn, i // 2, i % 2)

        layout.addWidget(design_group)

        # ── Info ─────────────────────────────────────────────────────
        self._info = QLabel("")
        self._info.setObjectName("infoLabel")
        self._info.setWordWrap(True)
        layout.addWidget(self._info)

        # ── Training ─────────────────────────────────────────────────
        train_group = QGroupBox("Training")
        tl = QHBoxLayout(train_group)

        tl.addWidget(QLabel("Essais par bloc:"))
        self.spin_trials = QSpinBox()
        self.spin_trials.setRange(4, 30)
        self.spin_trials.setValue(10)
        tl.addWidget(self.spin_trials)
        tl.addStretch()

        btn_train = QPushButton("  Lancer Training")
        btn_train.setObjectName("trainBtn")
        btn_train.clicked.connect(self._run_training)
        tl.addWidget(btn_train)

        layout.addWidget(train_group)
        layout.addStretch()

    def _run_design(self, design_id):
        self.parent_menu.run_experiment({
            'task_name': self.TASK_NAME,
            'design_id': design_id,
        })

    def _run_training(self):
        n = self.spin_trials.value()
        self.parent_menu.run_experiment({
            'task_name': self.TASK_NAME,
            'design_id': 1,
            'extra_params': {
                'block_sequence': [
                    {'condition': 'congruent',   'n_trials': n},
                    {'condition': 'incongruent', 'n_trials': n},
                    {'condition': 'mixed', 'n_trials': n,
                     'prop_incongruent': 0.5},
                ],
                'rest_duration': 5.0,
            },
        })


# ═════════════════════════════════════════════════════════════════════
# N-Back Panel
# ═════════════════════════════════════════════════════════════════════

@register_panel('N-Back')
class NBackPanel(QWidget):
    TASK_NAME = 'nback'

    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.config = load_task_config(self.TASK_NAME)
        self.designs = self.config.get('designs', {})
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Design buttons ───────────────────────────────────────────
        design_group = QGroupBox("Designs fMRI")
        dg = QGridLayout(design_group)
        dg.setSpacing(8)

        for i, (did, dconf) in enumerate(sorted(self.designs.items())):
            name = dconf.get('name', f'Design {did}')
            btn = QPushButton(f"  Design {did}")
            btn.setObjectName("designBtn")
            btn.setToolTip(name)
            btn.clicked.connect(lambda _, d=did: self._run_design(d))
            dg.addWidget(btn, i // 2, i % 2)

        layout.addWidget(design_group)

        # ── Info ─────────────────────────────────────────────────────
        self._info = QLabel("")
        self._info.setObjectName("infoLabel")
        self._info.setWordWrap(True)
        layout.addWidget(self._info)

        # ── Training ─────────────────────────────────────────────────
        train_group = QGroupBox("Training")
        tl = QHBoxLayout(train_group)

        tl.addWidget(QLabel("Essais par bloc:"))
        self.spin_trials = QSpinBox()
        self.spin_trials.setRange(3, 30)
        self.spin_trials.setValue(8)
        tl.addWidget(self.spin_trials)
        tl.addStretch()

        btn_train = QPushButton("  Lancer Training")
        btn_train.setObjectName("trainBtn")
        btn_train.clicked.connect(self._run_training)
        tl.addWidget(btn_train)

        layout.addWidget(train_group)
        layout.addStretch()

    def _run_design(self, design_id):
        self.parent_menu.run_experiment({
            'task_name': self.TASK_NAME,
            'design_id': design_id,
        })

    def _run_training(self):
        n = self.spin_trials.value()
        self.parent_menu.run_experiment({
            'task_name': self.TASK_NAME,
            'design_id': 1,
            'extra_params': {
                'block_sequence': [
                    {'level': 0, 'n_trials': n},
                    {'level': 1, 'n_trials': n},
                    {'level': 2, 'n_trials': n},
                ],
                'rest_duration': 5.0,
            },
        })
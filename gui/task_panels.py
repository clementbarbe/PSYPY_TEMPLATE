"""
Per-task panels. Direct-launch design buttons.
"""

from __future__ import annotations
from typing import Type

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QSpinBox,
)

from config.tasks_config import load_task_config

_PANELS: dict[str, Type] = {}


def register_panel(name: str):
    def decorator(cls):
        _PANELS[name] = cls
        return cls
    return decorator


def get_registered_panels() -> dict[str, Type]:
    return dict(_PANELS)


# ── Helper: builds design button grid from YAML ─────────────────────

def _make_design_group(widget, task_name: str, designs: dict,
                       run_cb) -> QGroupBox:
    group = QGroupBox("Designs")
    g = QGridLayout(group)
    g.setSpacing(6)
    for i, (did, d) in enumerate(sorted(designs.items())):
        name = d.get('name', f'Design {did}')
        btn = QPushButton(f"Design {did}")
        btn.setObjectName("run")
        btn.setToolTip(name)
        btn.clicked.connect(lambda _, d=did: run_cb(d))
        g.addWidget(btn, i // 2, i % 2)
    return group


def _make_training_group(spin_default, run_cb) -> tuple[QGroupBox, QSpinBox]:
    group = QGroupBox("Training")
    h = QHBoxLayout(group)
    h.addWidget(QLabel("Essais/bloc :"))
    spin = QSpinBox()
    spin.setRange(3, 30)
    spin.setValue(spin_default)
    spin.setFixedWidth(55)
    h.addWidget(spin)
    h.addStretch()
    btn = QPushButton("Lancer Training")
    btn.clicked.connect(run_cb)
    h.addWidget(btn)
    return group, spin


# ═════════════════════════════════════════════════════════════════════
# Flanker
# ═════════════════════════════════════════════════════════════════════

@register_panel('Flanker')
class FlankerPanel(QWidget):
    TASK = 'flanker'

    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        cfg = load_task_config(self.TASK)
        self.designs = cfg.get('designs', {})
        lo = QVBoxLayout(self)
        lo.setSpacing(8)

        lo.addWidget(_make_design_group(self, self.TASK, self.designs,
                                        self._run))

        grp, self.sp = _make_training_group(10, self._train)
        lo.addWidget(grp)
        lo.addStretch()

    def _run(self, did):
        self.menu.run_experiment({'task_name': self.TASK, 'design_id': did})

    def _train(self):
        n = self.sp.value()
        self.menu.run_experiment({
            'task_name': self.TASK, 'design_id': 1,
            'extra_params': {
                'block_sequence': [
                    {'condition': 'congruent',   'n_trials': n},
                    {'condition': 'incongruent', 'n_trials': n},
                    {'condition': 'mixed', 'n_trials': n, 'prop_incongruent': 0.5},
                ],
                'rest_duration': 5.0,
            },
        })


# ═════════════════════════════════════════════════════════════════════
# N-Back
# ═════════════════════════════════════════════════════════════════════

@register_panel('N-Back')
class NBackPanel(QWidget):
    TASK = 'nback'

    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        cfg = load_task_config(self.TASK)
        self.designs = cfg.get('designs', {})
        lo = QVBoxLayout(self)
        lo.setSpacing(8)

        lo.addWidget(_make_design_group(self, self.TASK, self.designs,
                                        self._run))

        grp, self.sp = _make_training_group(8, self._train)
        lo.addWidget(grp)
        lo.addStretch()

    def _run(self, did):
        self.menu.run_experiment({'task_name': self.TASK, 'design_id': did})

    def _train(self):
        n = self.sp.value()
        self.menu.run_experiment({
            'task_name': self.TASK, 'design_id': 1,
            'extra_params': {
                'block_sequence': [
                    {'level': 0, 'n_trials': n},
                    {'level': 1, 'n_trials': n},
                    {'level': 2, 'n_trials': n},
                ],
                'rest_duration': 5.0,
            },
        })


# ═════════════════════════════════════════════════════════════════════
# Stroop
# ═════════════════════════════════════════════════════════════════════

@register_panel('Stroop')
class StroopPanel(QWidget):
    TASK = 'stroop'

    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        cfg = load_task_config(self.TASK)
        self.designs = cfg.get('designs', {})
        lo = QVBoxLayout(self)
        lo.setSpacing(8)

        lo.addWidget(_make_design_group(self, self.TASK, self.designs,
                                        self._run))

        info = QLabel(
            "D1/D2 : Bloc (papier) ordre A/B contrebalance\n"
            "D3 : Bloc court  |  D4 : Event-related\n"
            "3 couleurs : ROUGE  ORANGE  VERT\n"
            "Touches PC : gauche  bas  droite"
        )
        info.setStyleSheet("color: #808080; font-size: 11px; padding: 4px;")
        lo.addWidget(info)

        grp, self.sp = _make_training_group(10, self._train)
        lo.addWidget(grp)
        lo.addStretch()

    def _run(self, did):
        self.menu.run_experiment({'task_name': self.TASK, 'design_id': did})

    def _train(self):
        n = self.sp.value()
        self.menu.run_experiment({
            'task_name': self.TASK, 'design_id': 3,
            'extra_params': {
                'block_sequence': [
                    {'condition': 'neutral',     'n_trials': n},
                    {'condition': 'incongruent', 'n_trials': n},
                    {'condition': 'congruent',   'n_trials': n},
                ],
                'rest_duration': 5.0,
            },
        })
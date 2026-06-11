"""
Per-task configuration panels (PyQt6 widgets).

NO PsychoPy imports — only reads YAML/built-in configs.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout,
    QLabel, QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox,
)
from PyQt6.QtCore import Qt

from config.tasks_config import load_task_config

# ═════════════════════════════════════════════════════════════════════════════
# Panel registry
# ═════════════════════════════════════════════════════════════════════════════

_PANEL_BUILDERS: dict[str, Callable] = {}


def register_panel(task_name: str):
    """Decorator: register a panel builder function for a task."""
    def decorator(func: Callable):
        _PANEL_BUILDERS[task_name.lower()] = func
        return func
    return decorator


def get_panel_builder(task_name: str) -> Callable | None:
    return _PANEL_BUILDERS.get(task_name.lower())


# ═════════════════════════════════════════════════════════════════════════════
# TaskPanel helper class
# ═════════════════════════════════════════════════════════════════════════════

class TaskPanel(QWidget):
    """
    Base panel widget for a task tab.

    Provides a design selector and a description area.
    Builders can add extra parameters via add_double_spin / add_int_spin.
    """

    def __init__(self, parent: QWidget, task_name: str):
        super().__init__(parent)
        self.task_name = task_name
        self.config = load_task_config(task_name)
        self.designs = self.config.get('designs', {})
        self.extra_vars: dict[str, QWidget] = {}

        self._selected_design_id: int = min(self.designs.keys()) if self.designs else 1
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Design selector
        design_group = QGroupBox("Design")
        dg_layout = QVBoxLayout(design_group)
        dg_layout.setSpacing(8)

        self._design_combo = QComboBox()
        self._design_map: dict[int, int] = {}  # combo_index -> design_id
        for did in sorted(self.designs.keys()):
            dconf = self.designs[did]
            label = f"{did}: {dconf.get('name', f'Design {did}')}"
            self._design_combo.addItem(label)
            self._design_map[self._design_combo.count() - 1] = did

        self._design_combo.currentIndexChanged.connect(
            self._on_design_changed
        )
        dg_layout.addWidget(self._design_combo)

        self._info_label = QLabel("")
        self._info_label.setObjectName("designInfo")
        self._info_label.setWordWrap(True)
        dg_layout.addWidget(self._info_label)

        layout.addWidget(design_group)

        # Parameters group
        self._params_group = QGroupBox("Parameters")
        self._params_layout = QGridLayout(self._params_group)
        self._params_layout.setSpacing(8)
        self._params_row = 0
        layout.addWidget(self._params_group)

        layout.addStretch()

        # Initial
        if self._design_combo.count() > 0:
            self._on_design_changed(0)

    def _on_design_changed(self, index: int) -> None:
        did = self._design_map.get(index, 1)
        self._selected_design_id = did
        d = self.designs.get(did, {})

        blocks = d.get('blocks', [])
        n_blocks = len(blocks)
        total_trials = sum(b.get('n_trials', 0) for b in blocks)

        stim_dur = d.get('stim_duration', '?')
        isi_min = d.get('isi_min', d.get('isi_duration', '?'))
        isi_max = d.get('isi_max', isi_min)
        rest = d.get('rest_duration', '?')

        # Estimate duration
        try:
            mean_isi = (float(isi_min) + float(isi_max)) / 2
            trial_time = total_trials * (float(stim_dur) + mean_isi)
            rest_time = (n_blocks + 1) * float(rest)
            instr_time = n_blocks * (
                d.get('instruction_duration', 3)
                + d.get('pre_block_fixation', 1)
            )
            dur_str = f"~{(trial_time + rest_time + instr_time) / 60:.1f} min"
        except (ValueError, TypeError):
            dur_str = "?"

        isi_str = (
            f"{isi_min}" if isi_min == isi_max
            else f"{isi_min}-{isi_max}"
        )

        paradigm = d.get('paradigm', '')

        info = (
            f"Blocks: {n_blocks}  |  Trials: {total_trials}  |  {dur_str}\n"
            f"Stim: {stim_dur}s  |  ISI: {isi_str}s  |  Rest: {rest}s"
        )
        if paradigm:
            info += f"\nParadigm: {paradigm}"

        self._info_label.setText(info)

    # Parameter helpers

    def add_double_spin(self, key: str, label: str,
                        default: float, minimum: float,
                        maximum: float, step: float) -> QDoubleSpinBox:
        lbl = QLabel(label)
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setValue(default)
        spin.setDecimals(2)

        row = self._params_row
        self._params_layout.addWidget(
            lbl, row, 0, Qt.AlignmentFlag.AlignRight
        )
        self._params_layout.addWidget(
            spin, row, 1, Qt.AlignmentFlag.AlignLeft
        )
        self._params_row += 1
        self.extra_vars[key] = spin
        return spin

    def add_int_spin(self, key: str, label: str,
                     default: int, minimum: int,
                     maximum: int) -> QSpinBox:
        lbl = QLabel(label)
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(default)

        row = self._params_row
        self._params_layout.addWidget(
            lbl, row, 0, Qt.AlignmentFlag.AlignRight
        )
        self._params_layout.addWidget(
            spin, row, 1, Qt.AlignmentFlag.AlignLeft
        )
        self._params_row += 1
        self.extra_vars[key] = spin
        return spin

    # Getters

    @property
    def selected_design_id(self) -> int:
        return self._selected_design_id

    def get_extra_params(self) -> dict:
        params = {}
        for key, widget in self.extra_vars.items():
            if isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                params[key] = widget.value()
        return params


# ═════════════════════════════════════════════════════════════════════════════
# Built-in panels
# ═════════════════════════════════════════════════════════════════════════════

@register_panel('flanker')
def build_flanker_panel(
    parent: QWidget, task_name: str = 'flanker'
) -> TaskPanel:
    panel = TaskPanel(parent, task_name)
    panel.add_double_spin(
        'prop_incongruent', 'Prop. incongruent:',
        default=0.50, minimum=0.0, maximum=1.0, step=0.05,
    )
    return panel


@register_panel('nback')
def build_nback_panel(
    parent: QWidget, task_name: str = 'nback'
) -> TaskPanel:
    panel = TaskPanel(parent, task_name)
    panel.add_double_spin(
        'target_ratio', 'Target ratio:',
        default=0.33, minimum=0.10, maximum=0.50, step=0.05,
    )
    return panel
# tabs_flanker.py
"""
Onglet Flanker pour le menu principal.
Gère 4 designs prédéfinis + mode custom + training.
"""

from collections import Counter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSpinBox, QPushButton, QComboBox,
    QGridLayout, QFrame, QDoubleSpinBox,
    QSizePolicy
)
from PyQt6.QtCore import Qt


# ─────────────────────────────────────────────────────────────────────────────
# Réplique locale des designs pour l'affichage (évite d'importer PsychoPy)
# ─────────────────────────────────────────────────────────────────────────────

DESIGN_SPECS = {
    1: {
        'name': 'Block (CON vs INC ~7min)',
        'paradigm': 'block',
        'rest': 12.0,
        'stim': 1.5,
        'isi_min': 1.0, 'isi_max': 1.0,
        'inter_min': 0, 'inter_max': 0,
        'blocks': [
            ('congruent', 20), ('incongruent', 20),
            ('incongruent', 20), ('congruent', 20),
            ('incongruent', 20), ('congruent', 20),
        ],
    },
    2: {
        'name': 'Event-related (jittered ~9min)',
        'paradigm': 'event',
        'rest': 15.0,
        'stim': 1.5,
        'isi_min': 2.0, 'isi_max': 6.0,
        'inter_min': 0, 'inter_max': 0,
        'blocks': [
            ('mixed', 96),
        ],
    },
    3: {
        'name': 'Hybrid mini-blocks (recommandé ~7min)',
        'paradigm': 'hybrid',
        'rest': 12.0,
        'stim': 1.5,
        'isi_min': 1.0, 'isi_max': 2.0,
        'inter_min': 4.0, 'inter_max': 10.0,
        'blocks': [('mixed', 8)] * 12,
    },
    4: {
        'name': 'Hybrid optimisé (randomisé ~7min)',
        'paradigm': 'hybrid',
        'rest': 10.0,
        'stim': 1.5,
        'isi_min': 1.0, 'isi_max': 1.5,
        'inter_min': 3.0, 'inter_max': 7.0,
        'blocks': [('mixed', 4)] * 24,
    },
}


def _format_design_summary(design_id):
    """Génère un résumé textuel d'un design pour info-bulle / tooltip."""
    spec = DESIGN_SPECS[design_id]
    blocks = spec['blocks']

    lines = [f"Design {design_id} — {spec['name']}",
             f"Paradigme : {spec['paradigm']}", ""]

    # Séquence visuelle
    lines.append(f"  Rest {spec['rest']}s")
    for cond, trials in blocks:
        lines.append(f"  {cond}  ({trials} essais)")
        if spec['paradigm'] == 'hybrid' and spec['inter_max'] > 0:
            lines.append(f"  Jitter {spec['inter_min']}–{spec['inter_max']}s")
        else:
            lines.append(f"  Rest {spec['rest']}s")
    lines.append("")

    # Stats
    total_trials = sum(t for _, t in blocks)
    n_blocks = len(blocks)
    level_counts = Counter(c for c, _ in blocks)
    count_str = ", ".join(
        f"{c}: {n} blocs" for c, n in sorted(level_counts.items())
    )

    mean_isi = (spec['isi_min'] + spec['isi_max']) / 2.0
    trial_dur = spec['stim'] + mean_isi
    task_time = total_trials * trial_dur

    if spec['paradigm'] == 'hybrid' and spec['inter_max'] > 0:
        mean_jitter = (spec['inter_min'] + spec['inter_max']) / 2.0
        rest_time = max(0, n_blocks - 1) * mean_jitter + 2 * spec['rest']
    else:
        rest_time = (n_blocks + 1) * spec['rest']

    instr_dur = 3.0 if spec['paradigm'] != 'hybrid' else 0.0
    instr_time = n_blocks * (instr_dur + 1.0)
    total_time = task_time + rest_time + instr_time

    lines.append(f"  Blocs: {n_blocks} | {count_str}")
    lines.append(f"  Essais total: {total_trials}")
    lines.append(f"  ISI: {spec['isi_min']}–{spec['isi_max']}s | Stim: {spec['stim']}s")
    lines.append(f"  Durée estimée: ~{total_time / 60:.1f} min")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM BLOCK EDITOR
# ─────────────────────────────────────────────────────────────────────────────

class FlankerBlockEditor(QFrame):
    """
    Éditeur de séquence de blocs personnalisée pour Flanker.
    Chaque ligne : condition + nombre d'essais + % incongruent.
    """

    CONDITION_OPTIONS = ['congruent', 'incongruent', 'mixed', 'neutral']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.block_rows = []
        self._init_ui()

    def _init_ui(self):
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("Séquence de blocs :"))
        header.addStretch()
        btn_add = QPushButton("+ Ajouter bloc")
        btn_add.clicked.connect(self._add_block_row)
        header.addWidget(btn_add)
        self.main_layout.addLayout(header)

        # Grid
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_widget.setLayout(self.grid_layout)

        for col, label in enumerate(["#", "Condition", "Essais", "%INC", ""]):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: bold;")
            self.grid_layout.addWidget(lbl, 0, col)

        self.main_layout.addWidget(self.grid_widget)

        # Info
        self.label_info = QLabel("")
        self.label_info.setStyleSheet("color: grey; font-style: italic;")
        self.main_layout.addWidget(self.label_info)

        # Default blocks
        for cond, trials in [('mixed', 8), ('mixed', 8), ('mixed', 8)]:
            self._add_block_row(default_cond=cond, default_trials=trials)

    def _add_block_row(self, default_cond='mixed', default_trials=8):
        """Ajoute une ligne de bloc au grid."""
        row_idx = len(self.block_rows) + 1

        label = QLabel(str(row_idx))

        combo_cond = QComboBox()
        for c in self.CONDITION_OPTIONS:
            combo_cond.addItem(c, c)
        idx = combo_cond.findData(default_cond)
        if idx >= 0:
            combo_cond.setCurrentIndex(idx)

        spin_trials = QSpinBox()
        spin_trials.setRange(2, 200)
        spin_trials.setValue(default_trials)

        spin_prop = QSpinBox()
        spin_prop.setRange(0, 100)
        spin_prop.setValue(50)
        spin_prop.setSuffix("%")
        # Enable only for mixed
        spin_prop.setEnabled(default_cond == 'mixed')

        btn_remove = QPushButton("✕")
        btn_remove.setFixedWidth(30)

        row_data = {
            'label': label,
            'combo': combo_cond,
            'spin_trials': spin_trials,
            'spin_prop': spin_prop,
            'btn': btn_remove,
        }

        btn_remove.clicked.connect(
            lambda _, rd=row_data: self._remove_block_row(rd)
        )
        combo_cond.currentIndexChanged.connect(
            lambda _, rd=row_data: self._on_condition_changed(rd)
        )
        combo_cond.currentIndexChanged.connect(self._update_info)
        spin_trials.valueChanged.connect(self._update_info)
        spin_prop.valueChanged.connect(self._update_info)

        self.grid_layout.addWidget(label, row_idx, 0)
        self.grid_layout.addWidget(combo_cond, row_idx, 1)
        self.grid_layout.addWidget(spin_trials, row_idx, 2)
        self.grid_layout.addWidget(spin_prop, row_idx, 3)
        self.grid_layout.addWidget(btn_remove, row_idx, 4)

        self.block_rows.append(row_data)
        self._update_info()

    def _on_condition_changed(self, row_data):
        """Enable/disable %INC spinner based on condition."""
        cond = row_data['combo'].currentData()
        row_data['spin_prop'].setEnabled(cond == 'mixed')

    def _remove_block_row(self, row_data):
        """Supprime une ligne de bloc."""
        if len(self.block_rows) <= 1:
            return
        for widget in [row_data['label'], row_data['combo'],
                       row_data['spin_trials'], row_data['spin_prop'],
                       row_data['btn']]:
            self.grid_layout.removeWidget(widget)
            widget.deleteLater()
        self.block_rows.remove(row_data)
        for i, rd in enumerate(self.block_rows):
            rd['label'].setText(str(i + 1))
        self._update_info()

    def _update_info(self):
        """Met à jour le label d'info avec résumé de la config."""
        try:
            blocks = self.get_block_sequence()
            total = sum(b['n_trials'] for b in blocks)
            seq_str = " → ".join(
                f"{b['condition'][:3].upper()}({b['n_trials']})"
                for b in blocks
            )
            self.label_info.setText(f"{seq_str}\nTotal: {total} essais")
        except Exception:
            self.label_info.setText("⚠ Configuration invalide")

    def get_block_sequence(self):
        """Retourne la séquence sous forme de list[dict]."""
        blocks = []
        for rd in self.block_rows:
            cond = rd['combo'].currentData()
            trials = rd['spin_trials'].value()
            entry = {'condition': cond, 'n_trials': trials}
            if cond == 'mixed':
                entry['prop_incongruent'] = rd['spin_prop'].value() / 100.0
            blocks.append(entry)
        return blocks


# ─────────────────────────────────────────────────────────────────────────────
# TAB PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class FlankerTab(QWidget):
    """Onglet Flanker pour le menu principal PyQt6."""

    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # ==========================================
        # DESIGNS (4 BOUTONS DIRECTS)
        # ==========================================
        design_group = QGroupBox("Designs fMRI — Flanker")
        design_layout = QGridLayout()

        for i in range(1, 5):
            spec = DESIGN_SPECS[i]
            btn = QPushButton(f"▶ Design {i}: {spec['paradigm'].capitalize()}")
            btn.setMinimumHeight(40)
            btn.setToolTip(_format_design_summary(i))
            btn.clicked.connect(lambda _, did=i: self.run_design(did))
            design_layout.addWidget(btn, (i - 1) // 2, (i - 1) % 2)

        design_group.setLayout(design_layout)
        layout.addWidget(design_group)

        # ==========================================
        # TRAINING
        # ==========================================
        train_group = QGroupBox("Training")
        train_layout = QVBoxLayout()

        row_train = QHBoxLayout()
        row_train.addWidget(QLabel("Essais par bloc :"))
        self.spin_train_trials = QSpinBox()
        self.spin_train_trials.setRange(4, 40)
        self.spin_train_trials.setValue(10)
        row_train.addWidget(self.spin_train_trials)
        row_train.addStretch()
        train_layout.addLayout(row_train)

        btn_train = QPushButton("▶ Lancer Training (CON → MIX → INC)")
        btn_train.setMinimumHeight(35)
        btn_train.clicked.connect(self.run_training)
        train_layout.addWidget(btn_train)

        train_group.setLayout(train_layout)
        layout.addWidget(train_group)

        # ==========================================
        # CUSTOM BUILDER
        # ==========================================
        custom_group = QGroupBox("Custom Builder")
        custom_layout = QVBoxLayout()

        # Paradigm selector
        row_paradigm = QHBoxLayout()
        row_paradigm.addWidget(QLabel("Paradigme :"))
        self.combo_paradigm = QComboBox()
        for p in ['block', 'event', 'hybrid', 'custom']:
            self.combo_paradigm.addItem(p, p)
        self.combo_paradigm.setCurrentIndex(2)  # hybrid default
        self.combo_paradigm.currentIndexChanged.connect(
            self._on_paradigm_changed
        )
        row_paradigm.addWidget(self.combo_paradigm)
        row_paradigm.addStretch()
        custom_layout.addLayout(row_paradigm)

        # Block editor
        self.custom_editor = FlankerBlockEditor()
        custom_layout.addWidget(self.custom_editor)

        # Timing controls
        timing_group = QGroupBox("Timing")
        timing_layout = QGridLayout()

        # Stim duration
        timing_layout.addWidget(QLabel("Stim (s) :"), 0, 0)
        self.spin_stim = QDoubleSpinBox()
        self.spin_stim.setRange(0.3, 5.0)
        self.spin_stim.setValue(1.5)
        self.spin_stim.setSingleStep(0.1)
        timing_layout.addWidget(self.spin_stim, 0, 1)

        # ISI
        timing_layout.addWidget(QLabel("ISI min (s) :"), 1, 0)
        self.spin_isi_min = QDoubleSpinBox()
        self.spin_isi_min.setRange(0.2, 10.0)
        self.spin_isi_min.setValue(1.0)
        self.spin_isi_min.setSingleStep(0.1)
        timing_layout.addWidget(self.spin_isi_min, 1, 1)

        timing_layout.addWidget(QLabel("ISI max (s) :"), 1, 2)
        self.spin_isi_max = QDoubleSpinBox()
        self.spin_isi_max.setRange(0.2, 15.0)
        self.spin_isi_max.setValue(2.0)
        self.spin_isi_max.setSingleStep(0.1)
        timing_layout.addWidget(self.spin_isi_max, 1, 3)

        # Rest
        timing_layout.addWidget(QLabel("Rest (s) :"), 2, 0)
        self.spin_rest = QDoubleSpinBox()
        self.spin_rest.setRange(2.0, 30.0)
        self.spin_rest.setValue(10.0)
        self.spin_rest.setSingleStep(1.0)
        timing_layout.addWidget(self.spin_rest, 2, 1)

        # Inter-block jitter (hybrid)
        timing_layout.addWidget(QLabel("Jitter min (s) :"), 3, 0)
        self.spin_jitter_min = QDoubleSpinBox()
        self.spin_jitter_min.setRange(0.0, 15.0)
        self.spin_jitter_min.setValue(4.0)
        self.spin_jitter_min.setSingleStep(0.5)
        timing_layout.addWidget(self.spin_jitter_min, 3, 1)

        timing_layout.addWidget(QLabel("Jitter max (s) :"), 3, 2)
        self.spin_jitter_max = QDoubleSpinBox()
        self.spin_jitter_max.setRange(0.0, 20.0)
        self.spin_jitter_max.setValue(8.0)
        self.spin_jitter_max.setSingleStep(0.5)
        timing_layout.addWidget(self.spin_jitter_max, 3, 3)

        self.label_jitter_min = timing_layout.itemAtPosition(3, 0).widget()
        self.label_jitter_max = timing_layout.itemAtPosition(3, 2).widget()

        timing_group.setLayout(timing_layout)
        custom_layout.addWidget(timing_group)

        # Duration estimate
        self.label_estimate = QLabel("")
        self.label_estimate.setStyleSheet(
            "color: #888; font-style: italic; padding: 4px;"
        )
        custom_layout.addWidget(self.label_estimate)

        # Launch button
        btn_custom = QPushButton("▶ Lancer Custom")
        btn_custom.setMinimumHeight(40)
        btn_custom.clicked.connect(self.run_custom)
        custom_layout.addWidget(btn_custom)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        layout.addStretch()
        self.setLayout(layout)

        # Connect signals for estimate update
        self.spin_stim.valueChanged.connect(self._update_estimate)
        self.spin_isi_min.valueChanged.connect(self._update_estimate)
        self.spin_isi_max.valueChanged.connect(self._update_estimate)
        self.spin_rest.valueChanged.connect(self._update_estimate)
        self.spin_jitter_min.valueChanged.connect(self._update_estimate)
        self.spin_jitter_max.valueChanged.connect(self._update_estimate)

        # Initial state
        self._on_paradigm_changed()
        self._update_estimate()

    # ── UI CALLBACKS ─────────────────────────────────────────────────

    def _on_paradigm_changed(self):
        """Enable/disable jitter controls based on paradigm."""
        paradigm = self.combo_paradigm.currentData()
        is_hybrid = (paradigm == 'hybrid')

        self.spin_jitter_min.setEnabled(is_hybrid)
        self.spin_jitter_max.setEnabled(is_hybrid)
        self.label_jitter_min.setEnabled(is_hybrid)
        self.label_jitter_max.setEnabled(is_hybrid)

        self._update_estimate()

    def _update_estimate(self):
        """Update duration estimate label."""
        try:
            blocks = self.custom_editor.get_block_sequence()
            total_trials = sum(b['n_trials'] for b in blocks)
            n_blocks = len(blocks)

            stim = self.spin_stim.value()
            isi_min = self.spin_isi_min.value()
            isi_max = self.spin_isi_max.value()
            rest = self.spin_rest.value()
            paradigm = self.combo_paradigm.currentData()

            mean_isi = (isi_min + isi_max) / 2.0
            task_time = total_trials * (stim + mean_isi)

            if paradigm == 'hybrid':
                jmin = self.spin_jitter_min.value()
                jmax = self.spin_jitter_max.value()
                mean_j = (jmin + jmax) / 2.0
                rest_time = max(0, n_blocks - 1) * mean_j + 2 * rest
            else:
                rest_time = (n_blocks + 1) * rest

            instr_time = n_blocks * 4.0 if paradigm != 'hybrid' else 0
            total = task_time + rest_time + instr_time

            self.label_estimate.setText(
                f"⏱ Estimation : {total_trials} essais | "
                f"~{total / 60:.1f} min"
            )
        except Exception:
            self.label_estimate.setText("⚠ Estimation impossible")

    # ── PARAMÈTRES COMMUNS ───────────────────────────────────────────

    def get_common(self):
        """Return common params shared by all run modes."""
        return {
            'tache': 'Flanker',
            'prop_incongruent': 0.5,
        }

    # ── RUNS ─────────────────────────────────────────────────────────

    def run_design(self, design_id):
        """Launch a predefined design."""
        params = self.get_common()
        params.update({
            'run_type': 'base',
            'design_id': design_id,
        })
        self.parent_menu.run_experiment(params)

    def run_training(self):
        """Launch progressive training: CON → MIXED → INC."""
        n_trials = self.spin_train_trials.value()

        block_sequence = [
            {'condition': 'congruent',   'n_trials': n_trials},
            {'condition': 'mixed',       'n_trials': n_trials,
             'prop_incongruent': 0.5},
            {'condition': 'incongruent', 'n_trials': n_trials},
        ]

        params = self.get_common()
        params.update({
            'run_type': 'training',
            'design_id': None,
            'paradigm': 'block',
            'block_sequence': block_sequence,
            'rest_duration': 5.0,
            'stim_duration': 2.0,   # Slower for training
            'isi_min': 1.5,
            'isi_max': 1.5,
            'instruction_duration': 4.0,
        })
        self.parent_menu.run_experiment(params)

    def run_custom(self):
        """Launch custom configuration."""
        block_sequence = self.custom_editor.get_block_sequence()
        if not block_sequence:
            return

        paradigm = self.combo_paradigm.currentData()

        params = self.get_common()
        params.update({
            'run_type': 'custom',
            'design_id': None,
            'paradigm': paradigm,
            'block_sequence': block_sequence,
            'rest_duration': self.spin_rest.value(),
            'stim_duration': self.spin_stim.value(),
            'isi_min': self.spin_isi_min.value(),
            'isi_max': self.spin_isi_max.value(),
            'inter_block_min': (self.spin_jitter_min.value()
                                if paradigm == 'hybrid' else 0.0),
            'inter_block_max': (self.spin_jitter_max.value()
                                if paradigm == 'hybrid' else 0.0),
        })
        self.parent_menu.run_experiment(params)
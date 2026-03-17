# tabs_nback.py
"""
Onglet N-Back pour le menu principal.
Gère 4 designs prédéfinis + mode custom + training.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSpinBox, QPushButton, QComboBox,
    QGridLayout, QFrame, QTextEdit, QCheckBox,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


# Réplique locale des designs pour l'affichage (évite d'importer PsychoPy)
DESIGN_SPECS = {
    1: {
        'name': '0 vs 2-back (standard ~8min)',
        'rest': 12.0,
        'blocks': [
            (0, 25), (2, 25), (2, 25), (0, 25), (2, 25), (0, 25)
        ],
    },
    2: {
        'name': '0 vs 2-back (dense optimisé)',
        'rest': 10.0,
        'blocks': [
            (0, 20), (2, 20), (2, 20), (0, 20), (2, 20), (0, 20)
        ],
    },
    3: {
        'name': '1-2-3-back (paramétrique simple)',
        'rest': 12.0,
        'blocks': [
            (1, 25), (2, 25), (3, 25), (2, 25), (1, 25), (3, 25)
        ],
    },
    4: {
        'name': '1-2-3-back (randomisé optimisé)',
        'rest': 10.0,
        'blocks': [
            (2, 20), (1, 20), (3, 20), (2, 20), (3, 20), (1, 20)
        ],
    },
}


def _format_design_summary(design_id):
    """Génère un résumé textuel d'un design."""
    spec = DESIGN_SPECS[design_id]
    blocks = spec['blocks']
    rest = spec['rest']

    lines = []
    lines.append(f"Design {design_id} — {spec['name']}")
    lines.append("")

    # Séquence visuelle
    lines.append(f"  Rest {rest}s")
    for level, trials in blocks:
        lines.append(f"  {level}-back  ({trials} essais)")
        lines.append(f"  Rest {rest}s")

    lines.append("")

    # Stats
    total_trials = sum(t for _, t in blocks)
    n_blocks = len(blocks)
    levels_used = sorted(set(l for l, _ in blocks))

    # Comptage par niveau
    from collections import Counter
    level_counts = Counter(l for l, _ in blocks)
    count_str = ", ".join(f"{l}-back: {c} blocs" for l, c in sorted(level_counts.items()))

    # Durée estimée
    trial_dur = 0.5 + 2.0  # stim + ISI par défaut
    task_time = total_trials * trial_dur
    rest_time = rest * (n_blocks + 1)
    instr_time = n_blocks * (4.0 + 2.0)
    total_time = task_time + rest_time + instr_time

    lines.append(f"  Blocs: {n_blocks} | {count_str}")
    lines.append(f"  Essais total: {total_trials}")
    lines.append(f"  Niveaux: {levels_used}")
    lines.append(f"  Durée estimée: ~{total_time/60:.1f} min")

    return "\n".join(lines)


class CustomBlockEditor(QFrame):
    """
    Éditeur de séquence de blocs personnalisée.
    Permet d'ajouter/supprimer des blocs avec niveau + nombre d'essais.
    """

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
        header.addWidget(QLabel("Séquence de blocs personnalisée :"))
        header.addStretch()

        btn_add = QPushButton("+ Ajouter bloc")
        btn_add.clicked.connect(self._add_block_row)
        header.addWidget(btn_add)

        self.main_layout.addLayout(header)

        # Grid pour les blocs
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_widget.setLayout(self.grid_layout)

        # Headers
        self.grid_layout.addWidget(QLabel("#"), 0, 0)
        self.grid_layout.addWidget(QLabel("Niveau"), 0, 1)
        self.grid_layout.addWidget(QLabel("Essais"), 0, 2)
        self.grid_layout.addWidget(QLabel(""), 0, 3)

        self.main_layout.addWidget(self.grid_widget)

        # Rest duration
        rest_row = QHBoxLayout()
        rest_row.addWidget(QLabel("Repos inter-blocs (s) :"))
        self.spin_rest = QSpinBox()
        self.spin_rest.setRange(2, 30)
        self.spin_rest.setValue(10)
        rest_row.addWidget(self.spin_rest)
        rest_row.addStretch()
        self.main_layout.addLayout(rest_row)

        # Info
        self.label_info = QLabel("")
        self.label_info.setStyleSheet("color: grey; font-style: italic;")
        self.main_layout.addWidget(self.label_info)

        # Ajouter quelques blocs par défaut
        for level, trials in [(1, 15), (2, 15), (1, 15)]:
            self._add_block_row(default_level=level, default_trials=trials)

    def _add_block_row(self, default_level=2, default_trials=15):
        """Ajoute une ligne de bloc."""
        row_idx = len(self.block_rows) + 1

        label = QLabel(str(row_idx))

        combo_level = QComboBox()
        for n in [0, 1, 2, 3]:
            combo_level.addItem(f"{n}-back", n)
        # Set default
        idx = combo_level.findData(default_level)
        if idx >= 0:
            combo_level.setCurrentIndex(idx)

        spin_trials = QSpinBox()
        spin_trials.setRange(3, 100)
        spin_trials.setValue(default_trials)

        btn_remove = QPushButton("✕")
        btn_remove.setFixedWidth(30)

        row_data = {
            'label': label,
            'combo': combo_level,
            'spin': spin_trials,
            'btn': btn_remove,
        }

        btn_remove.clicked.connect(lambda _, rd=row_data: self._remove_block_row(rd))
        combo_level.currentIndexChanged.connect(self._update_info)
        spin_trials.valueChanged.connect(self._update_info)

        self.grid_layout.addWidget(label, row_idx, 0)
        self.grid_layout.addWidget(combo_level, row_idx, 1)
        self.grid_layout.addWidget(spin_trials, row_idx, 2)
        self.grid_layout.addWidget(btn_remove, row_idx, 3)

        self.block_rows.append(row_data)
        self._update_info()

    def _remove_block_row(self, row_data):
        """Supprime une ligne de bloc."""
        if len(self.block_rows) <= 1:
            return  # Garder au moins un bloc

        for widget in [row_data['label'], row_data['combo'],
                       row_data['spin'], row_data['btn']]:
            self.grid_layout.removeWidget(widget)
            widget.deleteLater()

        self.block_rows.remove(row_data)

        # Renuméroter
        for i, rd in enumerate(self.block_rows):
            rd['label'].setText(str(i + 1))

        self._update_info()

    def _update_info(self):
        """Met à jour le label d'info."""
        try:
            blocks = self.get_block_sequence()
            total = sum(b['n_trials'] for b in blocks)
            rest = self.spin_rest.value()

            seq_str = " → ".join(f"{b['level']}-back({b['n_trials']})" for b in blocks)

            trial_dur = 2.5
            task_time = total * trial_dur
            rest_time = rest * (len(blocks) + 1)
            instr_time = len(blocks) * 6.0
            total_time = task_time + rest_time + instr_time

            self.label_info.setText(
                f"{seq_str}\n"
                f"Total: {total} essais | ~{total_time/60:.1f} min"
            )
        except Exception:
            self.label_info.setText("⚠ Configuration invalide")

    def get_block_sequence(self):
        """Retourne la séquence sous forme de list[dict]."""
        blocks = []
        for rd in self.block_rows:
            level = rd['combo'].currentData()
            trials = rd['spin'].value()
            blocks.append({'level': level, 'n_trials': trials})
        return blocks

    def get_rest_duration(self):
        return self.spin_rest.value()


class NBackTab(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.init_ui()

    def init_ui(self):
        # Scroll area pour tout le contenu
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout()
        content.setLayout(layout)

        # ==========================================
        # DESIGNS PRÉDÉFINIS
        # ==========================================
        design_group = QGroupBox("Designs prédéfinis (fMRI)")
        design_layout = QVBoxLayout()

        # Sélecteur de design
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Design :"))
        self.combo_design = QComboBox()
        for did, spec in DESIGN_SPECS.items():
            self.combo_design.addItem(f"Design {did} — {spec['name']}", did)
        self.combo_design.currentIndexChanged.connect(self._update_design_preview)
        selector_row.addWidget(self.combo_design)
        selector_row.addStretch()
        design_layout.addLayout(selector_row)

        # Preview du design
        self.design_preview = QTextEdit()
        self.design_preview.setReadOnly(True)
        self.design_preview.setMaximumHeight(200)
        self.design_preview.setFont(QFont("Consolas", 9))
        self.design_preview.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #555;"
        )
        design_layout.addWidget(self.design_preview)

        # Bouton lancer
        btn_design = QPushButton("▶  Lancer ce Design")
        btn_design.setStyleSheet(
            "QPushButton { padding: 8px; font-weight: bold; }"
        )
        btn_design.clicked.connect(self.run_design)
        design_layout.addWidget(btn_design)

        design_group.setLayout(design_layout)
        layout.addWidget(design_group)

        # ==========================================
        # TRAINING
        # ==========================================
        train_group = QGroupBox("Training (Entraînement)")
        train_layout = QVBoxLayout()

        train_layout.addWidget(QLabel(
            "Mode desktop, séquence simplifiée pour familiarisation."
        ))

        # Design de training
        train_design_row = QHBoxLayout()
        train_design_row.addWidget(QLabel("Basé sur le design :"))
        self.combo_train_design = QComboBox()
        self.combo_train_design.addItem("Simplifié (1 bloc/niveau, 8 essais)", 0)
        for did, spec in DESIGN_SPECS.items():
            self.combo_train_design.addItem(
                f"Design {did} (essais réduits)", did
            )
        train_design_row.addWidget(self.combo_train_design)
        train_design_row.addStretch()
        train_layout.addLayout(train_design_row)

        # Nombre d'essais par bloc (training)
        train_trials_row = QHBoxLayout()
        train_trials_row.addWidget(QLabel("Essais par bloc :"))
        self.spin_train_trials = QSpinBox()
        self.spin_train_trials.setRange(3, 30)
        self.spin_train_trials.setValue(8)
        train_trials_row.addWidget(self.spin_train_trials)
        train_trials_row.addStretch()
        train_layout.addLayout(train_trials_row)

        btn_train = QPushButton("▶  Lancer Training")
        btn_train.clicked.connect(self.run_training)
        train_layout.addWidget(btn_train)

        train_group.setLayout(train_layout)
        layout.addWidget(train_group)

        # ==========================================
        # CUSTOM
        # ==========================================
        custom_group = QGroupBox("Design personnalisé")
        custom_layout = QVBoxLayout()

        custom_layout.addWidget(QLabel(
            "Construisez votre propre séquence de blocs :"
        ))

        self.custom_editor = CustomBlockEditor()
        custom_layout.addWidget(self.custom_editor)

        btn_custom = QPushButton("▶  Lancer Custom")
        btn_custom.clicked.connect(self.run_custom)
        custom_layout.addWidget(btn_custom)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        layout.addStretch()

        scroll.setWidget(content)

        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

        # Init preview
        self._update_design_preview()

    # =========================================================================
    # PREVIEW
    # =========================================================================

    def _update_design_preview(self):
        """Met à jour l'aperçu du design sélectionné."""
        design_id = self.combo_design.currentData()
        if design_id and design_id in DESIGN_SPECS:
            self.design_preview.setText(_format_design_summary(design_id))

    # =========================================================================
    # PARAMÈTRES COMMUNS
    # =========================================================================

    def get_common(self):
        return {
            'tache': 'NBack',
            'target_ratio': 0.33,
        }

    # =========================================================================
    # LANCEURS
    # =========================================================================

    def run_design(self):
        """Lance un design prédéfini."""
        design_id = self.combo_design.currentData()
        if not design_id:
            return

        params = self.get_common()
        params.update({
            'run_type': 'base',
            'design_id': design_id,
        })
        self.parent_menu.run_experiment(params)

    def run_training(self):
        """Lance le training."""
        train_source = self.combo_train_design.currentData()
        n_trials = self.spin_train_trials.value()

        if train_source == 0:
            # Training simplifié : 1 bloc de chaque niveau basique
            block_sequence = [
                {'level': 0, 'n_trials': n_trials},
                {'level': 1, 'n_trials': n_trials},
                {'level': 2, 'n_trials': n_trials},
            ]
            rest_duration = 5.0
        else:
            # Basé sur un design existant mais avec essais réduits
            spec = DESIGN_SPECS[train_source]
            block_sequence = [
                {'level': level, 'n_trials': n_trials}
                for level, _ in spec['blocks']
            ]
            rest_duration = 5.0

        params = self.get_common()
        params.update({
            'run_type': 'training',
            'design_id': None,
            'block_sequence': block_sequence,
            'rest_duration': rest_duration,
        })
        self.parent_menu.run_experiment(params)

    def run_custom(self):
        """Lance un design personnalisé."""
        block_sequence = self.custom_editor.get_block_sequence()
        rest_duration = self.custom_editor.get_rest_duration()

        if not block_sequence:
            return

        params = self.get_common()
        params.update({
            'run_type': 'custom',
            'design_id': None,
            'block_sequence': block_sequence,
            'rest_duration': rest_duration,
        })
        self.parent_menu.run_experiment(params)
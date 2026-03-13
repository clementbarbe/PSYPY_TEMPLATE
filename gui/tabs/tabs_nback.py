from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLabel, QSpinBox, QPushButton, QCheckBox,
                             QGridLayout, QFrame)
from PyQt6.QtCore import Qt


class NBackLevelConfig(QFrame):
    """
    Widget réutilisable : configuration des niveaux N-Back.
    Affiche une ligne par niveau avec checkbox + spinbox essais.
    """

    AVAILABLE_LEVELS = [0, 1, 2, 3]

    def __init__(self, default_levels=(1, 2, 3), default_trials=15, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.checkboxes = {}
        self.spinboxes = {}
        self._init_ui(default_levels, default_trials)

    def _init_ui(self, default_levels, default_trials):
        grid = QGridLayout()
        self.setLayout(grid)

        # Header
        grid.addWidget(QLabel("Actif"), 0, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(QLabel("Niveau"), 0, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(QLabel("Essais / bloc"), 0, 2, alignment=Qt.AlignmentFlag.AlignCenter)

        for row, n in enumerate(self.AVAILABLE_LEVELS, start=1):
            # Checkbox
            cb = QCheckBox()
            cb.setChecked(n in default_levels)
            self.checkboxes[n] = cb
            grid.addWidget(cb, row, 0, alignment=Qt.AlignmentFlag.AlignCenter)

            # Label niveau
            if n == 0:
                label_text = "0-back (cible = 'X')"
            else:
                label_text = f"{n}-back"
            grid.addWidget(QLabel(label_text), row, 1)

            # Spinbox essais
            spin = QSpinBox()
            spin.setRange(3, 100)
            spin.setValue(default_trials if isinstance(default_trials, int)
                         else default_trials[row - 1] if row - 1 < len(default_trials)
                         else 15)
            self.spinboxes[n] = spin
            grid.addWidget(spin, row, 2)

            # Lier l'état du checkbox au spinbox
            cb.toggled.connect(spin.setEnabled)
            spin.setEnabled(cb.isChecked())

    def get_config(self):
        """
        Retourne les deux listes parallèles :
            n_levels:        tuple d'ints  (ex: (1, 2, 3))
            trials_per_level: tuple d'ints (ex: (15, 15, 15))

        Raises:
            ValueError si aucun niveau n'est sélectionné.
        """
        n_levels = []
        trials = []
        for n in self.AVAILABLE_LEVELS:
            if self.checkboxes[n].isChecked():
                n_levels.append(n)
                trials.append(self.spinboxes[n].value())

        if not n_levels:
            raise ValueError("Au moins un niveau N-Back doit être sélectionné.")

        return tuple(n_levels), tuple(trials)

    def get_total_trials(self, blocks_per_level):
        """Calcule le nombre total d'essais pour l'affichage."""
        try:
            n_levels, trials = self.get_config()
            return sum(t * blocks_per_level for t in trials)
        except ValueError:
            return 0


class NBackTab(QWidget):
    def __init__(self, parent_menu):
        super().__init__()
        self.parent_menu = parent_menu
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # ==========================================
        # TRAINING
        # ==========================================
        train_group = QGroupBox("Training (Entraînement)")
        train_layout = QVBoxLayout()

        # Niveaux + essais par niveau
        train_layout.addWidget(QLabel("Niveaux et essais :"))
        self.train_levels = NBackLevelConfig(
            default_levels=(1, 2),
            default_trials=8
        )
        train_layout.addWidget(self.train_levels)

        # Blocs par niveau
        train_blocks_row = QHBoxLayout()
        train_blocks_row.addWidget(QLabel("Blocs par niveau :"))
        self.spin_train_blocks = QSpinBox()
        self.spin_train_blocks.setRange(1, 10)
        self.spin_train_blocks.setValue(1)
        train_blocks_row.addWidget(self.spin_train_blocks)
        train_blocks_row.addStretch()
        train_layout.addLayout(train_blocks_row)

        # Info + bouton
        self.label_train_info = QLabel("")
        self.label_train_info.setStyleSheet("color: grey; font-style: italic;")
        train_layout.addWidget(self.label_train_info)

        btn_train = QPushButton("▶  Lancer Training")
        btn_train.clicked.connect(self.run_training)
        train_layout.addWidget(btn_train)

        train_group.setLayout(train_layout)
        layout.addWidget(train_group)

        # ==========================================
        # BASE (IRMf)
        # ==========================================
        base_group = QGroupBox("Run Base (IRMf)")
        base_layout = QVBoxLayout()

        base_layout.addWidget(QLabel("Niveaux et essais :"))
        self.base_levels = NBackLevelConfig(
            default_levels=(0, 1, 2, 3),
            default_trials=15
        )
        base_layout.addWidget(self.base_levels)

        base_blocks_row = QHBoxLayout()
        base_blocks_row.addWidget(QLabel("Blocs par niveau :"))
        self.spin_base_blocks = QSpinBox()
        self.spin_base_blocks.setRange(1, 10)
        self.spin_base_blocks.setValue(3)
        base_blocks_row.addWidget(self.spin_base_blocks)
        base_blocks_row.addStretch()
        base_layout.addLayout(base_blocks_row)

        self.label_base_info = QLabel("")
        self.label_base_info.setStyleSheet("color: grey; font-style: italic;")
        base_layout.addWidget(self.label_base_info)

        btn_base = QPushButton("▶  Lancer Run Base")
        btn_base.clicked.connect(self.run_base)
        base_layout.addWidget(btn_base)

        base_group.setLayout(base_layout)
        layout.addWidget(base_group)

        # ==========================================
        # CUSTOM
        # ==========================================
        custom_group = QGroupBox("Run Personnalisé")
        custom_layout = QVBoxLayout()

        custom_id_row = QHBoxLayout()
        custom_id_row.addWidget(QLabel("ID du Run :"))
        self.spin_custom_idx = QSpinBox()
        self.spin_custom_idx.setRange(1, 99)
        self.spin_custom_idx.setValue(1)
        custom_id_row.addWidget(self.spin_custom_idx)
        custom_id_row.addStretch()
        custom_layout.addLayout(custom_id_row)

        custom_layout.addWidget(QLabel("Niveaux et essais :"))
        self.custom_levels = NBackLevelConfig(
            default_levels=(1, 2, 3),
            default_trials=15
        )
        custom_layout.addWidget(self.custom_levels)

        custom_blocks_row = QHBoxLayout()
        custom_blocks_row.addWidget(QLabel("Blocs par niveau :"))
        self.spin_custom_blocks = QSpinBox()
        self.spin_custom_blocks.setRange(1, 10)
        self.spin_custom_blocks.setValue(3)
        custom_blocks_row.addWidget(self.spin_custom_blocks)
        custom_blocks_row.addStretch()
        custom_layout.addLayout(custom_blocks_row)

        self.label_custom_info = QLabel("")
        self.label_custom_info.setStyleSheet("color: grey; font-style: italic;")
        custom_layout.addWidget(self.label_custom_info)

        btn_custom = QPushButton("▶  Lancer Custom")
        btn_custom.clicked.connect(self.run_custom)
        custom_layout.addWidget(btn_custom)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        layout.addStretch()

        # --- Connecter les mises à jour du compteur ---
        self._connect_info_updates()
        self._update_all_info()

    # =========================================================================
    # MISE À JOUR DES LABELS D'INFO
    # =========================================================================

    def _connect_info_updates(self):
        """Connecte tous les widgets pour mettre à jour le compteur en temps réel."""
        # Training
        self.spin_train_blocks.valueChanged.connect(self._update_all_info)
        for cb in self.train_levels.checkboxes.values():
            cb.toggled.connect(self._update_all_info)
        for spin in self.train_levels.spinboxes.values():
            spin.valueChanged.connect(self._update_all_info)

        # Base
        self.spin_base_blocks.valueChanged.connect(self._update_all_info)
        for cb in self.base_levels.checkboxes.values():
            cb.toggled.connect(self._update_all_info)
        for spin in self.base_levels.spinboxes.values():
            spin.valueChanged.connect(self._update_all_info)

        # Custom
        self.spin_custom_blocks.valueChanged.connect(self._update_all_info)
        for cb in self.custom_levels.checkboxes.values():
            cb.toggled.connect(self._update_all_info)
        for spin in self.custom_levels.spinboxes.values():
            spin.valueChanged.connect(self._update_all_info)

    def _format_info(self, level_config, blocks_per_level):
        """Génère le texte récapitulatif."""
        try:
            n_levels, trials = level_config.get_config()
            total = sum(t * blocks_per_level for t in trials)
            details = ", ".join(f"{n}-back: {t}×{blocks_per_level}" for n, t in zip(n_levels, trials))
            return f"→ {details}  |  Total : {total} essais"
        except ValueError:
            return "⚠ Aucun niveau sélectionné"

    def _update_all_info(self):
        self.label_train_info.setText(
            self._format_info(self.train_levels, self.spin_train_blocks.value())
        )
        self.label_base_info.setText(
            self._format_info(self.base_levels, self.spin_base_blocks.value())
        )
        self.label_custom_info.setText(
            self._format_info(self.custom_levels, self.spin_custom_blocks.value())
        )

    # =========================================================================
    # PARAMÈTRES COMMUNS
    # =========================================================================

    def get_common(self):
        """Retourne les paramètres communs (timing, etc.)."""
        return {
            'tache': 'NBack',
            'stim_duration': 0.5,
            'isi_duration': 2.0,
            'target_ratio': 0.33,
        }

    # =========================================================================
    # LANCEURS
    # =========================================================================

    def run_training(self):
        try:
            n_levels, trials_per_level = self.train_levels.get_config()
        except ValueError as e:
            self.label_train_info.setText(f"⚠ {e}")
            return

        params = self.get_common()
        params.update({
            'run_type': 'training',
            'run_id': '00',
            'n_levels': n_levels,
            'trials_per_level': trials_per_level,
            'blocks_per_level': self.spin_train_blocks.value(),
        })
        self.parent_menu.run_experiment(params)

    def run_base(self):
        try:
            n_levels, trials_per_level = self.base_levels.get_config()
        except ValueError as e:
            self.label_base_info.setText(f"⚠ {e}")
            return

        params = self.get_common()
        params.update({
            'run_type': 'base',
            'run_id': '01',
            'n_levels': n_levels,
            'trials_per_level': trials_per_level,
            'blocks_per_level': self.spin_base_blocks.value(),
        })
        self.parent_menu.run_experiment(params)

    def run_custom(self):
        try:
            n_levels, trials_per_level = self.custom_levels.get_config()
        except ValueError as e:
            self.label_custom_info.setText(f"⚠ {e}")
            return

        params = self.get_common()
        params.update({
            'run_type': 'custom',
            'run_id': str(self.spin_custom_idx.value()).zfill(2),
            'n_levels': n_levels,
            'trials_per_level': trials_per_level,
            'blocks_per_level': self.spin_custom_blocks.value(),
        })
        self.parent_menu.run_experiment(params)
# nback.py
"""
N-Back Task — Version fMRI avec designs prédéfinis.

Designs supportés :
    1. 0 vs 2-back (standard ~8min)
    2. 0 vs 2-back (dense optimisé)
    3. 1-2-3-back (paramétrique simple)
    4. 1-2-3-back (randomisé optimisé)
    custom: ordre libre via paramètres

0-back : Une lettre cible est affichée dans la consigne de bloc.
         Le participant appuie quand il voit CETTE lettre.
N-back (N≥1) : Appuyer quand la lettre est identique à celle N essais avant.
"""

import random
import os
from datetime import datetime
from psychopy import visual, core
from utils.base_task import BaseTask


# =============================================================================
# DESIGNS PRÉDÉFINIS
# =============================================================================

DESIGNS = {
    1: {
        'name': '0 vs 2-back (standard ~8min)',
        'description': '3 blocs/condition, alternance 0-back / 2-back',
        'rest_duration': 12.0,
        'trials_per_block': 25,
        'stim_duration': 0.5,
        'isi_duration': 2.0,
        'block_sequence': [
            {'level': 0, 'n_trials': 25},
            {'level': 2, 'n_trials': 25},
            {'level': 2, 'n_trials': 25},
            {'level': 0, 'n_trials': 25},
            {'level': 2, 'n_trials': 25},
            {'level': 0, 'n_trials': 25},
        ],
    },
    2: {
        'name': '0 vs 2-back (dense optimisé)',
        'description': 'Plus de transitions, moins fatigant',
        'rest_duration': 10.0,
        'trials_per_block': 20,
        'stim_duration': 0.5,
        'isi_duration': 2.0,
        'block_sequence': [
            {'level': 0, 'n_trials': 20},
            {'level': 2, 'n_trials': 20},
            {'level': 2, 'n_trials': 20},
            {'level': 0, 'n_trials': 20},
            {'level': 2, 'n_trials': 20},
            {'level': 0, 'n_trials': 20},
        ],
    },
    3: {
        'name': '1-2-3-back (paramétrique simple)',
        'description': '2 blocs/condition, régression paramétrique 3>2>1',
        'rest_duration': 12.0,
        'trials_per_block': 25,
        'stim_duration': 0.5,
        'isi_duration': 2.0,
        'block_sequence': [
            {'level': 1, 'n_trials': 25},
            {'level': 2, 'n_trials': 25},
            {'level': 3, 'n_trials': 25},
            {'level': 2, 'n_trials': 25},
            {'level': 1, 'n_trials': 25},
            {'level': 3, 'n_trials': 25},
        ],
    },
    4: {
        'name': '1-2-3-back (randomisé optimisé)',
        'description': 'Moins prédictible, optimisé neuro',
        'rest_duration': 10.0,
        'trials_per_block': 20,
        'stim_duration': 0.5,
        'isi_duration': 2.0,
        'block_sequence': [
            {'level': 2, 'n_trials': 20},
            {'level': 1, 'n_trials': 20},
            {'level': 3, 'n_trials': 20},
            {'level': 2, 'n_trials': 20},
            {'level': 3, 'n_trials': 20},
            {'level': 1, 'n_trials': 20},
        ],
    },
}


class NBack(BaseTask):
    """
    Tâche N-Back fMRI avec designs prédéfinis.

    Paradigme Go/No-Go :
        0-back : Appuyer quand la lettre == lettre cible (affichée en consigne).
        N-back : Appuyer quand la lettre == lettre N essais avant.
        Sinon  : Ne rien faire.
    """

    # Lettres cibles possibles pour le 0-back (consonnes faciles à mémoriser)
    ZERO_BACK_TARGETS = ['B', 'D', 'K', 'M', 'R', 'T']

    CONSONANTS = [
        'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K',
        'L', 'M', 'N', 'P', 'R', 'S', 'T', 'V', 'W', 'Z'
    ]

    def __init__(self, win, nom, session='01', mode='fmri',
                 design_id=1, run_type='base',
                 # Overrides manuels (ignorés si design_id est fourni)
                 block_sequence=None, rest_duration=None,
                 stim_duration=None, isi_duration=None,
                 # Paramètres fixes
                 target_ratio=0.33, instruction_duration=4.0,
                 pre_block_fixation=2.0,
                 enregistrer=True, eyetracker_actif=False, parport_actif=True,
                 **kwargs):
        """
        Args:
            design_id:          int (1-4) pour un design prédéfini, ou None pour custom.
            block_sequence:     list[dict] si design_id is None.
                                Chaque dict : {'level': int, 'n_trials': int}
            rest_duration:      override du repos inter-blocs (s).
            stim_duration:      override durée stimulus (s).
            isi_duration:       override ISI (s).
            target_ratio:       proportion de cibles par bloc.
            instruction_duration: durée consigne de bloc (s).
            pre_block_fixation: fixation avant le premier essai du bloc (s).
        """

        super().__init__(
            win=win,
            nom=nom,
            session=session,
            task_name="NBack",
            folder_name="n_back",
            eyetracker_actif=eyetracker_actif,
            parport_actif=parport_actif,
            enregistrer=enregistrer,
            et_prefix='NBK'
        )

        self.mode = mode.lower()
        self.run_type = run_type.lower()
        self.target_ratio = target_ratio
        self.instruction_duration = instruction_duration
        self.pre_block_fixation = pre_block_fixation

        # --- Résolution du design ---
        self.design_id = design_id
        self._resolve_design(design_id, block_sequence,
                             rest_duration, stim_duration, isi_duration)

        self.global_records = []

        self._define_ttl_codes()
        self._setup_key_mapping()
        self._setup_task_stimuli()
        self._init_incremental_file(suffix=f"_{self.run_type}")

        # Log
        self._log_design_summary()

    # =========================================================================
    # RÉSOLUTION DU DESIGN
    # =========================================================================

    def _resolve_design(self, design_id, block_sequence,
                        rest_duration, stim_duration, isi_duration):
        """
        Charge un design prédéfini ou accepte un design custom.
        Les overrides manuels ont priorité sur les valeurs du design.
        """
        if design_id is not None and design_id in DESIGNS:
            design = DESIGNS[design_id]
            self.design_name = design['name']
            self.block_sequence = design['block_sequence']
            self.rest_duration = rest_duration or design['rest_duration']
            self.stim_duration = stim_duration or design['stim_duration']
            self.isi_duration = isi_duration or design['isi_duration']

        elif block_sequence is not None:
            self.design_name = 'Custom'
            self.block_sequence = block_sequence
            self.rest_duration = rest_duration or 10.0
            self.stim_duration = stim_duration or 0.5
            self.isi_duration = isi_duration or 2.0

        else:
            raise ValueError(
                f"design_id={design_id} invalide et pas de block_sequence fourni.\n"
                f"Designs disponibles : {list(DESIGNS.keys())}"
            )

        # Validation
        for i, blk in enumerate(self.block_sequence):
            if 'level' not in blk or 'n_trials' not in blk:
                raise ValueError(
                    f"Bloc {i} invalide : chaque bloc doit avoir 'level' et 'n_trials'.\n"
                    f"Reçu : {blk}"
                )

        # Niveaux uniques utilisés dans ce design
        self.levels_used = sorted(set(b['level'] for b in self.block_sequence))

    def _log_design_summary(self):
        """Log un résumé clair du design."""
        n_blocks = len(self.block_sequence)
        total_trials = sum(b['n_trials'] for b in self.block_sequence)

        # Durée estimée
        trial_dur = self.stim_duration + self.isi_duration
        task_time = sum(b['n_trials'] * trial_dur for b in self.block_sequence)
        rest_time = self.rest_duration * (n_blocks + 1)  # rest avant + entre + après
        instr_time = n_blocks * (self.instruction_duration + self.pre_block_fixation)
        total_time = task_time + rest_time + instr_time

        seq_str = " → ".join(
            f"{b['level']}-back({b['n_trials']})" for b in self.block_sequence
        )

        self.logger.ok("=" * 60)
        self.logger.ok(f"DESIGN : {self.design_name}")
        self.logger.ok(f"  Séquence : {seq_str}")
        self.logger.ok(f"  Blocs: {n_blocks} | Essais total: {total_trials}")
        self.logger.ok(f"  Repos inter-blocs: {self.rest_duration}s")
        self.logger.ok(f"  Timing: stim={self.stim_duration}s ISI={self.isi_duration}s")
        self.logger.ok(f"  Durée estimée: ~{total_time/60:.1f} min")
        self.logger.ok(f"  Niveaux: {self.levels_used}")
        self.logger.ok("=" * 60)

    # =========================================================================
    # INITIALISATION
    # =========================================================================

    def _define_ttl_codes(self):
        """Triggers EEG / port parallèle."""
        self.codes = {
            'start_exp':            255,
            'end_exp':              254,
            'stim_target':          100,
            'stim_nontarget':       101,
            'response_hit':         150,
            'response_false_alarm': 151,
            'rest_start':           200,
            'rest_end':             201,
            'instruction_onset':    210,
        }
        for n in range(4):
            self.codes[f'block_{n}back'] = 10 + n

    def _setup_key_mapping(self):
        """
        Go/No-Go : une seule touche de réponse.
        """
        if self.mode == 'fmri':
            self.key_go = 'b'
            self.key_trigger = 't'
        else:
            self.key_go = 'space'
            self.key_trigger = 't'

        self.valid_keys = [self.key_go]
        self.logger.log(
            f"Keys → Go: [{self.key_go}] | No-Go: rien | Trigger: [{self.key_trigger}]"
        )

    def _setup_task_stimuli(self):
        """Stimuli visuels."""
        self.letter_stim = visual.TextStim(
            self.win, text="", color='white', height=0.15,
            pos=(0, 0), bold=True
        )
        self.instruction_text = visual.TextStim(
            self.win, text="", color='yellow', height=0.07,
            pos=(0, 0), wrapWidth=1.5
        )
        self.target_cue = visual.TextStim(
            self.win, text="", color='cyan', height=0.20,
            pos=(0, 0.15), bold=True
        )
        self.fixation_cross = visual.TextStim(
            self.win, text="+", color='white', height=0.1, pos=(0, 0)
        )
        self.logger.log("Stimuli visuels chargés.")

    # =========================================================================
    # GÉNÉRATION DE SÉQUENCE
    # =========================================================================

    def _pick_zero_back_target(self):
        """Choisit aléatoirement une lettre cible pour un bloc 0-back."""
        return random.choice(self.ZERO_BACK_TARGETS)

    def _generate_sequence(self, n_level, n_trials, zero_back_target=None):
        """
        Génère une séquence de lettres pour un bloc.

        Args:
            n_level:          niveau N-Back (0, 1, 2, 3).
            n_trials:         nombre d'essais dans ce bloc.
            zero_back_target: lettre cible pour le 0-back (ignoré si n_level > 0).

        Returns:
            (list[str], list[bool]): séquence de lettres, liste is_target.
        """
        sequence = []
        is_target_list = []

        num_targets = max(1, int(n_trials * self.target_ratio))

        if n_level == 0:
            # --- 0-BACK ---
            target_letter = zero_back_target or self._pick_zero_back_target()

            # Positions des cibles
            all_positions = list(range(n_trials))
            num_targets = min(num_targets, n_trials)
            target_indices = set(random.sample(all_positions, num_targets))

            for i in range(n_trials):
                if i in target_indices:
                    sequence.append(target_letter)
                    is_target_list.append(True)
                else:
                    available = [c for c in self.CONSONANTS if c != target_letter]
                    # Éviter répétition immédiate
                    if i > 0 and sequence[i - 1] in available and len(available) > 1:
                        available = [c for c in available if c != sequence[i - 1]]
                    sequence.append(random.choice(available))
                    is_target_list.append(False)

        else:
            # --- N-BACK (N ≥ 1) ---
            possible_target_idx = list(range(n_level, n_trials))
            num_targets = min(num_targets, len(possible_target_idx))
            target_indices = set(random.sample(possible_target_idx, num_targets))

            for i in range(n_trials):
                if i in target_indices:
                    is_target_list.append(True)
                    sequence.append(sequence[i - n_level])
                else:
                    is_target_list.append(False)
                    available = self.CONSONANTS.copy()

                    # Ne pas créer de match accidentel
                    if i >= n_level:
                        forbidden = sequence[i - n_level]
                        if forbidden in available:
                            available.remove(forbidden)

                    # Anti-lure : pas de répétition directe (sauf 1-back)
                    if n_level != 1 and i > 0:
                        prev = sequence[i - 1]
                        if prev in available and len(available) > 1:
                            available.remove(prev)

                    if not available:
                        available = self.CONSONANTS.copy()

                    sequence.append(random.choice(available))

        return sequence, is_target_list

    # =========================================================================
    # CLASSIFICATION SDT
    # =========================================================================

    def _classify_response(self, is_target, responded):
        """Signal Detection Theory : Hit, Miss, FA, CR."""
        if is_target:
            hit = responded
            return {
                'hit': int(hit), 'miss': int(not hit),
                'false_alarm': 0, 'correct_rejection': 0,
                'is_correct': int(hit),
            }
        else:
            cr = not responded
            return {
                'hit': 0, 'miss': 0,
                'false_alarm': int(not cr), 'correct_rejection': int(cr),
                'is_correct': int(cr),
            }

    def log_trial(self, block_idx, n_level, n_trials_in_block,
                  trial_idx, letter, is_target, responded, rt,
                  zero_back_target=None):
        """Enregistre un essai."""
        sdt = self._classify_response(is_target, responded)

        record = {
            'participant':          self.nom,
            'session':              self.session,
            'design_id':            self.design_id or 'custom',
            'design_name':          self.design_name,
            'run_type':             self.run_type,
            'mode':                 self.mode,
            'block_idx':            block_idx,
            'n_level':              n_level,
            'n_level_label':        f"{n_level}-back",
            'n_trials_in_block':    n_trials_in_block,
            'trial_idx':            trial_idx,
            'letter':               letter,
            'zero_back_target':     zero_back_target if n_level == 0 else '',
            'is_target':            int(is_target),
            'responded':            int(responded),
            'rt':                   round(rt, 4) if rt is not None else -1,
            'is_correct':           sdt['is_correct'],
            'hit':                  sdt['hit'],
            'miss':                 sdt['miss'],
            'false_alarm':          sdt['false_alarm'],
            'correct_rejection':    sdt['correct_rejection'],
            'stim_duration':        self.stim_duration,
            'isi_duration':         self.isi_duration,
            'rest_duration':        self.rest_duration,
            'task_time':            round(self.task_clock.getTime(), 4),
            'timestamp':            datetime.now().strftime('%H:%M:%S.%f'),
        }

        self.global_records.append(record)
        self.save_trial_incremental(record)

    # =========================================================================
    # ESSAI
    # =========================================================================

    def run_trial(self, letter, is_target, block_idx, n_level,
                  n_trials_in_block, trial_idx, zero_back_target=None):
        """
        Un essai : Lettre → ISI (fixation).
        Collecte la réponse pendant les deux phases.
        """
        # --- Affichage lettre ---
        self.letter_stim.text = letter
        self.letter_stim.draw()
        self.win.flip()
        stim_onset = self.task_clock.getTime()

        ttl = self.codes['stim_target'] if is_target else self.codes['stim_nontarget']
        if self.parport_actif:
            self.send_trigger(ttl)
        if self.eyetracker_actif:
            tag = 'TGT' if is_target else 'NTG'
            self.EyeTracker.send_message(
                f"STIM_{letter}_{tag}_B{block_idx}_T{trial_idx}"
            )

        self.flush_keyboard()
        responded = False
        rt = None

        # --- Phase stimulus ---
        stim_end = stim_onset + self.stim_duration
        while self.task_clock.getTime() < stim_end:
            keys = self.get_keys(key_list=self.valid_keys)
            if keys and not responded:
                responded = True
                rt = keys[0].rt - stim_onset
                if self.parport_actif:
                    code = (self.codes['response_hit'] if is_target
                            else self.codes['response_false_alarm'])
                    self.send_trigger(code)

        # --- Phase ISI ---
        self.fixation_cross.draw()
        self.win.flip()
        isi_end = self.task_clock.getTime() + self.isi_duration

        while self.task_clock.getTime() < isi_end:
            if not responded:
                keys = self.get_keys(key_list=self.valid_keys)
                if keys:
                    responded = True
                    rt = keys[0].rt - stim_onset
                    if self.parport_actif:
                        code = (self.codes['response_hit'] if is_target
                                else self.codes['response_false_alarm'])
                        self.send_trigger(code)

        # --- Log ---
        self.log_trial(block_idx, n_level, n_trials_in_block,
                       trial_idx, letter, is_target, responded, rt,
                       zero_back_target)

    # =========================================================================
    # CONSIGNE DE BLOC
    # =========================================================================

    def _show_block_instruction(self, n_level, zero_back_target=None):
        """
        Affiche la consigne du bloc.

        0-back : montre la lettre cible en gros + explication.
        N-back : explication standard.
        """
        if self.parport_actif:
            self.send_trigger(self.codes['instruction_onset'])

        if n_level == 0:
            # --- Consigne 0-back avec lettre cible ---
            instr_line = (
                f"0-BACK\n\n"
                f"Appuyez sur [{self.key_go.upper()}]\n"
                f"quand vous voyez la lettre :"
            )
            self.instruction_text.text = instr_line
            self.instruction_text.pos = (0, -0.05)
            self.target_cue.text = zero_back_target
            self.target_cue.pos = (0, 0.25)

            # Affichage
            end_time = self.task_clock.getTime() + self.instruction_duration
            while self.task_clock.getTime() < end_time:
                self.target_cue.draw()
                self.instruction_text.draw()
                self.win.flip()
                self.get_keys(key_list=[])

            # Reset position
            self.instruction_text.pos = (0, 0)

        else:
            # --- Consigne N-back ---
            txt = (
                f"{n_level}-BACK\n\n"
                f"Appuyez sur [{self.key_go.upper()}]\n"
                f"si la lettre est la même\n"
                f"qu'il y a {n_level} essai{'s' if n_level > 1 else ''}.\n\n"
                f"Ne faites rien sinon."
            )
            self.instruction_text.text = txt

            end_time = self.task_clock.getTime() + self.instruction_duration
            while self.task_clock.getTime() < end_time:
                self.instruction_text.draw()
                self.win.flip()
                self.get_keys(key_list=[])

        if self.eyetracker_actif:
            msg = f"INSTR_{n_level}BACK"
            if n_level == 0:
                msg += f"_TARGET_{zero_back_target}"
            self.EyeTracker.send_message(msg)

    def _show_timed_fixation(self, duration):
        """Croix de fixation pendant `duration` secondes."""
        self.fixation_cross.draw()
        self.win.flip()
        end_time = self.task_clock.getTime() + duration
        while self.task_clock.getTime() < end_time:
            self.get_keys(key_list=[])

    # =========================================================================
    # BLOC
    # =========================================================================

    def run_block(self, block_idx, block_def):
        """
        Exécute un bloc complet.

        Args:
            block_idx: index du bloc (0-based).
            block_def: dict {'level': int, 'n_trials': int}.
        """
        n_level = block_def['level']
        n_trials = block_def['n_trials']

        self.logger.log(
            f"Block {block_idx} | {n_level}-Back | {n_trials} essais | START"
        )

        # Trigger bloc
        block_code_key = f'block_{n_level}back'
        if self.parport_actif and block_code_key in self.codes:
            self.send_trigger(self.codes[block_code_key])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(
                f"BLOCK_{block_idx}_{n_level}BACK_START"
            )

        # Choix cible 0-back
        zero_back_target = None
        if n_level == 0:
            zero_back_target = self._pick_zero_back_target()
            self.logger.log(f"  0-back cible : '{zero_back_target}'")

        # Consigne
        self._show_block_instruction(n_level, zero_back_target)

        # Fixation pré-bloc
        self._show_timed_fixation(self.pre_block_fixation)

        # Séquence
        sequence, is_target_list = self._generate_sequence(
            n_level, n_trials, zero_back_target
        )
        n_targets = sum(is_target_list)
        self.logger.log(
            f"  Séquence générée : {len(sequence)} essais, {n_targets} cibles"
        )

        # Essais
        for trial_idx, (letter, is_target) in enumerate(
            zip(sequence, is_target_list)
        ):
            self.run_trial(
                letter, is_target, block_idx, n_level,
                n_trials, trial_idx, zero_back_target
            )

        if self.eyetracker_actif:
            self.EyeTracker.send_message(
                f"BLOCK_{block_idx}_{n_level}BACK_END"
            )

        self.logger.log(f"Block {block_idx} | {n_level}-Back | END")

    # =========================================================================
    # REPOS
    # =========================================================================

    def _run_rest(self, label=""):
        """Repos inter-blocs avec triggers."""
        self.logger.log(f"Rest {self.rest_duration}s {label}")

        if self.parport_actif:
            self.send_trigger(self.codes['rest_start'])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(f"REST_START_{label}")

        self._show_timed_fixation(self.rest_duration)

        if self.parport_actif:
            self.send_trigger(self.codes['rest_end'])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(f"REST_END_{label}")

    # =========================================================================
    # SESSION
    # =========================================================================

    def _start_session(self):
        """Trigger IRM ou démarrage desktop."""
        if self.mode == 'fmri':
            self.wait_for_trigger(trigger_key=self.key_trigger)
        else:
            # Résumé du design pour le participant
            seq_str = " → ".join(
                f"{b['level']}-back({b['n_trials']})"
                for b in self.block_sequence
            )
            total_trials = sum(b['n_trials'] for b in self.block_sequence)

            self.show_instructions(
                text_override=(
                    f"N-Back — Mémoire de travail\n\n"
                    f"Design : {self.design_name}\n"
                    f"Séquence : {seq_str}\n"
                    f"Total : {total_trials} essais\n\n"
                    f"0-back : Appuyez sur [{self.key_go.upper()}] "
                    f"quand vous voyez la lettre cible.\n"
                    f"N-back : Appuyez sur [{self.key_go.upper()}] "
                    f"si la lettre = celle d'il y a N.\n"
                    f"Sinon : ne faites rien.\n\n"
                    "Appuyez sur une touche pour commencer."
                )
            )
            self.task_clock.reset()

        if self.parport_actif:
            self.send_trigger(self.codes['start_exp'])
        if self.eyetracker_actif:
            self.EyeTracker.start_recording()
            self.EyeTracker.send_message("START_EXP")

    def _end_session(self):
        """Nettoyage, sauvegarde finale, stats."""
        self.logger.log("Nettoyage et sauvegarde finale...")

        if self.parport_actif:
            try:
                self.send_trigger(self.codes['end_exp'])
            except Exception:
                pass

        if self.eyetracker_actif:
            try:
                self.EyeTracker.send_message("END_EXP")
                self.EyeTracker.stop_recording()
                self.EyeTracker.close_and_transfer_data(self.data_dir)
            except Exception as e:
                self.logger.err(f"EyeTracker cleanup error: {e}")

        saved_path = self.save_data(
            data_list=self.global_records,
            filename_suffix=f"_{self.run_type}"
        )

        # --- Stats ---
        if self.global_records:
            self._print_stats()

        # Écran de fin
        try:
            if self.win and not self.win._closed:
                self.instruction_text.text = (
                    "Fin de la session.\nMerci pour votre participation."
                )
                self.instruction_text.pos = (0, 0)
                self.instruction_text.draw()
                self.win.flip()
                core.wait(3.0)
        except Exception:
            self.logger.warn("Fenêtre déjà fermée.")

        # QC
        if saved_path and self.enregistrer:
            try:
                from tasks.qc.qc_nback import qc_nback
                qc_nback(saved_path)
            except Exception as e:
                self.logger.warn(f"QC auto-launch failed: {e}")

        return saved_path

    def _print_stats(self):
        """Affiche les statistiques de performance."""
        total = len(self.global_records)
        correct = sum(r['is_correct'] for r in self.global_records)
        hits = sum(r['hit'] for r in self.global_records)
        misses = sum(r['miss'] for r in self.global_records)
        fas = sum(r['false_alarm'] for r in self.global_records)
        crs = sum(r['correct_rejection'] for r in self.global_records)

        self.logger.ok(
            f"GLOBAL : {correct}/{total} ({100*correct/total:.1f}%) | "
            f"Hit={hits} Miss={misses} FA={fas} CR={crs}"
        )

        # Par niveau
        try:
            from collections import defaultdict
            by_level = defaultdict(list)
            for r in self.global_records:
                by_level[r['n_level']].append(r)

            for level in sorted(by_level.keys()):
                records = by_level[level]
                n = len(records)
                acc = 100 * sum(r['is_correct'] for r in records) / n
                h = sum(r['hit'] for r in records)
                m = sum(r['miss'] for r in records)
                fa = sum(r['false_alarm'] for r in records)
                cr = sum(r['correct_rejection'] for r in records)
                mean_rt = [r['rt'] for r in records if r['rt'] > 0]
                rt_str = f"{sum(mean_rt)/len(mean_rt)*1000:.0f}ms" if mean_rt else "N/A"

                self.logger.log(
                    f"  {level}-back: {acc:.1f}% ({n} essais) | "
                    f"H={h} M={m} FA={fa} CR={cr} | RT={rt_str}"
                )
        except Exception:
            pass

    # =========================================================================
    # POINT D'ENTRÉE
    # =========================================================================

    def run(self):
        """Point d'entrée principal."""
        self.logger.ok("=" * 60)
        self.logger.ok(
            f"N-Back | {self.nom} | Session {self.session} | "
            f"{self.mode} | Design: {self.design_name}"
        )
        self.logger.ok("=" * 60)

        saved_path = None

        try:
            self._start_session()

            # Rest initial
            self._run_rest(label="initial")

            # Boucle des blocs
            for block_idx, block_def in enumerate(self.block_sequence):
                self.run_block(block_idx, block_def)

                # Rest après chaque bloc (y compris le dernier → rest final)
                self._run_rest(label=f"after_block_{block_idx}")

            self.logger.ok("Tâche terminée avec succès.")

        except (KeyboardInterrupt, SystemExit):
            self.logger.warn("Interruption manuelle (Quit).")

        except Exception as e:
            self.logger.err(f"CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            raise

        finally:
            saved_path = self._end_session()

        return saved_path
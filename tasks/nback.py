# nback.py
import random
import os
from datetime import datetime
from psychopy import visual, core
from utils.base_task import BaseTask


class NBack(BaseTask):
    """
    Tâche de mémoire de travail N-Back — Version Go/No-Go.

    Paradigme :
        - Appuyer sur la touche quand la lettre EST une cible (Go).
        - Ne rien faire quand la lettre N'EST PAS une cible (No-Go).

    Paramétrage par listes parallèles :
        - n_levels :        (1, 2, 3)       → niveaux N-Back
        - trials_per_level : (15, 15, 15)   → essais par bloc pour chaque niveau
    """

    def __init__(self, win, nom, session='01', mode='fmri', run_type='base',
                 n_levels=(1, 2, 3), trials_per_level=(15, 15, 15),
                 blocks_per_level=3, stim_duration=0.5, isi_duration=2.0,
                 target_ratio=0.33, rest_duration=8.0, instruction_duration=3.0,
                 pre_block_fixation=2.0,
                 enregistrer=True, eyetracker_actif=False, parport_actif=True,
                 **kwargs):
        """
        Initialise la tâche N-Back Go/No-Go.

        Args:
            n_levels:           tuple/list des niveaux N-Back (ex: (1, 2, 3)).
            trials_per_level:   tuple/list du nombre d'essais par bloc pour chaque niveau.
                                Doit avoir la même longueur que n_levels.
            blocks_per_level:   nombre de répétitions de chaque niveau.
            stim_duration:      durée d'affichage de la lettre (s).
            isi_duration:       durée de l'intervalle inter-stimulus (s).
            target_ratio:       proportion de cibles par bloc.
            rest_duration:      durée du repos inter-blocs (s).
            instruction_duration: durée d'affichage des instructions de bloc (s).
            pre_block_fixation: durée de la fixation pré-bloc (s).
            mode:               'fmri' ou 'pc'.
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

        # --- Validation des listes parallèles ---
        self.n_levels = list(n_levels)
        self.trials_per_level = list(trials_per_level)

        if len(self.n_levels) != len(self.trials_per_level):
            raise ValueError(
                f"n_levels ({len(self.n_levels)}) et trials_per_level "
                f"({len(self.trials_per_level)}) doivent avoir la même longueur.\n"
                f"  n_levels        = {self.n_levels}\n"
                f"  trials_per_level = {self.trials_per_level}"
            )

        # Dictionnaire niveau → nombre d'essais par bloc
        self.level_trials = dict(zip(self.n_levels, self.trials_per_level))

        self.blocks_per_level = blocks_per_level
        self.target_ratio = target_ratio

        self.stim_duration = stim_duration
        self.isi_duration = isi_duration
        self.rest_duration = rest_duration
        self.instruction_duration = instruction_duration
        self.pre_block_fixation = pre_block_fixation

        self.global_records = []

        # Consonnes
        self.consonants = [
            'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K',
            'L', 'M', 'N', 'P', 'R', 'S', 'T', 'V', 'W', 'Z'
        ]

        self._define_ttl_codes()
        self._setup_key_mapping()
        self._setup_task_stimuli()
        self._init_incremental_file(suffix=f"_{self.run_type}")

        # Log de la configuration
        config_str = " | ".join(
            f"{n}-back: {t} essais"
            for n, t in zip(self.n_levels, self.trials_per_level)
        )
        self.logger.ok(
            f"N-Back Go/No-Go init | Mode: {self.mode} | "
            f"Blocs/niveau: {self.blocks_per_level} | {config_str}"
        )

    # =========================================================================
    # INITIALISATION
    # =========================================================================

    def _define_ttl_codes(self):
        """Triggers EEG / port parallèle."""
        self.codes = {
            'start_exp':            255,
            'stim_target':          100,
            'stim_nontarget':       101,
            'response_hit':         150,
            'response_false_alarm': 151,
            'rest_start':           200,
            'rest_end':             201,
        }
        # Codes dynamiques par niveau
        for n in self.n_levels:
            self.codes[f'block_{n}back'] = 10 + n

    def _setup_key_mapping(self):
        """
        Mappage des touches — Go/No-Go.
        Une seule touche de réponse (Go = cible détectée).
        """
        if self.mode == 'fmri':
            self.key_go = 'b'
            self.key_trigger = 't'
        else:
            self.key_go = 'space'
            self.key_trigger = 't'

        self.valid_keys = [self.key_go]
        self.logger.log(
            f"Keys → Go (cible): [{self.key_go}]  |  "
            f"No-Go (non-cible): ne rien faire  |  "
            f"Trigger: [{self.key_trigger}]"
        )

    def _setup_task_stimuli(self):
        """Création des stimuli visuels PsychoPy."""
        self.letter_stim = visual.TextStim(
            self.win, text="", color='white', height=0.15,
            pos=(0, 0), bold=True
        )
        self.instruction_text = visual.TextStim(
            self.win, text="", color='yellow', height=0.08,
            pos=(0, 0), wrapWidth=1.5
        )
        self.fixation_cross = visual.TextStim(
            self.win, text="+", color='white', height=0.1, pos=(0, 0)
        )
        self.logger.log("Stimuli visuels chargés.")

    # =========================================================================
    # GÉNÉRATION DE SÉQUENCE
    # =========================================================================

    def _generate_sequence(self, n_level):
        """
        Génère une séquence de lettres pour un bloc du niveau donné.
        Le nombre d'essais est lu depuis self.level_trials[n_level].

        Returns:
            tuple(list[str], list[bool]): (séquence de lettres, liste is_target)
        """
        n_trials = self.level_trials[n_level]

        sequence = []
        is_target_list = []

        num_targets = int(n_trials * self.target_ratio)
        target_letter_0back = 'X'

        # Positions cibles (impossible avant l'index n)
        possible_target_idx = list(range(n_level, n_trials))
        num_targets = min(num_targets, len(possible_target_idx))
        target_indices = set(random.sample(possible_target_idx, num_targets))

        for i in range(n_trials):
            if i in target_indices:
                # --- CIBLE ---
                is_target_list.append(True)
                if n_level == 0:
                    sequence.append(target_letter_0back)
                else:
                    sequence.append(sequence[i - n_level])
            else:
                # --- NON-CIBLE ---
                is_target_list.append(False)
                available = self.consonants.copy()

                if n_level == 0:
                    if target_letter_0back in available:
                        available.remove(target_letter_0back)
                elif i >= n_level:
                    forbidden = sequence[i - n_level]
                    if forbidden in available:
                        available.remove(forbidden)

                # Anti-lure : pas de répétition directe sauf pour 1-back
                if n_level != 1 and i > 0:
                    prev_letter = sequence[i - 1]
                    if prev_letter in available:
                        available.remove(prev_letter)

                if not available:
                    available = self.consonants.copy()

                sequence.append(random.choice(available))

        return sequence, is_target_list

    # =========================================================================
    # ENREGISTREMENT
    # =========================================================================

    def _classify_response(self, is_target, responded):
        """Classification SDT Go/No-Go."""
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

    def log_trial(self, block_idx, n_level, trial_idx, letter,
                  is_target, responded, rt):
        """Enregistre un essai (mémoire + fichier incrémental)."""
        sdt = self._classify_response(is_target, responded)

        record = {
            'participant':        self.nom,
            'session':            self.session,
            'run_type':           self.run_type,
            'mode':               self.mode,
            'block_idx':          block_idx,
            'n_level':            f"{n_level}-back",
            'n_trials_in_block':  self.level_trials[n_level],
            'trial_idx':          trial_idx,
            'letter':             letter,
            'is_target':          int(is_target),
            'responded':          int(responded),
            'rt':                 round(rt, 4) if rt is not None else -1,
            'is_correct':         sdt['is_correct'],
            'hit':                sdt['hit'],
            'miss':               sdt['miss'],
            'false_alarm':        sdt['false_alarm'],
            'correct_rejection':  sdt['correct_rejection'],
            'timestamp':          datetime.now().strftime('%H:%M:%S.%f'),
        }

        self.global_records.append(record)
        self.save_trial_incremental(record)

    # =========================================================================
    # EXÉCUTION — ESSAI
    # =========================================================================

    def run_trial(self, letter, is_target, block_idx, n_level, trial_idx):
        """
        Affiche un essai : Lettre → Fixation.
        Go = appuyer si cible | No-Go = ne rien faire sinon.
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
            self.EyeTracker.send_message(
                f"STIM_{letter}_{'TGT' if is_target else 'NTG'}_B{block_idx}_T{trial_idx}"
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
                    code = (self.codes['response_hit']
                            if is_target
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
                        code = (self.codes['response_hit']
                                if is_target
                                else self.codes['response_false_alarm'])
                        self.send_trigger(code)

        # --- Enregistrement ---
        self.log_trial(block_idx, n_level, trial_idx, letter,
                       is_target, responded, rt)

    # =========================================================================
    # EXÉCUTION — BLOC
    # =========================================================================

    def _show_block_instruction(self, n_level):
        """Affiche l'instruction du bloc."""
        n_trials = self.level_trials[n_level]

        if n_level == 0:
            txt = (
                f"0-BACK  ({n_trials} essais)\n\n"
                f"Appuyez sur [{self.key_go.upper()}] si la lettre est 'X'\n"
                "Ne faites rien sinon."
            )
        else:
            txt = (
                f"{n_level}-BACK  ({n_trials} essais)\n\n"
                f"Appuyez sur [{self.key_go.upper()}] si la lettre est la même\n"
                f"qu'il y a {n_level} essai(s).\n"
                "Ne faites rien sinon."
            )

        self.instruction_text.text = txt
        self.instruction_text.draw()
        self.win.flip()

        instr_end = self.task_clock.getTime() + self.instruction_duration
        while self.task_clock.getTime() < instr_end:
            self.get_keys(key_list=[])

    def _show_timed_fixation(self, duration):
        """Affiche la croix de fixation pendant `duration` secondes."""
        self.fixation_cross.draw()
        self.win.flip()
        fix_end = self.task_clock.getTime() + duration
        while self.task_clock.getTime() < fix_end:
            self.get_keys(key_list=[])

    def run_block(self, block_idx, n_level):
        """Exécute un bloc complet."""
        n_trials = self.level_trials[n_level]
        self.logger.log(f"Block {block_idx} | {n_level}-Back ({n_trials} essais) | START")

        # Trigger de début de bloc
        block_code_key = f'block_{n_level}back'
        if self.parport_actif and block_code_key in self.codes:
            self.send_trigger(self.codes[block_code_key])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(f"BLOCK_{block_idx}_{n_level}BACK_START")

        self._show_block_instruction(n_level)
        self._show_timed_fixation(self.pre_block_fixation)

        # Génération de la séquence
        sequence, is_target_list = self._generate_sequence(n_level)
        n_targets = sum(is_target_list)
        self.logger.log(f"  Séquence : {len(sequence)} essais, {n_targets} cibles")

        for trial_idx, (letter, is_target) in enumerate(zip(sequence, is_target_list)):
            self.run_trial(letter, is_target, block_idx, n_level, trial_idx)

        self.logger.log(f"Block {block_idx} | {n_level}-Back | END")

    # =========================================================================
    # REPOS INTER-BLOCS
    # =========================================================================

    def _run_inter_block_rest(self):
        """Repos inter-blocs avec triggers."""
        if self.parport_actif:
            self.send_trigger(self.codes['rest_start'])
        if self.eyetracker_actif:
            self.EyeTracker.send_message("REST_START")

        self._show_timed_fixation(self.rest_duration)

        if self.parport_actif:
            self.send_trigger(self.codes['rest_end'])
        if self.eyetracker_actif:
            self.EyeTracker.send_message("REST_END")

    # =========================================================================
    # POINT D'ENTRÉE
    # =========================================================================

    def _build_block_order(self):
        """Construit et mélange l'ordre des blocs."""
        blocks = self.n_levels * self.blocks_per_level
        random.shuffle(blocks)

        # Log détaillé
        detail = ", ".join(f"{n}-back({self.level_trials[n]})" for n in blocks)
        self.logger.log(f"Ordre des blocs : [{detail}]")
        return blocks

    def _start_session(self):
        """Gère l'attente de trigger (fMRI) ou le démarrage manuel (desktop)."""
        if self.mode == 'fmri':
            self.wait_for_trigger(trigger_key=self.key_trigger)
        else:
            config_lines = "\n".join(
                f"  • {n}-back : {t} essais/bloc × {self.blocks_per_level} blocs"
                for n, t in zip(self.n_levels, self.trials_per_level)
            )
            total_trials = sum(t * self.blocks_per_level for t in self.trials_per_level)

            self.show_instructions(
                text_override=(
                    f"N-Back — Mémoire de travail (Go/No-Go)\n\n"
                    f"Appuyez sur [{self.key_go.upper()}] quand la lettre est une CIBLE\n"
                    f"Ne faites RIEN sinon.\n\n"
                    f"Configuration :\n{config_lines}\n"
                    f"Total : {total_trials} essais\n\n"
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
        """Nettoyage, sauvegarde finale, écran de fin."""
        self.logger.log("Nettoyage et sauvegarde finale...")

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

        # Résumé par niveau
        if self.global_records:
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

            # Détail par niveau
            import pandas as pd
            df = pd.DataFrame(self.global_records)
            for level in sorted(df['n_level'].unique()):
                sub = df[df['n_level'] == level]
                acc = 100 * sub['is_correct'].mean()
                self.logger.log(f"  {level}: {acc:.1f}% ({len(sub)} essais)")

        # Écran de fin
        try:
            if self.win and not self.win._closed:
                self.instruction_text.text = (
                    "Fin de la session.\nMerci pour votre participation."
                )
                self.instruction_text.draw()
                self.win.flip()
                core.wait(3.0)
        except Exception:
            self.logger.warn("Fenêtre déjà fermée, écran de fin ignoré.")

        # QC automatique
        if saved_path and self.enregistrer:
            try:
                from tasks.qc.qc_nback import qc_nback
                qc_nback(saved_path)
            except Exception as e:
                self.logger.warn(f"QC auto-launch failed: {e}")

        return saved_path

    def run(self):
        """Point d'entrée principal de la tâche."""
        config_str = " | ".join(
            f"{n}-back:{t}t" for n, t in zip(self.n_levels, self.trials_per_level)
        )
        self.logger.ok("=" * 50)
        self.logger.ok(f"N-Back Go/No-Go | {self.nom} | Session {self.session} | {self.mode}")
        self.logger.ok(f"Config : {config_str} × {self.blocks_per_level} blocs")
        self.logger.ok("=" * 50)

        saved_path = None

        try:
            self._start_session()
            blocks = self._build_block_order()

            for block_idx, n_level in enumerate(blocks):
                self.run_block(block_idx, n_level)

                if block_idx < len(blocks) - 1:
                    self._run_inter_block_rest()

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
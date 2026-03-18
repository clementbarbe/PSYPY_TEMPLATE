# nback.py
"""
N-Back Task — Version fMRI avec designs prédéfinis.
===================================================

TIMING REFERENCE:
    t=0 is defined as the moment the 't' trigger key is received.
    ALL timestamps in CSV (stim_onset, task_time) are relative to this t=0.
    This applies to BOTH fmri and pc modes.

CRITICAL DISPLAY RULE:
    Every wait loop MUST redraw its stimulus and call win.flip() every frame.
    Never leave a loop running without redrawing — this causes visual artifacts.

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

    Timing:
        t=0 est défini par la réception du trigger 't' (fMRI et PC).
        Tous les timestamps sont relatifs à ce t=0.
    """

    ZERO_BACK_TARGETS = ['B', 'D', 'K', 'M', 'R', 'T']

    CONSONANTS = [
        'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K',
        'L', 'M', 'N', 'P', 'R', 'S', 'T', 'V', 'W', 'Z'
    ]

    def __init__(self, win, nom, session='01', mode='fmri',
                 design_id=1, run_type='base',
                 block_sequence=None, rest_duration=None,
                 stim_duration=None, isi_duration=None,
                 target_ratio=0.33, instruction_duration=4.0,
                 pre_block_fixation=2.0,
                 enregistrer=True, eyetracker_actif=False, parport_actif=True,
                 **kwargs):

        super().__init__(
            win=win, nom=nom, session=session,
            task_name="NBack", folder_name="n_back",
            eyetracker_actif=eyetracker_actif,
            parport_actif=parport_actif,
            enregistrer=enregistrer, et_prefix='NBK'
        )

        self.mode = mode.lower()
        self.run_type = run_type.lower()
        self.target_ratio = target_ratio
        self.instruction_duration = instruction_duration
        self.pre_block_fixation = pre_block_fixation

        self.design_id = design_id
        self._resolve_design(design_id, block_sequence,
                             rest_duration, stim_duration, isi_duration)

        self.global_records = []

        # Absolute wall-clock time of trigger — set in _start_session
        self.trigger_absolute_time = None

        self._define_ttl_codes()
        self._setup_key_mapping()
        self._setup_task_stimuli()
        self._init_incremental_file(suffix=f"_{self.run_type}")
        self._log_design_summary()

    # =========================================================================
    # DESIGN RESOLUTION
    # =========================================================================

    def _resolve_design(self, design_id, block_sequence,
                        rest_duration, stim_duration, isi_duration):
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
                f"design_id={design_id} invalide et pas de block_sequence.\n"
                f"Designs : {list(DESIGNS.keys())}"
            )

        for i, blk in enumerate(self.block_sequence):
            if 'level' not in blk or 'n_trials' not in blk:
                raise ValueError(f"Bloc {i} invalide: {blk}")

        self.levels_used = sorted(set(b['level'] for b in self.block_sequence))

    def _log_design_summary(self):
        n_blocks = len(self.block_sequence)
        total_trials = sum(b['n_trials'] for b in self.block_sequence)
        trial_dur = self.stim_duration + self.isi_duration
        task_time = sum(b['n_trials'] * trial_dur for b in self.block_sequence)
        rest_time = self.rest_duration * (n_blocks + 1)
        instr_time = n_blocks * (self.instruction_duration + self.pre_block_fixation)
        total_time = task_time + rest_time + instr_time
        seq_str = " → ".join(
            f"{b['level']}-back({b['n_trials']})" for b in self.block_sequence
        )
        self.logger.ok("=" * 60)
        self.logger.ok(f"DESIGN : {self.design_name}")
        self.logger.ok(f"  Séquence : {seq_str}")
        self.logger.ok(f"  Blocs: {n_blocks} | Essais: {total_trials}")
        self.logger.ok(f"  Rest: {self.rest_duration}s | "
                       f"Stim: {self.stim_duration}s | ISI: {self.isi_duration}s")
        self.logger.ok(f"  Durée estimée: ~{total_time / 60:.1f} min")
        self.logger.ok("=" * 60)

    # =========================================================================
    # INITIALISATION
    # =========================================================================

    def _define_ttl_codes(self):
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

    # =========================================================================
    # SEQUENCE GENERATION
    # =========================================================================

    def _pick_zero_back_target(self):
        return random.choice(self.ZERO_BACK_TARGETS)

    def _generate_sequence(self, n_level, n_trials, zero_back_target=None):
        sequence = []
        is_target_list = []
        num_targets = max(1, int(n_trials * self.target_ratio))

        if n_level == 0:
            target_letter = zero_back_target or self._pick_zero_back_target()
            num_targets = min(num_targets, n_trials)
            target_indices = set(random.sample(range(n_trials), num_targets))
            for i in range(n_trials):
                if i in target_indices:
                    sequence.append(target_letter)
                    is_target_list.append(True)
                else:
                    available = [c for c in self.CONSONANTS if c != target_letter]
                    if i > 0 and sequence[i - 1] in available and len(available) > 1:
                        available = [c for c in available if c != sequence[i - 1]]
                    sequence.append(random.choice(available))
                    is_target_list.append(False)
        else:
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
                    if i >= n_level:
                        forbidden = sequence[i - n_level]
                        if forbidden in available:
                            available.remove(forbidden)
                    if n_level != 1 and i > 0:
                        prev = sequence[i - 1]
                        if prev in available and len(available) > 1:
                            available.remove(prev)
                    if not available:
                        available = self.CONSONANTS.copy()
                    sequence.append(random.choice(available))

        return sequence, is_target_list

    # =========================================================================
    # SDT CLASSIFICATION
    # =========================================================================

    def _classify_response(self, is_target, responded):
        if is_target:
            return {
                'hit': int(responded), 'miss': int(not responded),
                'false_alarm': 0, 'correct_rejection': 0,
                'is_correct': int(responded),
            }
        else:
            return {
                'hit': 0, 'miss': 0,
                'false_alarm': int(responded),
                'correct_rejection': int(not responded),
                'is_correct': int(not responded),
            }

    # =========================================================================
    # LOGGING + CONSOLE FEEDBACK
    # =========================================================================

    def log_trial(self, block_idx, n_level, n_trials_in_block,
                  trial_idx, letter, is_target, responded, rt,
                  stim_onset, zero_back_target=None):
        """
        Record one trial.

        Args:
            stim_onset: time of stimulus flip, relative to trigger t=0 (task_clock).
        """
        sdt = self._classify_response(is_target, responded)

        # Time from trigger (task_clock was reset at trigger)
        current_time = self.task_clock.getTime()

        record = {
            'participant':          self.nom,
            'session':              self.session,
            'design_id':            self.design_id or 'custom',
            'design_name':          self.design_name,
            'run_type':             self.run_type,
            'mode':                 self.mode,
            'trigger_time':         self.trigger_absolute_time or '',
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
            'stim_onset':           round(stim_onset, 4),
            'stim_duration':        self.stim_duration,
            'isi_duration':         self.isi_duration,
            'rest_duration':        self.rest_duration,
            'task_time':            round(current_time, 4),
            'wall_timestamp':       datetime.now().strftime('%H:%M:%S.%f'),
        }

        self.global_records.append(record)
        self.save_trial_incremental(record)

        # Console feedback
        self._print_trial_feedback(
            block_idx, n_level, trial_idx, letter,
            is_target, responded, rt, sdt, stim_onset
        )

    def _print_trial_feedback(self, block_idx, n_level, trial_idx,
                              letter, is_target, responded, rt, sdt,
                              stim_onset):
        """
        One-line per trial to console for real-time monitoring.

        Format:
          B0 T03 | t= 42.501s | 2-back | K ★ | HIT  ✓ |  423ms
          B0 T04 | t= 45.003s | 2-back | P · | CR   ✓ |    —
        """
        if sdt['hit']:
            tag = "HIT "
            sym = "✓"
        elif sdt['miss']:
            tag = "MISS"
            sym = "✗"
        elif sdt['false_alarm']:
            tag = "FA  "
            sym = "✗"
        else:
            tag = "CR  "
            sym = "✓"

        tgt_mark = "★" if is_target else "·"

        if rt is not None and rt > 0:
            rt_str = f"{rt * 1000:5.0f}ms"
        else:
            rt_str = "    — "

        print(
            f"  B{block_idx} T{trial_idx:02d} | "
            f"t={stim_onset:8.3f}s | "
            f"{n_level}-back | "
            f"{letter} {tgt_mark} | "
            f"{tag} {sym} | "
            f"{rt_str}"
        )

    def _print_block_summary(self, block_idx, n_level):
        """Print block summary to console."""
        block_records = [
            r for r in self.global_records if r['block_idx'] == block_idx
        ]
        if not block_records:
            return

        total = len(block_records)
        correct = sum(r['is_correct'] for r in block_records)
        pct = 100 * correct / total if total else 0

        hits = sum(r['hit'] for r in block_records)
        misses = sum(r['miss'] for r in block_records)
        fas = sum(r['false_alarm'] for r in block_records)
        crs = sum(r['correct_rejection'] for r in block_records)

        rts = [r['rt'] for r in block_records if r['rt'] > 0]
        rt_str = f"{sum(rts) / len(rts) * 1000:.0f}ms" if rts else "—"

        # Block time span
        first_onset = block_records[0]['stim_onset']
        last_time = block_records[-1]['task_time']

        print(
            f"  ── B{block_idx} {n_level}-back │ "
            f"{correct}/{total} ({pct:.0f}%) │ "
            f"H={hits} M={misses} FA={fas} CR={crs} │ "
            f"RT={rt_str} │ "
            f"t={first_onset:.1f}–{last_time:.1f}s ──"
        )

    # =========================================================================
    # DISPLAY HELPERS — FRAME-ACCURATE
    # =========================================================================

    def _show_timed_fixation(self, duration):
        """
        Display fixation cross for exactly `duration` seconds.
        Redraws every frame to prevent visual artifacts.
        """
        self.fixation_cross.draw()
        self.win.flip()
        onset = self.task_clock.getTime()
        deadline = onset + duration

        while self.task_clock.getTime() < deadline:
            self.fixation_cross.draw()
            self.win.flip()
            self.get_keys(key_list=[])

    def _show_block_instruction(self, n_level, zero_back_target=None):
        """
        Display block instruction. Redraws every frame.
        0-back: shows target letter in large cyan.
        N-back: standard text.
        """
        if self.parport_actif:
            self.send_trigger(self.codes['instruction_onset'])

        if n_level == 0:
            instr_line = (
                f"0-BACK\n\n"
                f"Appuyez sur [{self.key_go.upper()}]\n"
                f"quand vous voyez la lettre :"
            )
            self.instruction_text.text = instr_line
            self.instruction_text.pos = (0, -0.10)
            self.target_cue.text = zero_back_target
            self.target_cue.pos = (0, 0.20)

            self.target_cue.draw()
            self.instruction_text.draw()
            self.win.flip()
            onset = self.task_clock.getTime()
            deadline = onset + self.instruction_duration

            while self.task_clock.getTime() < deadline:
                self.target_cue.draw()
                self.instruction_text.draw()
                self.win.flip()
                self.get_keys(key_list=[])

            self.instruction_text.pos = (0, 0)

        else:
            txt = (
                f"{n_level}-BACK\n\n"
                f"Appuyez sur [{self.key_go.upper()}]\n"
                f"si la lettre est la même\n"
                f"qu'il y a {n_level} essai{'s' if n_level > 1 else ''}.\n\n"
                f"Ne faites rien sinon."
            )
            self.instruction_text.text = txt

            self.instruction_text.draw()
            self.win.flip()
            onset = self.task_clock.getTime()
            deadline = onset + self.instruction_duration

            while self.task_clock.getTime() < deadline:
                self.instruction_text.draw()
                self.win.flip()
                self.get_keys(key_list=[])

        if self.eyetracker_actif:
            msg = f"INSTR_{n_level}BACK"
            if n_level == 0:
                msg += f"_TARGET_{zero_back_target}"
            self.EyeTracker.send_message(msg)

    # =========================================================================
    # TRIAL — FRAME-ACCURATE
    # =========================================================================

    def run_trial(self, letter, is_target, block_idx, n_level,
                  n_trials_in_block, trial_idx, zero_back_target=None):
        """
        One trial: Letter → ISI fixation.
        Both phases redraw every frame. Response collected across both.
        stim_onset is relative to trigger t=0.
        """
        self.letter_stim.text = letter
        self.flush_keyboard()
        responded = False
        rt = None

        # ── PHASE 1: STIMULUS ────────────────────────────────────────
        self.letter_stim.draw()
        self.win.flip()
        stim_onset = self.task_clock.getTime()  # relative to trigger t=0

        ttl = self.codes['stim_target'] if is_target else self.codes['stim_nontarget']
        if self.parport_actif:
            self.send_trigger(ttl)
        if self.eyetracker_actif:
            tag = 'TGT' if is_target else 'NTG'
            self.EyeTracker.send_message(
                f"STIM_{letter}_{tag}_B{block_idx}_T{trial_idx}_t{stim_onset:.3f}"
            )

        stim_deadline = stim_onset + self.stim_duration
        while self.task_clock.getTime() < stim_deadline:
            keys = self.get_keys(key_list=self.valid_keys)
            if keys and not responded:
                responded = True
                rt = keys[0].rt - stim_onset
                if self.parport_actif:
                    code = (self.codes['response_hit'] if is_target
                            else self.codes['response_false_alarm'])
                    self.send_trigger(code)

            self.letter_stim.draw()
            self.win.flip()

        # ── PHASE 2: ISI (fixation) ─────────────────────────────────
        self.fixation_cross.draw()
        self.win.flip()
        isi_deadline = self.task_clock.getTime() + self.isi_duration

        while self.task_clock.getTime() < isi_deadline:
            keys = self.get_keys(key_list=self.valid_keys)
            if keys and not responded:
                responded = True
                rt = keys[0].rt - stim_onset
                if self.parport_actif:
                    code = (self.codes['response_hit'] if is_target
                            else self.codes['response_false_alarm'])
                    self.send_trigger(code)

            self.fixation_cross.draw()
            self.win.flip()

        # ── LOG ──────────────────────────────────────────────────────
        self.log_trial(
            block_idx, n_level, n_trials_in_block,
            trial_idx, letter, is_target, responded, rt,
            stim_onset, zero_back_target
        )

    # =========================================================================
    # BLOCK
    # =========================================================================

    def run_block(self, block_idx, block_def):
        n_level = block_def['level']
        n_trials = block_def['n_trials']
        block_start = self.task_clock.getTime()

        print(f"\n╔══ Block {block_idx} | {n_level}-back "
              f"({n_trials} essais) | t={block_start:.1f}s ════════════════")

        self.logger.log(
            f"Block {block_idx} | {n_level}-Back | {n_trials} essais | "
            f"t={block_start:.3f}s | START"
        )

        block_code_key = f'block_{n_level}back'
        if self.parport_actif and block_code_key in self.codes:
            self.send_trigger(self.codes[block_code_key])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(
                f"BLOCK_{block_idx}_{n_level}BACK_START_t{block_start:.3f}"
            )

        zero_back_target = None
        if n_level == 0:
            zero_back_target = self._pick_zero_back_target()
            self.logger.log(f"  0-back cible: '{zero_back_target}'")
            print(f"║ Cible 0-back: {zero_back_target}")

        self._show_block_instruction(n_level, zero_back_target)
        self._show_timed_fixation(self.pre_block_fixation)

        sequence, is_target_list = self._generate_sequence(
            n_level, n_trials, zero_back_target
        )
        n_targets = sum(is_target_list)
        self.logger.log(
            f"  Séquence: {len(sequence)} essais, {n_targets} cibles"
        )
        print(f"║ {n_targets} cibles / {n_trials} essais "
              f"({100 * n_targets / n_trials:.0f}%)")
        print(f"╠{'═' * 56}")

        for trial_idx, (letter, is_target) in enumerate(
            zip(sequence, is_target_list)
        ):
            self.run_trial(
                letter, is_target, block_idx, n_level,
                n_trials, trial_idx, zero_back_target
            )

        if self.eyetracker_actif:
            t_end = self.task_clock.getTime()
            self.EyeTracker.send_message(
                f"BLOCK_{block_idx}_{n_level}BACK_END_t{t_end:.3f}"
            )

        print(f"╠{'═' * 56}")
        self._print_block_summary(block_idx, n_level)
        print(f"╚{'═' * 58}\n")

        self.logger.log(f"Block {block_idx} | {n_level}-Back | END")

    # =========================================================================
    # REST
    # =========================================================================

    def _run_rest(self, label=""):
        t_start = self.task_clock.getTime()
        self.logger.log(
            f"Rest {self.rest_duration}s {label} | t={t_start:.3f}s"
        )
        print(f"  ⏸ Rest {self.rest_duration}s | t={t_start:.1f}s | {label}")

        if self.parport_actif:
            self.send_trigger(self.codes['rest_start'])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(
                f"REST_START_{label}_t{t_start:.3f}"
            )

        self._show_timed_fixation(self.rest_duration)

        t_end = self.task_clock.getTime()
        if self.parport_actif:
            self.send_trigger(self.codes['rest_end'])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(
                f"REST_END_{label}_t{t_end:.3f}"
            )

    # =========================================================================
    # SESSION — TRIGGER SYNCHRONISATION
    # =========================================================================

    def _start_session(self):
        """
        Start session — BOTH modes (fmri and pc).

        Flow:
            1. Show task instructions (press any key to continue)
            2. Wait for 't' trigger key (fMRI sync or manual press)
            3. task_clock resets to t=0 at trigger reception
            4. All subsequent timestamps are relative to this t=0

        The 't' trigger is ALWAYS required, even in PC mode,
        to allow synchronization with external devices (fMRI, EEG, etc.).
        """
        # ── 1. Instructions ──────────────────────────────────────────
        seq_str = " → ".join(
            f"{b['level']}-back({b['n_trials']})"
            for b in self.block_sequence
        )
        total_trials = sum(b['n_trials'] for b in self.block_sequence)

        if self.mode == 'fmri':
            instr_text = (
                f"N-Back — Mémoire de travail\n\n"
                f"Design : {self.design_name}\n"
                f"Total : {total_trials} essais\n\n"
                f"0-back : Appuyez sur [{self.key_go.upper()}] "
                f"quand vous voyez la lettre cible.\n"
                f"N-back : Appuyez sur [{self.key_go.upper()}] "
                f"si la lettre = celle d'il y a N.\n"
                f"Sinon : ne faites rien.\n\n"
                "Appuyez sur une touche pour continuer..."
            )
        else:
            instr_text = (
                f"N-Back — Mémoire de travail\n\n"
                f"Design : {self.design_name}\n"
                f"Séquence : {seq_str}\n"
                f"Total : {total_trials} essais\n\n"
                f"0-back : Appuyez sur [{self.key_go.upper()}] "
                f"quand vous voyez la lettre cible.\n"
                f"N-back : Appuyez sur [{self.key_go.upper()}] "
                f"si la lettre = celle d'il y a N.\n"
                f"Sinon : ne faites rien.\n\n"
                "Appuyez sur une touche pour continuer..."
            )

        self.show_instructions(text_override=instr_text)

        # ── 2. Wait for trigger 't' — BOTH MODES ────────────────────
        #    This shows "Attente trigger [t]..." and blocks until 't'.
        #    task_clock.reset() is called inside wait_for_trigger().
        #    → This defines t=0 for the entire session.
        self.wait_for_trigger(trigger_key=self.key_trigger)

        # ── 3. Capture absolute wall-clock time of trigger ───────────
        self.trigger_absolute_time = datetime.now().strftime(
            '%Y-%m-%d_%H:%M:%S.%f'
        )

        print("\n" + "=" * 60)
        print(f"  ⏱  TRIGGER REÇU — t=0")
        print(f"  Horloge absolue : {self.trigger_absolute_time}")
        print(f"  Mode : {self.mode} | Design : {self.design_name}")
        print("=" * 60)

        self.logger.ok(
            f"TRIGGER t=0 | {self.trigger_absolute_time} | "
            f"mode={self.mode} | design={self.design_name}"
        )

        # ── 4. Start triggers ───────────────────────────────────────
        if self.parport_actif:
            self.send_trigger(self.codes['start_exp'])

        # Note: wait_for_trigger() already starts eyetracker recording
        # and sends START_NBACK message. We add an explicit START_EXP.
        if self.eyetracker_actif:
            self.EyeTracker.send_message("START_EXP_t0.000")

    def _end_session(self):
        """Cleanup, final save, stats display."""
        t_end = self.task_clock.getTime()
        self.logger.log(
            f"Session end | t={t_end:.3f}s | "
            f"Total duration: {t_end:.1f}s ({t_end/60:.1f}min)"
        )
        print(f"\n  ⏱ Session duration: {t_end:.1f}s ({t_end/60:.1f} min)")

        if self.parport_actif:
            try:
                self.send_trigger(self.codes['end_exp'])
            except Exception:
                pass

        if self.eyetracker_actif:
            try:
                self.EyeTracker.send_message(f"END_EXP_t{t_end:.3f}")
                self.EyeTracker.stop_recording()
                self.EyeTracker.close_and_transfer_data(self.data_dir)
            except Exception as e:
                self.logger.err(f"EyeTracker cleanup error: {e}")

        saved_path = self.save_data(
            data_list=self.global_records,
            filename_suffix=f"_{self.run_type}"
        )

        if self.global_records:
            self._print_stats()

        # End screen
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
        """Console + logger summary at end of session."""
        total = len(self.global_records)
        correct = sum(r['is_correct'] for r in self.global_records)
        hits = sum(r['hit'] for r in self.global_records)
        misses = sum(r['miss'] for r in self.global_records)
        fas = sum(r['false_alarm'] for r in self.global_records)
        crs = sum(r['correct_rejection'] for r in self.global_records)

        print("\n" + "=" * 60)
        print(f"  RÉSULTATS GLOBAUX")
        print(f"  {correct}/{total} ({100 * correct / total:.1f}%)")
        print(f"  HIT={hits}  MISS={misses}  FA={fas}  CR={crs}")

        self.logger.ok(
            f"GLOBAL: {correct}/{total} ({100 * correct / total:.1f}%) | "
            f"H={hits} M={misses} FA={fas} CR={crs}"
        )

        from collections import defaultdict
        by_level = defaultdict(list)
        for r in self.global_records:
            by_level[r['n_level']].append(r)

        print(f"  {'─' * 54}")

        for level in sorted(by_level.keys()):
            records = by_level[level]
            n = len(records)
            acc = 100 * sum(r['is_correct'] for r in records) / n
            h = sum(r['hit'] for r in records)
            m = sum(r['miss'] for r in records)
            fa = sum(r['false_alarm'] for r in records)
            cr = sum(r['correct_rejection'] for r in records)
            rts = [r['rt'] for r in records if r['rt'] > 0]
            rt_str = f"{sum(rts) / len(rts) * 1000:.0f}ms" if rts else "—"

            # Time span for this level
            onsets = [r['stim_onset'] for r in records]
            t_span = f"t={min(onsets):.1f}–{max(onsets):.1f}s"

            line = (
                f"  {level}-back: {acc:5.1f}% ({n:3d} essais) | "
                f"H={h:2d} M={m:2d} FA={fa:2d} CR={cr:2d} | "
                f"RT={rt_str} | {t_span}"
            )
            print(line)
            self.logger.log(f"  {line.strip()}")

        print("=" * 60 + "\n")

    # =========================================================================
    # ENTRY POINT
    # =========================================================================

    def run(self):
        self.logger.ok("=" * 60)
        self.logger.ok(
            f"N-Back | {self.nom} | Session {self.session} | "
            f"{self.mode} | Design: {self.design_name}"
        )
        self.logger.ok("=" * 60)

        saved_path = None

        try:
            self._start_session()
            self._run_rest(label="initial")

            for block_idx, block_def in enumerate(self.block_sequence):
                self.run_block(block_idx, block_def)
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
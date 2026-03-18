# flanker.py
"""
Eriksen Flanker Task — Version fMRI avec designs prédéfinis.
============================================================

TIMING REFERENCE:
    t=0 is defined as the moment the 't' trigger key is received.
    ALL timestamps in CSV (stim_onset, task_time) are relative to this t=0.
    This applies to BOTH fmri and pc modes.

CRITICAL DISPLAY RULE:
    Every wait loop MUST redraw its stimulus and call win.flip() every frame.
    Never leave a loop running without redrawing — this causes visual artifacts.

Designs supportés :
    1. Block (CON vs INC)       — localisation réseau attentionnel du conflit
    2. Event-related (jittered) — modélisation fine RT / erreurs / HRF
    3. Hybrid mini-blocks       — meilleur compromis puissance / flexibilité
    4. Hybrid optimisé          — mini-blocs courts, déconvolution HRF
    custom: ordre libre via paramètres

Paradigme :
    Le participant répond à la direction de la flèche CENTRALE (5 flèches).
    Flankers congruents (même direction) ou incongruents (direction opposée).

    Congruent   :  < < < < <   ou   > > > > >
    Incongruent :  > > < > >   ou   < < > < <
    Neutre      :  – – < – –   ou   – – > – –

Métriques clés :
    - Effet de congruence : RT_incongruent − RT_congruent
    - Taux d'erreur par condition
    - Précision globale et par bloc
"""

import random
import os
from datetime import datetime
from collections import defaultdict
from psychopy import visual, core
from utils.base_task import BaseTask


# =============================================================================
# DESIGNS PRÉDÉFINIS
# =============================================================================

DESIGNS = {
    1: {
        'name': 'Block (CON vs INC ~7min)',
        'description': (
            'Blocs purs alternés congruent / incongruent — '
            'optimal pour localiser le réseau attentionnel du conflit (ACC, DLPFC)'
        ),
        'paradigm': 'block',
        'rest_duration': 12.0,
        'stim_duration': 1.5,
        'isi_min': 1.0,
        'isi_max': 1.0,
        'inter_block_min': 0.0,
        'inter_block_max': 0.0,
        'instruction_duration': 3.0,
        'pre_block_fixation': 1.0,
        'block_sequence': [
            {'condition': 'congruent',   'n_trials': 20},
            {'condition': 'incongruent', 'n_trials': 20},
            {'condition': 'incongruent', 'n_trials': 20},
            {'condition': 'congruent',   'n_trials': 20},
            {'condition': 'incongruent', 'n_trials': 20},
            {'condition': 'congruent',   'n_trials': 20},
        ],
    },
    2: {
        'name': 'Event-related (jittered ~9min)',
        'description': (
            'Essais mélangés CON/INC, ISI jittéré 2–6 s — '
            'optimal pour modélisation fine RT, erreurs, HRF trial-by-trial'
        ),
        'paradigm': 'event',
        'rest_duration': 15.0,
        'stim_duration': 1.5,
        'isi_min': 2.0,
        'isi_max': 6.0,
        'inter_block_min': 0.0,
        'inter_block_max': 0.0,
        'instruction_duration': 3.0,
        'pre_block_fixation': 1.0,
        'block_sequence': [
            {'condition': 'mixed', 'n_trials': 96, 'prop_incongruent': 0.5},
        ],
    },
    3: {
        'name': 'Hybrid mini-blocks (recommandé ~7min)',
        'description': (
            'Mini-blocs de 8 essais mixtes, jitter inter-bloc 4–10 s — '
            'meilleur compromis puissance statistique block + flexibilité event'
        ),
        'paradigm': 'hybrid',
        'rest_duration': 12.0,
        'stim_duration': 1.5,
        'isi_min': 1.0,
        'isi_max': 2.0,
        'inter_block_min': 4.0,
        'inter_block_max': 10.0,
        'instruction_duration': 0.0,
        'pre_block_fixation': 0.0,
        'block_sequence': [
            {'condition': 'mixed', 'n_trials': 8, 'prop_incongruent': 0.5}
            for _ in range(12)
        ],
    },
    4: {
        'name': 'Hybrid optimisé (randomisé ~7min)',
        'description': (
            'Mini-blocs courts de 4 essais, jitter 3–7 s — '
            'optimisé pour déconvolution HRF et analyses paramétriques'
        ),
        'paradigm': 'hybrid',
        'rest_duration': 10.0,
        'stim_duration': 1.5,
        'isi_min': 1.0,
        'isi_max': 1.5,
        'inter_block_min': 3.0,
        'inter_block_max': 7.0,
        'instruction_duration': 0.0,
        'pre_block_fixation': 0.0,
        'block_sequence': [
            {'condition': 'mixed', 'n_trials': 4, 'prop_incongruent': 0.5}
            for _ in range(24)
        ],
    },
}


class Flanker(BaseTask):
    """
    Tâche Eriksen Flanker fMRI avec designs prédéfinis.

    Paradigme deux choix forcés (2-AFC) :
        Flèche centrale ← : touche gauche
        Flèche centrale → : touche droite
        Flankers = même direction (congruent) ou opposée (incongruent)

    Timing :
        t=0 est défini par la réception du trigger 't' (fMRI et PC).
        Tous les timestamps sont relatifs à ce t=0.
    """

    def __init__(self, win, nom, session='01', mode='fmri',
                 design_id=1, run_type='base',
                 block_sequence=None, paradigm=None,
                 rest_duration=None, stim_duration=None,
                 isi_min=None, isi_max=None,
                 inter_block_min=None, inter_block_max=None,
                 prop_incongruent=0.5,
                 instruction_duration=None,
                 pre_block_fixation=None,
                 enregistrer=True, eyetracker_actif=False,
                 parport_actif=True, **kwargs):

        super().__init__(
            win=win, nom=nom, session=session,
            task_name="Flanker", folder_name="flanker",
            eyetracker_actif=eyetracker_actif,
            parport_actif=parport_actif,
            enregistrer=enregistrer, et_prefix='FLK'
        )

        self.mode = mode.lower()
        self.run_type = run_type.lower()
        self.prop_incongruent = prop_incongruent
        self.global_trial_idx = 0

        self.design_id = design_id
        self._resolve_design(
            design_id, block_sequence, paradigm,
            rest_duration, stim_duration,
            isi_min, isi_max,
            inter_block_min, inter_block_max,
            instruction_duration, pre_block_fixation
        )

        self.global_records = []
        self.trigger_absolute_time = None

        self._define_ttl_codes()
        self._setup_key_mapping()
        self._setup_task_stimuli()
        self._init_incremental_file(suffix=f"_{self.run_type}")
        self._log_design_summary()

    # =========================================================================
    # DESIGN RESOLUTION
    # =========================================================================

    def _resolve_design(self, design_id, block_sequence, paradigm,
                        rest_duration, stim_duration,
                        isi_min, isi_max,
                        inter_block_min, inter_block_max,
                        instruction_duration, pre_block_fixation):
        """Resolve design parameters from predefined ID or custom args."""

        if design_id is not None and design_id in DESIGNS:
            d = DESIGNS[design_id]
            self.design_name = d['name']
            self.paradigm = paradigm or d['paradigm']
            # Deep copy block sequence (each block is independent dict)
            self.block_sequence = [dict(b) for b in d['block_sequence']]
            self.rest_duration = (rest_duration if rest_duration is not None
                                  else d['rest_duration'])
            self.stim_duration = (stim_duration if stim_duration is not None
                                  else d['stim_duration'])
            self.isi_min = isi_min if isi_min is not None else d['isi_min']
            self.isi_max = isi_max if isi_max is not None else d['isi_max']
            self.inter_block_min = (inter_block_min if inter_block_min is not None
                                    else d.get('inter_block_min', 0.0))
            self.inter_block_max = (inter_block_max if inter_block_max is not None
                                    else d.get('inter_block_max', 0.0))
            self.instruction_duration = (instruction_duration if instruction_duration is not None
                                         else d.get('instruction_duration', 3.0))
            self.pre_block_fixation = (pre_block_fixation if pre_block_fixation is not None
                                       else d.get('pre_block_fixation', 1.0))

        elif block_sequence is not None:
            self.design_name = 'Custom'
            self.paradigm = paradigm or 'custom'
            self.block_sequence = block_sequence
            self.rest_duration = rest_duration if rest_duration is not None else 10.0
            self.stim_duration = stim_duration if stim_duration is not None else 1.5
            self.isi_min = isi_min if isi_min is not None else 1.5
            self.isi_max = isi_max if isi_max is not None else 1.5
            self.inter_block_min = inter_block_min if inter_block_min is not None else 0.0
            self.inter_block_max = inter_block_max if inter_block_max is not None else 0.0
            self.instruction_duration = instruction_duration if instruction_duration is not None else 3.0
            self.pre_block_fixation = pre_block_fixation if pre_block_fixation is not None else 1.0

        else:
            raise ValueError(
                f"design_id={design_id} invalide et pas de block_sequence.\n"
                f"Designs disponibles : {list(DESIGNS.keys())}"
            )

        # Validation
        valid_conditions = ('congruent', 'incongruent', 'mixed', 'neutral')
        for i, blk in enumerate(self.block_sequence):
            if 'condition' not in blk or 'n_trials' not in blk:
                raise ValueError(f"Bloc {i} invalide (clés manquantes): {blk}")
            if blk['condition'] not in valid_conditions:
                raise ValueError(
                    f"Bloc {i}: condition '{blk['condition']}' invalide. "
                    f"Valides: {valid_conditions}"
                )

        self.conditions_used = sorted(set(b['condition'] for b in self.block_sequence))

    def _log_design_summary(self):
        """Print design summary to logger and console."""
        n_blocks = len(self.block_sequence)
        total_trials = sum(b['n_trials'] for b in self.block_sequence)
        mean_isi = (self.isi_min + self.isi_max) / 2.0
        trial_dur = self.stim_duration + mean_isi

        task_time = total_trials * trial_dur

        if self.paradigm == 'hybrid' and self.inter_block_max > 0:
            mean_jitter = (self.inter_block_min + self.inter_block_max) / 2.0
            rest_time = max(0, n_blocks - 1) * mean_jitter + 2 * self.rest_duration
        else:
            rest_time = (n_blocks + 1) * self.rest_duration

        instr_time = n_blocks * (self.instruction_duration + self.pre_block_fixation)
        total_time = task_time + rest_time + instr_time

        # Build sequence string (truncate if too long)
        seq_parts = []
        for b in self.block_sequence[:10]:
            cond_abbr = b['condition'][:3].upper()
            seq_parts.append(f"{cond_abbr}({b['n_trials']})")
        seq_str = " → ".join(seq_parts)
        if n_blocks > 10:
            seq_str += f" … (+{n_blocks - 10})"

        self.logger.ok("=" * 60)
        self.logger.ok(f"DESIGN : {self.design_name} [{self.paradigm}]")
        self.logger.ok(f"  Séquence : {seq_str}")
        self.logger.ok(f"  Blocs: {n_blocks} | Essais: {total_trials}")
        self.logger.ok(
            f"  Rest: {self.rest_duration}s | Stim: {self.stim_duration}s | "
            f"ISI: {self.isi_min}–{self.isi_max}s"
        )
        if self.paradigm == 'hybrid' and self.inter_block_max > 0:
            self.logger.ok(
                f"  Inter-bloc jitter: {self.inter_block_min}–{self.inter_block_max}s"
            )
        self.logger.ok(f"  Durée estimée: ~{total_time / 60:.1f} min")
        self.logger.ok("=" * 60)

    # =========================================================================
    # INITIALISATION
    # =========================================================================

    def _define_ttl_codes(self):
        """Define TTL parallel port codes for each event type."""
        self.codes = {
            'start_exp':            255,
            'end_exp':              254,
            'stim_congruent':       100,
            'stim_incongruent':     101,
            'stim_neutral':         102,
            'response_correct':     150,
            'response_incorrect':   151,
            'rest_start':           200,
            'rest_end':             201,
            'instruction_onset':    210,
            'block_congruent':      10,
            'block_incongruent':    11,
            'block_mixed':          12,
            'block_neutral':        13,
        }

    def _setup_key_mapping(self):
        """Configure response keys based on mode (fMRI / PC)."""
        if self.mode == 'fmri':
            self.key_left = 'b'       # Index finger — button box
            self.key_right = 'y'      # Middle finger — button box
            self.key_trigger = 't'
        else:
            self.key_left = 'left'    # Arrow key
            self.key_right = 'right'  # Arrow key
            self.key_trigger = 't'

        self.valid_keys = [self.key_left, self.key_right]
        self.key_to_dir = {self.key_left: 'left', self.key_right: 'right'}
        self.dir_to_key = {'left': self.key_left, 'right': self.key_right}

        self.logger.log(
            f"Keys → Left: [{self.key_left}] | Right: [{self.key_right}] | "
            f"Trigger: [{self.key_trigger}]"
        )

    def _setup_task_stimuli(self):
        """Create all visual stimuli for the task."""
        self.arrow_stim = visual.TextStim(
            self.win, text="", color='white', height=0.15,
            pos=(0, 0), bold=True, font='monospace'
        )
        self.instruction_text = visual.TextStim(
            self.win, text="", color='yellow', height=0.06,
            pos=(0, 0), wrapWidth=1.5
        )
        self.fixation_cross = visual.TextStim(
            self.win, text="+", color='white', height=0.1, pos=(0, 0)
        )

    # =========================================================================
    # STIMULUS GENERATION
    # =========================================================================

    def _build_stimulus_text(self, target_dir, flanker_dir):
        """
        Build the 5-arrow stimulus string.

        Args:
            target_dir: 'left' or 'right' — direction of CENTER arrow
            flanker_dir: 'left', 'right', or 'neutral' — direction of flankers

        Returns:
            str: e.g. ">  >  <  >  >" for incongruent-left
        """
        target = '<' if target_dir == 'left' else '>'

        if flanker_dir == 'neutral':
            flanker = '–'
        elif flanker_dir == 'left':
            flanker = '<'
        else:
            flanker = '>'

        return f"{flanker}  {flanker}  {target}  {flanker}  {flanker}"

    def _generate_trial_list(self, condition, n_trials, prop_incongruent=None):
        """
        Generate trial list for one block.

        Args:
            condition: 'congruent', 'incongruent', 'mixed', or 'neutral'
            n_trials: number of trials
            prop_incongruent: proportion incongruent (for 'mixed' only)

        Returns:
            list of (target_dir, flanker_dir, congruency) tuples
        """
        if prop_incongruent is None:
            prop_incongruent = self.prop_incongruent

        trials = []

        if condition == 'congruent':
            n_left = n_trials // 2
            n_right = n_trials - n_left
            trials.extend([('left', 'left', 'congruent')] * n_left)
            trials.extend([('right', 'right', 'congruent')] * n_right)

        elif condition == 'incongruent':
            n_left = n_trials // 2
            n_right = n_trials - n_left
            trials.extend([('left', 'right', 'incongruent')] * n_left)
            trials.extend([('right', 'left', 'incongruent')] * n_right)

        elif condition == 'mixed':
            n_inc = int(round(n_trials * prop_incongruent))
            n_con = n_trials - n_inc

            n_con_l = n_con // 2
            n_con_r = n_con - n_con_l
            trials.extend([('left', 'left', 'congruent')] * n_con_l)
            trials.extend([('right', 'right', 'congruent')] * n_con_r)

            n_inc_l = n_inc // 2
            n_inc_r = n_inc - n_inc_l
            trials.extend([('left', 'right', 'incongruent')] * n_inc_l)
            trials.extend([('right', 'left', 'incongruent')] * n_inc_r)

        elif condition == 'neutral':
            n_left = n_trials // 2
            n_right = n_trials - n_left
            trials.extend([('left', 'neutral', 'neutral')] * n_left)
            trials.extend([('right', 'neutral', 'neutral')] * n_right)

        random.shuffle(trials)
        trials = self._desequence(trials)
        return trials

    def _desequence(self, trials, max_consecutive=4):
        """
        Ensure no more than max_consecutive trials with the same target direction.
        Reshuffles if needed (up to 100 attempts, then gives up gracefully).
        """
        for _ in range(100):
            ok = True
            for i in range(max_consecutive, len(trials)):
                window = [trials[j][0] for j in range(i - max_consecutive, i + 1)]
                if len(set(window)) == 1:
                    ok = False
                    break
            if ok:
                return trials
            random.shuffle(trials)
        # Give up — still valid data, just suboptimal sequencing
        self.logger.warn("Desequencing failed after 100 attempts — using last shuffle.")
        return trials

    def _generate_isis(self, n_trials):
        """
        Generate ISI durations for a block of trials.

        Returns:
            list[float]: one ISI per trial
        """
        if abs(self.isi_min - self.isi_max) < 0.01:
            return [round(self.isi_min, 3)] * n_trials
        return [round(random.uniform(self.isi_min, self.isi_max), 3)
                for _ in range(n_trials)]

    # =========================================================================
    # LOGGING + CONSOLE FEEDBACK
    # =========================================================================

    def log_trial(self, block_idx, block_condition, n_trials_in_block,
                  trial_idx, target_dir, flanker_dir, congruency,
                  stim_text, responded, response_key, response_dir,
                  rt, is_correct, stim_onset, isi_actual):
        """
        Record one trial to global_records and incremental CSV.

        Args:
            stim_onset: time of stimulus flip relative to trigger t=0.
        """
        current_time = self.task_clock.getTime()

        record = {
            'participant':          self.nom,
            'session':              self.session,
            'design_id':            self.design_id or 'custom',
            'design_name':          self.design_name,
            'paradigm':             self.paradigm,
            'run_type':             self.run_type,
            'mode':                 self.mode,
            'trigger_time':         self.trigger_absolute_time or '',
            'block_idx':            block_idx,
            'block_condition':      block_condition,
            'n_trials_in_block':    n_trials_in_block,
            'trial_idx':            trial_idx,
            'trial_idx_global':     self.global_trial_idx,
            'target_direction':     target_dir,
            'flanker_direction':    flanker_dir,
            'congruency':           congruency,
            'stimulus':             stim_text,
            'correct_key':          self.dir_to_key.get(target_dir, ''),
            'responded':            int(responded),
            'response_key':         response_key or '',
            'response_direction':   response_dir or '',
            'rt':                   round(rt, 4) if rt is not None else -1,
            'is_correct':           int(is_correct),
            'is_error':             int(responded and not is_correct),
            'is_miss':              int(not responded),
            'stim_onset':           round(stim_onset, 4),
            'isi_actual':           round(isi_actual, 4),
            'stim_duration':        self.stim_duration,
            'isi_min':              self.isi_min,
            'isi_max':              self.isi_max,
            'task_time':            round(current_time, 4),
            'wall_timestamp':       datetime.now().strftime('%H:%M:%S.%f'),
        }

        self.global_records.append(record)
        self.save_trial_incremental(record)
        self.global_trial_idx += 1

        self._print_trial_feedback(
            block_idx, block_condition, trial_idx,
            stim_text, congruency, target_dir,
            responded, response_dir, rt, is_correct, stim_onset
        )

    def _print_trial_feedback(self, block_idx, block_condition, trial_idx,
                              stim_text, congruency, target_dir,
                              responded, response_dir, rt, is_correct,
                              stim_onset):
        """
        One-line per trial to console for real-time monitoring.

        Format:
          B0 T03 | t= 42.501s | CON | < < < < < | OK   ✓ |  423ms
          B0 T04 | t= 45.003s | INC | > > < > > | ERR  ✗ |  567ms
          B0 T05 | t= 47.510s | CON | > > > > > | MISS ✗ |    —
        """
        cong_mark = congruency[:3].upper()

        if not responded:
            tag = "MISS"
            sym = "✗"
        elif is_correct:
            tag = "OK  "
            sym = "✓"
        else:
            tag = "ERR "
            sym = "✗"

        if rt is not None and rt > 0:
            rt_str = f"{rt * 1000:5.0f}ms"
        else:
            rt_str = "    — "

        print(
            f"  B{block_idx:02d} T{trial_idx:02d} | "
            f"t={stim_onset:8.3f}s | "
            f"{cong_mark} | "
            f"{stim_text} | "
            f"{tag} {sym} | "
            f"{rt_str}"
        )

    def _print_block_summary(self, block_idx, block_condition):
        """Print block-level performance summary to console."""
        block_records = [
            r for r in self.global_records if r['block_idx'] == block_idx
        ]
        if not block_records:
            return

        total = len(block_records)
        correct = sum(r['is_correct'] for r in block_records)
        pct = 100 * correct / total if total else 0
        errors = sum(r['is_error'] for r in block_records)
        misses = sum(r['is_miss'] for r in block_records)

        rts = [r['rt'] for r in block_records if r['rt'] > 0 and r['is_correct']]
        rt_str = f"{sum(rts) / len(rts) * 1000:.0f}ms" if rts else "—"

        first_onset = block_records[0]['stim_onset']
        last_time = block_records[-1]['task_time']

        # Per-congruency breakdown if mixed
        by_cong = defaultdict(list)
        for r in block_records:
            by_cong[r['congruency']].append(r)

        cong_parts = []
        for c in sorted(by_cong.keys()):
            recs = by_cong[c]
            c_acc = 100 * sum(r['is_correct'] for r in recs) / len(recs)
            c_rts = [r['rt'] for r in recs if r['rt'] > 0 and r['is_correct']]
            c_rt = f"{sum(c_rts)/len(c_rts)*1000:.0f}" if c_rts else "—"
            cong_parts.append(f"{c[:3]}={c_acc:.0f}%/{c_rt}ms")

        cong_str = " ".join(cong_parts)

        print(
            f"  ── B{block_idx:02d} {block_condition} │ "
            f"{correct}/{total} ({pct:.0f}%) │ "
            f"Err={errors} Miss={misses} │ "
            f"RT={rt_str} │ {cong_str} │ "
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

    def _show_block_instruction(self, block_idx, condition):
        """
        Display block instruction card. Redraws every frame.
        Skipped if instruction_duration <= 0 (e.g., hybrid mini-blocks).
        """
        if self.instruction_duration <= 0:
            return

        if self.parport_actif:
            self.send_trigger(self.codes['instruction_onset'])

        kl = self.key_left.upper() if self.key_left != 'left' else '←'
        kr = self.key_right.upper() if self.key_right != 'right' else '→'
        n_total = len(self.block_sequence)

        txt = (
            f"Bloc {block_idx + 1}/{n_total}\n\n"
            f"Répondez à la flèche CENTRALE\n\n"
            f"<  →  [{kl}]       >  →  [{kr}]\n\n"
            f"Le plus vite possible !"
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
            self.EyeTracker.send_message(
                f"INSTR_BLOCK_{block_idx}_{condition.upper()}"
            )

    # =========================================================================
    # TRIAL — FRAME-ACCURATE
    # =========================================================================

    def run_trial(self, trial_data, block_idx, block_condition,
                  n_trials_in_block, trial_idx, isi):
        """
        One trial: Arrows → ISI fixation.
        Both phases redraw every frame. Response collected across both.
        stim_onset is relative to trigger t=0.

        Args:
            trial_data: (target_dir, flanker_dir, congruency) tuple
            isi: ISI duration for this specific trial (may be jittered)
        """
        target_dir, flanker_dir, congruency = trial_data
        stim_text = self._build_stimulus_text(target_dir, flanker_dir)

        self.arrow_stim.text = stim_text
        self.flush_keyboard()
        responded = False
        rt = None
        response_key = None
        response_dir = None

        # ── PHASE 1: STIMULUS ────────────────────────────────────────
        self.arrow_stim.draw()
        self.win.flip()
        stim_onset = self.task_clock.getTime()

        # TTL
        if congruency == 'congruent':
            ttl = self.codes['stim_congruent']
        elif congruency == 'incongruent':
            ttl = self.codes['stim_incongruent']
        else:
            ttl = self.codes['stim_neutral']

        if self.parport_actif:
            self.send_trigger(ttl)
        if self.eyetracker_actif:
            self.EyeTracker.send_message(
                f"STIM_{congruency[:3].upper()}_{target_dir[0].upper()}_"
                f"B{block_idx}_T{trial_idx}_t{stim_onset:.3f}"
            )

        stim_deadline = stim_onset + self.stim_duration
        while self.task_clock.getTime() < stim_deadline:
            keys = self.get_keys(key_list=self.valid_keys)
            if keys and not responded:
                responded = True
                rt = keys[0].rt - stim_onset
                response_key = keys[0].name
                response_dir = self.key_to_dir.get(response_key)
                if self.parport_actif:
                    code = (self.codes['response_correct']
                            if response_dir == target_dir
                            else self.codes['response_incorrect'])
                    self.send_trigger(code)

            self.arrow_stim.draw()
            self.win.flip()

        # ── PHASE 2: ISI (fixation) ─────────────────────────────────
        self.fixation_cross.draw()
        self.win.flip()
        isi_deadline = self.task_clock.getTime() + isi

        while self.task_clock.getTime() < isi_deadline:
            keys = self.get_keys(key_list=self.valid_keys)
            if keys and not responded:
                responded = True
                rt = keys[0].rt - stim_onset
                response_key = keys[0].name
                response_dir = self.key_to_dir.get(response_key)
                if self.parport_actif:
                    code = (self.codes['response_correct']
                            if response_dir == target_dir
                            else self.codes['response_incorrect'])
                    self.send_trigger(code)

            self.fixation_cross.draw()
            self.win.flip()

        # ── Correctness ─────────────────────────────────────────────
        is_correct = (response_dir == target_dir) if responded else False

        # ── LOG ──────────────────────────────────────────────────────
        self.log_trial(
            block_idx, block_condition, n_trials_in_block,
            trial_idx, target_dir, flanker_dir, congruency,
            stim_text, responded, response_key, response_dir,
            rt, is_correct, stim_onset, isi
        )

    # =========================================================================
    # BLOCK
    # =========================================================================

    def run_block(self, block_idx, block_def):
        """Run a complete block of trials."""
        condition = block_def['condition']
        n_trials = block_def['n_trials']
        prop_inc = block_def.get('prop_incongruent', self.prop_incongruent)
        block_start = self.task_clock.getTime()

        cond_label = condition.upper()
        print(
            f"\n╔══ Block {block_idx:02d} | {cond_label} "
            f"({n_trials} essais) | {self.paradigm} | "
            f"t={block_start:.1f}s ══════════════"
        )
        self.logger.log(
            f"Block {block_idx} | {condition} | {n_trials} essais | "
            f"t={block_start:.3f}s | START"
        )

        # TTL block marker
        block_code_key = f'block_{condition}'
        if self.parport_actif and block_code_key in self.codes:
            self.send_trigger(self.codes[block_code_key])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(
                f"BLOCK_{block_idx}_{cond_label}_START_t{block_start:.3f}"
            )

        # Block instruction (block/event paradigms only)
        self._show_block_instruction(block_idx, condition)
        if self.pre_block_fixation > 0:
            self._show_timed_fixation(self.pre_block_fixation)

        # Generate trials and ISIs
        trial_list = self._generate_trial_list(condition, n_trials, prop_inc)
        isis = self._generate_isis(n_trials)

        n_con = sum(1 for _, _, c in trial_list if c == 'congruent')
        n_inc = sum(1 for _, _, c in trial_list if c == 'incongruent')
        n_neu = sum(1 for _, _, c in trial_list if c == 'neutral')

        parts = []
        if n_con: parts.append(f"{n_con} CON")
        if n_inc: parts.append(f"{n_inc} INC")
        if n_neu: parts.append(f"{n_neu} NEU")
        composition = ", ".join(parts)

        self.logger.log(f"  Séquence: {n_trials} essais ({composition})")
        print(f"║ {composition}")
        if abs(self.isi_min - self.isi_max) > 0.01:
            print(f"║ ISI jittered: {self.isi_min}–{self.isi_max}s")
        print(f"╠{'═' * 56}")

        # Run trials
        for trial_idx, (trial_data, isi) in enumerate(zip(trial_list, isis)):
            self.run_trial(
                trial_data, block_idx, condition,
                n_trials, trial_idx, isi
            )

        if self.eyetracker_actif:
            t_end = self.task_clock.getTime()
            self.EyeTracker.send_message(
                f"BLOCK_{block_idx}_{cond_label}_END_t{t_end:.3f}"
            )

        print(f"╠{'═' * 56}")
        self._print_block_summary(block_idx, condition)
        print(f"╚{'═' * 58}\n")

        self.logger.log(f"Block {block_idx} | {condition} | END")

    # =========================================================================
    # REST
    # =========================================================================

    def _run_rest(self, label="", duration=None):
        """
        Display fixation rest period with TTL markers.

        Args:
            label: descriptive label for logging
            duration: override self.rest_duration if provided (for hybrid jitter)
        """
        dur = duration if duration is not None else self.rest_duration
        t_start = self.task_clock.getTime()
        self.logger.log(f"Rest {dur:.1f}s {label} | t={t_start:.3f}s")
        print(f"  ⏸ Rest {dur:.1f}s | t={t_start:.1f}s | {label}")

        if self.parport_actif:
            self.send_trigger(self.codes['rest_start'])
        if self.eyetracker_actif:
            self.EyeTracker.send_message(
                f"REST_START_{label}_t{t_start:.3f}"
            )

        self._show_timed_fixation(dur)

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
            1. Show task instructions with examples (press any key)
            2. Wait for 't' trigger key (fMRI sync or manual press)
            3. task_clock resets to t=0 at trigger reception
            4. All subsequent timestamps relative to this t=0
        """
        # ── 1. Instructions ──────────────────────────────────────────
        total_trials = sum(b['n_trials'] for b in self.block_sequence)
        kl = self.key_left.upper() if self.key_left != 'left' else '←'
        kr = self.key_right.upper() if self.key_right != 'right' else '→'

        if self.mode == 'fmri':
            instr_text = (
                f"Flanker — Attention sélective\n\n"
                f"Répondez à la direction de la flèche CENTRALE\n"
                f"en ignorant les flèches qui l'entourent.\n\n"
                f"Exemples :\n"
                f"   < < < < <   →   gauche [{kl}]\n"
                f"   > > < > >   →   gauche [{kl}]\n"
                f"   > > > > >   →   droite [{kr}]\n"
                f"   < < > < <   →   droite [{kr}]\n\n"
                f"Répondez le plus VITE et PRÉCISÉMENT possible.\n\n"
                f"Appuyez sur une touche pour continuer..."
            )
        else:
            instr_text = (
                f"Flanker — Attention sélective\n\n"
                f"Design : {self.design_name}\n"
                f"Total : {total_trials} essais\n\n"
                f"Répondez à la direction de la flèche CENTRALE\n"
                f"en ignorant les flèches qui l'entourent.\n\n"
                f"Exemples :\n"
                f"   < < < < <   →   gauche [{kl}]\n"
                f"   > > < > >   →   gauche [{kl}]\n"
                f"   > > > > >   →   droite [{kr}]\n"
                f"   < < > < <   →   droite [{kr}]\n\n"
                f"Répondez le plus VITE et PRÉCISÉMENT possible.\n\n"
                f"Appuyez sur une touche pour continuer..."
            )

        self.show_instructions(text_override=instr_text)

        # ── 2. Wait for trigger 't' — BOTH MODES ────────────────────
        self.wait_for_trigger(trigger_key=self.key_trigger)

        # ── 3. Capture absolute wall-clock time of trigger ───────────
        self.trigger_absolute_time = datetime.now().strftime(
            '%Y-%m-%d_%H:%M:%S.%f'
        )

        print("\n" + "=" * 60)
        print(f"  ⏱  TRIGGER REÇU — t=0")
        print(f"  Horloge absolue : {self.trigger_absolute_time}")
        print(f"  Mode : {self.mode} | Paradigme : {self.paradigm}")
        print(f"  Design : {self.design_name}")
        print("=" * 60)

        self.logger.ok(
            f"TRIGGER t=0 | {self.trigger_absolute_time} | "
            f"mode={self.mode} | paradigm={self.paradigm} | "
            f"design={self.design_name}"
        )

        # ── 4. Start triggers ───────────────────────────────────────
        if self.parport_actif:
            self.send_trigger(self.codes['start_exp'])
        if self.eyetracker_actif:
            self.EyeTracker.send_message("START_EXP_t0.000")

    def _end_session(self):
        """Cleanup, final save, stats display."""
        t_end = self.task_clock.getTime()
        self.logger.log(
            f"Session end | t={t_end:.3f}s | "
            f"Total duration: {t_end:.1f}s ({t_end / 60:.1f}min)"
        )
        print(f"\n  ⏱ Session duration: {t_end:.1f}s ({t_end / 60:.1f} min)")

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

        # QC auto-launch
        if saved_path and self.enregistrer:
            try:
                from tasks.qc.qc_flanker import qc_flanker
                qc_flanker(saved_path)
            except Exception as e:
                self.logger.warn(f"QC auto-launch failed: {e}")

        return saved_path

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def _print_stats(self):
        """Console + logger summary at end of session."""
        total = len(self.global_records)
        if total == 0:
            return

        correct = sum(r['is_correct'] for r in self.global_records)
        errors = sum(r['is_error'] for r in self.global_records)
        misses = sum(r['is_miss'] for r in self.global_records)

        print("\n" + "=" * 60)
        print(f"  RÉSULTATS GLOBAUX — Flanker")
        print(f"  {correct}/{total} ({100 * correct / total:.1f}%)")
        print(f"  Corrects={correct}  Erreurs={errors}  Miss={misses}")

        self.logger.ok(
            f"GLOBAL: {correct}/{total} ({100 * correct / total:.1f}%) | "
            f"Err={errors} Miss={misses}"
        )

        # ── Par congruence ───────────────────────────────────────────
        by_cong = defaultdict(list)
        for r in self.global_records:
            by_cong[r['congruency']].append(r)

        print(f"  {'─' * 54}")

        rt_by_cong = {}
        for cong in sorted(by_cong.keys()):
            records = by_cong[cong]
            n = len(records)
            acc = 100 * sum(r['is_correct'] for r in records) / n
            err = sum(r['is_error'] for r in records)
            mis = sum(r['is_miss'] for r in records)
            rts = [r['rt'] for r in records if r['rt'] > 0 and r['is_correct']]
            mean_rt = sum(rts) / len(rts) if rts else 0
            rt_str = f"{mean_rt * 1000:.0f}ms" if rts else "—"
            rt_by_cong[cong] = mean_rt

            onsets = [r['stim_onset'] for r in records]
            t_span = f"t={min(onsets):.1f}–{max(onsets):.1f}s"

            line = (
                f"  {cong:12s}: {acc:5.1f}% ({n:3d} essais) | "
                f"Err={err:2d} Miss={mis:2d} | RT={rt_str:>6s} | {t_span}"
            )
            print(line)
            self.logger.log(f"  {line.strip()}")

        # ── Effet de congruence ──────────────────────────────────────
        con_rt = rt_by_cong.get('congruent', 0)
        inc_rt = rt_by_cong.get('incongruent', 0)
        if con_rt > 0 and inc_rt > 0:
            effect_ms = (inc_rt - con_rt) * 1000
            print(f"\n  ⚡ Effet de congruence: {effect_ms:+.0f}ms "
                  f"(INC {inc_rt*1000:.0f} − CON {con_rt*1000:.0f})")
            self.logger.ok(f"Congruency effect: {effect_ms:+.0f}ms")

            # Accuracy difference
            con_acc = 100 * sum(r['is_correct'] for r in by_cong.get('congruent', []))
            inc_acc = 100 * sum(r['is_correct'] for r in by_cong.get('incongruent', []))
            n_con = len(by_cong.get('congruent', []))
            n_inc = len(by_cong.get('incongruent', []))
            if n_con > 0 and n_inc > 0:
                con_pct = con_acc / n_con
                inc_pct = inc_acc / n_inc
                print(f"  ⚡ Δ Accuracy: {inc_pct - con_pct:+.1f}% "
                      f"(INC {inc_pct:.1f}% − CON {con_pct:.1f}%)")

        print("=" * 60 + "\n")

    # =========================================================================
    # ENTRY POINT
    # =========================================================================

    def run(self):
        """Main entry point — runs the complete Flanker session."""
        self.logger.ok("=" * 60)
        self.logger.ok(
            f"Flanker | {self.nom} | Session {self.session} | "
            f"{self.mode} | {self.paradigm} | Design: {self.design_name}"
        )
        self.logger.ok("=" * 60)

        saved_path = None

        try:
            self._start_session()

            # ── Initial rest ─────────────────────────────────────────
            self._run_rest(label="initial")

            # ── Block loop ───────────────────────────────────────────
            n_blocks = len(self.block_sequence)
            for block_idx, block_def in enumerate(self.block_sequence):
                self.run_block(block_idx, block_def)

                is_last = (block_idx == n_blocks - 1)
                if not is_last:
                    # Hybrid: jittered inter-block fixation
                    if (self.paradigm == 'hybrid'
                            and self.inter_block_max > 0):
                        jitter_dur = random.uniform(
                            self.inter_block_min,
                            self.inter_block_max
                        )
                        self._run_rest(
                            label=f"jitter_block_{block_idx}",
                            duration=jitter_dur
                        )
                    else:
                        # Block / Event: standard rest
                        self._run_rest(label=f"after_block_{block_idx}")

            # ── Final rest ───────────────────────────────────────────
            self._run_rest(label="final")

            self.logger.ok("Tâche Flanker terminée avec succès.")

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
"""
Stroop Color-Word Task — blocked fMRI design.

Reference:
    Banich et al. (2000) blocked fMRI Stroop paradigm.

Paradigm:
    Name the INK COLOR of a printed word, ignoring the word itself.
    3 ink colors: red, orange, green
    3 trial types:
        - Congruent:   word matches ink (RED in red)
        - Incongruent: word conflicts with ink (RED in green)
        - Neutral:     word unrelated to color (LOT in red)

Trial timing (per paper):
    300ms fixation -> 1200ms colored word -> 500ms ITI = 2000ms total

Block structure:
    Neutral blocks alternate with congruent/incongruent blocks.
    Con/Inc blocks contain 50% neutral trials intermixed
    to prevent word-reading strategies.

Response mapping (PC mode):
    Left arrow  = RED
    Down arrow  = ORANGE
    Right arrow = GREEN
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime

from psychopy import visual

from tasks.base import BaseTask
from tasks.registry import register_task
from tasks.utils.sequence import desequence
from utils.console import SYM_OK, SYM_ERR


@register_task('stroop')
class StroopTask(BaseTask):
    """Stroop Color-Word fMRI task."""

    TASK_NAME = 'stroop'

    INK_COLORS = ['red', 'orange', 'green']

    # ═════════════════════════════════════════════════════════════════
    # SETUP
    # ═════════════════════════════════════════════════════════════════

    def _setup_stimuli(self) -> None:
        stim_cfg = self.task_config.get('stimulus', {})

        self._word_stim = visual.TextStim(
            self.win, text='', color='white',
            height=stim_cfg.get('word_height', 0.15),
            pos=(0, 0), bold=True, font='monospace',
        )

        # ── Color definitions ────────────────────────────────────────
        colors_cfg = self.task_config.get('colors', {})
        self._color_rgb = {
            'red':    colors_cfg.get('red',    [1.0, -1.0, -1.0]),
            'orange': colors_cfg.get('orange', [1.0,  0.3, -1.0]),
            'green':  colors_cfg.get('green',  [-1.0, 0.8, -1.0]),
        }

        # ── Word lists ───────────────────────────────────────────────
        cw = self.task_config.get('color_words', {})
        self._color_words = {
            'red':    cw.get('red', 'RED'),
            'orange': cw.get('orange', 'ORANGE'),
            'green':  cw.get('green', 'GREEN'),
        }

        nw = self.task_config.get('neutral_words', {})
        self._neutral_words = {
            'red':    nw.get('red',    ['LOT', 'SET', 'PIN']),
            'green':  nw.get('green',  ['CHAIR', 'PLANE', 'TABLE']),
            'orange': nw.get('orange', ['BRIDGE', 'PLANET', 'STAPLE']),
        }

        # ── Response keys (3-choice) ────────────────────────────────
        mode = self.settings.mode
        if mode == 'fmri':
            keys_cfg = self.task_config.get('response_keys_fmri', {})
        else:
            keys_cfg = self.task_config.get('response_keys_pc', {})

        self._color_to_key = {
            'red':    keys_cfg.get('red',    'left'),
            'orange': keys_cfg.get('orange', 'down'),
            'green':  keys_cfg.get('green',  'right'),
        }
        self._key_to_color = {v: k for k, v in self._color_to_key.items()}
        self._valid_keys = list(self._color_to_key.values())

        # ── TTL codes ────────────────────────────────────────────────
        self._ttl = self.task_config.get('ttl_codes', {})

    # ═════════════════════════════════════════════════════════════════
    # INSTRUCTIONS
    # ═════════════════════════════════════════════════════════════════

    def _get_instruction_text(self) -> str:
        k_r = self._color_to_key['red'].upper()
        k_o = self._color_to_key['orange'].upper()
        k_g = self._color_to_key['green'].upper()
        total = sum(b.get('n_trials', 0) for b in self.block_sequence)

        return (
            f"Stroop — Color naming\n\n"
            f"Design: {self.design.get('name', '')}\n"
            f"Total: {total} trials\n\n"
            f"Name the INK COLOR of each word.\n"
            f"Ignore what the word says!\n\n"
            f"  RED    ->  [{k_r}]\n"
            f"  ORANGE ->  [{k_o}]\n"
            f"  GREEN  ->  [{k_g}]\n\n"
            f"Be as FAST and ACCURATE as possible.\n\n"
            f"Press any key to continue..."
        )

    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        instr_dur = self.design.get('instruction_duration', 3.0)
        if instr_dur <= 0:
            return None

        k_r = self._color_to_key['red'].upper()
        k_o = self._color_to_key['orange'].upper()
        k_g = self._color_to_key['green'].upper()
        n = len(self.block_sequence)
        cond = block_def['condition'].upper()

        return (
            f"Block {block_idx + 1}/{n}  ({cond})\n\n"
            f"Name the INK COLOR\n\n"
            f"RED=[{k_r}]  ORANGE=[{k_o}]  GREEN=[{k_g}]"
        )

    # ═════════════════════════════════════════════════════════════════
    # TRIAL GENERATION
    # ═════════════════════════════════════════════════════════════════

    def generate_trials(self, block_def: dict) -> list:
        """
        Generate trial list for one block.

        Each trial = (word, ink_color, trial_type)

        Block types:
            neutral:      all neutral trials
            congruent:    50% congruent + 50% neutral (mixed)
            incongruent:  50% incongruent + 50% neutral (mixed)
            mixed:        equal mix of all three types
        """
        condition = block_def['condition']
        n = block_def['n_trials']
        prop_mix = self.design.get('prop_neutral_mix', 0.5)

        if condition == 'neutral':
            trials = self._gen_neutral(n)

        elif condition == 'congruent':
            n_con = int(round(n * (1.0 - prop_mix)))
            n_neu = n - n_con
            trials = self._gen_congruent(n_con) + self._gen_neutral(n_neu)

        elif condition == 'incongruent':
            n_inc = int(round(n * (1.0 - prop_mix)))
            n_neu = n - n_inc
            trials = self._gen_incongruent(n_inc) + self._gen_neutral(n_neu)

        elif condition == 'mixed':
            p_con = block_def.get('prop_congruent', 0.33)
            p_inc = block_def.get('prop_incongruent', 0.33)
            n_con = int(round(n * p_con))
            n_inc = int(round(n * p_inc))
            n_neu = n - n_con - n_inc
            trials = (
                self._gen_congruent(n_con)
                + self._gen_incongruent(n_inc)
                + self._gen_neutral(n_neu)
            )
        else:
            trials = self._gen_neutral(n)

        random.shuffle(trials)
        # Desequence on ink_color to avoid >3 same response in a row
        trials = desequence(trials, key_func=lambda t: t[1], max_consecutive=3)
        return trials

    def _gen_congruent(self, n: int) -> list:
        """Generate n congruent trials (word == ink color)."""
        trials = []
        colors = self.INK_COLORS.copy()
        for i in range(n):
            c = colors[i % len(colors)]
            word = self._color_words[c]
            trials.append((word, c, 'congruent'))
        random.shuffle(trials)
        return trials

    def _gen_incongruent(self, n: int) -> list:
        """Generate n incongruent trials (word != ink color)."""
        trials = []
        for i in range(n):
            ink = self.INK_COLORS[i % len(self.INK_COLORS)]
            # Pick a word from a DIFFERENT color
            other_colors = [c for c in self.INK_COLORS if c != ink]
            word_color = random.choice(other_colors)
            word = self._color_words[word_color]
            trials.append((word, ink, 'incongruent'))
        random.shuffle(trials)
        return trials

    def _gen_neutral(self, n: int) -> list:
        """Generate n neutral trials (non-color word in colored ink)."""
        trials = []
        for i in range(n):
            ink = self.INK_COLORS[i % len(self.INK_COLORS)]
            # Pick a neutral word matched to any color-word length
            # Use words matched to the ink color's word length
            word_list = self._neutral_words.get(ink, ['XXX'])
            word = random.choice(word_list)
            trials.append((word, ink, 'neutral'))
        random.shuffle(trials)
        return trials

    # ═════════════════════════════════════════════════════════════════
    # TRIAL EXECUTION
    # ═════════════════════════════════════════════════════════════════

    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:
        """
        One trial: fixation(300ms) -> colored word(1200ms) -> ITI(500ms).

        Responses collected during stimulus + ITI phases.
        """
        word, ink_color, trial_type = trial_data

        fix_dur = self.design.get('fixation_duration', 0.3)
        stim_dur = self.design.get('stim_duration', 1.2)
        iti_dur = self.design.get('iti_duration', 0.5)

        correct_key = self._color_to_key[ink_color]
        self.flush_keyboard()

        responded = False
        rt = None
        response_key = None
        response_color = None

        # ── Phase 1: Fixation (300ms) ────────────────────────────────
        self._fixation.draw()
        self.win.flip()
        fix_onset = self.clock.time
        fix_deadline = fix_onset + fix_dur

        while self.clock.time < fix_deadline:
            self._fixation.draw()
            self.win.flip()
            self.get_keys(key_list=[])  # escape check only

        # ── Phase 2: Colored word (1200ms) ───────────────────────────
        self._word_stim.text = word
        self._word_stim.color = self._color_rgb[ink_color]
        self._word_stim.draw()
        self.win.flip()
        stim_onset = self.clock.time

        # TTL
        ttl_code = self._ttl.get(f'stim_{trial_type}', 0)
        if ttl_code:
            self.hardware.send_trigger(ttl_code)
        self.hardware.send_eyetracker_message(
            f"STIM_{trial_type[:3].upper()}_{word}_{ink_color}_"
            f"B{block_idx}_T{trial_idx}_t{stim_onset:.3f}"
        )

        stim_deadline = stim_onset + stim_dur
        while self.clock.time < stim_deadline:
            if not responded:
                keys = self.get_keys(key_list=self._valid_keys)
                if keys:
                    responded = True
                    rt = self.clock.time - stim_onset
                    response_key = keys[0].name
                    response_color = self._key_to_color.get(response_key)
                    ttl_r = self._ttl.get(
                        'response_correct' if response_color == ink_color
                        else 'response_incorrect', 0
                    )
                    if ttl_r:
                        self.hardware.send_trigger(ttl_r)
            self._word_stim.draw()
            self.win.flip()

        # ── Phase 3: ITI fixation (500ms) ────────────────────────────
        self._fixation.draw()
        self.win.flip()
        iti_deadline = self.clock.time + iti_dur

        while self.clock.time < iti_deadline:
            if not responded:
                keys = self.get_keys(key_list=self._valid_keys)
                if keys:
                    responded = True
                    rt = self.clock.time - stim_onset
                    response_key = keys[0].name
                    response_color = self._key_to_color.get(response_key)
                    ttl_r = self._ttl.get(
                        'response_correct' if response_color == ink_color
                        else 'response_incorrect', 0
                    )
                    if ttl_r:
                        self.hardware.send_trigger(ttl_r)
            self._fixation.draw()
            self.win.flip()

        # ── Classify ─────────────────────────────────────────────────
        is_correct = (response_color == ink_color) if responded else False

        # ── Record ───────────────────────────────────────────────────
        record = self._base_record(block_idx, trial_idx, block_def)
        record.update({
            'block_condition': block_def['condition'],
            'n_trials_in_block': block_def['n_trials'],
            'word': word,
            'ink_color': ink_color,
            'trial_type': trial_type,
            'correct_key': correct_key,
            'correct_color': ink_color,
            'responded': int(responded),
            'response_key': response_key or '',
            'response_color': response_color or '',
            'rt': round(rt, 4) if rt is not None else -1,
            'is_correct': int(is_correct),
            'is_error': int(responded and not is_correct),
            'is_miss': int(not responded),
            'stim_onset': round(stim_onset, 4),
            'fixation_duration': fix_dur,
            'stim_duration': stim_dur,
            'iti_duration': iti_dur,
        })

        self._print_trial(
            block_idx, trial_idx, word, ink_color, trial_type,
            responded, is_correct, rt, stim_onset,
        )
        return record

    # ═════════════════════════════════════════════════════════════════
    # CONSOLE
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _print_trial(bi, ti, word, ink, ttype, responded, correct, rt, onset):
        tt = ttype[:3].upper()
        if not responded:
            tag, sym = 'MISS', SYM_ERR
        elif correct:
            tag, sym = 'OK  ', SYM_OK
        else:
            tag, sym = 'ERR ', SYM_ERR
        rt_s = f"{rt * 1000:5.0f}ms" if rt and rt > 0 else "    - "
        # Color indicator
        ink_mark = ink[0].upper()
        print(
            f"  B{bi:02d} T{ti:02d} | t={onset:8.3f}s | "
            f"{tt} | {word:>8s} [{ink_mark}] | {tag} {sym} | {rt_s}"
        )

    def _print_task_stats(self) -> None:
        records = self.data_writer.records
        if not records:
            return

        total = len(records)
        correct = sum(r['is_correct'] for r in records)
        errors = sum(r.get('is_error', 0) for r in records)
        misses = sum(r.get('is_miss', 0) for r in records)

        print(f"\n{'=' * 60}")
        print(f"  STROOP RESULTS - {correct}/{total} "
              f"({100 * correct / total:.1f}%)")
        print(f"  Correct={correct}  Errors={errors}  Misses={misses}")
        print(f"  {'-' * 54}")

        by_type = defaultdict(list)
        for r in records:
            by_type[r['trial_type']].append(r)

        rt_by_type = {}
        for ttype in ['congruent', 'incongruent', 'neutral']:
            recs = by_type.get(ttype, [])
            if not recs:
                continue
            n = len(recs)
            acc = 100 * sum(r['is_correct'] for r in recs) / n
            rts = [r['rt'] for r in recs if r['rt'] > 0 and r['is_correct']]
            mean_rt = sum(rts) / len(rts) if rts else 0
            rt_by_type[ttype] = mean_rt
            rt_str = f"{mean_rt * 1000:.0f}ms" if rts else "-"
            err = sum(r.get('is_error', 0) for r in recs)
            mis = sum(r.get('is_miss', 0) for r in recs)
            print(
                f"  {ttype:12s}: {acc:5.1f}% ({n:3d} trials) | "
                f"RT={rt_str:>6s} | Err={err:2d} Miss={mis:2d}"
            )

        # ── Stroop effects ───────────────────────────────────────────
        con_rt = rt_by_type.get('congruent', 0)
        inc_rt = rt_by_type.get('incongruent', 0)
        neu_rt = rt_by_type.get('neutral', 0)

        print(f"  {'-' * 54}")

        if inc_rt > 0 and con_rt > 0:
            stroop_effect = (inc_rt - con_rt) * 1000
            print(f"  Stroop effect (INC-CON):      {stroop_effect:+.0f}ms")

        if inc_rt > 0 and neu_rt > 0:
            interference = (inc_rt - neu_rt) * 1000
            print(f"  Interference (INC-NEU):       {interference:+.0f}ms")

        if neu_rt > 0 and con_rt > 0:
            facilitation = (neu_rt - con_rt) * 1000
            print(f"  Facilitation (NEU-CON):       {facilitation:+.0f}ms")

        # ── Per ink-color accuracy ───────────────────────────────────
        by_ink = defaultdict(list)
        for r in records:
            by_ink[r['ink_color']].append(r)

        if len(by_ink) > 1:
            print(f"  {'-' * 54}")
            for color in sorted(by_ink):
                recs = by_ink[color]
                n = len(recs)
                acc = 100 * sum(r['is_correct'] for r in recs) / n
                rts = [r['rt'] for r in recs if r['rt'] > 0 and r['is_correct']]
                rt_str = f"{sum(rts)/len(rts)*1000:.0f}ms" if rts else "-"
                print(f"  ink={color:7s}: {acc:5.1f}% ({n} trials) | RT={rt_str}")

        print(f"{'=' * 60}\n")
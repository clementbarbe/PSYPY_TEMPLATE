"""
Stroop Color-Word Task (French) — blocked fMRI design.

Paradigme :
    Nommer la COULEUR DE L'ENCRE d'un mot, en ignorant le mot.
    3 couleurs : rouge, orange, vert
    3 types d'essais :
        - Congruent :   mot = encre (ROUGE en rouge)
        - Incongruent : mot != encre (ROUGE en vert)
        - Neutre :      mot non-couleur (TABLE en rouge)

Timing (par essai) :
    300ms fixation + 1200ms mot colore + 500ms ITI = 2000ms

Touches PC :
    Fleche gauche = ROUGE
    Fleche bas    = ORANGE
    Fleche droite = VERT
"""

from __future__ import annotations

import random
from collections import defaultdict

from psychopy import visual

from tasks.base import BaseTask
from tasks.registry import register_task
from tasks.utils.sequence import desequence
from utils.console import SYM_OK, SYM_ERR


@register_task('stroop')
class StroopTask(BaseTask):
    """Stroop Color-Word fMRI task (French)."""

    TASK_NAME = 'stroop'

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

        colors_cfg = self.task_config.get('colors', {})
        self._color_rgb = {
            'rouge':  colors_cfg.get('rouge',  [1.0, -1.0, -1.0]),
            'orange': colors_cfg.get('orange', [1.0,  0.3, -1.0]),
            'vert':   colors_cfg.get('vert',   [-1.0, 0.8, -1.0]),
        }
        self._ink_colors = list(self._color_rgb.keys())

        cw = self.task_config.get('color_words', {})
        self._color_words = {
            'rouge':  cw.get('rouge',  'ROUGE'),
            'orange': cw.get('orange', 'ORANGE'),
            'vert':   cw.get('vert',   'VERT'),
        }

        nw = self.task_config.get('neutral_words', {})
        self._neutral_words = {
            'rouge':  nw.get('rouge',  ['TABLE', 'PORTE', 'LIVRE']),
            'vert':   nw.get('vert',   ['PONT', 'BRAS', 'LOUP']),
            'orange': nw.get('orange', ['JARDIN', 'BATEAU', 'PIERRE']),
        }

        mode = self.settings.mode
        if mode == 'fmri':
            keys_cfg = self.task_config.get('response_keys_fmri', {})
        else:
            keys_cfg = self.task_config.get('response_keys_pc', {})

        self._color_to_key = {
            'rouge':  keys_cfg.get('rouge',  'left'),
            'orange': keys_cfg.get('orange', 'down'),
            'vert':   keys_cfg.get('vert',   'right'),
        }
        self._key_to_color = {v: k for k, v in self._color_to_key.items()}
        self._valid_keys = list(self._color_to_key.values())

        self._ttl = self.task_config.get('ttl_codes', {})

    # ═════════════════════════════════════════════════════════════════
    # INSTRUCTIONS
    # ═════════════════════════════════════════════════════════════════

    def _get_instruction_text(self) -> str:
        k_r = self._color_to_key['rouge'].upper()
        k_o = self._color_to_key['orange'].upper()
        k_v = self._color_to_key['vert'].upper()
        total = sum(b.get('n_trials', 0) for b in self.block_sequence)

        return (
            f"Stroop — Denomination de couleur\n\n"
            f"Design : {self.design.get('name', '')}\n"
            f"Total : {total} essais\n\n"
            f"Nommez la COULEUR DE L'ENCRE de chaque mot.\n"
            f"Ignorez ce que le mot dit !\n\n"
            f"  ROUGE   ->  [{k_r}]\n"
            f"  ORANGE  ->  [{k_o}]\n"
            f"  VERT    ->  [{k_v}]\n\n"
            f"Repondez le plus VITE et PRECISEMENT possible.\n\n"
            f"Appuyez sur une touche pour continuer..."
        )

    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        instr_dur = self.design.get('instruction_duration', 3.0)
        if instr_dur <= 0:
            return None

        k_r = self._color_to_key['rouge'].upper()
        k_o = self._color_to_key['orange'].upper()
        k_v = self._color_to_key['vert'].upper()
        n = len(self.block_sequence)

        return (
            f"Bloc {block_idx + 1}/{n}\n\n"
            f"Nommez la COULEUR DE L'ENCRE\n\n"
            f"ROUGE=[{k_r}]  ORANGE=[{k_o}]  VERT=[{k_v}]"
        )

    # ═════════════════════════════════════════════════════════════════
    # TRIAL GENERATION
    # ═════════════════════════════════════════════════════════════════

    def generate_trials(self, block_def: dict) -> list:
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
        trials = desequence(trials, key_func=lambda t: t[1], max_consecutive=3)
        return trials

    def _gen_congruent(self, n):
        trials = []
        for i in range(n):
            c = self._ink_colors[i % len(self._ink_colors)]
            trials.append((self._color_words[c], c, 'congruent'))
        random.shuffle(trials)
        return trials

    def _gen_incongruent(self, n):
        trials = []
        for i in range(n):
            ink = self._ink_colors[i % len(self._ink_colors)]
            others = [c for c in self._ink_colors if c != ink]
            word_c = random.choice(others)
            trials.append((self._color_words[word_c], ink, 'incongruent'))
        random.shuffle(trials)
        return trials

    def _gen_neutral(self, n):
        trials = []
        for i in range(n):
            ink = self._ink_colors[i % len(self._ink_colors)]
            wlist = self._neutral_words.get(ink, ['XXX'])
            trials.append((random.choice(wlist), ink, 'neutral'))
        random.shuffle(trials)
        return trials

    # ═════════════════════════════════════════════════════════════════
    # TRIAL EXECUTION
    # ═════════════════════════════════════════════════════════════════

    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:
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

        # ── Fixation 300ms ───────────────────────────────────────────
        self._fixation.draw()
        self.win.flip()
        deadline = self.clock.time + fix_dur
        while self.clock.time < deadline:
            self._fixation.draw()
            self.win.flip()
            self.get_keys(key_list=[])

        # ── Mot colore 1200ms ────────────────────────────────────────
        self._word_stim.text = word
        self._word_stim.color = self._color_rgb[ink_color]
        self._word_stim.draw()
        self.win.flip()
        stim_onset = self.clock.time

        ttl_code = self._ttl.get(f'stim_{trial_type}', 0)
        if ttl_code:
            self.hardware.send_trigger(ttl_code)
        self.hardware.send_eyetracker_message(
            f"STIM_{trial_type[:3].upper()}_{word}_{ink_color}_"
            f"B{block_idx}_T{trial_idx}_t{stim_onset:.3f}"
        )

        deadline = stim_onset + stim_dur
        while self.clock.time < deadline:
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

        # ── ITI 500ms ────────────────────────────────────────────────
        self._fixation.draw()
        self.win.flip()
        deadline = self.clock.time + iti_dur
        while self.clock.time < deadline:
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

        is_correct = (response_color == ink_color) if responded else False

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
        print(
            f"  B{bi:02d} T{ti:02d} | t={onset:8.3f}s | "
            f"{tt} | {word:>8s} [{ink[:3]}] | {tag} {sym} | {rt_s}"
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
        print(f"  STROOP - {correct}/{total} "
              f"({100 * correct / total:.1f}%)")
        print(f"  Correct={correct}  Erreurs={errors}  Miss={misses}")
        print(f"  {'-' * 54}")

        by_type = defaultdict(list)
        for r in records:
            by_type[r['trial_type']].append(r)

        rt_by = {}
        for tt in ['congruent', 'incongruent', 'neutral']:
            recs = by_type.get(tt, [])
            if not recs:
                continue
            n = len(recs)
            acc = 100 * sum(r['is_correct'] for r in recs) / n
            rts = [r['rt'] for r in recs if r['rt'] > 0 and r['is_correct']]
            m = sum(rts) / len(rts) if rts else 0
            rt_by[tt] = m
            rt_s = f"{m * 1000:.0f}ms" if rts else "-"
            err = sum(r.get('is_error', 0) for r in recs)
            mis = sum(r.get('is_miss', 0) for r in recs)
            print(
                f"  {tt:12s}: {acc:5.1f}% ({n:3d}) | "
                f"RT={rt_s:>6s} | Err={err:2d} Miss={mis:2d}"
            )

        con = rt_by.get('congruent', 0)
        inc = rt_by.get('incongruent', 0)
        neu = rt_by.get('neutral', 0)

        print(f"  {'-' * 54}")
        if inc > 0 and con > 0:
            print(f"  Effet Stroop  (INC-CON): {(inc-con)*1000:+.0f}ms")
        if inc > 0 and neu > 0:
            print(f"  Interference  (INC-NEU): {(inc-neu)*1000:+.0f}ms")
        if neu > 0 and con > 0:
            print(f"  Facilitation  (NEU-CON): {(neu-con)*1000:+.0f}ms")

        print(f"{'=' * 60}\n")
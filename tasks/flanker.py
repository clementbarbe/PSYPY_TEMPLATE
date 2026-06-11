"""
Eriksen Flanker Task — Windows compatible, escape-aware.

2-AFC: respond to the direction of the CENTRAL arrow.
RT computed from self.clock.time (not key.rt).
Escape triggers clean abort at any point.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime

from psychopy import visual

from tasks.base import BaseTask
from tasks.registry import register_task
from tasks.utils.sequence import desequence, generate_jittered_isis
from utils.console import SYM_OK, SYM_ERR


@register_task('flanker')
class FlankerTask(BaseTask):
    """Eriksen Flanker fMRI task."""

    TASK_NAME = 'flanker'

    def _setup_stimuli(self) -> None:
        stim_cfg = self.task_config.get('stimulus', {})
        self._arrow_stim = visual.TextStim(
            self.win, text='', color='white',
            height=stim_cfg.get('arrow_height', 0.15),
            pos=(0, 0), bold=True,
            font=stim_cfg.get('arrow_font', 'monospace'),
        )
        self._key_left = self._response_keys.get('left', 'left')
        self._key_right = self._response_keys.get('right', 'right')
        self._valid_keys = [self._key_left, self._key_right]
        self._key_to_dir = {
            self._key_left: 'left',
            self._key_right: 'right',
        }
        self._dir_to_key = {v: k for k, v in self._key_to_dir.items()}
        self._ttl = self.task_config.get('ttl_codes', {})

    def _get_instruction_text(self) -> str:
        kl = self._key_left.upper() if len(self._key_left) > 1 else self._key_left
        kr = self._key_right.upper() if len(self._key_right) > 1 else self._key_right
        total = sum(b.get('n_trials', 0) for b in self.block_sequence)
        return (
            f"Flanker — Attention selective\n\n"
            f"Design : {self.design.get('name', '')}\n"
            f"Total : {total} essais\n\n"
            f"Repondez a la direction de la fleche CENTRALE\n"
            f"en ignorant les fleches qui l'entourent.\n\n"
            f"Exemples :\n"
            f"   < < < < <   ->   gauche [{kl}]\n"
            f"   > > < > >   ->   gauche [{kl}]\n"
            f"   > > > > >   ->   droite [{kr}]\n"
            f"   < < > < <   ->   droite [{kr}]\n\n"
            f"Repondez le plus VITE et PRECISEMENT possible.\n\n"
            f"Appuyez sur une touche pour continuer..."
        )

    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        instr_dur = self.design.get('instruction_duration', 3.0)
        if instr_dur <= 0:
            return None
        kl = self._key_left.upper() if len(self._key_left) > 1 else '<-'
        kr = self._key_right.upper() if len(self._key_right) > 1 else '->'
        n_total = len(self.block_sequence)
        return (
            f"Bloc {block_idx + 1}/{n_total}\n\n"
            f"Repondez a la fleche CENTRALE\n\n"
            f"<  ->  [{kl}]       >  ->  [{kr}]\n\n"
            f"Le plus vite possible !"
        )

    @staticmethod
    def _build_arrow_text(target_dir: str, flanker_dir: str) -> str:
        target = '<' if target_dir == 'left' else '>'
        if flanker_dir == 'neutral':
            flanker = '-'
        elif flanker_dir == 'left':
            flanker = '<'
        else:
            flanker = '>'
        return f"{flanker}  {flanker}  {target}  {flanker}  {flanker}"

    def generate_trials(self, block_def: dict) -> list:
        condition = block_def['condition']
        n = block_def['n_trials']
        prop_inc = block_def.get('prop_incongruent', 0.5)

        trials = []
        if condition == 'congruent':
            n_l = n // 2
            trials += [('left', 'left', 'congruent')] * n_l
            trials += [('right', 'right', 'congruent')] * (n - n_l)
        elif condition == 'incongruent':
            n_l = n // 2
            trials += [('left', 'right', 'incongruent')] * n_l
            trials += [('right', 'left', 'incongruent')] * (n - n_l)
        elif condition == 'mixed':
            n_inc = int(round(n * prop_inc))
            n_con = n - n_inc
            n_cl = n_con // 2
            trials += [('left', 'left', 'congruent')] * n_cl
            trials += [('right', 'right', 'congruent')] * (n_con - n_cl)
            n_il = n_inc // 2
            trials += [('left', 'right', 'incongruent')] * n_il
            trials += [('right', 'left', 'incongruent')] * (n_inc - n_il)
        elif condition == 'neutral':
            n_l = n // 2
            trials += [('left', 'neutral', 'neutral')] * n_l
            trials += [('right', 'neutral', 'neutral')] * (n - n_l)

        trials = desequence(trials, key_func=lambda t: t[0])
        isis = generate_jittered_isis(
            n,
            self.design.get('isi_min', 1.0),
            self.design.get('isi_max', 1.0),
        )
        return [(t[0], t[1], t[2], isi) for t, isi in zip(trials, isis)]

    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:
        target_dir, flanker_dir, congruency, isi = trial_data
        stim_text = self._build_arrow_text(target_dir, flanker_dir)

        self._arrow_stim.text = stim_text
        self.flush_keyboard()

        responded = False
        rt = None
        response_key = None
        response_dir = None

        stim_duration = self.design.get('stim_duration', 1.5)

        # Phase 1: Stimulus
        self._arrow_stim.draw()
        self.win.flip()
        stim_onset = self.clock.time

        ttl_code = self._ttl.get(f'stim_{congruency}', 0)
        if ttl_code:
            self.hardware.send_trigger(ttl_code)
        self.hardware.send_eyetracker_message(
            f"STIM_{congruency[:3].upper()}_{target_dir[0]}_"
            f"B{block_idx}_T{trial_idx}_t{stim_onset:.3f}"
        )

        deadline = stim_onset + stim_duration
        while self.clock.time < deadline:
            if not responded:
                keys = self.get_keys(key_list=self._valid_keys)
                if keys:
                    responded = True
                    rt = self.clock.time - stim_onset
                    response_key = keys[0].name
                    response_dir = self._key_to_dir.get(response_key)
                    resp_ttl = self._ttl.get(
                        'response_correct' if response_dir == target_dir
                        else 'response_incorrect', 0
                    )
                    if resp_ttl:
                        self.hardware.send_trigger(resp_ttl)
            self._arrow_stim.draw()
            self.win.flip()

        # Phase 2: ISI fixation
        self._fixation.draw()
        self.win.flip()
        isi_deadline = self.clock.time + isi

        while self.clock.time < isi_deadline:
            if not responded:
                keys = self.get_keys(key_list=self._valid_keys)
                if keys:
                    responded = True
                    rt = self.clock.time - stim_onset
                    response_key = keys[0].name
                    response_dir = self._key_to_dir.get(response_key)
                    resp_ttl = self._ttl.get(
                        'response_correct' if response_dir == target_dir
                        else 'response_incorrect', 0
                    )
                    if resp_ttl:
                        self.hardware.send_trigger(resp_ttl)
            self._fixation.draw()
            self.win.flip()

        is_correct = (response_dir == target_dir) if responded else False

        record = self._base_record(block_idx, trial_idx, block_def)
        record.update({
            'block_condition': block_def['condition'],
            'n_trials_in_block': block_def['n_trials'],
            'target_direction': target_dir,
            'flanker_direction': flanker_dir,
            'congruency': congruency,
            'stimulus': stim_text,
            'correct_key': self._dir_to_key.get(target_dir, ''),
            'responded': int(responded),
            'response_key': response_key or '',
            'response_direction': response_dir or '',
            'rt': round(rt, 4) if rt is not None else -1,
            'is_correct': int(is_correct),
            'is_error': int(responded and not is_correct),
            'is_miss': int(not responded),
            'stim_onset': round(stim_onset, 4),
            'stim_duration': stim_duration,
            'isi_actual': round(isi, 4),
        })

        self._print_trial(block_idx, trial_idx, stim_text, congruency,
                          responded, is_correct, rt, stim_onset)
        return record

    @staticmethod
    def _print_trial(bi, ti, stim, cong, responded, correct, rt, onset):
        c = cong[:3].upper()
        if not responded:
            tag, sym = 'MISS', SYM_ERR
        elif correct:
            tag, sym = 'OK  ', SYM_OK
        else:
            tag, sym = 'ERR ', SYM_ERR
        rt_s = f"{rt * 1000:5.0f}ms" if rt and rt > 0 else "    - "
        print(
            f"  B{bi:02d} T{ti:02d} | t={onset:8.3f}s | "
            f"{c} | {stim} | {tag} {sym} | {rt_s}"
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
        print(f"  FLANKER RESULTS - {correct}/{total} "
              f"({100 * correct / total:.1f}%)")
        print(f"  Correct={correct}  Errors={errors}  Misses={misses}")

        by_cong = defaultdict(list)
        for r in records:
            by_cong[r['congruency']].append(r)

        rt_by_cong = {}
        for cong in sorted(by_cong):
            recs = by_cong[cong]
            n = len(recs)
            acc = 100 * sum(r['is_correct'] for r in recs) / n
            rts = [r['rt'] for r in recs if r['rt'] > 0 and r['is_correct']]
            mean_rt = sum(rts) / len(rts) if rts else 0
            rt_by_cong[cong] = mean_rt
            rt_str = f"{mean_rt * 1000:.0f}ms" if rts else "-"
            print(f"  {cong:12s}: {acc:5.1f}% ({n} trials) | RT={rt_str}")

        con_rt = rt_by_cong.get('congruent', 0)
        inc_rt = rt_by_cong.get('incongruent', 0)
        if con_rt > 0 and inc_rt > 0:
            effect = (inc_rt - con_rt) * 1000
            print(f"\n  Congruency effect: {effect:+.0f}ms")

        print(f"{'=' * 60}\n")
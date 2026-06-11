"""
N-Back Task — Windows compatible, escape-aware.

Go/No-Go paradigm:
    0-back: press when letter == target
    N-back: press when letter == letter N trials ago

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
from tasks.utils.sdt import classify_sdt
from utils.console import SYM_OK, SYM_ERR, SYM_STAR, SYM_DOT


@register_task('nback')
class NBackTask(BaseTask):
    """N-Back fMRI task."""

    TASK_NAME = 'nback'

    CONSONANTS = [
        'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K',
        'L', 'M', 'N', 'P', 'R', 'S', 'T', 'V', 'W', 'Z',
    ]
    ZERO_BACK_TARGETS = ['B', 'D', 'K', 'M', 'R', 'T']

    def _setup_stimuli(self) -> None:
        stim_cfg = self.task_config.get('stimulus', {})
        self._letter_stim = visual.TextStim(
            self.win, text='', color='white',
            height=stim_cfg.get('letter_height', 0.15),
            pos=(0, 0), bold=True,
        )
        self._target_cue = visual.TextStim(
            self.win, text='', color='cyan',
            height=stim_cfg.get('cue_height', 0.20),
            pos=(0, 0.15), bold=True,
        )
        self._key_go = self._response_keys.get('go', 'space')
        self._valid_keys = [self._key_go]
        self._ttl = self.task_config.get('ttl_codes', {})

    def _get_instruction_text(self) -> str:
        total = sum(b.get('n_trials', 0) for b in self.block_sequence)
        key = self._key_go.upper()
        return (
            f"N-Back - Memoire de travail\n\n"
            f"Design : {self.design.get('name', '')}\n"
            f"Total : {total} essais\n\n"
            f"0-back : Appuyez sur [{key}] "
            f"quand vous voyez la lettre cible.\n"
            f"N-back : Appuyez sur [{key}] "
            f"si la lettre = celle d'il y a N.\n"
            f"Sinon : ne faites rien.\n\n"
            f"Appuyez sur une touche pour continuer..."
        )

    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        n_level = block_def['level']
        key = self._key_go.upper()

        if n_level == 0:
            target = random.choice(self.ZERO_BACK_TARGETS)
            block_def['_zero_back_target'] = target
            return (
                f"0-BACK\n\n"
                f"Appuyez sur [{key}]\n"
                f"quand vous voyez la lettre :\n\n"
                f"    {target}"
            )
        else:
            return (
                f"{n_level}-BACK\n\n"
                f"Appuyez sur [{key}]\n"
                f"si la lettre est la meme\n"
                f"qu'il y a {n_level} essai{'s' if n_level > 1 else ''}.\n\n"
                f"Ne faites rien sinon."
            )

    def generate_trials(self, block_def: dict) -> list:
        n_level = block_def['level']
        n_trials = block_def['n_trials']
        target_ratio = self.design.get('target_ratio', 0.33)
        num_targets = max(1, int(n_trials * target_ratio))
        zero_target = block_def.get('_zero_back_target')

        if n_level == 0:
            return self._gen_zero_back(n_trials, num_targets, zero_target)
        else:
            return self._gen_n_back(n_level, n_trials, num_targets)

    def _gen_zero_back(self, n, num_tgt, target) -> list:
        target_idx = set(random.sample(range(n), min(num_tgt, n)))
        seq = []
        for i in range(n):
            if i in target_idx:
                seq.append((target, True))
            else:
                avail = [c for c in self.CONSONANTS if c != target]
                if seq and seq[-1][0] in avail and len(avail) > 1:
                    avail = [c for c in avail if c != seq[-1][0]]
                seq.append((random.choice(avail), False))
        return seq

    def _gen_n_back(self, n_level, n, num_tgt) -> list:
        possible = list(range(n_level, n))
        num_tgt = min(num_tgt, len(possible))
        target_idx = set(random.sample(possible, num_tgt))

        sequence = []
        is_target = []
        for i in range(n):
            if i in target_idx:
                sequence.append(sequence[i - n_level])
                is_target.append(True)
            else:
                avail = list(self.CONSONANTS)
                if i >= n_level:
                    forbidden = sequence[i - n_level]
                    avail = [c for c in avail if c != forbidden]
                if i > 0 and n_level != 1:
                    prev = sequence[i - 1]
                    avail = [c for c in avail if c != prev] or avail
                sequence.append(random.choice(avail or self.CONSONANTS))
                is_target.append(False)
        return list(zip(sequence, is_target))

    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:
        letter, is_target = trial_data
        n_level = block_def['level']

        self._letter_stim.text = letter
        self.flush_keyboard()

        responded = False
        rt = None

        stim_duration = self.design.get('stim_duration', 0.5)
        isi_duration = self.design.get('isi_duration', 2.0)

        # Phase 1: Letter
        self._letter_stim.draw()
        self.win.flip()
        stim_onset = self.clock.time

        ttl = self._ttl.get(
            'stim_target' if is_target else 'stim_nontarget', 0
        )
        if ttl:
            self.hardware.send_trigger(ttl)
        tag = 'TGT' if is_target else 'NTG'
        self.hardware.send_eyetracker_message(
            f"STIM_{letter}_{tag}_B{block_idx}_T{trial_idx}_t{stim_onset:.3f}"
        )

        deadline = stim_onset + stim_duration
        while self.clock.time < deadline:
            if not responded:
                keys = self.get_keys(key_list=self._valid_keys)
                if keys:
                    responded = True
                    rt = self.clock.time - stim_onset
                    resp_ttl = self._ttl.get(
                        'response_hit' if is_target
                        else 'response_false_alarm', 0
                    )
                    if resp_ttl:
                        self.hardware.send_trigger(resp_ttl)
            self._letter_stim.draw()
            self.win.flip()

        # Phase 2: ISI fixation
        self._fixation.draw()
        self.win.flip()
        isi_deadline = self.clock.time + isi_duration

        while self.clock.time < isi_deadline:
            if not responded:
                keys = self.get_keys(key_list=self._valid_keys)
                if keys:
                    responded = True
                    rt = self.clock.time - stim_onset
                    resp_ttl = self._ttl.get(
                        'response_hit' if is_target
                        else 'response_false_alarm', 0
                    )
                    if resp_ttl:
                        self.hardware.send_trigger(resp_ttl)
            self._fixation.draw()
            self.win.flip()

        sdt = classify_sdt(is_target, responded)

        record = self._base_record(block_idx, trial_idx, block_def)
        record.update({
            'n_level': n_level,
            'n_level_label': f'{n_level}-back',
            'n_trials_in_block': block_def['n_trials'],
            'letter': letter,
            'zero_back_target': block_def.get('_zero_back_target', ''),
            'is_target': int(is_target),
            'responded': int(responded),
            'rt': round(rt, 4) if rt is not None else -1,
            'stim_onset': round(stim_onset, 4),
            'stim_duration': stim_duration,
            'isi_duration': isi_duration,
            **sdt,
        })

        self._print_trial(block_idx, trial_idx, n_level, letter,
                          is_target, sdt, rt, stim_onset)
        return record

    @staticmethod
    def _print_trial(bi, ti, level, letter, is_tgt, sdt, rt, onset):
        if sdt['hit']:
            tag, sym = 'HIT ', SYM_OK
        elif sdt['miss']:
            tag, sym = 'MISS', SYM_ERR
        elif sdt['false_alarm']:
            tag, sym = 'FA  ', SYM_ERR
        else:
            tag, sym = 'CR  ', SYM_OK
        m = SYM_STAR if is_tgt else SYM_DOT
        rt_s = f"{rt * 1000:5.0f}ms" if rt and rt > 0 else "    - "
        print(
            f"  B{bi} T{ti:02d} | t={onset:8.3f}s | "
            f"{level}-back | {letter} {m} | {tag} {sym} | {rt_s}"
        )

    def _print_task_stats(self) -> None:
        records = self.data_writer.records
        if not records:
            return

        total = len(records)
        correct = sum(r['is_correct'] for r in records)
        hits = sum(r.get('hit', 0) for r in records)
        misses = sum(r.get('miss', 0) for r in records)
        fas = sum(r.get('false_alarm', 0) for r in records)
        crs = sum(r.get('correct_rejection', 0) for r in records)

        print(f"\n{'=' * 60}")
        print(f"  N-BACK RESULTS - {correct}/{total} "
              f"({100 * correct / total:.1f}%)")
        print(f"  HIT={hits}  MISS={misses}  FA={fas}  CR={crs}")

        by_level = defaultdict(list)
        for r in records:
            by_level[r['n_level']].append(r)

        for level in sorted(by_level):
            recs = by_level[level]
            n = len(recs)
            acc = 100 * sum(r['is_correct'] for r in recs) / n
            h = sum(r.get('hit', 0) for r in recs)
            m = sum(r.get('miss', 0) for r in recs)
            fa = sum(r.get('false_alarm', 0) for r in recs)
            rts = [r['rt'] for r in recs if r['rt'] > 0]
            rt_str = f"{sum(rts) / len(rts) * 1000:.0f}ms" if rts else "-"
            print(
                f"  {level}-back: {acc:5.1f}% ({n} trials) | "
                f"H={h} M={m} FA={fa} | RT={rt_str}"
            )

        print(f"{'=' * 60}\n")
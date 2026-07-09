"""
Stroop Color-Word Task (French) — manual & vocal versions.

Manual version:
    Respond with buttons: left=ROUGE, down=BLEU, right=VERT.
    No visual indicators on screen during trials (trained beforehand).

Vocal version:
    Say the ink color aloud. Continuous mic recording from trigger to end.
    No button press required. RT extracted offline from audio.

Both versions share identical stimuli, timing, and block structure.

Trial timing (2s total):
    500ms fixation + 1200ms colored word + 300ms ITI

Stimuli:
    Congruent:   ROUGE in red, BLEU in blue, VERT in green
    Incongruent: ROUGE in blue, ROUGE in green, BLEU in red, etc (6 pairs)
    Neutral:     XXXX / %%%% / OOOO in color

Randomization:
    - No >2 same color consecutively
    - No >2 same word consecutively
    - Colors balanced within each block
    - Incongruent: 6 pairs balanced
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
    """Stroop Color-Word fMRI task — manual or vocal."""

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

        # Colors
        colors_cfg = self.task_config.get('colors', {})
        self._color_rgb = {
            'rouge': colors_cfg.get('rouge', [1.0, -1.0, -1.0]),
            'bleu':  colors_cfg.get('bleu',  [-1.0, -1.0, 1.0]),
            'vert':  colors_cfg.get('vert',  [-1.0, 0.8, -1.0]),
        }
        self._ink_colors = list(self._color_rgb.keys())

        # Words
        cw = self.task_config.get('color_words', {})
        self._color_words = {
            'rouge': cw.get('rouge', 'ROUGE'),
            'bleu':  cw.get('bleu',  'BLEU'),
            'vert':  cw.get('vert',  'VERT'),
        }
        self._neutral_words = self.task_config.get(
            'neutral_words', ['XXXX', '%%%%', 'OOOO']
        )

        # Incongruent pairs
        pairs_cfg = self.task_config.get('incongruent_pairs', [])
        if pairs_cfg:
            self._inc_pairs = [(p['word'], p['ink']) for p in pairs_cfg]
        else:
            self._inc_pairs = [
                (self._color_words[w], i)
                for w in self._ink_colors for i in self._ink_colors if w != i
            ]

        # ── Response mode ────────────────────────────────────────────
        self._response_mode = self.task_config.get('response_mode', 'manual')
        self._is_vocal = (self._response_mode == 'vocal')

        # ── Manual mode: keys only, NO visual indicators ─────────────
        if not self._is_vocal:
            mode = self.settings.mode
            if mode == 'fmri':
                keys_cfg = self.task_config.get('response_keys_fmri', {})
            else:
                keys_cfg = self.task_config.get('response_keys_pc', {})

            self._color_to_key = {
                'rouge': keys_cfg.get('rouge', 'left'),
                'bleu':  keys_cfg.get('bleu',  'down'),
                'vert':  keys_cfg.get('vert',  'right'),
            }
            self._key_to_color = {v: k for k, v in self._color_to_key.items()}
            self._valid_keys = list(self._color_to_key.values())
        else:
            self._color_to_key = {}
            self._key_to_color = {}
            self._valid_keys = []

        # ── Microphone (vocal mode) ──────────────────────────────────
        self._mic = None
        if self._is_vocal:
            from hardware.microphone import MicrophoneRecorder
            sr = self.task_config.get('mic_sample_rate', 44100)
            self._mic = MicrophoneRecorder(
                sample_rate=sr, logger=self.logger,
            )

        self._ttl = self.task_config.get('ttl_codes', {})

    # ═════════════════════════════════════════════════════════════════
    # INSTRUCTIONS
    # ═════════════════════════════════════════════════════════════════

    def _get_instruction_text(self) -> str:
        total = sum(b.get('n_trials', 0) for b in self.block_sequence)
        n_blocs = len(self.block_sequence)

        if self._is_vocal:
            return (
                f"Stroop Vocal\n\n"
                f"Design : {self.design.get('name', '')}\n"
                f"{n_blocs} blocs, {total} essais\n\n"
                f"Nommez a voix haute la COULEUR DE L'ENCRE.\n"
                f"Ignorez ce que le mot dit !\n\n"
                f"Dites uniquement :\n"
                f"  'rouge', 'bleu' ou 'vert'\n\n"
                f"Votre voix sera enregistree.\n\n"
                f"Repondez le plus VITE et PRECISEMENT possible.\n\n"
                f"Appuyez sur une touche pour continuer..."
            )
        else:
            k_r = self._color_to_key['rouge'].upper()
            k_b = self._color_to_key['bleu'].upper()
            k_v = self._color_to_key['vert'].upper()
            return (
                f"Stroop — Denomination de couleur\n\n"
                f"Design : {self.design.get('name', '')}\n"
                f"{n_blocs} blocs, {total} essais\n\n"
                f"Repondez a la COULEUR DE L'ENCRE.\n"
                f"Ignorez ce que le mot dit !\n\n"
                f"  ROUGE  ->  [{k_r}]  (index)\n"
                f"  BLEU   ->  [{k_b}]  (majeur)\n"
                f"  VERT   ->  [{k_v}]  (annulaire)\n\n"
                f"Repondez le plus VITE et PRECISEMENT possible.\n\n"
                f"Appuyez sur une touche pour continuer..."
            )

    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        instr_dur = self.design.get('instruction_duration', 3.0)
        if instr_dur <= 0:
            return None

        n = len(self.block_sequence)
        if self._is_vocal:
            return (
                f"Bloc {block_idx + 1}/{n}\n\n"
                f"Nommez la COULEUR DE L'ENCRE\n"
                f"a voix haute"
            )
        else:
            return (
                f"Bloc {block_idx + 1}/{n}\n\n"
                f"Nommez la COULEUR DE L'ENCRE\n"
                f"le plus vite possible"
            )

    # ═════════════════════════════════════════════════════════════════
    # TRIGGER — start mic recording
    # ═════════════════════════════════════════════════════════════════

    def wait_for_trigger(self) -> None:
        """Override: start microphone right after trigger (vocal mode)."""
        super().wait_for_trigger()

        if self._is_vocal and self._mic is not None:
            mic_path = (
                self.settings.task_dir(self.TASK_NAME)
                / self.settings.output_filename(self.TASK_NAME, 'audio')
            ).with_suffix('.wav')
            self._mic.start(mic_path, self.clock)

    # ═════════════════════════════════════════════════════════════════
    # TRIAL GENERATION
    # ═════════════════════════════════════════════════════════════════

    def generate_trials(self, block_def: dict) -> list:
        condition = block_def['condition']
        n = block_def['n_trials']

        if condition == 'neutral':
            trials = self._gen_neutral(n)
        elif condition == 'congruent':
            trials = self._gen_congruent(n)
        elif condition == 'incongruent':
            trials = self._gen_incongruent(n)
        else:
            trials = self._gen_neutral(n)

        trials = self._double_desequence(trials)
        return trials

    def _gen_congruent(self, n):
        trials = []
        per = n // 3
        rem = n - per * 3
        for i, c in enumerate(self._ink_colors):
            cnt = per + (1 if i < rem else 0)
            trials.extend([(self._color_words[c], c, 'congruent')] * cnt)
        random.shuffle(trials)
        return trials

    def _gen_incongruent(self, n):
        trials = []
        np_ = len(self._inc_pairs)
        per = n // np_
        rem = n - per * np_
        for i, (w, ink) in enumerate(self._inc_pairs):
            cnt = per + (1 if i < rem else 0)
            trials.extend([(w, ink, 'incongruent')] * cnt)
        random.shuffle(trials)
        return trials

    def _gen_neutral(self, n):
        trials = []
        per = n // 3
        rem = n - per * 3
        for i, c in enumerate(self._ink_colors):
            cnt = per + (1 if i < rem else 0)
            for j in range(cnt):
                sym = self._neutral_words[j % len(self._neutral_words)]
                trials.append((sym, c, 'neutral'))
        random.shuffle(trials)
        return trials

    def _double_desequence(self, trials, max_c=2):
        trials = desequence(trials, key_func=lambda t: t[1], max_consecutive=max_c)
        for _ in range(50):
            ok = True
            for i in range(max_c, len(trials)):
                w = [trials[j][0] for j in range(i - max_c, i + 1)]
                if len(set(w)) == 1:
                    ok = False
                    cands = [k for k in range(i + 1, len(trials))
                             if trials[k][0] != trials[i][0]]
                    if cands:
                        s = random.choice(cands)
                        trials[i], trials[s] = trials[s], trials[i]
                    break
            if ok:
                break
        return trials

    # ═════════════════════════════════════════════════════════════════
    # TRIAL EXECUTION
    # ═════════════════════════════════════════════════════════════════

    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:
        word, ink_color, trial_type = trial_data

        fix_dur = self.design.get('fixation_duration', 0.5)
        stim_dur = self.design.get('stim_duration', 1.2)
        iti_dur = self.design.get('iti_duration', 0.3)

        correct_key = self._color_to_key.get(ink_color, '')
        self.flush_keyboard()

        responded = False
        rt = None
        response_key = None
        response_color = None

        # ── Fixation 500ms ───────────────────────────────────────────
        self._fixation.draw()
        self.win.flip()
        deadline = self.clock.time + fix_dur
        while self.clock.time < deadline:
            self._fixation.draw()
            self.win.flip()
            self.get_keys(key_list=[])

        # ── Colored word 1200ms ──────────────────────────────────────
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
            if not self._is_vocal and not responded:
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
            else:
                self.get_keys(key_list=[])
            self._word_stim.draw()
            self.win.flip()

        # ── ITI 300ms ────────────────────────────────────────────────
        self._fixation.draw()
        self.win.flip()
        deadline = self.clock.time + iti_dur
        while self.clock.time < deadline:
            if not self._is_vocal and not responded:
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
            else:
                self.get_keys(key_list=[])
            self._fixation.draw()
            self.win.flip()

        is_correct = (response_color == ink_color) if responded else False

        record = self._base_record(block_idx, trial_idx, block_def)
        record.update({
            'response_mode': self._response_mode,
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
            'is_correct': int(is_correct) if not self._is_vocal else -1,
            'is_error': int(responded and not is_correct) if not self._is_vocal else -1,
            'is_miss': int(not responded) if not self._is_vocal else -1,
            'stim_onset': round(stim_onset, 4),
            'fixation_duration': fix_dur,
            'stim_duration': stim_dur,
            'iti_duration': iti_dur,
        })

        self._print_trial(
            block_idx, trial_idx, word, ink_color, trial_type,
            responded, is_correct, rt, stim_onset, self._is_vocal,
        )
        return record

    # ═════════════════════════════════════════════════════════════════
    # FINISH — stop mic
    # ═════════════════════════════════════════════════════════════════

    def _finish(self) -> 'Path | None':
        if self._mic is not None and self._mic.is_recording:
            wav_path = self._mic.stop(self.clock)
            sync = self._mic.get_sync_info()
            self.logger.ok(
                f"Mic sync: start={sync['mic_start_time']:.3f}s "
                f"stop={sync['mic_stop_time']:.3f}s "
                f"dur={sync['mic_duration']:.1f}s"
            )
            try:
                import json
                sync_path = (
                    self.settings.task_dir(self.TASK_NAME)
                    / self.settings.output_filename(self.TASK_NAME, 'audio_sync')
                ).with_suffix('.json')
                with open(sync_path, 'w') as f:
                    json.dump(sync, f, indent=2, default=str)
                self.logger.ok(f"Audio sync saved: {sync_path.name}")
            except Exception as e:
                self.logger.warn(f"Sync save failed: {e}")

        return super()._finish()

    # ═════════════════════════════════════════════════════════════════
    # CONSOLE
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _print_trial(bi, ti, word, ink, ttype, responded, correct,
                     rt, onset, is_vocal):
        tt = ttype[:3].upper()
        if is_vocal:
            tag, sym = 'VOC ', '~'
            rt_s = "    - "
        elif not responded:
            tag, sym = 'MISS', SYM_ERR
            rt_s = "    - "
        elif correct:
            tag, sym = 'OK  ', SYM_OK
            rt_s = f"{rt * 1000:5.0f}ms"
        else:
            tag, sym = 'ERR ', SYM_ERR
            rt_s = f"{rt * 1000:5.0f}ms" if rt and rt > 0 else "    - "
        print(
            f"  B{bi:02d} T{ti:02d} | t={onset:8.3f}s | "
            f"{tt} | {word:>6s} [{ink[:3]}] | {tag} {sym} | {rt_s}"
        )

    def _print_task_stats(self) -> None:
        records = self.data_writer.records
        if not records:
            return

        total = len(records)

        if self._is_vocal:
            print(f"\n{'=' * 60}")
            print(f"  STROOP VOCAL - {total} essais enregistres")
            print(f"  Mode : reponse vocale (RT a extraire offline)")
            if self._mic:
                sync = self._mic.get_sync_info()
                if sync['mic_duration']:
                    print(f"  Audio : {sync['mic_duration']:.1f}s enregistrees")
                print(f"  Fichier : {sync['mic_file']}")
            print(f"{'=' * 60}\n")
            return

        correct = sum(r['is_correct'] for r in records)
        errors = sum(r.get('is_error', 0) for r in records)
        misses = sum(r.get('is_miss', 0) for r in records)

        print(f"\n{'=' * 60}")
        print(f"  STROOP MANUEL - {correct}/{total} "
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
            rts_sorted = sorted(rts)
            if rts_sorted:
                mid = len(rts_sorted) // 2
                median = (rts_sorted[mid] if len(rts_sorted) % 2
                          else (rts_sorted[mid - 1] + rts_sorted[mid]) / 2)
                med_s = f"{median * 1000:.0f}ms"
            else:
                med_s = "-"
            mean_s = f"{m * 1000:.0f}ms" if rts else "-"
            err = sum(r.get('is_error', 0) for r in recs)
            mis = sum(r.get('is_miss', 0) for r in recs)
            print(
                f"  {tt:12s}: {acc:5.1f}% ({n:3d}) | "
                f"Mean={mean_s:>6s} Med={med_s:>6s} | "
                f"Err={err:2d} Miss={mis:2d}"
            )

        con = rt_by.get('congruent', 0)
        inc = rt_by.get('incongruent', 0)
        neu = rt_by.get('neutral', 0)
        print(f"  {'-' * 54}")
        if inc > 0 and con > 0:
            print(f"  Interference (INC-CON): {(inc-con)*1000:+.0f}ms")
        if inc > 0 and neu > 0:
            print(f"  Interference (INC-NEU): {(inc-neu)*1000:+.0f}ms")
        if neu > 0 and con > 0:
            print(f"  Facilitation (CON-NEU): {(con-neu)*1000:+.0f}ms")

        by_ink = defaultdict(list)
        for r in records:
            by_ink[r['ink_color']].append(r)
        if len(by_ink) > 1:
            print(f"  {'-' * 54}")
            for c in sorted(by_ink):
                recs = by_ink[c]
                n = len(recs)
                acc = 100 * sum(r['is_correct'] for r in recs) / n
                rts = [r['rt'] for r in recs if r['rt'] > 0 and r['is_correct']]
                rt_s = f"{sum(rts)/len(rts)*1000:.0f}ms" if rts else "-"
                print(f"  ink={c:6s}: {acc:5.1f}% ({n}) | RT={rt_s}")

        print(f"{'=' * 60}\n")
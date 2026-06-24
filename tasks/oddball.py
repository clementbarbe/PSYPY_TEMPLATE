"""
Oddball Auditif — tache de detection de sons deviants.

Paradigme Go/No-Go auditif :
    - Sons standards (ex: 1000 Hz) : 80% -> ne rien faire
    - Sons deviants  (ex: 1200 Hz) : 20% -> appuyer

Le participant fixe une croix et ecoute une sequence de sons.
Il appuie uniquement quand il entend le son deviant.

Mesures :
    - Taux de detection (hit rate)
    - Temps de reaction aux deviants
    - Contraste IRMf : deviant > standard

Activations attendues :
    - Cortex auditif bilateral
    - Reseaux attentionnels fronto-parietaux
    - Insula, cortex cingulaire anterieur (reseau de saillance)

Audio :
    Utilise le AudioManager avec scheduling PTB.
    Sons generes comme tons purs et precharges au setup.
    Le son est programme ~100ms avant le SOA cible pour
    une precision temporelle maximale.
"""

from __future__ import annotations

import random
from collections import defaultdict

from tasks.base import BaseTask
from tasks.registry import register_task
from tasks.utils.sdt import classify_sdt
from tasks.utils.sequence import generate_jittered_isis
from utils.console import SYM_OK, SYM_ERR, SYM_STAR, SYM_DOT, SYM_PAUSE
from config.constants import AUDIO_SCHEDULE_LEAD


@register_task('oddball')
class OddballTask(BaseTask):
    """Oddball auditif fMRI."""

    TASK_NAME = 'oddball'

    # ═════════════════════════════════════════════════════════════════
    # SETUP
    # ═════════════════════════════════════════════════════════════════

    def _setup_stimuli(self) -> None:
        audio_cfg = self.task_config.get('audio', {})

        self._std_freq = audio_cfg.get('standard_freq', 1000)
        self._dev_freq = audio_cfg.get('deviant_freq', 1200)
        self._tone_dur = audio_cfg.get('tone_duration', 0.2)
        self._tone_vol = audio_cfg.get('tone_volume', 0.8)

        # Preload tones via AudioManager (lazy init in BaseTask)
        self.audio.preload_tone(
            'standard',
            frequency=self._std_freq,
            duration=self._tone_dur,
            volume=self._tone_vol,
        )
        self.audio.preload_tone(
            'deviant',
            frequency=self._dev_freq,
            duration=self._tone_dur,
            volume=self._tone_vol,
        )
        self.logger.log(
            f"Oddball audio: standard={self._std_freq}Hz, "
            f"deviant={self._dev_freq}Hz, dur={self._tone_dur}s"
        )

        # Response key = Go key from scanner config
        self._key_go = self._response_keys.get('go', 'space')
        self._valid_keys = [self._key_go]

        self._ttl = self.task_config.get('ttl_codes', {})

    # ═════════════════════════════════════════════════════════════════
    # INSTRUCTIONS
    # ═════════════════════════════════════════════════════════════════

    def _get_instruction_text(self) -> str:
        total = sum(b.get('n_trials', 0) for b in self.block_sequence)
        prop = self.design.get('prop_deviant', 0.20)
        key = self._key_go.upper()

        return (
            f"Oddball Auditif\n\n"
            f"Design : {self.design.get('name', '')}\n"
            f"Total : {total} sons\n\n"
            f"Vous allez entendre une serie de sons.\n"
            f"La plupart seront des sons GRAVES (standard).\n"
            f"De temps en temps, un son AIGU (deviant) apparait.\n\n"
            f"Appuyez sur [{key}] UNIQUEMENT\n"
            f"quand vous entendez le son AIGU.\n\n"
            f"Ne faites RIEN pour les sons graves.\n\n"
            f"Fixez la croix au centre de l'ecran.\n\n"
            f"Appuyez sur une touche pour continuer..."
        )

    def _get_block_instruction(self, block_idx: int,
                               block_def: dict) -> str | None:
        instr_dur = self.design.get('instruction_duration', 3.0)
        if instr_dur <= 0:
            return None

        n = len(self.block_sequence)
        key = self._key_go.upper()

        return (
            f"Bloc {block_idx + 1}/{n}\n\n"
            f"Son AIGU -> [{key}]\n"
            f"Son grave -> ne rien faire\n\n"
            f"Fixez la croix"
        )

    # ═════════════════════════════════════════════════════════════════
    # TRIAL GENERATION
    # ═════════════════════════════════════════════════════════════════

    def generate_trials(self, block_def: dict) -> list:
        """
        Generate oddball sequence.

        Returns list of (is_deviant, soa) tuples.
        Ensures:
            - Correct proportion of deviants
            - No 2 deviants in a row
            - At least 2 standards before first deviant
        """
        n = block_def['n_trials']
        prop_dev = self.design.get('prop_deviant', 0.20)
        soa_min = self.design.get('soa_min', 1.2)
        soa_max = self.design.get('soa_max', 1.8)

        n_dev = max(1, int(round(n * prop_dev)))
        n_std = n - n_dev

        # Build sequence
        seq = [True] * n_dev + [False] * n_std

        # Shuffle with constraints
        seq = self._constrained_shuffle(seq, n_dev)

        # Generate SOAs
        soas = generate_jittered_isis(n, soa_min, soa_max)

        return list(zip(seq, soas))

    def _constrained_shuffle(self, seq: list[bool], n_dev: int,
                             max_attempts: int = 200) -> list[bool]:
        """
        Shuffle ensuring:
            - No 2 deviants in a row
            - First 2 trials are standards
        """
        for _ in range(max_attempts):
            random.shuffle(seq)

            # Force first 2 to be standard
            if seq[0] or seq[1]:
                # Move deviants to later positions
                std_positions = [
                    i for i in range(2, len(seq)) if not seq[i]
                ]
                dev_early = [i for i in range(2) if seq[i]]
                for di, si in zip(dev_early, std_positions):
                    seq[di], seq[si] = seq[si], seq[di]

            # Check no consecutive deviants
            ok = True
            for i in range(1, len(seq)):
                if seq[i] and seq[i - 1]:
                    ok = False
                    break

            if ok:
                return seq

        self.logger.warn("Oddball: shuffle constraints not fully met.")
        return seq

    # ═════════════════════════════════════════════════════════════════
    # TRIAL EXECUTION
    # ═════════════════════════════════════════════════════════════════

    def run_trial(self, trial_data, block_idx: int, trial_idx: int,
                  block_def: dict, **kwargs) -> dict:
        """
        One trial:
            1. Schedule sound ~100ms before target time
            2. Play sound at precise time (PTB scheduling)
            3. Show fixation throughout
            4. Collect response during SOA window

        The fixation cross is displayed continuously.
        Only the audio changes between trials.
        """
        is_deviant, soa = trial_data
        sound_name = 'deviant' if is_deviant else 'standard'

        self.flush_keyboard()
        responded = False
        rt = None

        # ── Schedule and play sound ──────────────────────────────────
        # Call play_scheduled ~100ms before desired onset
        # PTB handles the precise timing
        target_time = self.clock.time + AUDIO_SCHEDULE_LEAD
        actual_onset = self.audio.play_scheduled(
            sound_name, target_time, self.clock,
        )
        stim_onset = actual_onset

        # TTL
        ttl = self._ttl.get(
            'stim_deviant' if is_deviant else 'stim_standard', 0
        )
        if ttl:
            self.hardware.send_trigger(ttl)

        tag = 'DEV' if is_deviant else 'STD'
        self.hardware.send_eyetracker_message(
            f"STIM_{tag}_{sound_name}_B{block_idx}_T{trial_idx}_"
            f"t{stim_onset:.3f}"
        )

        # ── SOA window: fixation + response collection ───────────────
        soa_deadline = stim_onset + soa

        while self.clock.time < soa_deadline:
            if not responded:
                keys = self.get_keys(key_list=self._valid_keys)
                if keys:
                    responded = True
                    rt = self.clock.time - stim_onset
                    ttl_r = self._ttl.get(
                        'response_hit' if is_deviant
                        else 'response_fa', 0
                    )
                    if ttl_r:
                        self.hardware.send_trigger(ttl_r)

            self._fixation.draw()
            self.win.flip()

        # ── SDT classification ───────────────────────────────────────
        sdt = classify_sdt(is_deviant, responded)

        # ── Record ───────────────────────────────────────────────────
        record = self._base_record(block_idx, trial_idx, block_def)
        record.update({
            'n_trials_in_block': block_def['n_trials'],
            'sound_type': 'deviant' if is_deviant else 'standard',
            'sound_freq': self._dev_freq if is_deviant else self._std_freq,
            'is_deviant': int(is_deviant),
            'responded': int(responded),
            'rt': round(rt, 4) if rt is not None else -1,
            'stim_onset': round(stim_onset, 4),
            'soa': round(soa, 4),
            'tone_duration': self._tone_dur,
            **sdt,
        })

        self._print_trial(
            block_idx, trial_idx, is_deviant, sdt, rt, stim_onset,
        )
        return record

    # ═════════════════════════════════════════════════════════════════
    # BLOCK — override to keep fixation visible throughout
    # ═════════════════════════════════════════════════════════════════

    def run_block(self, block_idx: int, block_def: dict) -> None:
        """
        Oddball block: fixation stays on screen the entire time.
        Only audio changes between trials.
        """
        n = block_def.get('n_trials', 0)
        t = self.clock.time
        prop = self.design.get('prop_deviant', 0.20)

        self.logger.log(f"Block {block_idx} | {n} trials | t={t:.3f}s")
        self.event_bus.publish(
            'block_start', block_idx=block_idx, block_def=block_def,
        )

        # Block instruction
        instr = self._get_block_instruction(block_idx, block_def)
        instr_dur = self.design.get('instruction_duration', 3.0)
        if instr and instr_dur > 0:
            from config.constants import TTL_INSTRUCTION
            self.hardware.send_trigger(TTL_INSTRUCTION)
            self.show_timed_text(instr, instr_dur)

        pre_fix = self.design.get('pre_block_fixation', 1.0)
        if pre_fix > 0:
            self.show_fixation(pre_fix)

        # Generate trials
        trials = self.generate_trials(block_def)
        n_dev = sum(1 for t in trials if t[0])
        print(
            f"  Block {block_idx}: {n} trials "
            f"({n_dev} deviants, {n - n_dev} standards)"
        )

        # Initial fixation frame
        self._fixation.draw()
        self.win.flip()

        # Run trials (fixation always visible, only sound changes)
        for trial_idx, trial_data in enumerate(trials):
            record = self.run_trial(
                trial_data, block_idx=block_idx,
                trial_idx=trial_idx, block_def=block_def,
            )
            record['trial_idx_global'] = self._global_trial_idx
            self._global_trial_idx += 1
            self.data_writer.write_trial(record)
            self.event_bus.publish('trial_end', record=record)

        self.event_bus.publish(
            'block_end', block_idx=block_idx, block_def=block_def,
        )
        self.logger.log(f"Block {block_idx} | END")

    # ═════════════════════════════════════════════════════════════════
    # CONSOLE
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def _print_trial(bi, ti, is_dev, sdt, rt, onset):
        if sdt['hit']:
            tag, sym = 'HIT ', SYM_OK
        elif sdt['miss']:
            tag, sym = 'MISS', SYM_ERR
        elif sdt['false_alarm']:
            tag, sym = 'FA  ', SYM_ERR
        else:
            tag, sym = 'CR  ', SYM_OK

        mark = SYM_STAR if is_dev else SYM_DOT
        stype = 'DEV' if is_dev else 'STD'
        rt_s = f"{rt * 1000:5.0f}ms" if rt and rt > 0 else "    - "

        print(
            f"  B{bi} T{ti:03d} | t={onset:8.3f}s | "
            f"{stype} {mark} | {tag} {sym} | {rt_s}"
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

        n_dev = sum(r['is_deviant'] for r in records)
        n_std = total - n_dev

        print(f"\n{'=' * 60}")
        print(f"  ODDBALL AUDITIF - {correct}/{total} "
              f"({100 * correct / total:.1f}%)")
        print(f"  Standards: {n_std}  |  Deviants: {n_dev}")
        print(f"  HIT={hits}  MISS={misses}  FA={fas}  CR={crs}")
        print(f"  {'-' * 54}")

        # Deviant performance
        dev_recs = [r for r in records if r['is_deviant']]
        if dev_recs:
            n = len(dev_recs)
            hit_rate = 100 * sum(r.get('hit', 0) for r in dev_recs) / n
            rts = [r['rt'] for r in dev_recs if r['rt'] > 0 and r.get('hit')]
            rt_str = f"{sum(rts) / len(rts) * 1000:.0f}ms" if rts else "-"
            print(
                f"  Deviants:  Hit rate={hit_rate:.1f}% "
                f"({sum(r.get('hit',0) for r in dev_recs)}/{n}) | "
                f"RT={rt_str}"
            )

        # Standard performance
        std_recs = [r for r in records if not r['is_deviant']]
        if std_recs:
            n = len(std_recs)
            fa_rate = 100 * sum(r.get('false_alarm', 0) for r in std_recs) / n
            print(f"  Standards: FA rate={fa_rate:.1f}% ({fas}/{n})")

        # d' approximation
        if dev_recs and std_recs:
            hr = sum(r.get('hit', 0) for r in dev_recs) / len(dev_recs)
            far = sum(r.get('false_alarm', 0)
                      for r in std_recs) / len(std_recs)
            # Clamp to avoid inf
            hr = max(0.01, min(0.99, hr))
            far = max(0.01, min(0.99, far))
            try:
                from math import erfinv, sqrt
                z_hr = sqrt(2) * erfinv(2 * hr - 1)
                z_far = sqrt(2) * erfinv(2 * far - 1)
                dprime = z_hr - z_far
                print(f"  d' = {dprime:.2f}")
            except Exception:
                pass

        print(f"{'=' * 60}\n")
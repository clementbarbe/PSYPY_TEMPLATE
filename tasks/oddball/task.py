from __future__ import annotations

from typing import Any

from statistics import NormalDist

from core.design import DesignGenerator
from core.errors import TaskConfigurationError
from tasks.base import BaseTask


class Task(BaseTask):
    """Oddball auditif Go/No-Go avec tons standards et déviants."""

    NAME = "oddball"

    def setup(self) -> None:
        """Précharge les deux tons et le mapping de réponse."""
        audio = self.config["audio"]

        self.standard_frequency = float(audio["standard_frequency"])
        self.deviant_frequency = float(audio["deviant_frequency"])
        self.tone_duration = float(audio["tone_duration"])
        self.volume = float(audio.get("volume", 0.8))

        self.go_key = self.settings.responses.get("go", "space")
        self.valid_keys = [self.go_key]
        self.markers = self.config.get("markers", {})

        self.hardware.audio.preload_tone(
            "standard",
            frequency=self.standard_frequency,
            duration=self.tone_duration,
            volume=self.volume,
        )

        self.hardware.audio.preload_tone(
            "deviant",
            frequency=self.deviant_frequency,
            duration=self.tone_duration,
            volume=self.volume,
        )

    def instructions(self) -> str:
        """Retourne les consignes générales de l’oddball auditif."""
        return (
            "ODDBALL AUDITIF\n\n"
            "Vous entendrez surtout des sons graves.\n"
            "Parfois, un son aigu apparaîtra.\n\n"
            f"Appuyez sur [{self.go_key}] UNIQUEMENT\n"
            "pour les sons aigus.\n\n"
            "Fixez la croix au centre de l'écran.\n\n"
            "Attendez l'autorisation de l'expérimentateur."
        )

    def block_instruction(self, block_index: int, block: dict) -> str:
        """Retourne le rappel Go/No-Go affiché avant un bloc."""
        return (
            f"Bloc {block_index + 1}/{len(self.blocks)}\n\n"
            f"Son aigu : appuyez sur [{self.go_key}]\n"
            "Son grave : ne rien faire."
        )

    def build_trials(self, block: dict) -> list[dict]:
        """Construit l’ordre standards/déviants et un SOA stratifié."""
        n = int(block["n_trials"])
        ratio = float(self.design["prop_deviant"])
        n_deviants = max(1, round(n * ratio))
        # Réserver deux standards initiaux puis répartir les déviants dans
        # des positions non adjacentes, sans recherche aléatoire par rejet.
        if not 0 < ratio < 1 or n_deviants > (n - 1) // 2:
            raise TaskConfigurationError(
                "Impossible de pseudo-randomiser l’Oddball sans déviants adjacents."
            )
        compressed = sorted(self.rng.sample(range(2, n - n_deviants + 1), n_deviants))
        positions = {value + index for index, value in enumerate(compressed)}
        sequence = [index in positions for index in range(n)]

        soas = DesignGenerator.stratified_jitter(
            n,
            float(self.design["soa_min"]),
            float(self.design["soa_max"]),
            self.rng,
        )
        return [
            {
                "is_deviant": is_deviant,
                "trial_type": "deviant" if is_deviant else "standard",
                "soa": round(soa, 4),
            }
            for is_deviant, soa in zip(sequence, soas)
        ]

    def run_trial(
        self,
        trial: dict[str, Any],
        block_index: int,
        trial_index: int,
        block: dict[str, Any],
    ) -> dict[str, Any]:
        """Joue un ton et classe la réponse selon la théorie de détection."""
        is_deviant = bool(trial["is_deviant"])
        sound_name = "deviant" if is_deviant else "standard"

        self.flush_keyboard()

        target_time = self.clock.time + self.settings.audio_schedule_lead_seconds

        onset = self.hardware.audio.play_scheduled(
            sound_name,
            target_time,
            self.clock,
        )

        self.hardware.marker(
            self.markers.get("deviant" if is_deviant else "standard", 0)
        )

        responded = False
        rt = None
        deadline = onset + float(trial["soa"])

        while self.clock.time < deadline:
            if not responded:
                keys = self.get_keys(self.valid_keys)

                if keys:
                    responded = True
                    rt = self.clock.time - onset

            self.fixation.draw()
            self.win.flip()

        hit = int(is_deviant and responded)
        miss = int(is_deviant and not responded)
        false_alarm = int(not is_deviant and responded)
        correct_rejection = int(not is_deviant and not responded)
        correct = int(hit or correct_rejection)

        if responded:
            self.hardware.marker(
                self.markers.get("hit" if is_deviant else "false_alarm", 0)
            )

        return self.record(
            block_index=block_index,
            trial_index=trial_index,
            block=block,
            onset=onset,
            duration=self.tone_duration,
            trial_type="deviant" if is_deviant else "standard",
            sound_frequency=(
                self.deviant_frequency if is_deviant else self.standard_frequency
            ),
            is_deviant=int(is_deviant),
            responded=int(responded),
            rt=round(rt, 4) if rt is not None else None,
            hit=hit,
            miss=miss,
            false_alarm=false_alarm,
            correct_rejection=correct_rejection,
            is_correct=correct,
            soa=trial["soa"],
        )

    def print_summary(self) -> None:
        """Affiche hit rate, fausses alarmes et d-prime."""
        records = self.writer.records

        if not records:
            return

        deviants = [record for record in records if record["is_deviant"]]
        standards = [record for record in records if not record["is_deviant"]]

        hits = sum(record["hit"] for record in deviants)
        false_alarms = sum(record["false_alarm"] for record in standards)

        hit_rate = hits / len(deviants) if deviants else 0.0
        fa_rate = false_alarms / len(standards) if standards else 0.0

        hit_rate_clamped = min(0.99, max(0.01, hit_rate))
        fa_rate_clamped = min(0.99, max(0.01, fa_rate))

        normal = NormalDist()
        dprime = (
            normal.inv_cdf(hit_rate_clamped)
            - normal.inv_cdf(fa_rate_clamped)
        )

        print("\nODDBALL")
        print(f"  Hit rate : {100 * hit_rate:.1f}%")
        print(f"  FA rate  : {100 * fa_rate:.1f}%")
        print(f"  d'       : {dprime:.2f}")

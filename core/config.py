"""Chargement et validation de la configuration globale de session."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"


def _bids_label(value: str, prefix: str) -> str:
    """Nettoie un identifiant pour l'utiliser comme label BIDS.

    Parameters
    ----------
    value:
        Valeur saisie par l'expérimentateur.
    prefix:
        Préfixe BIDS éventuellement déjà présent (``sub`` ou ``ses``).

    Returns
    -------
    str
        Label alphanumérique sans le préfixe BIDS.
    """
    text = str(value).strip()
    text = re.sub(fr"^{re.escape(prefix)}-", "", text, flags=re.IGNORECASE)
    label = re.sub(r"[^A-Za-z0-9]", "", text)

    if not label:
        raise ValueError(f"Identifiant {prefix} vide ou invalide : {value!r}")

    return label


def sanitize_id(value: str) -> str:
    """Retourne un label participant compatible BIDS, sans ``sub-``."""
    return _bids_label(value, "sub")


def sanitize_session(value: str) -> str:
    """Retourne un label session compatible BIDS, sans ``ses-``.

    Les sessions purement numériques sur un chiffre sont complétées avec un
    zéro afin de conserver l'affichage historique ``01``, ``02``, etc.
    """
    label = _bids_label(value, "ses")
    return label.zfill(2) if label.isdigit() and len(label) == 1 else label


def sanitize_run(value: str | int | None) -> str | None:
    """Normalise un numéro de run ou retourne ``None`` pour le mode automatique."""
    if value is None:
        return None

    text = str(value).strip()
    if not text or text.lower() == "auto":
        return None

    text = re.sub(r"^run-", "", text, flags=re.IGNORECASE)
    if not text.isdigit():
        raise ValueError("Le run doit être un entier positif ou 'auto'.")

    number = int(text)
    if number < 1:
        raise ValueError("Le run doit être supérieur ou égal à 1.")

    return f"{number:02d}"


@dataclass(slots=True)
class SessionSettings:
    """Configuration effective d'une acquisition.

    Cette structure contient uniquement les paramètres transversaux à toutes
    les tâches. Les paramètres spécifiques à Stroop, N-Back, etc. restent dans
    ``tasks/<task>/config.yaml``.
    """

    participant: str
    session: str = "01"
    requested_run: str | None = None
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")

    fullscreen: bool = True
    screen_index: int = 0
    background_color: tuple[float, float, float] = (-1.0, -1.0, -1.0)
    quit_key: str = "escape"
    operator_start_key: str = "return"
    end_screen_seconds: float = 3.0

    resolution: tuple[int, int] = (1920, 1080)
    width_cm: float = 53.0
    viewing_distance_cm: float = 60.0
    refresh_rate: float = 60.0
    flip_horizontal: bool = False
    flip_vertical: bool = False

    trigger_enabled: bool = False
    trigger_source: str = "keyboard"
    trigger_key: str = "t"
    trigger_serial_port: str = ""
    trigger_baudrate: int = 115200
    trigger_timeout_seconds: float = 300.0
    trigger_parallel_address: int | None = None
    trigger_parallel_pin: int = 10

    responses: dict[str, str] = field(default_factory=dict)
    response_box_backend: str = "keyboard"
    response_box_serial_port: str = ""
    response_box_baudrate: int = 115200

    markers_enabled: bool = False
    marker_transport: str = "none"
    parallel_address: int | None = None
    marker_serial_port: str = ""
    marker_baudrate: int = 115200
    marker_pulse_seconds: float = 0.005

    audio_backend: str = "ptb"
    audio_sample_rate: int = 48000
    audio_schedule_lead_seconds: float = 0.1
    audio_minimum_schedule_lead_seconds: float = 0.03

    eyetracker_enabled: bool = False
    eyetracker_backend: str = "eyelink"
    eyetracker_host: str = "100.1.1.1"

    microphone_enabled: bool = False
    microphone_sample_rate: int = 44100
    microphone_channels: int = 1

    mock_mode: bool = False
    save_data: bool = True

    @classmethod
    def from_yaml(
        cls,
        path: Path = DEFAULT_SETTINGS_PATH,
        participant: str = "TEST",
        session: str = "01",
        run: str | int | None = None,
        fullscreen: bool | None = None,
        screen_index: int | None = None,
        wait_for_trigger: bool | None = None,
        markers_enabled: bool | None = None,
        eyetracker_enabled: bool | None = None,
        mock_mode: bool | None = None,
        save_data: bool = True,
    ) -> "SessionSettings":
        """Construit les paramètres effectifs depuis le YAML global.

        Les arguments non ``None`` sont des overrides explicites venant du CLI
        ou du GUI. Cela évite de modifier le fichier YAML pour chaque session.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration globale introuvable : {path}")

        with path.open("r", encoding="utf-8") as stream:
            raw: dict[str, Any] = yaml.safe_load(stream) or {}

        project = raw.get("project", {})
        display = raw.get("display", {})
        input_cfg = raw.get("input", {})
        trigger = input_cfg.get("trigger", {})
        response_box = input_cfg.get("response_box", {})
        output = raw.get("output", {})
        markers = output.get("markers", {})
        audio = raw.get("audio", {})
        eyetracker = raw.get("eyetracker", {})
        microphone = raw.get("microphone", {})

        data_dir = Path(project.get("data_dir", "data"))
        if not data_dir.is_absolute():
            data_dir = PROJECT_ROOT / data_dir

        return cls(
            participant=sanitize_id(participant),
            session=sanitize_session(session),
            requested_run=sanitize_run(run),
            data_dir=data_dir,
            fullscreen=bool(fullscreen) if fullscreen is not None else bool(project.get("fullscreen", True)),
            screen_index=int(screen_index) if screen_index is not None else int(project.get("default_screen", 0)),
            background_color=tuple(float(x) for x in display.get("background_color", [-1, -1, -1])),
            quit_key=str(project.get("quit_key", "escape")),
            operator_start_key=str(project.get("operator_start_key", "return")),
            end_screen_seconds=float(project.get("end_screen_seconds", 3.0)),
            resolution=tuple(int(x) for x in display.get("resolution", [1920, 1080])),
            width_cm=float(display.get("width_cm", 53.0)),
            viewing_distance_cm=float(display.get("viewing_distance_cm", 60.0)),
            refresh_rate=float(display.get("refresh_rate", 60.0)),
            flip_horizontal=bool(display.get("flip_horizontal", False)),
            flip_vertical=bool(display.get("flip_vertical", False)),
            trigger_enabled=bool(wait_for_trigger) if wait_for_trigger is not None else bool(trigger.get("enabled", False)),
            trigger_source=str(trigger.get("source", "keyboard")),
            trigger_key=str(trigger.get("key", "t")),
            trigger_serial_port=str(trigger.get("serial_port", "")),
            trigger_baudrate=int(trigger.get("baudrate", 115200)),
            trigger_timeout_seconds=float(trigger.get("timeout_seconds", 300.0)),
            trigger_parallel_address=trigger.get("parallel_address"),
            trigger_parallel_pin=int(trigger.get("parallel_pin", 10)),
            responses=dict(input_cfg.get("responses", {})),
            response_box_backend=str(response_box.get("backend", "keyboard")),
            response_box_serial_port=str(response_box.get("serial_port", "")),
            response_box_baudrate=int(response_box.get("baudrate", 115200)),
            markers_enabled=bool(markers_enabled) if markers_enabled is not None else bool(markers.get("enabled", False)),
            marker_transport=str(markers.get("transport", "none")),
            parallel_address=markers.get("parallel_address"),
            marker_serial_port=str(markers.get("serial_port", "")),
            marker_baudrate=int(markers.get("baudrate", 115200)),
            marker_pulse_seconds=float(markers.get("pulse_seconds", 0.005)),
            audio_backend=str(audio.get("backend", "ptb")),
            audio_sample_rate=int(audio.get("sample_rate", 48000)),
            audio_schedule_lead_seconds=float(audio.get("schedule_lead_seconds", 0.1)),
            audio_minimum_schedule_lead_seconds=float(audio.get("minimum_schedule_lead_seconds", 0.03)),
            eyetracker_enabled=bool(eyetracker_enabled) if eyetracker_enabled is not None else bool(eyetracker.get("enabled", False)),
            eyetracker_backend=str(eyetracker.get("backend", "eyelink")),
            eyetracker_host=str(eyetracker.get("host", "100.1.1.1")),
            microphone_enabled=bool(microphone.get("enabled", False)),
            microphone_sample_rate=int(microphone.get("sample_rate", 44100)),
            microphone_channels=int(microphone.get("channels", 1)),
            mock_mode=bool(mock_mode) if mock_mode is not None else bool(project.get("mock_mode", False)),
            save_data=bool(save_data),
        )

    def validate(self) -> None:
        """Refuse les conflits de touches et les transports non configurés."""
        if not self.operator_start_key or self.operator_start_key in {
            self.trigger_key, self.quit_key, *self.responses.values()
        }:
            raise ValueError("La touche opérateur doit être distincte du trigger, des réponses et d'Escape.")
        if self.quit_key in self.responses.values() or (
            self.trigger_enabled and self.trigger_key in self.responses.values()
        ):
            raise ValueError("Les réponses ne doivent pas utiliser le trigger ou la touche d'arrêt.")
        if self.trigger_source not in {"keyboard", "serial", "parallel"}:
            raise ValueError("Source de trigger invalide.")
        if self.markers_enabled and not self.mock_mode and self.marker_transport not in {"parallel", "serial"}:
            raise ValueError("Marqueurs activés : configurer un transport parallèle ou série.")
        if self.refresh_rate <= 0 or self.trigger_timeout_seconds <= 0:
            raise ValueError("Fréquence écran et timeout du trigger doivent être positifs.")
        if self.audio_schedule_lead_seconds < self.audio_minimum_schedule_lead_seconds:
            raise ValueError("Le délai de programmation audio est inférieur au minimum requis.")
        if self.trigger_enabled and self.trigger_source == "serial" and len(self.trigger_key.encode("ascii")) != 1:
            raise ValueError("Le trigger série doit être un caractère ASCII unique.")
        if self.trigger_enabled and self.trigger_source == "serial" and self.response_box_backend == "serial" and self.trigger_serial_port == self.response_box_serial_port:
            raise ValueError("Le trigger et les réponses série doivent utiliser des ports distincts.")

    def with_hardware_overrides(
        self,
        *,
        trigger_enabled: bool | None = None,
        eyetracker_enabled: bool | None = None,
        mock_mode: bool | None = None,
    ) -> "SessionSettings":
        """Retourne une copie avec quelques switches hardware remplacés."""
        return replace(
            self,
            trigger_enabled=self.trigger_enabled if trigger_enabled is None else trigger_enabled,
            eyetracker_enabled=self.eyetracker_enabled if eyetracker_enabled is None else eyetracker_enabled,
            mock_mode=self.mock_mode if mock_mode is None else mock_mode,
        )

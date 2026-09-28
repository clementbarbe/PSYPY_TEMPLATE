"""
Orchestration générale de l'expérience.

Contient :
- SessionSettings : chargement settings.yaml + paramètres de session ;
- ExperimentClock : référence t=0 ;
- Experiment : fenêtre PsychoPy, lancement, cleanup propre.
"""

from __future__ import annotations

import atexit
import copy
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from psychopy import core, monitors, visual

from data import DataWriter, Logger, OutputPaths
from hardware import Hardware


PROJECT_ROOT = Path(__file__).resolve().parent


class AbortExperiment(Exception):
    """Interruption propre demandée par Escape ou une exception contrôlée."""


class TaskConfigurationError(Exception):
    """Configuration de tâche invalide."""


class ExperimentClock:
    """Horloge unique de l'expérience, remise à zéro au trigger."""

    def __init__(self) -> None:
        self._clock = core.Clock()
        self.trigger_wall_time: str | None = None

    @property
    def time(self) -> float:
        return self._clock.getTime()

    @property
    def psychopy_clock(self):
        return self._clock

    def reset(self) -> None:
        self._clock.reset()
        self.trigger_wall_time = datetime.now().isoformat(timespec="microseconds")

    def wait(self, duration: float) -> None:
        core.wait(max(0.0, duration), hogCPUperiod=min(duration, 0.2))


@dataclass
class SessionSettings:
    """Configuration globale réellement utilisée pendant une session."""

    participant: str
    session: str = "01"

    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")

    fullscreen: bool = True
    screen_index: int = 0
    background_color: tuple = (-1, -1, -1)
    quit_key: str = "escape"
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

    responses: dict[str, str] = field(default_factory=dict)

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
    eyetracker_host: str = "100.1.1.1"

    microphone_enabled: bool = False
    microphone_sample_rate: int = 44100
    microphone_channels: int = 1

    save_data: bool = True

    @classmethod
    def from_yaml(
        cls,
        path: Path,
        participant: str,
        session: str = "01",
        fullscreen: bool | None = None,
        screen_index: int | None = None,
        wait_for_trigger: bool | None = None,
        markers_enabled: bool | None = None,
        save_data: bool = True,
    ) -> "SessionSettings":
        if not path.exists():
            raise FileNotFoundError(f"Configuration globale introuvable : {path}")

        with path.open("r", encoding="utf-8") as file:
            raw = yaml.safe_load(file) or {}

        project = raw.get("project", {})
        display = raw.get("display", {})
        input_cfg = raw.get("input", {})
        trigger = input_cfg.get("trigger", {})
        output = raw.get("output", {})
        markers = output.get("markers", {})
        audio = raw.get("audio", {})
        eyetracker = raw.get("eyetracker", {})
        microphone = raw.get("microphone", {})

        pid = sanitize_id(participant)
        ses = sanitize_session(session)

        return cls(
            participant=pid,
            session=ses,
            data_dir=PROJECT_ROOT / project.get("data_dir", "data"),
            fullscreen=(
                bool(fullscreen)
                if fullscreen is not None
                else bool(project.get("fullscreen", True))
            ),
            screen_index=(
                int(screen_index)
                if screen_index is not None
                else int(project.get("default_screen", 0))
            ),
            background_color=tuple(
                display.get("background_color", [-1, -1, -1])
            ),
            quit_key=project.get("quit_key", "escape"),
            end_screen_seconds=float(project.get("end_screen_seconds", 3.0)),
            resolution=tuple(display.get("resolution", [1920, 1080])),
            width_cm=float(display.get("width_cm", 53.0)),
            viewing_distance_cm=float(display.get("viewing_distance_cm", 60.0)),
            refresh_rate=float(display.get("refresh_rate", 60.0)),
            flip_horizontal=bool(display.get("flip_horizontal", False)),
            flip_vertical=bool(display.get("flip_vertical", False)),
            trigger_enabled=(
                bool(wait_for_trigger)
                if wait_for_trigger is not None
                else bool(trigger.get("enabled", False))
            ),
            trigger_source=trigger.get("source", "keyboard"),
            trigger_key=trigger.get("key", "t"),
            trigger_serial_port=trigger.get("serial_port", ""),
            trigger_baudrate=int(trigger.get("baudrate", 115200)),
            trigger_timeout_seconds=float(trigger.get("timeout_seconds", 300)),
            responses=dict(input_cfg.get("responses", {})),
            markers_enabled=(
                bool(markers_enabled)
                if markers_enabled is not None
                else bool(markers.get("enabled", False))
            ),
            marker_transport=markers.get("transport", "none"),
            parallel_address=markers.get("parallel_address"),
            marker_serial_port=markers.get("serial_port", ""),
            marker_baudrate=int(markers.get("baudrate", 115200)),
            marker_pulse_seconds=float(markers.get("pulse_seconds", 0.005)),
            audio_backend=audio.get("backend", "ptb"),
            audio_sample_rate=int(audio.get("sample_rate", 48000)),
            audio_schedule_lead_seconds=float(
                audio.get("schedule_lead_seconds", 0.1)
            ),
            audio_minimum_schedule_lead_seconds=float(
                audio.get("minimum_schedule_lead_seconds", 0.03)
            ),
            eyetracker_enabled=bool(eyetracker.get("enabled", False)),
            eyetracker_host=eyetracker.get("host", "100.1.1.1"),
            microphone_enabled=bool(microphone.get("enabled", False)),
            microphone_sample_rate=int(microphone.get("sample_rate", 44100)),
            microphone_channels=int(microphone.get("channels", 1)),
            save_data=save_data,
        )


class Experiment:
    """Crée les ressources partagées, lance une tâche et ferme proprement."""

    _active: "Experiment | None" = None

    def __init__(self, settings: SessionSettings):
        self.settings = settings
        self.clock = ExperimentClock()
        self.paths = OutputPaths(settings)
        self.logger = Logger(self.paths.log_dir)
        self.win = self._create_window()
        self.hardware = Hardware(settings, self.logger)

        self._closed = False
        Experiment._active = self

        atexit.register(self._atexit_cleanup)
        self._install_signal_handlers()

        self.logger.info(
            f"Experiment initialized | participant={settings.participant} "
            f"| session={settings.session}"
        )

    def _create_window(self):
        monitor = monitors.Monitor(
            name="experiment_monitor",
            width=self.settings.width_cm,
            distance=self.settings.viewing_distance_cm,
        )
        monitor.setSizePix(list(self.settings.resolution))

        win = visual.Window(
            size=self.settings.resolution,
            fullscr=self.settings.fullscreen,
            screen=self.settings.screen_index,
            monitor=monitor,
            color=self.settings.background_color,
            colorSpace="rgb",
            units="norm",
            allowGUI=False,
            waitBlanking=True,
        )

        if self.settings.flip_horizontal or self.settings.flip_vertical:
            win.viewScale = [
                -1.0 if self.settings.flip_horizontal else 1.0,
                -1.0 if self.settings.flip_vertical else 1.0,
            ]

        return win

    def run(
        self,
        task_name: str,
        design_id: int,
        task_config: dict,
        task_class,
        seed: int | None = None,
    ) -> Path | None:
        self.paths.ensure_task_dir(task_name)

        run = self.paths.resolve_run(task_name, design_id)
        writer = DataWriter(
            output_dir=self.paths.task_dir(task_name),
            stem=self.paths.stem(task_name, design_id, run),
            logger=self.logger,
            enabled=self.settings.save_data,
        )

        task = task_class(
            win=self.win,
            clock=self.clock,
            settings=self.settings,
            hardware=self.hardware,
            writer=writer,
            logger=self.logger,
            task_name=task_name,
            task_config=copy.deepcopy(task_config),
            design_id=design_id,
            run=run,
            seed=seed,
        )

        return task.run()

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True

        try:
            self.hardware.close()
        except Exception:
            pass

        try:
            if self.win and not getattr(self.win, "_closed", True):
                self.win.close()
        except Exception:
            pass

        try:
            self.logger.info("Experiment closed.")
            self.logger.close()
        except Exception:
            pass

        if Experiment._active is self:
            Experiment._active = None

    @staticmethod
    def _atexit_cleanup() -> None:
        active = Experiment._active

        if active is not None:
            try:
                active.close()
            except Exception:
                pass

    def _install_signal_handlers(self) -> None:
        def handler(signum, frame):
            self.logger.warning(f"Signal {signum} received.")
            self.close()
            raise SystemExit(1)

        try:
            signal.signal(signal.SIGINT, handler)

            if hasattr(signal, "SIGTERM"):
                signal.signal(signal.SIGTERM, handler)

        except Exception:
            pass


def sanitize_id(value: str) -> str:
    value = value.strip()
    safe = "".join(char for char in value if char.isalnum() or char in "-_")

    if not safe:
        raise ValueError("Participant invalide.")

    return safe


def sanitize_session(value: str) -> str:
    value = str(value).strip()

    if not value:
        return "01"

    try:
        return f"{int(value):02d}"
    except ValueError:
        return sanitize_id(value)
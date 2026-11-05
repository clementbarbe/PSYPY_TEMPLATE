"""Abstraction des réponses participant (clavier ou boîtier série)."""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass
from typing import Sequence


@dataclass(slots=True)
class ResponseEvent:
    """Réponse minimale compatible avec ``psychopy.hardware.keyboard.KeyPress``."""

    name: str
    rt: float | None = None


class KeyboardResponseBox:
    """Utilise le clavier PsychoPy comme boîtier de réponse par défaut."""

    def __init__(self, psychopy_clock: Any) -> None:
        """Associe le clavier PsychoPy à l’horloge expérimentale."""
        from psychopy.hardware import keyboard

        self._keyboard = keyboard.Keyboard(clock=psychopy_clock)

    def clear_events(self) -> None:
        """Supprime les événements clavier en attente."""
        self._keyboard.clearEvents()

    def get_keys(
        self,
        key_list: Sequence[str] | None = None,
        *,
        wait_release: bool = False,
    ) -> list[Any]:
        """Retourne les touches PsychoPy disponibles sans blocage."""
        return self._keyboard.getKeys(
            keyList=None if key_list is None else list(key_list),
            waitRelease=wait_release,
        )

    def close(self) -> None:
        """Ne fait rien : PsychoPy gère le clavier globalement."""


class SerialResponseBox:
    """Lecteur générique d'un boîtier qui envoie un caractère ASCII par appui.

    Cette implémentation volontairement minimale convient aux boîtiers série
    simples. Pour un protocole propriétaire, il suffit de remplacer cette classe
    sans modifier les tâches.
    """

    def __init__(self, port: str, baudrate: int, clock: Any) -> None:
        """Ouvre le port du boîtier série et conserve l’horloge du run."""
        import serial

        if not port:
            raise ValueError("response_box.serial_port est requis en mode série.")
        self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=0)
        self._clock = clock

    def clear_events(self) -> None:
        """Vide le buffer d'entrée série."""
        self._serial.reset_input_buffer()

    def get_keys(
        self,
        key_list: Sequence[str] | None = None,
        *,
        wait_release: bool = False,
    ) -> list[ResponseEvent]:
        """Lit les caractères disponibles et applique éventuellement un filtre."""
        del wait_release
        events: list[ResponseEvent] = []
        allowed = None if key_list is None else set(key_list)
        while self._serial.in_waiting:
            raw = self._serial.read(1)
            try:
                name = raw.decode("ascii").strip()
            except UnicodeDecodeError:
                continue
            if name and (allowed is None or name in allowed):
                events.append(ResponseEvent(name=name, rt=float(self._clock.raw_time)))
        return events

    def close(self) -> None:
        """Ferme le port série."""
        self._serial.close()


def create_response_box(settings: Any, clock: Any, logger: Any) -> Any:
    """Construit le backend de réponse configuré."""
    backend = str(settings.response_box_backend).lower()
    if backend == "keyboard":
        return KeyboardResponseBox(clock.psychopy_clock)
    if backend == "serial":
        logger.info(f"Boîtier de réponse série : {settings.response_box_serial_port}")
        return SerialResponseBox(
            settings.response_box_serial_port,
            settings.response_box_baudrate,
            clock,
        )
    raise ValueError(f"Backend de response box inconnu : {backend}")

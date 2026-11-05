"""Réception du trigger scanner et émission de marqueurs TTL/série."""

from __future__ import annotations

from typing import Any
import time

from core.errors import AbortExperiment


class TriggerReceiver:
    """Attend un trigger clavier, série ou parallèle."""

    def __init__(self, settings: Any, logger: Any, clock: Any = None) -> None:
        """Initialise le backend de réception configuré."""
        self.settings = settings
        self.logger = logger
        self.clock = clock
        self.last_trigger_time: float | None = None
        self._serial = None
        self._parallel = None
        self._open_backend()

    def _open_backend(self) -> None:
        """Ouvre uniquement le backend nécessaire à la session."""
        if not self.settings.trigger_enabled:
            return
        source = self.settings.trigger_source.lower()
        if source == "serial":
            import serial

            if not self.settings.trigger_serial_port:
                raise ValueError("Trigger série activé sans serial_port.")
            self._serial = serial.Serial(
                port=self.settings.trigger_serial_port,
                baudrate=self.settings.trigger_baudrate,
                timeout=0,
            )
        elif source == "parallel":
            from psychopy import parallel

            if self.settings.trigger_parallel_address is None:
                raise ValueError("Trigger parallèle activé sans parallel_address.")
            self._parallel = parallel.ParallelPort(
                address=self.settings.trigger_parallel_address
            )
        elif source != "keyboard":
            raise ValueError(f"Source de trigger inconnue : {source}")

    def wait(self, response_box: Any, quit_key: str) -> bool:
        """Bloque jusqu'au trigger ou au timeout, tout en surveillant Escape."""
        if not self.settings.trigger_enabled:
            return True

        deadline = time.monotonic() + self.settings.trigger_timeout_seconds
        source = self.settings.trigger_source.lower()
        response_box.clear_events()
        self.last_trigger_time = None
        if source == "serial" and self._serial is not None:
            self._serial.reset_input_buffer()
        previous_high = bool(self._parallel.readPin(self.settings.trigger_parallel_pin)) if source == "parallel" else False

        while time.monotonic() < deadline:
            keys = response_box.get_keys(
                [self.settings.trigger_key, quit_key] if source == "keyboard" else [quit_key],
                wait_release=False,
            )
            if any(key.name == quit_key for key in keys):
                raise AbortExperiment("Interruption pendant l'attente du trigger.")
            if source == "keyboard":
                for key in keys:
                    if key.name == self.settings.trigger_key:
                        self.last_trigger_time = float(key.rt)
                        return True
            elif source == "serial" and self._serial is not None:
                if self._serial.in_waiting:
                    data = self._serial.read(1)
                    if data == self.settings.trigger_key.encode("ascii"):
                        self.last_trigger_time = self.clock.raw_time
                        return True
            elif source == "parallel" and self._parallel is not None:
                pin = self.settings.trigger_parallel_pin
                high = bool(self._parallel.readPin(pin))
                if high and not previous_high:
                    self.last_trigger_time = self.clock.raw_time
                    return True
                previous_high = high
            time.sleep(0.001)
        return False

    def close(self) -> None:
        """Ferme le port série de trigger si nécessaire."""
        if self._serial is not None:
            self._serial.close()
            self._serial = None


class MarkerOutput:
    """Émet des marqueurs via port parallèle ou série."""

    def __init__(self, settings: Any, logger: Any) -> None:
        """Initialise le transport d’émission des marqueurs."""
        self.settings = settings
        self.logger = logger
        self._device = None
        self._open_backend()

    def _open_backend(self) -> None:
        """Initialise le transport des marqueurs si activé."""
        if not self.settings.markers_enabled:
            return
        transport = self.settings.marker_transport.lower()
        if transport == "parallel":
            from psychopy import parallel

            if self.settings.parallel_address is None:
                raise ValueError("Marqueurs parallèles activés sans adresse.")
            self._device = parallel.ParallelPort(address=self.settings.parallel_address)
            self._device.setData(0)
        elif transport == "serial":
            import serial

            if not self.settings.marker_serial_port:
                raise ValueError("Marqueurs série activés sans serial_port.")
            self._device = serial.Serial(
                port=self.settings.marker_serial_port,
                baudrate=self.settings.marker_baudrate,
                timeout=0,
            )
        elif transport != "none":
            raise ValueError(f"Transport de marqueur inconnu : {transport}")

    def send(self, code: int) -> None:
        """Envoie un code 8 bits sans interrompre la tâche en cas d'erreur I/O."""
        if self._device is None:
            return
        code = int(code)
        if not 1 <= code <= 255:
            raise ValueError("Un marqueur doit être compris entre 1 et 255.")
        if self.settings.marker_transport.lower() == "parallel":
            self._device.setData(code)
            try:
                time.sleep(self.settings.marker_pulse_seconds)
            finally:
                self._device.setData(0)
        elif self._device.write(bytes([code])) != 1:
            raise OSError(f"Marqueur série {code} non transmis.")

    def close(self) -> None:
        """Remet le TTL à zéro puis ferme le transport si possible."""
        if self._device is None:
            return
        try:
            if self.settings.marker_transport.lower() == "parallel":
                self._device.setData(0)
            if hasattr(self._device, "close"):
                self._device.close()
        finally:
            self._device = None

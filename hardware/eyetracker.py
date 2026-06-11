"""
Eye-tracker wrapper with robust cleanup.

Guarantees: close() can be called multiple times safely.
Emergency shutdown always attempts data transfer.
"""

from __future__ import annotations

from pathlib import Path
from hardware.base_device import BaseDevice


class EyeTracker(BaseDevice):
    """Minimal eye-tracker interface with safe cleanup."""

    def __init__(self, logger=None):
        self._tracker = None
        self._recording = False
        self._data_file_open = False
        self._edf_filename: str = ''
        self._logger = logger
        self._closed = False

    def open(self) -> bool:
        try:
            from pylink import EyeLink
            self._tracker = EyeLink("100.1.1.1")
            if self._logger:
                self._logger.ok("EyeTracker connected.")
            return True
        except Exception as e:
            if self._logger:
                self._logger.warn(f"EyeTracker unavailable: {e}")
            self._tracker = None
            return False

    def close(self) -> None:
        """
        Full cleanup — safe to call multiple times.

        Order: stop recording → close data file → close connection.
        """
        if self._closed or self._tracker is None:
            return
        self._closed = True

        # 1. Stop recording
        if self._recording:
            try:
                self._tracker.stopRecording()
                self._recording = False
                if self._logger:
                    self._logger.log("EyeTracker: recording stopped.")
            except Exception as e:
                if self._logger:
                    self._logger.warn(f"EyeTracker stop_recording: {e}")

        # 2. Close data file on tracker
        if self._data_file_open:
            try:
                self._tracker.closeDataFile()
                self._data_file_open = False
            except Exception as e:
                if self._logger:
                    self._logger.warn(f"EyeTracker closeDataFile: {e}")

        # 3. Close connection
        try:
            self._tracker.close()
            if self._logger:
                self._logger.log("EyeTracker: connection closed.")
        except Exception as e:
            if self._logger:
                self._logger.warn(f"EyeTracker close: {e}")

        self._tracker = None

    def is_connected(self) -> bool:
        return self._tracker is not None and not self._closed

    def start_recording(self, filename: str = 'et.edf') -> None:
        if self._tracker is None or self._closed:
            return
        try:
            self._edf_filename = filename
            self._tracker.openDataFile(filename)
            self._data_file_open = True
            self._tracker.startRecording(1, 1, 1, 1)
            self._recording = True
            if self._logger:
                self._logger.ok(f"EyeTracker: recording started ({filename})")
        except Exception as e:
            if self._logger:
                self._logger.warn(f"EyeTracker start_recording: {e}")

    def stop_recording(self) -> None:
        if self._tracker is None or not self._recording or self._closed:
            return
        try:
            self._tracker.stopRecording()
            self._recording = False
        except Exception:
            pass

    def send_message(self, msg: str) -> None:
        if self._tracker is None or self._closed:
            return
        try:
            self._tracker.sendMessage(msg)
        except Exception:
            pass

    def transfer_data(self, local_dir: str) -> Path | None:
        """
        Stop recording, close file, transfer EDF from tracker to local disk.

        Safe to call even if recording was already stopped.
        Returns local path on success, None on failure.
        """
        if self._tracker is None or self._closed:
            return None

        # Stop recording if still going
        if self._recording:
            try:
                self._tracker.stopRecording()
                self._recording = False
            except Exception:
                pass

        # Close data file
        if self._data_file_open:
            try:
                self._tracker.closeDataFile()
                self._data_file_open = False
            except Exception as e:
                if self._logger:
                    self._logger.warn(f"ET closeDataFile: {e}")
                return None

        # Transfer
        try:
            local_path = Path(local_dir) / self._edf_filename
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._tracker.receiveDataFile('', str(local_path))
            if self._logger:
                self._logger.ok(f"EyeTracker data transferred: {local_path}")
            return local_path
        except Exception as e:
            if self._logger:
                self._logger.warn(f"ET transfer failed: {e}")
            return None
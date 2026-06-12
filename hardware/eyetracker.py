"""
Eye-tracker wrapper with force reset capability.
"""

from __future__ import annotations

from pathlib import Path
from hardware.base_device import BaseDevice


class EyeTracker(BaseDevice):
    """EyeLink eye-tracker interface with safe cleanup."""

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
        if self._closed or self._tracker is None:
            return
        self._closed = True

        if self._recording:
            try:
                self._tracker.stopRecording()
                self._recording = False
            except Exception:
                pass

        if self._data_file_open:
            try:
                self._tracker.closeDataFile()
                self._data_file_open = False
            except Exception:
                pass

        try:
            self._tracker.close()
        except Exception:
            pass
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
        except Exception as e:
            if self._logger:
                self._logger.warn(f"ET start_recording: {e}")

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
        if self._tracker is None or self._closed:
            return None

        if self._recording:
            try:
                self._tracker.stopRecording()
                self._recording = False
            except Exception:
                pass

        if self._data_file_open:
            try:
                self._tracker.closeDataFile()
                self._data_file_open = False
            except Exception:
                return None

        try:
            local_path = Path(local_dir) / self._edf_filename
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._tracker.receiveDataFile('', str(local_path))
            return local_path
        except Exception:
            return None

    # ═════════════════════════════════════════════════════════════════
    # Force Reset — static, callable from GUI
    # ═════════════════════════════════════════════════════════════════

    @staticmethod
    def force_reset(ip: str = "100.1.1.1") -> tuple[bool, str]:
        """
        Force reset a stuck EyeLink tracker.

        Closes any existing connection, waits, reconnects.
        Safe to call at any time — catches all exceptions.

        Returns:
            (success: bool, message: str)
        """
        try:
            import pylink
        except ImportError:
            return False, "pylink non installe."

        # 1. Close existing connection
        try:
            el = pylink.getEYELINK()
            if el is not None:
                try:
                    el.stopRecording()
                except Exception:
                    pass
                try:
                    el.setOfflineMode()
                except Exception:
                    pass
                try:
                    el.closeDataFile()
                except Exception:
                    pass
                try:
                    el.close()
                except Exception:
                    pass
        except Exception:
            pass

        # 2. Wait
        try:
            pylink.msecDelay(1000)
        except Exception:
            import time
            time.sleep(1.0)

        # 3. Close graphics if any
        try:
            pylink.closeGraphics()
        except Exception:
            pass

        # 4. Reconnect to verify
        try:
            el = pylink.EyeLink(ip)
            if el.isConnected():
                el.setOfflineMode()
                el.close()
                return True, "Eye-tracker reinitialise avec succes."
            else:
                return False, "Reconnexion echouee."
        except Exception as e:
            return False, f"Erreur reconnexion: {e}"
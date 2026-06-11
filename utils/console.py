"""
Windows-compatible console setup.

Call init_console() at application startup before any print().
Enables:
    - ANSI escape codes on Windows (for coloured logging)
    - UTF-8 console encoding
    - Safe symbol fallbacks if terminal can't render Unicode
"""

from __future__ import annotations

import sys
import os


def init_console() -> None:
    """
    Initialise console for Windows compatibility.

    Safe to call on any platform — does nothing on Linux/macOS.
    """
    if sys.platform == 'win32':
        _enable_windows_ansi()
        _enable_windows_utf8()


def _enable_windows_ansi() -> None:
    """Enable VT100 ANSI escape processing on Windows 10+."""
    try:
        # This trick enables ANSI on Windows cmd.exe and PowerShell
        os.system('')

        # More robust: use ctypes to enable VT processing
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)

        # Same for stderr
        handle_err = kernel32.GetStdHandle(-12)
        mode_err = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle_err, ctypes.byref(mode_err))
        kernel32.SetConsoleMode(handle_err, mode_err.value | 0x0004)
    except Exception:
        pass  # Old Windows version — ANSI won't work, but experiment still runs


def _enable_windows_utf8() -> None:
    """Set UTF-8 encoding for Windows console streams."""
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


# ═════════════════════════════════════════════════════════════════════════════
# Safe symbols — ASCII fallback for terminals that can't render Unicode
# ═════════════════════════════════════════════════════════════════════════════

def _can_render_unicode() -> bool:
    """Check if the current stdout can render our symbols."""
    try:
        test = '✓✗★⚡⏸'
        encoding = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
        test.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


if _can_render_unicode():
    SYM_OK = '✓'
    SYM_ERR = '✗'
    SYM_STAR = '★'
    SYM_DOT = '·'
    SYM_BOLT = '⚡'
    SYM_PAUSE = '⏸'
    SYM_CHECK = '✅'
    SYM_BRAIN = '🧠'
    SYM_PLAY = '▶'
    SYM_STOP = '✕'
    SYM_BLOCK_H = '═'
    SYM_BLOCK_V = '║'
    SYM_CORNER_TL = '╔'
    SYM_CORNER_BL = '╚'
    SYM_TEE = '╠'
else:
    SYM_OK = 'v'
    SYM_ERR = 'x'
    SYM_STAR = '*'
    SYM_DOT = '.'
    SYM_BOLT = '!'
    SYM_PAUSE = '||'
    SYM_CHECK = '[OK]'
    SYM_BRAIN = '[*]'
    SYM_PLAY = '>'
    SYM_STOP = 'X'
    SYM_BLOCK_H = '='
    SYM_BLOCK_V = '|'
    SYM_CORNER_TL = '+='
    SYM_CORNER_BL = '+='
    SYM_TEE = '+='
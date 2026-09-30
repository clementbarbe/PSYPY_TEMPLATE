"""Tests de configuration et labels BIDS."""

from pathlib import Path

from core.config import SessionSettings, sanitize_id, sanitize_run, sanitize_session


def test_sanitize_id() -> None:
    """Le préfixe sub- ne doit jamais être dupliqué."""
    assert sanitize_id(" participant 01 ") == "participant01"
    assert sanitize_id("sub-01") == "01"


def test_sanitize_session() -> None:
    """Les sessions numériques courtes sont normalisées sur deux chiffres."""
    assert sanitize_session("1") == "01"
    assert sanitize_session("ses-12") == "12"


def test_sanitize_run() -> None:
    """Le run accepte auto et les formats run-XX."""
    assert sanitize_run("auto") is None
    assert sanitize_run(2) == "02"
    assert sanitize_run("run-12") == "12"


def test_settings_load() -> None:
    """Le YAML global est chargeable sans PsychoPy."""
    root = Path(__file__).resolve().parent.parent
    settings = SessionSettings.from_yaml(
        root / "config" / "settings.yaml",
        participant="TEST",
        session="1",
        fullscreen=False,
    )
    assert settings.participant == "TEST"
    assert settings.session == "01"
    assert settings.fullscreen is False
    assert settings.responses["go"] == "space"

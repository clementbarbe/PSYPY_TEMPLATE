from pathlib import Path

from experiment import SessionSettings, sanitize_id, sanitize_session


def test_sanitize_id():
    assert sanitize_id(" participant 01 ") == "participant01"
    assert sanitize_id("sub-01") == "sub-01"


def test_sanitize_session():
    assert sanitize_session("1") == "01"
    assert sanitize_session("12") == "12"


def test_settings_load():
    root = Path(__file__).resolve().parent.parent

    settings = SessionSettings.from_yaml(
        root / "settings.yaml",
        participant="TEST",
        session="1",
        fullscreen=False,
    )

    assert settings.participant == "TEST"
    assert settings.session == "01"
    assert settings.fullscreen is False
    assert settings.responses["go"] == "space"
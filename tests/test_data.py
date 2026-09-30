"""Tests de la sauvegarde incrémentale et BIDS."""

from unittest.mock import MagicMock

from core.data import DataWriter


def test_incremental_and_final_tsv(tmp_path) -> None:
    """Chaque trial crée un fichier de secours puis un final atomique."""
    writer = DataWriter(
        output_dir=tmp_path,
        stem="sub-01_ses-01_task-test_run-01",
        logger=MagicMock(),
    )
    writer.write_trial(
        {"onset": 0.0, "duration": 1.0, "trial_type": "test", "response_key": None}
    )
    assert writer.incremental_path.exists()
    final = writer.save_final()
    assert final is not None and final.exists()
    text = final.read_text(encoding="utf-8")
    assert "onset\tduration\ttrial_type" in text
    assert "n/a" in text


def test_late_column_is_preserved(tmp_path) -> None:
    """Une colonne apparue au second essai doit être conservée sans perte."""
    writer = DataWriter(output_dir=tmp_path, stem="test", logger=MagicMock())
    writer.write_trial({"onset": 0.0, "trial_type": "a"})
    writer.write_trial({"onset": 1.0, "trial_type": "b", "rt": 0.4})
    final = writer.save_final()
    assert final is not None
    assert "rt" in final.read_text(encoding="utf-8").splitlines()[0]


def test_writer_disabled_does_not_create_file(tmp_path) -> None:
    """Le mode no-save ne doit rien écrire sur disque."""
    writer = DataWriter(
        output_dir=tmp_path,
        stem="test",
        logger=MagicMock(),
        enabled=False,
    )
    writer.write_trial({"onset": 0.0})
    assert writer.save_final() is None
    assert not list(tmp_path.iterdir())

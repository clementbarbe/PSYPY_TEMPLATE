from unittest.mock import MagicMock

from data import DataWriter, OutputPaths


def test_incremental_and_final_tsv(tmp_path):
    logger = MagicMock()

    writer = DataWriter(
        output_dir=tmp_path,
        stem="test",
        logger=logger,
    )

    writer.write_trial(
        {
            "onset": 0.0,
            "duration": 1.0,
            "trial_type": "test",
            "response": None,
        }
    )

    assert (tmp_path / "test_events_incremental.tsv").exists()

    final = writer.save_final()

    assert final is not None
    assert final.exists()

    text = final.read_text(encoding="utf-8")
    assert "onset\tduration\ttrial_type" in text
    assert "n/a" in text


def test_writer_disabled_does_not_create_file(tmp_path):
    writer = DataWriter(
        output_dir=tmp_path,
        stem="test",
        logger=MagicMock(),
        enabled=False,
    )

    writer.write_trial({"onset": 0.0})
    assert writer.save_final() is None
    assert not list(tmp_path.iterdir())
from __future__ import annotations

from pathlib import Path


def test_detective_private_artifacts_are_ignored_and_documented() -> None:
    root = Path(__file__).resolve().parents[1]
    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    protocol = (
        root
        / "examples"
        / "detective_corpus"
        / "treatments"
        / "detective_fair_play_pilot_protocol.md"
    ).read_text(encoding="utf-8")

    assert "*blinding_key*.json" in gitignore
    assert "completed_blinded_run_sheets/" in gitignore
    assert "*_g_rows_completed.csv" in gitignore
    assert "ignored by git" in protocol
    assert "should not be shared with participants" in protocol

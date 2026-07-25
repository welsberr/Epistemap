from __future__ import annotations

from pathlib import Path


def test_detective_pilot_protocol_records_run_and_postrun_steps() -> None:
    protocol = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "detective_corpus"
        / "treatments"
        / "detective_fair_play_pilot_protocol.md"
    ).read_text(encoding="utf-8")

    assert "examples/detective_corpus/run_ui/index.html" in protocol
    assert "detective-run-sheets" in protocol
    assert "detective-blind-run-sheets" in protocol
    assert "detective-unblind-run-sheets" in protocol
    assert "detective-g-manifest" in protocol
    assert "g-summary" in protocol
    assert "not result data" in protocol
    assert "Do not show" in protocol

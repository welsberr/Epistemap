from __future__ import annotations

from pathlib import Path


def test_detective_run_ui_is_blinded_collection_surface() -> None:
    html = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "detective_corpus"
        / "run_ui"
        / "index.html"
    ).read_text(encoding="utf-8")

    assert "Epistemap Detective Run" in html
    assert "Recognition Outcome" in html
    assert "Confidence p(y=1)" in html
    assert "recognized_at" in html
    assert "row_key" in html
    assert "pilot-reader-plain-reading-01_completed.csv" in html or "_completed.csv" in html
    assert "detective-fair-play-pilot-001-plain-reading-01" in html
    assert "Reviewed Quote" not in html
    assert "Reviewed Locator" not in html
    assert "Fair-Play Rating" not in html
    assert "Sidecars" not in html
    assert "fair_play_rating" not in html
    assert "fair_play_status" not in html
    assert "graph_file" not in html
    assert "fair_play_diagnostic_file" not in html
    assert "claim_id" not in html
    assert "contradiction_available_at" not in html
    assert "recognition_lag" not in html

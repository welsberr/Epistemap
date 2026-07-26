from __future__ import annotations

from pathlib import Path


def test_detective_g_collection_ui_contains_expected_fields() -> None:
    html = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "detective_corpus"
        / "collection_ui"
        / "index.html"
    ).read_text(encoding="utf-8")

    assert "Epistemap Detective G Collection" in html
    assert "Recognition Outcome" in html
    assert "Confidence p(y=1)" in html
    assert "Claim Text" in html
    assert "Reviewed Locator" in html
    assert "Reviewed Quote" in html
    assert "claimContext" in html
    assert "recognition_lag" in html
    assert "detective_fair_play_g_rows_completed.csv" in html
    assert "claim::blue-carbuncle::baker-stole-jewel" in html

from __future__ import annotations

from pathlib import Path


def test_detective_anchor_review_ui_contains_expected_fields() -> None:
    html = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "detective_corpus"
        / "review_ui"
        / "index.html"
    ).read_text(encoding="utf-8")

    assert "Epistemap Detective Anchor Review" in html
    assert "reviewed_source_locator" in html
    assert "reviewed_source_quote" in html
    assert "reviewed_narrative_anchor" in html
    assert "candidateReviewDefaults" in html
    assert "Candidate locator, passage, and anchor fields are prefilled" in html
    assert "Source Vicinity" in html
    assert "sourceVicinity" in html
    assert "Precise citation target" in html
    assert "Short narrative label" in html
    assert "claim::blue-carbuncle::baker-stole-jewel" in html
    assert "police-court report vicinity" in html
    assert "Prefilled candidate passage" in html
    assert "detective_anchor_review_completed.csv" in html

from __future__ import annotations

import pytest

from epistemap import (
    detective_treatment_manifest,
    read_detective_treatment_manifest,
    validate_detective_treatment_manifest,
    write_detective_treatment_manifest,
)


def test_detective_treatment_manifest_round_trips_and_validates(tmp_path) -> None:
    manifest = detective_treatment_manifest(
        experiment_id="detective-fair-play-001",
        name="Detective fair-play pilot",
        corpus_sidecar_manifest="examples/detective_corpus/sidecars/detective_corpus_sidecars.json",
        row_file="results/g_rows.csv",
        created_by="codex",
    )
    destination = tmp_path / "detective_treatment.json"

    write_detective_treatment_manifest(manifest, destination)
    loaded = read_detective_treatment_manifest(destination)
    validation = validate_detective_treatment_manifest(loaded)

    assert loaded["manifest_kind"] == "epistemap_detective_treatment"
    assert loaded["experiment_id"] == "detective-fair-play-001"
    assert loaded["evaluation_target"] == "detective_contradiction_recognition"
    assert [item["condition"] for item in loaded["treatments"]] == ["plain-reading", "graph-assisted"]
    assert loaded["fair_play_policy"]["admit_ratings"] == ["fair"]
    assert validation["summary"]["status"] == "pass"


def test_detective_treatment_manifest_accepts_custom_treatments() -> None:
    manifest = detective_treatment_manifest(
        experiment_id="custom",
        corpus_sidecar_manifest="sidecars.json",
        treatments=[
            {
                "condition": "diagnostic-visible",
                "exposed_artifacts": ["source_text", "epistemap_graph", "fair_play_diagnostic"],
                "hidden_artifacts": ["answer_key"],
            }
        ],
        phases=["single-pass"],
    )

    assert manifest["treatments"][0]["condition"] == "diagnostic-visible"
    assert manifest["phases"] == ["single-pass"]


def test_detective_treatment_manifest_validation_flags_missing_or_duplicate_conditions() -> None:
    manifest = detective_treatment_manifest(
        experiment_id="bad",
        corpus_sidecar_manifest="sidecars.json",
        treatments=[
            {"condition": "plain", "exposed_artifacts": ["source_text"]},
            {"condition": "plain", "exposed_artifacts": ["epistemap_graph"]},
        ],
    )
    validation = validate_detective_treatment_manifest(manifest)
    codes = {finding["code"] for finding in validation["findings"]}

    assert validation["summary"]["status"] == "error"
    assert "duplicate_treatment_condition" in codes


def test_detective_treatment_manifest_requires_identifiers() -> None:
    with pytest.raises(ValueError, match="experiment_id"):
        detective_treatment_manifest(experiment_id="", corpus_sidecar_manifest="sidecars.json")
    with pytest.raises(ValueError, match="corpus_sidecar_manifest"):
        detective_treatment_manifest(experiment_id="x", corpus_sidecar_manifest="")

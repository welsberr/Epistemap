from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, TextIO


DEFAULT_DETECTIVE_TREATMENTS = (
    {
        "condition": "plain-reading",
        "description": "Reader sees the story text without Epistemap graph sidecars.",
        "exposed_artifacts": ["source_text"],
        "hidden_artifacts": ["epistemap_graph", "fair_play_diagnostic", "answer_key"],
    },
    {
        "condition": "graph-assisted",
        "description": "Reader sees the story text plus Epistemap graph context without the answer key.",
        "exposed_artifacts": ["source_text", "epistemap_graph"],
        "hidden_artifacts": ["fair_play_diagnostic", "answer_key"],
    },
)
DEFAULT_DETECTIVE_PHASES = ("pre-reveal", "post-reveal")


def detective_treatment_manifest(
    *,
    experiment_id: str,
    corpus_sidecar_manifest: str,
    row_file: str = "g_rows.csv",
    name: str = "",
    evaluation_target: str = "detective_contradiction_recognition",
    treatments: Iterable[Mapping[str, Any]] | None = None,
    phases: Iterable[str] = DEFAULT_DETECTIVE_PHASES,
    fair_play_policy: Mapping[str, Any] | None = None,
    temporal_policy: Mapping[str, Any] | None = None,
    scoring_policy: Mapping[str, Any] | None = None,
    created_by: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe planned detective corpus treatments before G rows are collected."""

    if not str(experiment_id).strip():
        raise ValueError("detective treatment manifests require a non-empty experiment_id")
    if not str(corpus_sidecar_manifest).strip():
        raise ValueError("detective treatment manifests require a non-empty corpus_sidecar_manifest")
    if not str(evaluation_target).strip():
        raise ValueError("detective treatment manifests require a non-empty evaluation_target")

    payload: dict[str, Any] = {
        "manifest_kind": "epistemap_detective_treatment",
        "schema_version": "0.1",
        "experiment_id": str(experiment_id),
        "name": str(name),
        "evaluation_target": str(evaluation_target),
        "corpus_sidecar_manifest": str(corpus_sidecar_manifest),
        "row_file": str(row_file),
        "treatments": [_normalize_treatment(treatment) for treatment in (treatments or DEFAULT_DETECTIVE_TREATMENTS)],
        "phases": [str(phase) for phase in phases],
        "fair_play_policy": dict(fair_play_policy or _default_fair_play_policy()),
        "temporal_policy": dict(temporal_policy or _default_temporal_policy()),
        "scoring_policy": dict(scoring_policy or _default_scoring_policy()),
        "created_by": str(created_by),
        "metadata": dict(metadata or {}),
    }
    return {key: value for key, value in payload.items() if not _blank(value)}


def write_detective_treatment_manifest(manifest: Mapping[str, Any], destination: str | Path | TextIO) -> None:
    """Write a detective treatment manifest as deterministic JSON."""

    text = json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n"
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        return
    Path(destination).write_text(text, encoding="utf-8")


def read_detective_treatment_manifest(source: str | Path | TextIO) -> dict[str, Any]:
    """Read a detective treatment manifest from JSON."""

    if hasattr(source, "read"):
        text = source.read()  # type: ignore[union-attr]
    else:
        text = Path(source).read_text(encoding="utf-8")
    manifest = json.loads(text)
    if manifest.get("manifest_kind") != "epistemap_detective_treatment":
        raise ValueError("not an Epistemap detective treatment manifest")
    return manifest


def validate_detective_treatment_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Check a detective treatment manifest for experiment-critical fields."""

    findings: list[dict[str, Any]] = []
    if manifest.get("manifest_kind") != "epistemap_detective_treatment":
        findings.append(_finding("error", "unexpected_manifest_kind", field="manifest_kind"))
    for field in ("experiment_id", "evaluation_target", "corpus_sidecar_manifest", "row_file"):
        if _blank(manifest.get(field)):
            findings.append(_finding("error", "missing_required_treatment_field", field=field))

    treatments = list(manifest.get("treatments", []) or [])
    if not treatments:
        findings.append(_finding("error", "missing_treatments", field="treatments"))
    treatment_names = [str(treatment.get("condition", "")) for treatment in treatments]
    if len(set(treatment_names)) != len(treatment_names):
        findings.append(_finding("error", "duplicate_treatment_condition", field="treatments"))
    for treatment in treatments:
        condition = str(treatment.get("condition", ""))
        if _blank(condition):
            findings.append(_finding("error", "missing_treatment_condition", field="treatments"))
        if not treatment.get("exposed_artifacts"):
            findings.append(_finding("warning", "missing_treatment_exposed_artifacts", condition=condition))

    phases = list(manifest.get("phases", []) or [])
    if not phases:
        findings.append(_finding("warning", "missing_phases", field="phases"))
    for field in ("fair_play_policy", "temporal_policy", "scoring_policy"):
        if not isinstance(manifest.get(field), Mapping):
            findings.append(_finding("error", "invalid_policy_block", field=field))

    severity_counts = {
        "error": sum(1 for finding in findings if finding["severity"] == "error"),
        "warning": sum(1 for finding in findings if finding["severity"] == "warning"),
        "info": sum(1 for finding in findings if finding["severity"] == "info"),
    }
    return {
        "report_kind": "epistemap_detective_treatment_manifest_validation",
        "experiment_id": str(manifest.get("experiment_id", "")),
        "summary": {
            "status": "error" if severity_counts["error"] else "warning" if severity_counts["warning"] else "pass",
            "finding_count": len(findings),
            **severity_counts,
        },
        "findings": findings,
    }


def _normalize_treatment(treatment: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "condition": str(treatment.get("condition", "")),
        "description": str(treatment.get("description", "")),
        "exposed_artifacts": [str(item) for item in treatment.get("exposed_artifacts", []) or []],
        "hidden_artifacts": [str(item) for item in treatment.get("hidden_artifacts", []) or []],
        "metadata": dict(treatment.get("metadata", {}) or {}),
    }


def _default_fair_play_policy() -> dict[str, Any]:
    return {
        "name": "admit_fair_play_keep_controls_separate",
        "admit_ratings": ["fair"],
        "control_ratings": ["unfair"],
        "description": "Use fair items for primary recognition comparisons and withheld-evidence items as controls.",
    }


def _default_temporal_policy() -> dict[str, Any]:
    return {
        "name": "narrative_timestep_recognition_lag",
        "description": "Use annotation timesteps for contradiction availability, reveal point, and recognition lag.",
    }


def _default_scoring_policy() -> dict[str, Any]:
    return {
        "name": "canonical_g_rows",
        "description": "Collect one canonical G row per subject, condition, phase, story, and target claim.",
    }


def _finding(severity: str, code: str, **payload: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, **payload}


def _blank(value: Any) -> bool:
    return value in ("", None, [], {})

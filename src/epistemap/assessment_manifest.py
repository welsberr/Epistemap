from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, TextIO


DEFAULT_GRAPH_EXTRACTION_POLICY = {
    "name": "unspecified",
    "description": "Graph extraction policy was not declared by the caller.",
}
DEFAULT_EVIDENCE_WEIGHTING_POLICY = {
    "name": "confidence_weighted_edges",
    "description": "Evidence is weighted by edge confidence when present, then source node confidence when available.",
}
DEFAULT_TEMPORAL_POLICY = {
    "name": "metadata_available_at_or_timestep",
    "description": "Temporal operations use availability metadata such as available_at or timestep when present.",
}
DEFAULT_RELIABILITY_TREATMENT = {
    "name": "assessment_metadata_only",
    "description": "Reliability outputs are triage and audit metadata, not automatic claim promotion decisions.",
}
DEFAULT_VALIDATION_POLICY = {
    "name": "assessment_readiness_default",
    "description": "Default Epistemap assessment-readiness validation policy.",
}


def assessment_manifest(
    *,
    assessment_id: str,
    graph_file: str,
    assessment_file: str = "",
    validation_file: str = "",
    bayesian_prior_profile: str = "neutral",
    graph_extraction_policy: Mapping[str, Any] | str | None = None,
    evidence_weighting_policy: Mapping[str, Any] | str | None = None,
    temporal_policy: Mapping[str, Any] | str | None = None,
    reliability_treatment: Mapping[str, Any] | str | None = None,
    validation_policy: Mapping[str, Any] | str | None = None,
    g_manifest_file: str = "",
    experiment_id: str = "",
    condition: str = "",
    corpus: str = "",
    created_by: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe graph assessment artifacts well enough for audit and reproduction."""

    if not str(assessment_id).strip():
        raise ValueError("assessment manifests require a non-empty assessment_id")
    if not str(graph_file).strip():
        raise ValueError("assessment manifests require a non-empty graph_file")
    if not str(bayesian_prior_profile).strip():
        raise ValueError("assessment manifests require a non-empty bayesian_prior_profile")

    manifest: dict[str, Any] = {
        "manifest_kind": "epistemap_assessment",
        "schema_version": "0.1",
        "assessment_id": str(assessment_id),
        "graph_file": str(graph_file),
        "assessment_file": str(assessment_file),
        "validation_file": str(validation_file),
        "bayesian_prior_profile": str(bayesian_prior_profile),
        "graph_extraction_policy": _policy_block(graph_extraction_policy, DEFAULT_GRAPH_EXTRACTION_POLICY),
        "evidence_weighting_policy": _policy_block(evidence_weighting_policy, DEFAULT_EVIDENCE_WEIGHTING_POLICY),
        "temporal_policy": _policy_block(temporal_policy, DEFAULT_TEMPORAL_POLICY),
        "reliability_treatment": _policy_block(reliability_treatment, DEFAULT_RELIABILITY_TREATMENT),
        "validation_policy": _policy_block(validation_policy, DEFAULT_VALIDATION_POLICY),
        "g_manifest_file": str(g_manifest_file),
        "experiment_id": str(experiment_id),
        "condition": str(condition),
        "corpus": str(corpus),
        "created_by": str(created_by),
        "metadata": dict(metadata or {}),
    }
    return {key: value for key, value in manifest.items() if not _blank_manifest_value(value)}


def write_assessment_manifest(manifest: Mapping[str, Any], destination: str | Path | TextIO) -> None:
    """Write an assessment manifest as deterministic JSON."""

    text = json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n"
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        return
    Path(destination).write_text(text, encoding="utf-8")


def read_assessment_manifest(source: str | Path | TextIO) -> dict[str, Any]:
    """Read an Epistemap assessment manifest from JSON."""

    if hasattr(source, "read"):
        text = source.read()  # type: ignore[union-attr]
    else:
        text = Path(source).read_text(encoding="utf-8")
    manifest = json.loads(text)
    if manifest.get("manifest_kind") != "epistemap_assessment":
        raise ValueError("not an Epistemap assessment manifest")
    return manifest


def validate_assessment_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Check an assessment manifest for reproducibility-critical fields."""

    findings: list[dict[str, Any]] = []
    required_fields = ("assessment_id", "graph_file", "bayesian_prior_profile")
    for field in required_fields:
        if _blank_manifest_value(manifest.get(field)):
            findings.append(_finding("error", "missing_required_manifest_field", field=field))

    if manifest.get("manifest_kind") != "epistemap_assessment":
        findings.append(_finding("error", "unexpected_manifest_kind", field="manifest_kind"))

    for field in (
        "graph_extraction_policy",
        "evidence_weighting_policy",
        "temporal_policy",
        "reliability_treatment",
        "validation_policy",
    ):
        value = manifest.get(field)
        if not isinstance(value, Mapping):
            findings.append(_finding("error", "invalid_policy_block", field=field))
            continue
        if _blank_manifest_value(value.get("name")):
            findings.append(_finding("warning", "missing_policy_name", field=field))

    if _blank_manifest_value(manifest.get("assessment_file")):
        findings.append(_finding("info", "missing_assessment_file", field="assessment_file"))
    if _blank_manifest_value(manifest.get("validation_file")):
        findings.append(_finding("info", "missing_validation_file", field="validation_file"))

    severity_counts = {
        "error": sum(1 for finding in findings if finding["severity"] == "error"),
        "warning": sum(1 for finding in findings if finding["severity"] == "warning"),
        "info": sum(1 for finding in findings if finding["severity"] == "info"),
    }
    return {
        "report_kind": "epistemap_assessment_manifest_validation",
        "assessment_id": str(manifest.get("assessment_id", "")),
        "summary": {
            "status": "error" if severity_counts["error"] else "warning" if severity_counts["warning"] else "pass",
            "finding_count": len(findings),
            **severity_counts,
        },
        "findings": findings,
    }


def _policy_block(value: Mapping[str, Any] | str | None, default: Mapping[str, Any]) -> dict[str, Any]:
    if value is None:
        return dict(default)
    if isinstance(value, str):
        return {"name": value}
    return dict(value)


def _finding(severity: str, code: str, **payload: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, **payload}


def _blank_manifest_value(value: Any) -> bool:
    return value in ("", None, [], {})

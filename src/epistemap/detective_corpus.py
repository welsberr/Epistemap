from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, TextIO

from .grounding_effect import g_evaluation_row
from .models import Edge, GraphBundle, Node, ProvenanceRef
from .temporal import fair_play_diagnostic

FAIR_PLAY_STATUSES = {
    "fair_play",
    "late_decisive_evidence",
    "withheld_decisive_evidence",
    "ambiguous",
    "excluded",
}


def detective_story_annotation(
    *,
    story_id: str,
    title: str,
    author: str = "",
    publication_year: int | str | None = None,
    source_url: str = "",
    source_license: str = "",
    public_domain: bool | None = None,
    narrative_unit: str = "chapter",
    reveal_point: str | int | float = "",
    fair_play_status: str = "ambiguous",
    claims: Iterable[Mapping[str, Any]] = (),
    decisive_evidence: Iterable[Mapping[str, Any]] = (),
    manifest_file: str = "",
    validation_file: str = "",
    graph_file: str = "",
    notes: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a normalized fair-play detective story annotation."""

    if not str(story_id).strip():
        raise ValueError("detective story annotations require a non-empty story_id")
    if not str(title).strip():
        raise ValueError("detective story annotations require a non-empty title")
    if fair_play_status not in FAIR_PLAY_STATUSES:
        raise ValueError(f"unknown fair_play_status: {fair_play_status}")

    normalized_claims = [_normalize_claim(claim) for claim in claims]
    normalized_evidence = [_normalize_evidence(item) for item in decisive_evidence]
    payload: dict[str, Any] = {
        "annotation_kind": "epistemap_detective_story_annotation",
        "schema_version": "0.1",
        "story_id": str(story_id),
        "title": str(title),
        "author": str(author),
        "publication_year": "" if publication_year is None else publication_year,
        "source_url": str(source_url),
        "source_license": str(source_license),
        "public_domain": public_domain,
        "narrative_unit": str(narrative_unit),
        "reveal_point": "" if reveal_point is None else reveal_point,
        "fair_play_status": fair_play_status,
        "claims": normalized_claims,
        "decisive_evidence": normalized_evidence,
        "manifest_file": str(manifest_file),
        "validation_file": str(validation_file),
        "graph_file": str(graph_file),
        "notes": str(notes),
        "metadata": dict(metadata or {}),
    }
    return {key: value for key, value in payload.items() if not _blank(value)}


def write_detective_story_annotation(annotation: Mapping[str, Any], destination: str | Path | TextIO) -> None:
    """Write a detective story annotation as deterministic JSON."""

    text = json.dumps(dict(annotation), indent=2, sort_keys=True) + "\n"
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        return
    Path(destination).write_text(text, encoding="utf-8")


def read_detective_story_annotation(source: str | Path | TextIO) -> dict[str, Any]:
    """Read a detective story annotation from JSON."""

    if hasattr(source, "read"):
        text = source.read()  # type: ignore[union-attr]
    else:
        text = Path(source).read_text(encoding="utf-8")
    annotation = json.loads(text)
    if annotation.get("annotation_kind") != "epistemap_detective_story_annotation":
        raise ValueError("not an Epistemap detective story annotation")
    return annotation


def validate_detective_story_annotation(annotation: Mapping[str, Any]) -> dict[str, Any]:
    """Check whether a detective story annotation is ready for experiments."""

    findings: list[dict[str, Any]] = []
    if annotation.get("annotation_kind") != "epistemap_detective_story_annotation":
        findings.append(_finding("error", "unexpected_annotation_kind", field="annotation_kind"))
    for field in ("story_id", "title", "narrative_unit", "reveal_point", "fair_play_status"):
        if _blank(annotation.get(field)):
            findings.append(_finding("error", "missing_required_annotation_field", field=field))
    if annotation.get("fair_play_status") not in FAIR_PLAY_STATUSES:
        findings.append(_finding("error", "unknown_fair_play_status", field="fair_play_status"))

    claims = list(annotation.get("claims", []) or [])
    evidence = list(annotation.get("decisive_evidence", []) or [])
    claim_ids = {str(claim.get("claim_id", "")) for claim in claims if not _blank(claim.get("claim_id"))}
    false_claim_ids = {
        str(claim.get("claim_id", ""))
        for claim in claims
        if claim.get("truth_status") in {"false", "misleading", "contradicted"}
    }

    if not claims:
        findings.append(_finding("error", "missing_claim_annotations", field="claims"))
    if not false_claim_ids:
        findings.append(_finding("warning", "missing_false_claim_annotation", field="claims"))
    if not evidence:
        findings.append(_finding("error", "missing_decisive_evidence", field="decisive_evidence"))

    for claim in claims:
        claim_id = str(claim.get("claim_id", ""))
        for field in ("claim_id", "text", "truth_status"):
            if _blank(claim.get(field)):
                findings.append(_finding("error", "missing_claim_field", claim_id=claim_id, field=field))
        if claim.get("truth_status") not in {"true", "false", "misleading", "unknown", "contradicted"}:
            findings.append(_finding("warning", "unknown_claim_truth_status", claim_id=claim_id, field="truth_status"))

    for item in evidence:
        evidence_id = str(item.get("evidence_id", ""))
        for field in ("evidence_id", "text", "available_at", "contradicts_claim_id"):
            if _blank(item.get(field)):
                findings.append(_finding("error", "missing_evidence_field", evidence_id=evidence_id, field=field))
        claim_id = str(item.get("contradicts_claim_id", ""))
        if claim_id and claim_id not in claim_ids:
            findings.append(
                _finding(
                    "error",
                    "evidence_references_unknown_claim",
                    evidence_id=evidence_id,
                    claim_id=claim_id,
                )
            )
        if claim_id in claim_ids and claim_id not in false_claim_ids:
            findings.append(
                _finding(
                    "warning",
                    "decisive_evidence_targets_nonfalse_claim",
                    evidence_id=evidence_id,
                    claim_id=claim_id,
                )
            )
        if _point_is_after(item.get("available_at"), annotation.get("reveal_point")):
            findings.append(
                _finding(
                    "warning",
                    "decisive_evidence_after_reveal",
                    evidence_id=evidence_id,
                    available_at=item.get("available_at"),
                    reveal_point=annotation.get("reveal_point"),
                )
            )
        if item.get("access_scope") in {"detective_only", "hidden", "withheld", "private"}:
            findings.append(
                _finding(
                    "warning",
                    "decisive_evidence_not_reader_available",
                    evidence_id=evidence_id,
                    access_scope=item.get("access_scope"),
                )
            )

    for field in ("manifest_file", "validation_file", "graph_file"):
        if _blank(annotation.get(field)):
            findings.append(_finding("info", "missing_sidecar_reference", field=field))

    severity_counts = _severity_counts(findings)
    return {
        "report_kind": "epistemap_detective_story_annotation_validation",
        "story_id": str(annotation.get("story_id", "")),
        "summary": {
            "status": "error" if severity_counts["error"] else "warning" if severity_counts["warning"] else "pass",
            "finding_count": len(findings),
            "claim_count": len(claims),
            "false_claim_count": len(false_claim_ids),
            "decisive_evidence_count": len(evidence),
            **severity_counts,
        },
        "findings": findings,
    }


def detective_recognition_g_row(
    annotation: Mapping[str, Any],
    *,
    claim_id: str,
    y: int,
    p: float,
    env: str,
    run_id: str = "",
    subject_id: str = "",
    condition: str = "",
    phase: str = "",
    answer: str = "",
    response: str = "",
    recognized_at: str | int | float | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a canonical G row for a detective contradiction-recognition item."""

    claim = _claim_by_id(annotation, claim_id)
    evidence = _first_evidence_for_claim(annotation, claim_id)
    contradiction_available_at = evidence.get("available_at", "") if evidence else ""
    recognized = recognized_at if recognized_at is not None else ""
    return g_evaluation_row(
        y=y,
        p=p,
        env=env,
        run_id=run_id,
        subject_id=subject_id,
        condition=condition,
        phase=phase,
        item_id=str(annotation.get("story_id", "")),
        claim_id=claim_id,
        answer=answer or str(claim.get("truth_status", "")),
        response=response,
        source_anchor=str(claim.get("narrative_anchor", "")),
        recognized_at=recognized,
        contradiction_available_at=contradiction_available_at,
        recognition_lag=_lag(contradiction_available_at, recognized),
        fair_play_rating=str(annotation.get("fair_play_status", "")),
        metadata={
            "evaluation_target": "detective_contradiction_recognition",
            "story_id": str(annotation.get("story_id", "")),
            "story_title": str(annotation.get("title", "")),
            "reveal_point": annotation.get("reveal_point", ""),
            "decisive_evidence_id": evidence.get("evidence_id", "") if evidence else "",
            **dict(metadata or {}),
        },
    )


def detective_corpus_summary(annotations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize an annotation set for experiment planning."""

    rows = list(annotations)
    validation_reports = [validate_detective_story_annotation(row) for row in rows]
    status_counts: dict[str, int] = {}
    fair_play_counts: dict[str, int] = {}
    for annotation, report in zip(rows, validation_reports):
        status = str(report["summary"]["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
        fair_play = str(annotation.get("fair_play_status", ""))
        fair_play_counts[fair_play] = fair_play_counts.get(fair_play, 0) + 1
    return {
        "summary_kind": "epistemap_detective_corpus_summary",
        "story_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "fair_play_status_counts": dict(sorted(fair_play_counts.items())),
        "claim_count": sum(len(annotation.get("claims", []) or []) for annotation in rows),
        "decisive_evidence_count": sum(len(annotation.get("decisive_evidence", []) or []) for annotation in rows),
        "annotations": [
            {
                "story_id": annotation.get("story_id", ""),
                "title": annotation.get("title", ""),
                "fair_play_status": annotation.get("fair_play_status", ""),
                "validation_status": report["summary"]["status"],
                "finding_count": report["summary"]["finding_count"],
            }
            for annotation, report in zip(rows, validation_reports)
        ],
    }


def detective_annotation_graph_bundle(annotation: Mapping[str, Any]) -> GraphBundle:
    """Convert a detective story annotation into a temporal graph bundle."""

    story_id = str(annotation.get("story_id", ""))
    story_title = str(annotation.get("title", ""))
    provenance = _annotation_provenance(annotation)
    nodes: list[Node] = [
        Node(
            id=story_id,
            type="story",
            title=story_title,
            description=str(annotation.get("notes", "")),
            status=str(annotation.get("fair_play_status", "")),
            provenance=provenance,
            metadata={
                "publication_year": annotation.get("publication_year", ""),
                "public_domain": annotation.get("public_domain", ""),
                "source_license": annotation.get("source_license", ""),
                "narrative_unit": annotation.get("narrative_unit", ""),
                "reveal_point": annotation.get("reveal_point", ""),
                **dict(annotation.get("metadata", {}) or {}),
            },
        )
    ]
    edges: list[Edge] = []

    for claim in annotation.get("claims", []) or []:
        claim_id = str(claim.get("claim_id", ""))
        nodes.append(
            Node(
                id=claim_id,
                type="claim",
                title=str(claim.get("text", "")),
                description=str(claim.get("notes", "")),
                status=str(claim.get("truth_status", "")),
                provenance=provenance,
                metadata={
                    "speaker": claim.get("speaker", ""),
                    "truth_status": claim.get("truth_status", ""),
                    "narrative_anchor": claim.get("narrative_anchor", ""),
                    "introduced_at": claim.get("introduced_at", ""),
                    "story_id": story_id,
                    **dict(claim.get("metadata", {}) or {}),
                },
            )
        )
        edges.append(
            Edge(
                id=f"edge::{story_id}::contains::{claim_id}",
                source=story_id,
                target=claim_id,
                type="contains_claim",
                title="Story contains claim",
                provenance=provenance,
                metadata={
                    "story_id": story_id,
                    "introduced_at": claim.get("introduced_at", ""),
                },
            )
        )

    for item in annotation.get("decisive_evidence", []) or []:
        evidence_id = str(item.get("evidence_id", ""))
        claim_id = str(item.get("contradicts_claim_id", ""))
        nodes.append(
            Node(
                id=evidence_id,
                type="evidence",
                title=str(item.get("text", "")),
                description=str(item.get("notes", "")),
                status=str(item.get("access_scope", "")),
                provenance=provenance,
                metadata={
                    "available_at": item.get("available_at", ""),
                    "narrative_anchor": item.get("narrative_anchor", ""),
                    "access_scope": item.get("access_scope", "reader_available"),
                    "story_id": story_id,
                    **dict(item.get("metadata", {}) or {}),
                },
            )
        )
        edges.extend(
            [
                Edge(
                    id=f"edge::{story_id}::contains::{evidence_id}",
                    source=story_id,
                    target=evidence_id,
                    type="contains_evidence",
                    title="Story contains decisive evidence",
                    provenance=provenance,
                    metadata={
                        "story_id": story_id,
                        "available_at": item.get("available_at", ""),
                    },
                ),
                Edge(
                    id=f"edge::{evidence_id}::contradicts::{claim_id}",
                    source=evidence_id,
                    target=claim_id,
                    type="contradicts",
                    title="Evidence contradicts claim",
                    justification=str(item.get("text", "")),
                    evidence_ids=[evidence_id],
                    provenance=provenance,
                    metadata={
                        "available_at": item.get("available_at", ""),
                        "narrative_anchor": item.get("narrative_anchor", ""),
                        "access_scope": item.get("access_scope", "reader_available"),
                        "story_id": story_id,
                    },
                ),
            ]
        )

    return GraphBundle(
        graph_id=f"{story_id}::detective-annotation-graph",
        title=story_title,
        description=f"Temporal graph derived from detective annotation {story_id}",
        nodes=nodes,
        edges=edges,
        metadata={
            "annotation_kind": annotation.get("annotation_kind", ""),
            "schema_version": annotation.get("schema_version", ""),
            "story_id": story_id,
            "fair_play_status": annotation.get("fair_play_status", ""),
            "reveal_point": annotation.get("reveal_point", ""),
            "narrative_unit": annotation.get("narrative_unit", ""),
            "summary": {
                "claim_count": len(annotation.get("claims", []) or []),
                "decisive_evidence_count": len(annotation.get("decisive_evidence", []) or []),
            },
        },
    )


def detective_annotation_fair_play_diagnostic(annotation: Mapping[str, Any]) -> dict[str, Any]:
    """Run temporal fair-play checks for false or misleading annotation claims."""

    graph = detective_annotation_graph_bundle(annotation)
    claim_ids = [
        str(claim.get("claim_id", ""))
        for claim in annotation.get("claims", []) or []
        if claim.get("truth_status") in {"false", "misleading", "contradicted"}
    ]
    report = fair_play_diagnostic(graph, claim_ids=claim_ids, reveal_at=annotation.get("reveal_point"))
    report["annotation"] = {
        "story_id": annotation.get("story_id", ""),
        "title": annotation.get("title", ""),
        "fair_play_status": annotation.get("fair_play_status", ""),
        "graph_id": graph.graph_id,
    }
    return report


def _normalize_claim(claim: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "claim_id": str(claim.get("claim_id", "")),
        "text": str(claim.get("text", "")),
        "speaker": str(claim.get("speaker", "")),
        "truth_status": str(claim.get("truth_status", "unknown")),
        "narrative_anchor": str(claim.get("narrative_anchor", "")),
        "introduced_at": claim.get("introduced_at", ""),
        "notes": str(claim.get("notes", "")),
        "metadata": dict(claim.get("metadata", {}) or {}),
    }


def _normalize_evidence(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": str(item.get("evidence_id", "")),
        "text": str(item.get("text", "")),
        "contradicts_claim_id": str(item.get("contradicts_claim_id", "")),
        "available_at": item.get("available_at", ""),
        "narrative_anchor": str(item.get("narrative_anchor", "")),
        "access_scope": str(item.get("access_scope", "reader_available")),
        "notes": str(item.get("notes", "")),
        "metadata": dict(item.get("metadata", {}) or {}),
    }


def _annotation_provenance(annotation: Mapping[str, Any]) -> list[ProvenanceRef]:
    return [
        ProvenanceRef(
            source_id=str(annotation.get("story_id", "")),
            artifact_id=str(annotation.get("title", "")),
            source_url=str(annotation.get("source_url", "")),
            support_kind="detective_story_annotation",
            grounding_status=str(annotation.get("metadata", {}).get("annotation_status", "")),
            metadata={
                "author": annotation.get("author", ""),
                "publication_year": annotation.get("publication_year", ""),
                "source_license": annotation.get("source_license", ""),
                "public_domain": annotation.get("public_domain", ""),
            },
        )
    ]


def _claim_by_id(annotation: Mapping[str, Any], claim_id: str) -> dict[str, Any]:
    for claim in annotation.get("claims", []) or []:
        if str(claim.get("claim_id", "")) == claim_id:
            return dict(claim)
    raise KeyError(f"unknown claim_id: {claim_id}")


def _first_evidence_for_claim(annotation: Mapping[str, Any], claim_id: str) -> dict[str, Any]:
    candidates = [
        dict(item)
        for item in annotation.get("decisive_evidence", []) or []
        if str(item.get("contradicts_claim_id", "")) == claim_id
    ]
    if not candidates:
        return {}
    return sorted(candidates, key=lambda item: _point_key(item.get("available_at")))[0]


def _point_is_after(left: Any, right: Any) -> bool:
    left_key = _point_key(left)
    right_key = _point_key(right)
    if left_key[0] != right_key[0]:
        return False
    return left_key[1] > right_key[1]


def _lag(start: Any, end: Any) -> float | str:
    if _blank(start) or _blank(end):
        return ""
    start_key = _point_key(start)
    end_key = _point_key(end)
    if start_key[0] != end_key[0]:
        return ""
    return end_key[1] - start_key[1]


def _point_key(value: Any) -> tuple[str, float | str]:
    if isinstance(value, (int, float)):
        return ("number", float(value))
    text = str(value).strip()
    try:
        return ("number", float(text))
    except ValueError:
        return ("text", text)


def _severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "error": sum(1 for finding in findings if finding["severity"] == "error"),
        "warning": sum(1 for finding in findings if finding["severity"] == "warning"),
        "info": sum(1 for finding in findings if finding["severity"] == "info"),
    }


def _finding(severity: str, code: str, **payload: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, **payload}


def _blank(value: Any) -> bool:
    return value in ("", None, [], {})

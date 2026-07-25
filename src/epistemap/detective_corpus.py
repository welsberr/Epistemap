from __future__ import annotations

import csv
import json
import random
import re
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

from .grounding_effect import G_ROW_FIELDS, g_evaluation_row
from .grounding_effect import g_experiment_manifest, write_g_experiment_manifest
from .io import write_graph_bundle
from .models import Edge, GraphBundle, Node, ProvenanceRef
from .temporal import fair_play_diagnostic

FAIR_PLAY_STATUSES = {
    "fair_play",
    "late_decisive_evidence",
    "withheld_decisive_evidence",
    "ambiguous",
    "excluded",
}
DETECTIVE_G_TEMPLATE_EXTRA_FIELDS = (
    "experiment_id",
    "evaluation_target",
    "story_title",
    "fair_play_status",
    "graph_file",
    "fair_play_diagnostic_file",
    "template_role",
)
DETECTIVE_G_TEMPLATE_FIELDS = G_ROW_FIELDS + DETECTIVE_G_TEMPLATE_EXTRA_FIELDS
DETECTIVE_BLINDED_RUN_FIELDS = (
    "run_id",
    "subject_id",
    "story_title",
    "phase",
    "item_id",
    "source_anchor",
    "y",
    "p",
    "answer",
    "response",
    "recognized_at",
    "row_key",
)
DETECTIVE_ANCHOR_REVIEW_FIELDS = (
    "story_id",
    "story_title",
    "source_url",
    "artifact_kind",
    "artifact_id",
    "current_narrative_anchor",
    "text",
    "reviewed_source_locator",
    "reviewed_source_quote",
    "reviewed_narrative_anchor",
    "review_status",
    "reviewer",
    "reviewed_at",
    "notes",
)


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


def write_detective_annotation_sidecars(
    annotation: Mapping[str, Any],
    out_dir: str | Path,
    *,
    slug: str | None = None,
) -> dict[str, Any]:
    """Write graph and diagnostic sidecars for a detective annotation."""

    story_slug = slug or _story_slug(annotation)
    target_dir = Path(out_dir) / story_slug
    graph_path = target_dir / "epistemap_graph.json"
    diagnostic_path = target_dir / "fair_play_diagnostic.json"

    graph = detective_annotation_graph_bundle(annotation)
    diagnostic = detective_annotation_fair_play_diagnostic(annotation)
    write_graph_bundle(graph, graph_path)
    _write_json(diagnostic, diagnostic_path)
    return {
        "story_id": annotation.get("story_id", ""),
        "title": annotation.get("title", ""),
        "fair_play_status": annotation.get("fair_play_status", ""),
        "graph_file": str(graph_path),
        "fair_play_diagnostic_file": str(diagnostic_path),
        "fair_play_rating": diagnostic.get("rating", ""),
    }


def write_detective_corpus_sidecars(
    annotation_sources: Iterable[str | Path],
    out_dir: str | Path,
) -> dict[str, Any]:
    """Write graph and diagnostic sidecars for annotation JSON files."""

    rows = [
        write_detective_annotation_sidecars(read_detective_story_annotation(source), out_dir)
        for source in annotation_sources
    ]
    fair_play_counts: dict[str, int] = {}
    rating_counts: dict[str, int] = {}
    for row in rows:
        fair_play = str(row.get("fair_play_status", ""))
        rating = str(row.get("fair_play_rating", ""))
        fair_play_counts[fair_play] = fair_play_counts.get(fair_play, 0) + 1
        rating_counts[rating] = rating_counts.get(rating, 0) + 1
    manifest = {
        "sidecar_manifest_kind": "epistemap_detective_corpus_sidecars",
        "sidecar_count": len(rows),
        "out_dir": str(out_dir),
        "fair_play_status_counts": dict(sorted(fair_play_counts.items())),
        "fair_play_rating_counts": dict(sorted(rating_counts.items())),
        "sidecars": rows,
    }
    _write_json(manifest, Path(out_dir) / "detective_corpus_sidecars.json")
    return manifest


def detective_anchor_review_template(annotation: Mapping[str, Any]) -> dict[str, Any]:
    """Build blank human-review rows for claim and evidence source anchors."""

    rows: list[dict[str, Any]] = []
    story_id = str(annotation.get("story_id", ""))
    story_title = str(annotation.get("title", ""))
    source_url = str(annotation.get("source_url", ""))
    for claim in annotation.get("claims", []) or []:
        review = _anchor_review_metadata(claim)
        rows.append(
            {
                "story_id": story_id,
                "story_title": story_title,
                "source_url": source_url,
                "artifact_kind": "claim",
                "artifact_id": str(claim.get("claim_id", "")),
                "current_narrative_anchor": str(claim.get("narrative_anchor", "")),
                "text": str(claim.get("text", "")),
                "reviewed_source_locator": str(review.get("reviewed_source_locator", "")),
                "reviewed_source_quote": str(review.get("reviewed_source_quote", "")),
                "reviewed_narrative_anchor": str(review.get("reviewed_narrative_anchor", "")),
                "review_status": str(review.get("review_status", "needs_review") or "needs_review"),
                "reviewer": str(review.get("reviewer", "")),
                "reviewed_at": str(review.get("reviewed_at", "")),
                "notes": str(claim.get("notes", "")),
            }
        )
    for item in annotation.get("decisive_evidence", []) or []:
        review = _anchor_review_metadata(item)
        rows.append(
            {
                "story_id": story_id,
                "story_title": story_title,
                "source_url": source_url,
                "artifact_kind": "decisive_evidence",
                "artifact_id": str(item.get("evidence_id", "")),
                "current_narrative_anchor": str(item.get("narrative_anchor", "")),
                "text": str(item.get("text", "")),
                "reviewed_source_locator": str(review.get("reviewed_source_locator", "")),
                "reviewed_source_quote": str(review.get("reviewed_source_quote", "")),
                "reviewed_narrative_anchor": str(review.get("reviewed_narrative_anchor", "")),
                "review_status": str(review.get("review_status", "needs_review") or "needs_review"),
                "reviewer": str(review.get("reviewer", "")),
                "reviewed_at": str(review.get("reviewed_at", "")),
                "notes": str(item.get("notes", "")),
            }
        )
    return {
        "template_kind": "epistemap_detective_anchor_review_template",
        "schema_version": "0.1",
        "story_id": story_id,
        "row_count": len(rows),
        "fields": list(DETECTIVE_ANCHOR_REVIEW_FIELDS),
        "rows": rows,
    }


def detective_corpus_anchor_review_template(annotations: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a combined human-review template for detective corpus anchors."""

    templates = [detective_anchor_review_template(annotation) for annotation in annotations]
    rows = [row for template in templates for row in template["rows"]]
    return {
        "template_kind": "epistemap_detective_corpus_anchor_review_template",
        "schema_version": "0.1",
        "story_count": len(templates),
        "row_count": len(rows),
        "fields": list(DETECTIVE_ANCHOR_REVIEW_FIELDS),
        "rows": rows,
    }


def detective_anchor_review_template_csv(template: Mapping[str, Any]) -> str:
    """Serialize a detective anchor-review template to deterministic CSV."""

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(DETECTIVE_ANCHOR_REVIEW_FIELDS),
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(list(template.get("rows", []) or []))
    return output.getvalue()


def write_detective_anchor_review_template_csv(template: Mapping[str, Any], destination: str | Path | TextIO) -> None:
    """Write a detective anchor-review template CSV."""

    text = detective_anchor_review_template_csv(template)
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        return
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def apply_detective_anchor_review(
    annotation: Mapping[str, Any],
    review_rows: Iterable[Mapping[str, Any]],
    *,
    review_source: str = "",
) -> dict[str, Any]:
    """Apply completed anchor-review rows to a detective annotation payload."""

    review_by_id = {
        str(row.get("artifact_id", "")): dict(row)
        for row in review_rows
        if str(row.get("artifact_id", "")).strip()
    }
    payload = json.loads(json.dumps(dict(annotation)))
    applied = 0
    missing: list[str] = []
    reviewers: set[str] = set()
    reviewed_dates: set[str] = set()
    for collection, id_key in (("claims", "claim_id"), ("decisive_evidence", "evidence_id")):
        for item in payload.get(collection, []) or []:
            artifact_id = str(item.get(id_key, ""))
            row = review_by_id.get(artifact_id)
            if row is None:
                missing.append(artifact_id)
                continue
            metadata = dict(item.get("metadata", {}) or {})
            metadata["anchor_review"] = _review_row_metadata(row)
            item["metadata"] = metadata
            reviewed_anchor = str(row.get("reviewed_narrative_anchor", "")).strip()
            if reviewed_anchor:
                item["narrative_anchor"] = reviewed_anchor
            if str(row.get("reviewer", "")).strip():
                reviewers.add(str(row.get("reviewer", "")))
            if str(row.get("reviewed_at", "")).strip():
                reviewed_dates.add(str(row.get("reviewed_at", "")))
            applied += 1

    metadata = dict(payload.get("metadata", {}) or {})
    metadata["annotation_status"] = "human_anchor_reviewed" if applied and not missing else "anchor_review_incomplete"
    metadata["anchor_review"] = {
        "review_status": "reviewed" if applied and not missing else "incomplete",
        "reviewed_at": sorted(reviewed_dates)[-1] if reviewed_dates else "",
        "review_row_count": applied,
        "missing_row_count": len(missing),
        "reviewers": sorted(reviewers),
        "source_file": review_source,
    }
    payload["metadata"] = metadata
    return {
        "annotation": payload,
        "summary": {
            "story_id": str(payload.get("story_id", "")),
            "applied_row_count": applied,
            "missing_row_count": len(missing),
            "missing_artifact_ids": missing,
            "status": "reviewed" if applied and not missing else "incomplete",
        },
    }


def apply_detective_anchor_review_csv(
    annotation_sources: Iterable[str | Path],
    review_csv: str | Path,
    *,
    out_dir: str | Path | None = None,
    in_place: bool = False,
) -> dict[str, Any]:
    """Apply a completed anchor-review CSV to annotation JSON files."""

    if out_dir is None and not in_place:
        raise ValueError("apply_detective_anchor_review_csv requires out_dir or in_place=True")
    review_path = Path(review_csv)
    with review_path.open(encoding="utf-8", newline="") as handle:
        review_rows = list(csv.DictReader(handle))
    rows: list[dict[str, Any]] = []
    for source in annotation_sources:
        source_path = Path(source)
        result = apply_detective_anchor_review(
            read_detective_story_annotation(source_path),
            review_rows,
            review_source=str(review_path),
        )
        destination = source_path if in_place else Path(out_dir) / source_path.name  # type: ignore[arg-type]
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        write_detective_story_annotation(result["annotation"], destination)
        rows.append(
            {
                **result["summary"],
                "source_file": str(source_path),
                "output_file": str(destination),
            }
        )
    return {
        "report_kind": "epistemap_detective_anchor_review_application",
        "review_file": str(review_path),
        "annotation_count": len(rows),
        "applied_row_count": sum(row["applied_row_count"] for row in rows),
        "missing_row_count": sum(row["missing_row_count"] for row in rows),
        "annotations": rows,
    }


def detective_g_collection_template(
    treatment_manifest: Mapping[str, Any],
    corpus_sidecar_manifest: Mapping[str, Any],
    *,
    env: str = "K",
    include_controls: bool = True,
    sidecar_base_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build blank row templates for detective contradiction-recognition collection."""

    admit_ratings = {
        str(item)
        for item in treatment_manifest.get("fair_play_policy", {}).get("admit_ratings", [])
    }
    control_ratings = {
        str(item)
        for item in treatment_manifest.get("fair_play_policy", {}).get("control_ratings", [])
    }
    allowed_ratings = set(admit_ratings)
    if include_controls:
        allowed_ratings.update(control_ratings)

    rows: list[dict[str, Any]] = []
    treatments = list(treatment_manifest.get("treatments", []) or [])
    phases = list(treatment_manifest.get("phases", []) or [])
    for sidecar in corpus_sidecar_manifest.get("sidecars", []) or []:
        rating = str(sidecar.get("fair_play_rating", ""))
        if allowed_ratings and rating not in allowed_ratings:
            continue
        diagnostic = _read_json(_resolve_sidecar_path(sidecar.get("fair_play_diagnostic_file", ""), sidecar_base_dir))
        graph_nodes = _graph_nodes_by_id(sidecar.get("graph_file", ""), sidecar_base_dir)
        for claim in diagnostic.get("claims", []) or []:
            claim_id = str(claim.get("claim_id", ""))
            claim_node = graph_nodes.get(claim_id, {})
            for treatment in treatments:
                for phase in phases:
                    rows.append(
                        {
                            "run_id": "",
                            "subject_id": "",
                            "condition": str(treatment.get("condition", "")),
                            "phase": str(phase),
                            "item_id": str(sidecar.get("story_id", "")),
                            "claim_id": claim_id,
                            "env": str(env),
                            "y": "",
                            "p": "",
                            "answer": "",
                            "response": "",
                            "source_anchor": _node_source_anchor(claim_node),
                            "recognized_at": "",
                            "contradiction_available_at": claim.get("first_decisive_evidence", {}).get("time", ""),
                            "recognition_lag": "",
                            "fair_play_rating": rating,
                            "experiment_id": str(treatment_manifest.get("experiment_id", "")),
                            "evaluation_target": str(treatment_manifest.get("evaluation_target", "")),
                            "story_title": str(sidecar.get("title", "")),
                            "fair_play_status": str(sidecar.get("fair_play_status", "")),
                            "graph_file": str(sidecar.get("graph_file", "")),
                            "fair_play_diagnostic_file": str(sidecar.get("fair_play_diagnostic_file", "")),
                            "template_role": "control" if rating in control_ratings else "primary",
                        }
                    )
    return {
        "template_kind": "epistemap_detective_g_collection_template",
        "schema_version": "0.1",
        "experiment_id": str(treatment_manifest.get("experiment_id", "")),
        "evaluation_target": str(treatment_manifest.get("evaluation_target", "")),
        "row_count": len(rows),
        "fields": list(DETECTIVE_G_TEMPLATE_FIELDS),
        "rows": rows,
    }


def detective_g_collection_template_csv(template: Mapping[str, Any]) -> str:
    """Serialize a detective G collection template to deterministic CSV."""

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(DETECTIVE_G_TEMPLATE_FIELDS), extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(list(template.get("rows", []) or []))
    return output.getvalue()


def write_detective_g_collection_template_csv(template: Mapping[str, Any], destination: str | Path | TextIO) -> None:
    """Write a detective G collection template CSV."""

    text = detective_g_collection_template_csv(template)
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        return
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def detective_g_run_sheets(
    rows: Iterable[Mapping[str, Any]],
    *,
    run_id_prefix: str,
    subject_prefix: str = "subject",
    subjects_per_condition: int = 1,
    conditions: Sequence[str] = (),
    phases: Sequence[str] = (),
    seed: int = 0,
) -> dict[str, Any]:
    """Build deterministic per-subject detective G collection sheets."""

    if not str(run_id_prefix).strip():
        raise ValueError("detective_g_run_sheets requires a non-empty run_id_prefix")
    if subjects_per_condition < 1:
        raise ValueError("subjects_per_condition must be at least 1")
    materialized = [dict(row) for row in rows]
    requested_conditions = [str(condition) for condition in conditions if str(condition)]
    selected_conditions = requested_conditions or sorted(
        {str(row.get("condition", "")) for row in materialized if str(row.get("condition", ""))}
    )
    selected_phase_set = {str(phase) for phase in phases if str(phase)}
    sheets: list[dict[str, Any]] = []
    for condition in selected_conditions:
        condition_rows = [
            row
            for row in materialized
            if str(row.get("condition", "")) == condition
            and (not selected_phase_set or str(row.get("phase", "")) in selected_phase_set)
        ]
        if not condition_rows:
            continue
        for subject_number in range(1, subjects_per_condition + 1):
            condition_slug = _slug(condition)
            subject_id = f"{subject_prefix}-{condition_slug}-{subject_number:02d}"
            run_id = f"{run_id_prefix}-{condition_slug}-{subject_number:02d}"
            sheet_rows = [dict(row, run_id=run_id, subject_id=subject_id) for row in condition_rows]
            rng = random.Random(f"{seed}:{condition}:{subject_number}")
            rng.shuffle(sheet_rows)
            sheets.append(
                {
                    "run_id": run_id,
                    "subject_id": subject_id,
                    "condition": condition,
                    "phases": sorted({str(row.get("phase", "")) for row in sheet_rows if str(row.get("phase", ""))}),
                    "row_count": len(sheet_rows),
                    "file_name": f"{run_id}.csv",
                    "rows": sheet_rows,
                }
            )
    return {
        "packet_kind": "epistemap_detective_g_run_sheets",
        "schema_version": "0.1",
        "run_id_prefix": str(run_id_prefix),
        "subject_prefix": str(subject_prefix),
        "subjects_per_condition": subjects_per_condition,
        "conditions": selected_conditions,
        "phases": sorted(selected_phase_set) if selected_phase_set else sorted(
            {str(row.get("phase", "")) for row in materialized if str(row.get("phase", ""))}
        ),
        "seed": seed,
        "sheet_count": len(sheets),
        "row_count": sum(sheet["row_count"] for sheet in sheets),
        "sheets": sheets,
    }


def write_detective_g_run_sheets_from_csv(
    template_csv: str | Path,
    out_dir: str | Path,
    *,
    run_id_prefix: str,
    subject_prefix: str = "subject",
    subjects_per_condition: int = 1,
    conditions: Sequence[str] = (),
    phases: Sequence[str] = (),
    seed: int = 0,
) -> dict[str, Any]:
    """Write per-subject detective G run sheets from a collection template CSV."""

    template_path = Path(template_csv)
    with template_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    packet = detective_g_run_sheets(
        rows,
        run_id_prefix=run_id_prefix,
        subject_prefix=subject_prefix,
        subjects_per_condition=subjects_per_condition,
        conditions=conditions,
        phases=phases,
        seed=seed,
    )
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_sheets = []
    for sheet in packet["sheets"]:
        sheet_path = target_dir / str(sheet["file_name"])
        write_detective_g_collection_rows_csv(sheet["rows"], sheet_path)
        manifest_sheets.append({key: value for key, value in sheet.items() if key != "rows"})
    manifest = {**packet, "template_file": str(template_path), "out_dir": str(target_dir), "sheets": manifest_sheets}
    manifest_path = target_dir / "detective_g_run_sheets.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def write_detective_g_collection_rows_csv(rows: Iterable[Mapping[str, Any]], destination: str | Path | TextIO) -> None:
    """Write detective G collection rows, preserving the detective template header."""

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(DETECTIVE_G_TEMPLATE_FIELDS), extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows([dict(row) for row in rows])
    text = output.getvalue()
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        return
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def write_blinded_detective_g_run_sheets(
    sources: Iterable[str | Path],
    out_dir: str | Path,
    *,
    key_file: str | Path | None = None,
) -> dict[str, Any]:
    """Write participant-safe run sheets plus a private key for rehydration."""

    source_paths = _expand_run_sheet_sources(sources)
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    key_rows: dict[str, dict[str, Any]] = {}
    sheets: list[dict[str, Any]] = []
    for source_path in source_paths:
        with source_path.open(encoding="utf-8", newline="") as handle:
            rows = [dict(row) for row in csv.DictReader(handle)]
        blinded_rows: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            row_key = str(row.get("row_key", "") or f"{row.get('run_id', source_path.stem)}::{index:03d}")
            canonical = dict(row)
            canonical["row_key"] = row_key
            key_rows[row_key] = canonical
            blinded_rows.append({field: canonical.get(field, "") for field in DETECTIVE_BLINDED_RUN_FIELDS})
        output_name = f"{source_path.stem}.blinded.csv"
        _write_dict_rows(blinded_rows, target_dir / output_name, DETECTIVE_BLINDED_RUN_FIELDS)
        sheets.append(
            {
                "source_file": str(source_path),
                "blinded_file": str(target_dir / output_name),
                "row_count": len(blinded_rows),
            }
        )
    key_path = Path(key_file) if key_file is not None else target_dir / "detective_g_blinding_key.json"
    key_payload = {
        "key_kind": "epistemap_detective_g_blinding_key",
        "schema_version": "0.1",
        "source_count": len(source_paths),
        "row_count": len(key_rows),
        "rows_by_key": key_rows,
    }
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps(key_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "packet_kind": "epistemap_detective_g_blinded_run_sheets",
        "schema_version": "0.1",
        "source_count": len(source_paths),
        "sheet_count": len(sheets),
        "row_count": sum(sheet["row_count"] for sheet in sheets),
        "out_dir": str(target_dir),
        "key_file": str(key_path),
        "sheets": sheets,
    }


def unblind_detective_g_run_sheets(
    sources: Iterable[str | Path],
    key_file: str | Path,
    destination: str | Path | TextIO,
    *,
    require_completed: bool = True,
) -> dict[str, Any]:
    """Rehydrate completed blinded sheets into canonical detective G rows."""

    key_payload = json.loads(Path(key_file).read_text(encoding="utf-8"))
    rows_by_key = key_payload.get("rows_by_key", {})
    if not isinstance(rows_by_key, Mapping):
        raise ValueError("invalid detective G blinding key")
    source_paths = _expand_run_sheet_sources(sources)
    rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    for source_path in source_paths:
        with source_path.open(encoding="utf-8", newline="") as handle:
            source_rows = [dict(row) for row in csv.DictReader(handle)]
        inputs.append({"source_file": str(source_path), "row_count": len(source_rows)})
        for index, public_row in enumerate(source_rows, start=1):
            row_key = str(public_row.get("row_key", ""))
            canonical = rows_by_key.get(row_key)
            if not isinstance(canonical, Mapping):
                findings.append(_finding("error", "unknown_blinded_row_key", source_file=str(source_path), index=index, row_key=row_key))
                continue
            row = dict(canonical)
            for field in ("y", "p", "answer", "response", "recognized_at"):
                row[field] = public_row.get(field, "")
            row["recognition_lag"] = _lag(row.get("contradiction_available_at"), row.get("recognized_at"))
            rows.append(row)
    write_detective_g_collection_rows_csv(rows, destination)
    validation = validate_detective_g_collection_rows(rows, require_completed=require_completed)
    all_findings = list(validation["findings"]) + findings
    severity_counts = _severity_counts(all_findings)
    validation = {
        **validation,
        "summary": {
            "status": "error" if severity_counts["error"] else "warning" if severity_counts["warning"] else "pass",
            "finding_count": len(all_findings),
            **severity_counts,
        },
        "findings": all_findings,
    }
    return {
        "report_kind": "epistemap_detective_g_blinded_run_sheet_unblind",
        "source_count": len(source_paths),
        "row_count": len(rows),
        "output_file": str(destination) if not hasattr(destination, "write") else "",
        "key_file": str(key_file),
        "require_completed": require_completed,
        "inputs": inputs,
        "validation": validation,
    }


def merge_detective_g_run_sheets(
    sources: Iterable[str | Path],
    destination: str | Path | TextIO,
    *,
    require_completed: bool = True,
) -> dict[str, Any]:
    """Merge per-subject detective G run sheets into one canonical rows CSV."""

    source_paths = _expand_run_sheet_sources(sources)
    rows: list[dict[str, Any]] = []
    inputs: list[dict[str, Any]] = []
    seen: dict[tuple[str, str, str, str, str, str], str] = {}
    duplicate_findings: list[dict[str, Any]] = []
    for source_path in source_paths:
        with source_path.open(encoding="utf-8", newline="") as handle:
            source_rows = [dict(row) for row in csv.DictReader(handle)]
        inputs.append({"source_file": str(source_path), "row_count": len(source_rows)})
        for row in source_rows:
            key = (
                str(row.get("run_id", "")),
                str(row.get("subject_id", "")),
                str(row.get("condition", "")),
                str(row.get("phase", "")),
                str(row.get("item_id", "")),
                str(row.get("claim_id", "")),
            )
            if key in seen:
                duplicate_findings.append(
                    _finding(
                        "error",
                        "duplicate_run_sheet_row",
                        source_file=str(source_path),
                        previous_source_file=seen[key],
                        run_id=key[0],
                        subject_id=key[1],
                        condition=key[2],
                        phase=key[3],
                        item_id=key[4],
                        claim_id=key[5],
                    )
                )
            else:
                seen[key] = str(source_path)
            rows.append(row)
    write_detective_g_collection_rows_csv(rows, destination)
    validation = validate_detective_g_collection_rows(rows, require_completed=require_completed)
    findings = list(validation["findings"]) + duplicate_findings
    severity_counts = _severity_counts(findings)
    validation = {
        **validation,
        "summary": {
            "status": "error" if severity_counts["error"] else "warning" if severity_counts["warning"] else "pass",
            "finding_count": len(findings),
            **severity_counts,
        },
        "findings": findings,
    }
    return {
        "report_kind": "epistemap_detective_g_run_sheet_merge",
        "source_count": len(source_paths),
        "row_count": len(rows),
        "output_file": str(destination) if not hasattr(destination, "write") else "",
        "require_completed": require_completed,
        "inputs": inputs,
        "validation": validation,
    }


def validate_detective_g_collection_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    require_completed: bool = True,
) -> dict[str, Any]:
    """Validate detective contradiction-recognition rows before G summarization."""

    materialized = [dict(row) for row in rows]
    findings: list[dict[str, Any]] = []
    required_identity_fields = (
        "condition",
        "phase",
        "item_id",
        "claim_id",
        "env",
        "source_anchor",
        "contradiction_available_at",
        "fair_play_rating",
    )
    completed_fields = ("y", "p")
    for index, row in enumerate(materialized, start=1):
        row_ref = _row_ref(index, row)
        for field in required_identity_fields:
            if _blank(row.get(field)):
                findings.append(_finding("error", "missing_required_g_collection_field", row=row_ref, field=field))
        if require_completed:
            for field in completed_fields:
                if _blank(row.get(field)):
                    findings.append(_finding("error", "missing_completed_g_field", row=row_ref, field=field))
        if not _blank(row.get("y")) and str(row.get("y")) not in {"0", "1"}:
            findings.append(_finding("error", "invalid_y_value", row=row_ref, value=row.get("y")))
        if not _blank(row.get("p")):
            probability = _float_or_none(row.get("p"))
            if probability is None or probability < 0.0 or probability > 1.0:
                findings.append(_finding("error", "invalid_probability_value", row=row_ref, value=row.get("p")))
        if require_completed and _blank(row.get("response")):
            findings.append(_finding("warning", "missing_response_text", row=row_ref))
        if str(row.get("y", "")) == "1" and _blank(row.get("recognized_at")):
            findings.append(_finding("warning", "positive_recognition_missing_time", row=row_ref))
        expected_lag = _lag(row.get("contradiction_available_at"), row.get("recognized_at"))
        if expected_lag != "" and _blank(row.get("recognition_lag")):
            findings.append(_finding("warning", "missing_recognition_lag", row=row_ref, expected=expected_lag))
        elif expected_lag != "" and _float_or_none(row.get("recognition_lag")) != expected_lag:
            findings.append(
                _finding(
                    "warning",
                    "recognition_lag_mismatch",
                    row=row_ref,
                    expected=expected_lag,
                    actual=row.get("recognition_lag"),
                )
            )

    severity_counts = _severity_counts(findings)
    return {
        "report_kind": "epistemap_detective_g_collection_validation",
        "row_count": len(materialized),
        "require_completed": require_completed,
        "summary": {
            "status": "error" if severity_counts["error"] else "warning" if severity_counts["warning"] else "pass",
            "finding_count": len(findings),
            **severity_counts,
        },
        "findings": findings,
    }


def validate_detective_g_collection_csv(source: str | Path | TextIO, *, require_completed: bool = True) -> dict[str, Any]:
    """Read and validate a detective contradiction-recognition CSV."""

    if hasattr(source, "read"):
        text = source.read()  # type: ignore[union-attr]
    else:
        text = Path(source).read_text(encoding="utf-8")
    rows = list(csv.DictReader(StringIO(text)))
    return validate_detective_g_collection_rows(rows, require_completed=require_completed)


def detective_g_experiment_manifest_from_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    experiment_id: str,
    row_file: str,
    name: str = "",
    corpus: str = "",
    evaluation_target: str = "detective_contradiction_recognition",
    reliability_treatment: str = "",
    temporal_assumptions: Mapping[str, Any] | None = None,
    fair_play_policy: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a G experiment manifest from detective collection rows."""

    materialized = [dict(row) for row in rows]
    conditions = sorted({str(row.get("condition", "")) for row in materialized if str(row.get("condition", ""))})
    phases = sorted({str(row.get("phase", "")) for row in materialized if str(row.get("phase", ""))})
    return g_experiment_manifest(
        experiment_id=experiment_id,
        row_file=row_file,
        evaluation_target=evaluation_target,
        name=name,
        corpus=corpus,
        conditions=conditions,
        phases=phases,
        reliability_treatment=reliability_treatment,
        temporal_assumptions=temporal_assumptions or {"name": "narrative_timestep_recognition_lag"},
        fair_play_policy=fair_play_policy or {},
        row_count=len(materialized),
        metadata={
            "row_source": "detective_g_collection_rows",
            "fair_play_ratings": sorted(
                {str(row.get("fair_play_rating", "")) for row in materialized if str(row.get("fair_play_rating", ""))}
            ),
            **dict(metadata or {}),
        },
    )


def write_detective_g_experiment_manifest_from_csv(
    rows_csv: str | Path,
    destination: str | Path | TextIO,
    *,
    experiment_id: str,
    name: str = "",
    corpus: str = "",
    evaluation_target: str = "detective_contradiction_recognition",
    reliability_treatment: str = "",
    temporal_assumptions: Mapping[str, Any] | None = None,
    fair_play_policy: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a G experiment manifest for a detective row CSV."""

    rows_path = Path(rows_csv)
    with rows_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    manifest = detective_g_experiment_manifest_from_rows(
        rows,
        experiment_id=experiment_id,
        row_file=str(rows_path),
        name=name,
        corpus=corpus,
        evaluation_target=evaluation_target,
        reliability_treatment=reliability_treatment,
        temporal_assumptions=temporal_assumptions,
        fair_play_policy=fair_play_policy,
        metadata=metadata,
    )
    write_g_experiment_manifest(manifest, destination)
    return manifest


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


def _anchor_review_metadata(item: Mapping[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata", {}) if isinstance(item.get("metadata", {}), Mapping) else {}
    review = metadata.get("anchor_review", {}) if isinstance(metadata.get("anchor_review", {}), Mapping) else {}
    return dict(review)


def _review_row_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "review_status": str(row.get("review_status", "")),
        "reviewed_source_locator": str(row.get("reviewed_source_locator", "")),
        "reviewed_source_quote": str(row.get("reviewed_source_quote", "")),
        "reviewed_narrative_anchor": str(row.get("reviewed_narrative_anchor", "")),
        "reviewer": str(row.get("reviewer", "")),
        "reviewed_at": str(row.get("reviewed_at", "")),
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


def _story_slug(annotation: Mapping[str, Any]) -> str:
    story_id = str(annotation.get("story_id", "")).strip()
    title = str(annotation.get("title", "")).strip()
    basis = story_id.rsplit("::", 1)[-1] if story_id else title
    slug = "".join(character.lower() if character.isalnum() else "-" for character in basis)
    return "-".join(part for part in slug.split("-") if part) or "story"


def _write_json(payload: Mapping[str, Any], destination: str | Path) -> None:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(source: str | Path) -> dict[str, Any]:
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _graph_nodes_by_id(path: Any, base_dir: str | Path | None) -> dict[str, dict[str, Any]]:
    resolved = _resolve_sidecar_path(path, base_dir)
    if not str(path).strip() or not resolved.exists():
        return {}
    payload = _read_json(resolved)
    return {
        str(node.get("id", "")): dict(node)
        for node in payload.get("nodes", []) or []
        if str(node.get("id", "")).strip()
    }


def _node_source_anchor(node: Mapping[str, Any]) -> str:
    metadata = node.get("metadata", {}) if isinstance(node.get("metadata", {}), Mapping) else {}
    review = metadata.get("anchor_review", {}) if isinstance(metadata.get("anchor_review", {}), Mapping) else {}
    return str(review.get("reviewed_narrative_anchor") or metadata.get("narrative_anchor") or "")


def _resolve_sidecar_path(path: Any, base_dir: str | Path | None) -> Path:
    candidate = Path(str(path))
    if candidate.is_absolute() or base_dir is None:
        return candidate
    relative_candidate = Path(base_dir) / candidate
    if relative_candidate.exists():
        return relative_candidate
    return candidate


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


def _row_ref(index: int, row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "index": index,
        "item_id": str(row.get("item_id", "")),
        "claim_id": str(row.get("claim_id", "")),
        "condition": str(row.get("condition", "")),
        "phase": str(row.get("phase", "")),
    }


def _float_or_none(value: Any) -> float | None:
    if _blank(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _expand_run_sheet_sources(sources: Iterable[str | Path]) -> list[Path]:
    paths: list[Path] = []
    for source in sources:
        path = Path(source)
        if path.is_dir():
            paths.extend(sorted(candidate for candidate in path.glob("*.csv") if candidate.is_file()))
        else:
            paths.append(path)
    return paths


def _write_dict_rows(rows: Iterable[Mapping[str, Any]], destination: str | Path, fieldnames: Sequence[str]) -> None:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(fieldnames), extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows([dict(row) for row in rows])
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output.getvalue(), encoding="utf-8")


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")
    return text or "unlabeled"


def _blank(value: Any) -> bool:
    return value in ("", None, [], {})

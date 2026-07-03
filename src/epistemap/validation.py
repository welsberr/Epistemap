from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .algorithms import cycle_nodes, graph_qa_report
from .epistemic import CHALLENGE_EDGE_TYPES, REVISION_EDGE_TYPES, SUPPORT_EDGE_TYPES
from .models import GraphBundle


@dataclass
class GraphShape:
    required_node_fields: dict[str, set[str]] = field(default_factory=dict)
    required_edge_fields: dict[str, set[str]] = field(default_factory=dict)
    allowed_edge_types: dict[str, set[str]] = field(default_factory=dict)
    acyclic_edge_types: set[str] = field(default_factory=set)
    provenance_required_edge_types: set[str] = field(default_factory=set)


@dataclass
class AssessmentValidationPolicy:
    """Policy for checking whether a graph is ready for epistemic assessment."""

    assessed_node_types: set[str] = field(default_factory=lambda: {"claim", "concept"})
    evidence_edge_types: set[str] = field(
        default_factory=lambda: (SUPPORT_EDGE_TYPES | CHALLENGE_EDGE_TYPES | REVISION_EDGE_TYPES)
        - {"about_concept", "teaches_concept"}
    )
    require_graph_id: bool = True
    require_titles_for_node_types: set[str] = field(default_factory=lambda: {"claim", "concept", "source"})
    require_provenance_for_evidence_edges: bool = True
    require_grounding_for_evidence: bool = False
    require_temporal_metadata_for_temporal_edges: bool = True
    require_bayesian_policy_metadata: bool = True
    temporal_edge_types: set[str] = field(
        default_factory=lambda: SUPPORT_EDGE_TYPES | CHALLENGE_EDGE_TYPES | REVISION_EDGE_TYPES
    )
    temporal_metadata_keys: set[str] = field(
        default_factory=lambda: {
            "available_at",
            "introduced_at",
            "timestep",
            "valid_at",
            "valid_from",
            "valid_until",
        }
    )
    bayesian_policy_keys: set[str] = field(
        default_factory=lambda: {
            "bayesian_prior_profile",
            "evidence_weighting_policy",
            "graph_extraction_policy",
        }
    )


def validate_shape(bundle: GraphBundle, shape: GraphShape) -> dict:
    findings: list[dict] = []
    node_ids = {node.id for node in bundle.nodes}
    for node in bundle.nodes:
        for field_name in shape.required_node_fields.get(node.type, set()):
            if not _node_field_present(node, field_name):
                findings.append(
                    {
                        "severity": "error",
                        "code": "missing_node_field",
                        "node_id": node.id,
                        "field": field_name,
                    }
                )
    for edge in bundle.edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_edge_endpoint",
                    "source": edge.source,
                    "target": edge.target,
                    "edge_type": edge.type,
                }
            )
            continue
        source_type = bundle.node_index()[edge.source].type
        target_type = bundle.node_index()[edge.target].type
        allowed_targets = shape.allowed_edge_types.get(source_type)
        if allowed_targets is not None and target_type not in allowed_targets:
            findings.append(
                {
                    "severity": "warning",
                    "code": "unexpected_edge_target_type",
                    "source": edge.source,
                    "target": edge.target,
                    "edge_type": edge.type,
                    "source_type": source_type,
                    "target_type": target_type,
                }
            )
        for field_name in shape.required_edge_fields.get(edge.type, set()):
            if not _edge_field_present(edge, field_name):
                findings.append(
                    {
                        "severity": "error",
                        "code": "missing_edge_field",
                        "source": edge.source,
                        "target": edge.target,
                        "edge_type": edge.type,
                        "field": field_name,
                    }
                )
    for edge_type in sorted(shape.acyclic_edge_types):
        nodes = cycle_nodes(bundle, edge_types={edge_type})
        if nodes:
            findings.append(
                {
                    "severity": "error",
                    "code": "edge_type_cycle",
                    "edge_type": edge_type,
                    "node_ids": nodes,
                }
            )
    qa = graph_qa_report(bundle, required_provenance_edge_types=shape.provenance_required_edge_types)
    for item in qa["missing_provenance"]:
        findings.append({"severity": "warning", "code": "missing_edge_provenance", **item})
    return {
        "summary": {
            "error_count": sum(1 for item in findings if item["severity"] == "error"),
            "warning_count": sum(1 for item in findings if item["severity"] == "warning"),
            **qa["summary"],
        },
        "findings": findings,
    }


def validate_assessment_readiness(
    bundle: GraphBundle,
    policy: AssessmentValidationPolicy | None = None,
) -> dict[str, Any]:
    """Return assessment-readiness findings for scholarly graph operations.

    This validator is intentionally conservative. It checks whether assessment
    outputs can be audited, not whether claims are true.
    """

    policy = policy or AssessmentValidationPolicy()
    findings: list[dict[str, Any]] = []
    node_ids = {node.id for node in bundle.nodes}
    nodes = bundle.node_index()
    qa = graph_qa_report(bundle, required_provenance_edge_types=policy.evidence_edge_types)

    if policy.require_graph_id and not bundle.graph_id:
        findings.append(_finding("warning", "missing_graph_id", "Graph bundle has no graph_id."))

    for node_id in qa["duplicate_node_ids"]:
        findings.append(
            _finding(
                "error",
                "duplicate_node_id",
                "Graph bundle contains duplicate node ids.",
                node_id=node_id,
            )
        )

    for item in qa["missing_targets"]:
        findings.append(
            _finding(
                "error",
                "missing_edge_endpoint",
                "Edge references a missing source or target node.",
                **item,
            )
        )

    for node in bundle.nodes:
        if node.type in policy.require_titles_for_node_types and not node.title:
            findings.append(
                _finding(
                    "warning",
                    "missing_node_title",
                    "Assessment-relevant nodes should have human-readable titles.",
                    node_id=node.id,
                    node_type=node.type,
                )
            )
        if node.confidence is not None and not 0.0 <= node.confidence <= 1.0:
            findings.append(
                _finding(
                    "error",
                    "invalid_node_confidence",
                    "Node confidence must be between 0 and 1.",
                    node_id=node.id,
                    confidence=node.confidence,
                )
            )
        if node.type in policy.assessed_node_types and _needs_bayesian_policy(node.metadata):
            findings.extend(_bayesian_policy_findings(node.metadata, policy, subject={"node_id": node.id}))

    assessed_node_ids = {node.id for node in bundle.nodes if node.type in policy.assessed_node_types}
    supported_assessed_nodes = {
        edge.target
        for edge in bundle.edges
        if edge.target in assessed_node_ids and edge.source in node_ids and edge.type in policy.evidence_edge_types
    }
    for node_id in sorted(assessed_node_ids - supported_assessed_nodes):
        findings.append(
            _finding(
                "warning",
                "assessed_node_without_evidence",
                "Assessed claim/concept node has no direct evidential edge.",
                node_id=node_id,
                node_type=nodes[node_id].type,
            )
        )

    for edge in bundle.edges:
        edge_subject = {
            "source": edge.source,
            "target": edge.target,
            "edge_type": edge.type,
            "edge_id": edge.id,
        }
        if edge.confidence is not None and not 0.0 <= edge.confidence <= 1.0:
            findings.append(
                _finding(
                    "error",
                    "invalid_edge_confidence",
                    "Edge confidence must be between 0 and 1.",
                    confidence=edge.confidence,
                    **edge_subject,
                )
            )
        if edge.type in policy.evidence_edge_types:
            if policy.require_provenance_for_evidence_edges and not edge.provenance and not edge.evidence_ids:
                findings.append(
                    _finding(
                        "warning",
                        "missing_evidence_provenance",
                        "Evidential edge should cite provenance or evidence ids.",
                        **edge_subject,
                    )
                )
            if policy.require_grounding_for_evidence and not _has_grounding(edge):
                findings.append(
                    _finding(
                        "warning",
                        "missing_evidence_grounding_status",
                        "Evidential edge should include grounding status.",
                        **edge_subject,
                    )
                )
        if policy.require_temporal_metadata_for_temporal_edges and edge.type in policy.temporal_edge_types:
            if _has_any_temporal_metadata(edge.metadata, policy.temporal_metadata_keys):
                continue
            if edge.source in nodes and _has_any_temporal_metadata(nodes[edge.source].metadata, policy.temporal_metadata_keys):
                continue
            findings.append(
                _finding(
                    "info",
                    "missing_temporal_metadata",
                    "Temporal graph operations work best when evidence edges or source nodes carry availability metadata.",
                    **edge_subject,
                )
            )

    if _needs_bayesian_policy(bundle.metadata):
        findings.extend(_bayesian_policy_findings(bundle.metadata, policy, subject={"graph_id": bundle.graph_id}))

    severity_counts = _severity_counts(findings)
    return {
        "report_kind": "epistemap_assessment_validation_report",
        "graph_id": bundle.graph_id,
        "policy": {
            "assessed_node_types": sorted(policy.assessed_node_types),
            "evidence_edge_types": sorted(policy.evidence_edge_types),
            "require_graph_id": policy.require_graph_id,
            "require_provenance_for_evidence_edges": policy.require_provenance_for_evidence_edges,
            "require_grounding_for_evidence": policy.require_grounding_for_evidence,
            "require_temporal_metadata_for_temporal_edges": policy.require_temporal_metadata_for_temporal_edges,
            "require_bayesian_policy_metadata": policy.require_bayesian_policy_metadata,
            "bayesian_policy_keys": sorted(policy.bayesian_policy_keys),
        },
        "summary": {
            "status": "error" if severity_counts["error"] else "warning" if severity_counts["warning"] else "pass",
            "finding_count": len(findings),
            **severity_counts,
            **qa["summary"],
        },
        "findings": sorted(findings, key=_finding_sort_key),
    }


def assessment_validation_markdown(report: dict[str, Any]) -> str:
    """Render a compact Markdown assessment-validation report."""

    summary = report.get("summary", {})
    lines = [
        "# Epistemap Assessment Validation",
        "",
        f"- Graph: `{report.get('graph_id', '')}`",
        f"- Status: `{summary.get('status', '')}`",
        f"- Findings: `{summary.get('finding_count', 0)}`",
        f"- Errors: `{summary.get('error', 0)}`",
        f"- Warnings: `{summary.get('warning', 0)}`",
        f"- Info: `{summary.get('info', 0)}`",
        "",
        "| Severity | Code | Subject | Message |",
        "| --- | --- | --- | --- |",
    ]
    for finding in report.get("findings", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(finding.get("severity", "")),
                    _md(finding.get("code", "")),
                    _md(_finding_subject(finding)),
                    _md(finding.get("message", "")),
                ]
            )
            + " |"
        )
    if not report.get("findings"):
        lines.append("| pass | no_findings | graph | No validation findings. |")
    lines.extend(
        [
            "",
            "Validation reports indicate whether an assessment artifact is auditable; they are not claim-promotion decisions.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_assessment_validation_markdown(report: dict[str, Any], destination: str | Path) -> None:
    """Write an assessment-validation Markdown report."""

    Path(destination).write_text(assessment_validation_markdown(report), encoding="utf-8")


def _node_field_present(node, field_name: str) -> bool:
    if hasattr(node, field_name):
        return getattr(node, field_name) not in ("", None, [], {})
    return node.metadata.get(field_name) not in ("", None, [], {})


def _edge_field_present(edge, field_name: str) -> bool:
    if hasattr(edge, field_name):
        return getattr(edge, field_name) not in ("", None, [], {})
    return edge.metadata.get(field_name) not in ("", None, [], {})


def _finding(severity: str, code: str, message: str, **payload: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, "message": message, **payload}


def _severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "error": sum(1 for item in findings if item["severity"] == "error"),
        "warning": sum(1 for item in findings if item["severity"] == "warning"),
        "info": sum(1 for item in findings if item["severity"] == "info"),
    }


def _finding_sort_key(finding: dict[str, Any]) -> tuple[int, str, str]:
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    return (
        severity_rank.get(str(finding.get("severity", "")), 9),
        str(finding.get("code", "")),
        _finding_subject(finding),
    )


def _finding_subject(finding: dict[str, Any]) -> str:
    if finding.get("node_id"):
        return str(finding["node_id"])
    source = finding.get("source")
    target = finding.get("target")
    edge_type = finding.get("edge_type") or finding.get("type")
    if source or target:
        return f"{source or ''} -[{edge_type or ''}]-> {target or ''}"
    if finding.get("graph_id"):
        return str(finding["graph_id"])
    return "graph"


def _has_grounding(edge) -> bool:
    if edge.status in {"grounded", "partially_grounded", "ungrounded"}:
        return True
    if edge.metadata.get("grounding_status"):
        return True
    return any(item.grounding_status for item in edge.provenance)


def _has_any_temporal_metadata(metadata: dict[str, Any], keys: set[str]) -> bool:
    return any(metadata.get(key) not in ("", None, [], {}) for key in keys)


def _needs_bayesian_policy(metadata: dict[str, Any]) -> bool:
    keys = {
        "bayesian_reliability",
        "bayesian_assessment",
        "bayesian_assessment_report",
        "assessment_summary",
    }
    return any(key in metadata for key in keys)


def _bayesian_policy_findings(
    metadata: dict[str, Any],
    policy: AssessmentValidationPolicy,
    *,
    subject: dict[str, Any],
) -> list[dict[str, Any]]:
    if not policy.require_bayesian_policy_metadata:
        return []
    assessment_policy = metadata.get("assessment_policy")
    if not isinstance(assessment_policy, dict):
        assessment_policy = {}
    findings = []
    for key in sorted(policy.bayesian_policy_keys):
        if metadata.get(key) in ("", None, [], {}) and assessment_policy.get(key) in ("", None, [], {}):
            findings.append(
                _finding(
                    "warning",
                    "missing_bayesian_policy_metadata",
                    "Bayesian assessment metadata should record the policy used to produce it.",
                    field=key,
                    **subject,
                )
            )
    return findings


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")

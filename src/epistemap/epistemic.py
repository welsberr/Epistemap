from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .bayesian import bayesian_evidence_update, bayesian_prior_sensitivity, classify_bayesian_reliability
from .models import Edge, GraphBundle, Node

SUPPORT_EDGE_TYPES = {"supports", "supports_claim", "about_concept", "supports_concept", "teaches_concept"}
CHALLENGE_EDGE_TYPES = {"contradicts", "challenges", "disputes"}
REVISION_EDGE_TYPES = {"supersedes", "corrects", "retracts", "qualifies"}
HIGH_TRUST_VALUES = {"high", "trusted", "peer_reviewed", "primary", "official", "expert_reviewed"}
MIXED_TRUST_VALUES = {"medium", "mixed", "provisional", "secondary", "tertiary"}
LOW_TRUST_VALUES = {"low", "rejected", "unreviewed", "advocacy", "misinformation", "denialist", "retracted"}
ADVERSARIAL_STANCE_VALUES = {"adversarial", "denialist", "misinformation", "manufactured_doubt", "trust_eroding"}


def epistemic_summary(bundle: GraphBundle, node_id: str, *, low_confidence_threshold: float = 0.5) -> dict[str, Any]:
    nodes = bundle.node_index()
    target = nodes.get(node_id)
    incident = [edge for edge in bundle.edges if edge.source == node_id or edge.target == node_id]
    incoming = [edge for edge in incident if edge.target == node_id]
    outgoing = [edge for edge in incident if edge.source == node_id]
    claim_ids = _claim_ids_for_target(bundle, node_id)
    claim_evidence_edges = [edge for edge in bundle.edges if edge.target in claim_ids or edge.source in claim_ids]
    relevant_node_ids = (
        {node_id}
        | claim_ids
        | {edge.source for edge in incident}
        | {edge.target for edge in incident}
        | {edge.source for edge in claim_evidence_edges}
        | {edge.target for edge in claim_evidence_edges}
    )
    relevant_edges = [
        edge
        for edge in bundle.edges
        if edge.source in relevant_node_ids and edge.target in relevant_node_ids
    ]
    relevant_nodes = [node for node in bundle.nodes if node.id in relevant_node_ids]
    support_edges = [edge for edge in relevant_edges if edge.type in SUPPORT_EDGE_TYPES and (edge.target == node_id or edge.target in claim_ids)]
    challenge_edges = [edge for edge in relevant_edges if edge.type in CHALLENGE_EDGE_TYPES]
    revision_edges = [edge for edge in relevant_edges if edge.type in REVISION_EDGE_TYPES]
    low_confidence_nodes = [
        node
        for node in relevant_nodes
        if node.confidence is not None and node.confidence < low_confidence_threshold
    ]
    grounding = Counter(_grounding_values(relevant_nodes, relevant_edges))
    source_roles = Counter(_source_roles(relevant_nodes))
    source_quality = Counter(_source_quality_values(relevant_nodes, relevant_edges))
    source_stances = Counter(_source_stance_values(relevant_nodes, relevant_edges))
    flags = _epistemic_flags(
        support_edges=support_edges,
        challenge_edges=challenge_edges,
        revision_edges=revision_edges,
        low_confidence_nodes=low_confidence_nodes,
        grounding=grounding,
        source_roles=source_roles,
        source_quality=source_quality,
        source_stances=source_stances,
    )
    reliability = reliability_assessment(
        support_edges=support_edges,
        challenge_edges=challenge_edges,
        revision_edges=revision_edges,
        relevant_nodes=relevant_nodes,
        grounding=grounding,
        source_roles=source_roles,
        source_quality=source_quality,
        source_stances=source_stances,
    )
    bayesian = bayesian_evidence_update(
        support_edges=support_edges,
        challenge_edges=challenge_edges,
        nodes_by_id=nodes,
    )
    bayesian["prior_sensitivity"] = bayesian_prior_sensitivity(
        support_edges=support_edges,
        challenge_edges=challenge_edges,
        nodes_by_id=nodes,
    )
    bayesian["classification"] = classify_bayesian_reliability(bayesian)
    return {
        "node_id": node_id,
        "node_type": target.type if target is not None else "",
        "title": target.title if target is not None else "",
        "summary": {
            "direct_support_count": len(support_edges),
            "challenge_count": len(challenge_edges),
            "revision_count": len(revision_edges),
            "low_confidence_node_count": len(low_confidence_nodes),
            "incoming_count": len(incoming),
            "outgoing_count": len(outgoing),
        },
        "grounding_status_summary": dict(sorted(grounding.items())),
        "source_role_summary": dict(sorted(source_roles.items())),
        "source_quality_summary": dict(sorted(source_quality.items())),
        "source_stance_summary": dict(sorted(source_stances.items())),
        "flags": flags,
        "reliability": reliability,
        "bayesian_reliability": bayesian,
        "support_edges": [_edge_ref(edge) for edge in support_edges[:12]],
        "challenge_edges": [_edge_ref(edge) for edge in challenge_edges[:12]],
        "revision_edges": [_edge_ref(edge) for edge in revision_edges[:12]],
        "low_confidence_nodes": [_node_ref(node) for node in low_confidence_nodes[:12]],
    }


def epistemic_report(bundle: GraphBundle, *, node_types: set[str] | None = None) -> dict[str, Any]:
    node_types = node_types or {"concept", "claim"}
    summaries = [
        epistemic_summary(bundle, node.id)
        for node in bundle.nodes
        if node.type in node_types
    ]
    flag_counts: Counter[str] = Counter()
    reliability_bands: Counter[str] = Counter()
    for summary in summaries:
        flag_counts.update(summary["flags"])
        reliability_bands.update([summary.get("reliability", {}).get("band", "unknown")])
    return {
        "summary": {
            "node_count": len(summaries),
            "flagged_node_count": sum(1 for item in summaries if item["flags"]),
            "flag_counts": dict(sorted(flag_counts.items())),
            "reliability_bands": dict(sorted(reliability_bands.items())),
        },
        "nodes": summaries,
    }


def bayesian_assessment_report(bundle: GraphBundle, *, node_types: set[str] | None = None) -> dict[str, Any]:
    """Batch Bayesian assessment summaries over graph claims or concepts."""
    node_types = node_types or {"concept", "claim"}
    rows = [
        _bayesian_assessment_row(epistemic_summary(bundle, node.id))
        for node in bundle.nodes
        if node.type in node_types
    ]
    rows = sorted(rows, key=_bayesian_assessment_sort_key)
    label_counts = Counter(row["bayesian_label"] for row in rows)
    flag_counts: Counter[str] = Counter()
    for row in rows:
        flag_counts.update(row["bayesian_flags"])
    return {
        "report_kind": "epistemap_bayesian_assessment_report",
        "graph_id": bundle.graph_id,
        "summary": {
            "node_count": len(rows),
            "label_counts": dict(sorted(label_counts.items())),
            "flag_counts": dict(sorted(flag_counts.items())),
        },
        "nodes": rows,
    }


def bayesian_assessment_markdown(report: dict[str, Any]) -> str:
    """Render a compact Markdown report for a graph-level Bayesian assessment."""
    summary = report.get("summary", {})
    lines = [
        "# Epistemap Bayesian Assessment",
        "",
        f"- Graph: `{report.get('graph_id', '')}`",
        f"- Nodes assessed: `{summary.get('node_count', 0)}`",
        f"- Label counts: `{_counter_text(summary.get('label_counts', {}))}`",
        f"- Flag counts: `{_counter_text(summary.get('flag_counts', {}))}`",
        "",
        "| Node | Type | Label | Flags | Mean | N | Prior Range |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in report.get("nodes", []):
        lines.append(
            "| {node} | {node_type} | `{label}` | {flags} | {mean} | {n} | {prior_range} |".format(
                node=row.get("title") or row.get("node_id", ""),
                node_type=row.get("node_type", ""),
                label=row.get("bayesian_label", ""),
                flags=", ".join(row.get("bayesian_flags", [])) or "none",
                mean=_fmt_float(row.get("posterior_mean")),
                n=_fmt_float(row.get("effective_sample_size")),
                prior_range=_fmt_float(row.get("prior_sensitivity_range")),
            )
        )
    lines.extend(
        [
            "",
            "Labels are review triage signals over explicit priors and extracted graph evidence, not automatic claim promotion decisions.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_bayesian_assessment_markdown(report: dict[str, Any], destination: str | Path) -> None:
    """Write a graph-level Bayesian assessment Markdown report."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bayesian_assessment_markdown(report), encoding="utf-8")


def _bayesian_assessment_row(summary: dict[str, Any]) -> dict[str, Any]:
    bayesian = summary.get("bayesian_reliability", {})
    posterior = bayesian.get("posterior", {}) if isinstance(bayesian, dict) else {}
    evidence = bayesian.get("evidence", {}) if isinstance(bayesian, dict) else {}
    sensitivity = bayesian.get("prior_sensitivity", {}) if isinstance(bayesian, dict) else {}
    classification = bayesian.get("classification", {}) if isinstance(bayesian, dict) else {}
    metrics = classification.get("metrics", {}) if isinstance(classification, dict) else {}
    interval = posterior.get("credible_interval", {}) if isinstance(posterior, dict) else {}
    return {
        "node_id": summary.get("node_id", ""),
        "node_type": summary.get("node_type", ""),
        "title": summary.get("title", ""),
        "bayesian_label": classification.get("label", ""),
        "bayesian_flags": list(classification.get("flags", []) or []),
        "posterior_mean": posterior.get("mean"),
        "credible_interval_lower": interval.get("lower"),
        "credible_interval_upper": interval.get("upper"),
        "credible_interval_width": metrics.get("credible_interval_width"),
        "effective_sample_size": evidence.get("effective_sample_size"),
        "support_edge_count": evidence.get("support_edge_count", 0),
        "challenge_edge_count": evidence.get("challenge_edge_count", 0),
        "prior_sensitivity_range": sensitivity.get("mean_range"),
        "reliability_band": summary.get("reliability", {}).get("band", ""),
        "epistemic_flags": list(summary.get("flags", []) or []),
    }


def _bayesian_assessment_sort_key(row: dict[str, Any]) -> tuple[int, float, float, str]:
    label_rank = {
        "prior_sensitive": 0,
        "thin_evidence": 1,
        "contested": 2,
        "fragile_support": 3,
        "stable_support": 4,
    }
    return (
        label_rank.get(str(row.get("bayesian_label", "")), 9),
        -float(row.get("prior_sensitivity_range") or 0.0),
        float(row.get("effective_sample_size") or 0.0),
        str(row.get("node_id", "")),
    )


def _counter_text(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "none"
    return ", ".join(f"{key}: {value[key]}" for key in sorted(value))


def _fmt_float(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


def reliability_assessment(
    *,
    support_edges: list[Edge],
    challenge_edges: list[Edge],
    revision_edges: list[Edge],
    relevant_nodes: list[Node],
    grounding: Counter[str],
    source_roles: Counter[str],
    source_quality: Counter[str] | None = None,
    source_stances: Counter[str] | None = None,
) -> dict[str, Any]:
    source_quality = source_quality or Counter()
    source_stances = source_stances or Counter()
    grounding_score = _grounding_score(grounding)
    support_score = min(1.0, len(support_edges) / 3.0)
    challenge_penalty = min(0.35, len(challenge_edges) * 0.12)
    revision_bonus = min(0.15, len(revision_edges) * 0.05)
    confidence_values = [node.confidence for node in relevant_nodes if node.confidence is not None]
    confidence_score = sum(confidence_values) / len(confidence_values) if confidence_values else 0.5
    diversity_score = min(1.0, len(source_roles) / 3.0) if source_roles else 0.0
    source_quality_score = _source_quality_score(source_quality)
    adversarial_penalty = _adversarial_penalty(source_stances)
    score = (
        0.25 * grounding_score
        + 0.25 * support_score
        + 0.18 * confidence_score
        + 0.12 * diversity_score
        + 0.12 * source_quality_score
        + revision_bonus
        - challenge_penalty
        - adversarial_penalty
    )
    score = max(0.0, min(1.0, score))
    return {
        "score": round(score, 3),
        "band": _score_band(score),
        "components": {
            "grounding": round(grounding_score, 3),
            "support": round(support_score, 3),
            "confidence": round(confidence_score, 3),
            "source_role_diversity": round(diversity_score, 3),
            "source_quality": round(source_quality_score, 3),
            "challenge_penalty": round(challenge_penalty, 3),
            "adversarial_penalty": round(adversarial_penalty, 3),
            "revision_bonus": round(revision_bonus, 3),
        },
        "rationale": _reliability_rationale(
            grounding=grounding,
            support_edges=support_edges,
            challenge_edges=challenge_edges,
            revision_edges=revision_edges,
            source_roles=source_roles,
            source_quality=source_quality,
            source_stances=source_stances,
        ),
    }


def _claim_ids_for_target(bundle: GraphBundle, node_id: str) -> set[str]:
    nodes = bundle.node_index()
    target = nodes.get(node_id)
    if target is not None and target.type == "claim":
        return {node_id}
    return {
        edge.source
        for edge in bundle.edges
        if edge.target == node_id and edge.type == "about_concept" and nodes.get(edge.source, Node(id="", type="")).type == "claim"
    }


def _grounding_values(nodes: list[Node], edges: list[Edge]) -> list[str]:
    values: list[str] = []
    for node in nodes:
        if node.status in {"grounded", "partially_grounded", "ungrounded"}:
            values.append(node.status)
        values.extend(item.grounding_status for item in node.provenance if item.grounding_status)
    for edge in edges:
        values.extend(item.grounding_status for item in edge.provenance if item.grounding_status)
    return values


def _source_roles(nodes: list[Node]) -> list[str]:
    roles: list[str] = []
    for node in nodes:
        role = str(node.metadata.get("source_role", "")).strip()
        if role:
            roles.append(role)
        roles.extend(str(value).strip() for value in node.metadata.get("source_roles", []) if str(value).strip())
    return roles


def _source_quality_values(nodes: list[Node], edges: list[Edge]) -> list[str]:
    values: list[str] = []
    for node in nodes:
        values.extend(_metadata_values(node.metadata, ("source_quality", "source_reliability", "trust_status")))
        for item in node.provenance:
            values.extend(_metadata_values(item.metadata, ("source_quality", "source_reliability", "trust_status")))
    for edge in edges:
        values.extend(_metadata_values(edge.metadata, ("source_quality", "source_reliability", "trust_status")))
        for item in edge.provenance:
            values.extend(_metadata_values(item.metadata, ("source_quality", "source_reliability", "trust_status")))
    return values


def _source_stance_values(nodes: list[Node], edges: list[Edge]) -> list[str]:
    values: list[str] = []
    for node in nodes:
        values.extend(_metadata_values(node.metadata, ("source_stance", "stance", "adversarial_intent")))
        if node.metadata.get("adversarial") is True:
            values.append("adversarial")
        if node.metadata.get("denialist") is True:
            values.append("denialist")
    for edge in edges:
        values.extend(_metadata_values(edge.metadata, ("source_stance", "stance", "adversarial_intent")))
        if edge.metadata.get("adversarial") is True:
            values.append("adversarial")
        if edge.metadata.get("denialist") is True:
            values.append("denialist")
    return values


def _metadata_values(metadata: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw = metadata.get(key)
        if isinstance(raw, str):
            value = raw.strip().lower()
            if value:
                values.append(value)
        elif isinstance(raw, list):
            values.extend(str(value).strip().lower() for value in raw if str(value).strip())
    return values


def _epistemic_flags(
    *,
    support_edges: list[Edge],
    challenge_edges: list[Edge],
    revision_edges: list[Edge],
    low_confidence_nodes: list[Node],
    grounding: Counter[str],
    source_roles: Counter[str],
    source_quality: Counter[str],
    source_stances: Counter[str],
) -> list[str]:
    flags: list[str] = []
    if not support_edges:
        flags.append("no_direct_support")
    if challenge_edges:
        flags.append("challenged")
    if revision_edges:
        flags.append("revised_or_qualified")
    if low_confidence_nodes:
        flags.append("low_confidence")
    if grounding.get("ungrounded", 0) or (grounding and not grounding.get("grounded", 0)):
        flags.append("weak_grounding")
    if len(source_roles) == 1:
        flags.append("narrow_source_role")
    if any(value in LOW_TRUST_VALUES for value in source_quality):
        flags.append("low_trust_source_signal")
    if any(value in ADVERSARIAL_STANCE_VALUES for value in source_stances):
        flags.append("adversarial_source_signal")
    return flags


def _grounding_score(grounding: Counter[str]) -> float:
    if not grounding:
        return 0.35
    total = sum(grounding.values())
    weighted = (
        grounding.get("grounded", 0) * 1.0
        + grounding.get("partially_grounded", 0) * 0.55
        + grounding.get("ungrounded", 0) * 0.05
    )
    return weighted / total


def _score_band(score: float) -> str:
    if score >= 0.75:
        return "strong"
    if score >= 0.5:
        return "moderate"
    if score >= 0.3:
        return "weak"
    return "poor"


def _source_quality_score(source_quality: Counter[str]) -> float:
    if not source_quality:
        return 0.5
    total = sum(source_quality.values())
    weighted = 0.0
    for value, count in source_quality.items():
        if value in HIGH_TRUST_VALUES:
            weighted += count * 1.0
        elif value in MIXED_TRUST_VALUES:
            weighted += count * 0.55
        elif value in LOW_TRUST_VALUES:
            weighted += count * 0.1
        else:
            weighted += count * 0.45
    return weighted / total


def _adversarial_penalty(source_stances: Counter[str]) -> float:
    if not source_stances:
        return 0.0
    adversarial_count = sum(count for value, count in source_stances.items() if value in ADVERSARIAL_STANCE_VALUES)
    return min(0.25, adversarial_count * 0.1)


def _reliability_rationale(
    *,
    grounding: Counter[str],
    support_edges: list[Edge],
    challenge_edges: list[Edge],
    revision_edges: list[Edge],
    source_roles: Counter[str],
    source_quality: Counter[str],
    source_stances: Counter[str],
) -> list[str]:
    rationale: list[str] = []
    if support_edges:
        rationale.append(f"{len(support_edges)} direct support edge(s)")
    else:
        rationale.append("no direct support edge")
    if challenge_edges:
        rationale.append(f"{len(challenge_edges)} challenge edge(s)")
    if revision_edges:
        rationale.append(f"{len(revision_edges)} revision/qualification edge(s)")
    if grounding:
        rationale.append("grounding=" + ",".join(f"{key}:{value}" for key, value in sorted(grounding.items())))
    else:
        rationale.append("no explicit grounding status")
    if source_roles:
        rationale.append("source_roles=" + ",".join(sorted(source_roles)))
    else:
        rationale.append("no source-role diversity signal")
    if source_quality:
        rationale.append("source_quality=" + ",".join(f"{key}:{value}" for key, value in sorted(source_quality.items())))
    if source_stances:
        rationale.append("source_stances=" + ",".join(f"{key}:{value}" for key, value in sorted(source_stances.items())))
    return rationale


def _edge_ref(edge: Edge) -> dict[str, Any]:
    return {
        "source": edge.source,
        "target": edge.target,
        "type": edge.type,
        "confidence": edge.confidence,
        "evidence_ids": list(edge.evidence_ids),
    }


def _node_ref(node: Node) -> dict[str, Any]:
    return {
        "id": node.id,
        "type": node.type,
        "title": node.title,
        "confidence": node.confidence,
        "status": node.status,
    }

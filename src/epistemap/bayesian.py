from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping, Sequence

from .models import Edge, Node

HIGH_TRUST_VALUES = {"high", "trusted", "peer_reviewed", "primary", "official", "expert_reviewed"}
MIXED_TRUST_VALUES = {"medium", "mixed", "provisional", "secondary", "tertiary"}
LOW_TRUST_VALUES = {"low", "rejected", "unreviewed", "advocacy", "misinformation", "denialist", "retracted"}
ADVERSARIAL_STANCE_VALUES = {"adversarial", "denialist", "misinformation", "manufactured_doubt", "trust_eroding"}


def beta_binomial_posterior(
    *,
    success_weight: float,
    failure_weight: float,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    credibility: float = 0.95,
) -> dict[str, Any]:
    """Return a transparent beta-binomial posterior summary for weighted evidence."""
    if prior_alpha <= 0 or prior_beta <= 0:
        raise ValueError("beta priors require positive alpha and beta")
    if success_weight < 0 or failure_weight < 0:
        raise ValueError("evidence weights must be non-negative")
    alpha = float(prior_alpha) + float(success_weight)
    beta = float(prior_beta) + float(failure_weight)
    total = alpha + beta
    mean = alpha / total
    variance = (alpha * beta) / ((total**2) * (total + 1.0))
    z = _normal_z_for_credibility(credibility)
    half_width = z * math.sqrt(variance)
    return {
        "model": "beta_binomial_weighted_evidence",
        "prior": {
            "alpha": float(prior_alpha),
            "beta": float(prior_beta),
            "mean": prior_alpha / (prior_alpha + prior_beta),
        },
        "posterior": {
            "alpha": round(alpha, 6),
            "beta": round(beta, 6),
            "mean": round(mean, 6),
            "variance": round(variance, 6),
            "credible_interval": {
                "level": credibility,
                "method": "normal_approximation",
                "lower": round(max(0.0, mean - half_width), 6),
                "upper": round(min(1.0, mean + half_width), 6),
            },
        },
        "evidence": {
            "success_weight": round(float(success_weight), 6),
            "failure_weight": round(float(failure_weight), 6),
            "effective_sample_size": round(float(success_weight) + float(failure_weight), 6),
        },
        "interpretation": (
            "Posterior support estimate from weighted support/challenge evidence; "
            "not a truth oracle and sensitive to evidence extraction and prior choice."
        ),
    }


def bayesian_evidence_update(
    *,
    support_edges: Sequence[Edge],
    challenge_edges: Sequence[Edge],
    nodes_by_id: Mapping[str, Node] | None = None,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    credibility: float = 0.95,
) -> dict[str, Any]:
    """Estimate posterior claim support from support and challenge edges."""
    nodes_by_id = nodes_by_id or {}
    support_weights = [_edge_evidence_weight(edge, nodes_by_id) for edge in support_edges]
    challenge_weights = [_edge_evidence_weight(edge, nodes_by_id) for edge in challenge_edges]
    posterior = beta_binomial_posterior(
        success_weight=sum(support_weights),
        failure_weight=sum(challenge_weights),
        prior_alpha=prior_alpha,
        prior_beta=prior_beta,
        credibility=credibility,
    )
    posterior["evidence"]["support_edge_count"] = len(support_edges)
    posterior["evidence"]["challenge_edge_count"] = len(challenge_edges)
    posterior["evidence"]["support_weights"] = [round(weight, 6) for weight in support_weights]
    posterior["evidence"]["challenge_weights"] = [round(weight, 6) for weight in challenge_weights]
    posterior["stability"] = _posterior_stability(posterior)
    return posterior


def bayesian_prior_sensitivity(
    *,
    support_edges: Sequence[Edge],
    challenge_edges: Sequence[Edge],
    nodes_by_id: Mapping[str, Node] | None = None,
    priors: Mapping[str, tuple[float, float]] | None = None,
    credibility: float = 0.95,
) -> dict[str, Any]:
    """Run the same evidence through named priors to expose prior sensitivity."""
    priors = priors or {
        "skeptical": (1.0, 2.0),
        "neutral": (1.0, 1.0),
        "supportive": (2.0, 1.0),
    }
    estimates = {
        name: bayesian_evidence_update(
            support_edges=support_edges,
            challenge_edges=challenge_edges,
            nodes_by_id=nodes_by_id,
            prior_alpha=alpha,
            prior_beta=beta,
            credibility=credibility,
        )
        for name, (alpha, beta) in priors.items()
    }
    means = [estimate["posterior"]["mean"] for estimate in estimates.values()]
    return {
        "model": "beta_binomial_prior_sensitivity",
        "priors": {
            name: {"alpha": alpha, "beta": beta}
            for name, (alpha, beta) in priors.items()
        },
        "estimates": estimates,
        "mean_range": round(max(means) - min(means), 6) if means else 0.0,
        "interpretation": (
            "Prior sensitivity compares posterior support under alternate explicit priors; "
            "large ranges indicate fragile confidence rather than settled evidence."
        ),
    }


def _edge_evidence_weight(edge: Edge, nodes_by_id: Mapping[str, Node]) -> float:
    confidence = (
        edge.confidence
        if edge.confidence is not None
        else nodes_by_id.get(edge.source, Node(id="", type="")).confidence
    )
    confidence_weight = _clamp(float(confidence)) if confidence is not None else 0.75
    source = nodes_by_id.get(edge.source)
    quality_values = _metadata_values(edge.metadata, ("source_quality", "source_reliability", "trust_status"))
    stance_values = _metadata_values(edge.metadata, ("source_stance", "stance", "adversarial_intent"))
    grounding_values: list[str] = []
    if source is not None:
        quality_values.extend(
            _metadata_values(source.metadata, ("source_quality", "source_reliability", "trust_status"))
        )
        stance_values.extend(_metadata_values(source.metadata, ("source_stance", "stance", "adversarial_intent")))
        if source.metadata.get("adversarial") is True:
            stance_values.append("adversarial")
        if source.metadata.get("denialist") is True:
            stance_values.append("denialist")
        if source.status:
            grounding_values.append(str(source.status).strip().lower())
        grounding_values.extend(
            item.grounding_status.strip().lower()
            for item in source.provenance
            if item.grounding_status
        )
    grounding_values.extend(item.grounding_status.strip().lower() for item in edge.provenance if item.grounding_status)
    return (
        confidence_weight
        * _quality_multiplier(Counter(quality_values))
        * _stance_multiplier(Counter(stance_values))
        * _grounding_multiplier(Counter(grounding_values))
    )


def _metadata_values(metadata: Mapping[str, Any], keys: tuple[str, ...]) -> list[str]:
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


def _quality_multiplier(values: Counter[str]) -> float:
    if not values:
        return 0.65
    total = sum(values.values())
    weighted = 0.0
    for value, count in values.items():
        if value in HIGH_TRUST_VALUES:
            weighted += count * 1.0
        elif value in MIXED_TRUST_VALUES:
            weighted += count * 0.65
        elif value in LOW_TRUST_VALUES:
            weighted += count * 0.2
        else:
            weighted += count * 0.5
    return weighted / total


def _stance_multiplier(values: Counter[str]) -> float:
    if not values:
        return 1.0
    adversarial = sum(count for value, count in values.items() if value in ADVERSARIAL_STANCE_VALUES)
    if adversarial:
        return max(0.2, 1.0 - 0.45 * adversarial)
    return 1.0


def _grounding_multiplier(values: Counter[str]) -> float:
    if not values:
        return 0.85
    total = sum(values.values())
    weighted = 0.0
    for value, count in values.items():
        if value == "grounded":
            weighted += count * 1.0
        elif value == "partially_grounded":
            weighted += count * 0.65
        elif value == "ungrounded":
            weighted += count * 0.2
        else:
            weighted += count * 0.5
    return weighted / total


def _posterior_stability(posterior: Mapping[str, Any]) -> str:
    interval = posterior["posterior"]["credible_interval"]
    width = float(interval["upper"]) - float(interval["lower"])
    effective_n = float(posterior["evidence"]["effective_sample_size"])
    if effective_n < 1.0 or width >= 0.6:
        return "fragile"
    if width >= 0.35:
        return "moderate"
    return "stable"


def _normal_z_for_credibility(credibility: float) -> float:
    if credibility <= 0 or credibility >= 1:
        raise ValueError("credibility must be between 0 and 1")
    known = {
        0.8: 1.281552,
        0.9: 1.644854,
        0.95: 1.959964,
        0.99: 2.575829,
    }
    return known.get(round(float(credibility), 2), 1.959964)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))

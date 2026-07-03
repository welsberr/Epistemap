from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from .models import Edge, GraphBundle


def g_estimate(
    rows: Iterable[Mapping[str, Any]],
    *,
    target_env: str = "K",
    clean_env: str = "C",
    weights: tuple[float, float, float] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
) -> dict[str, Any]:
    """Compute the practical G grounding-effectiveness estimate.

    Rows must contain `y` in {0, 1}, `p` as the probability/confidence assigned
    to y=1, and `env` as a clean/reference or target/shifted environment label.
    This measures learner/model truth tracking, discrimination, and robustness;
    it is not a claim-truth or provenance-reliability score.
    """

    materialized = list(rows)
    clean = [_coerce_row(row) for row in materialized if str(row.get("env", "")) == clean_env]
    target = [_coerce_row(row) for row in materialized if str(row.get("env", "")) == target_env]
    if not clean or not target:
        return {
            "G": 0.0,
            "components": {},
            "n": {"clean": len(clean), "target": len(target)},
            "env_labels": {"clean": clean_env, "target": target_env},
            "warning": "both clean and target environments are required",
        }

    prevalence = sum(row["y"] for row in target) / len(target)
    brier_target = _brier(target)
    auc_target = _auc(target)
    auc_clean = _auc(clean)
    s_t = _norm_brier(brier_target, prevalence)
    s_d = _norm_auc(auc_target)
    s_r = _robust_auc(auc_clean, auc_target)
    w_t, w_d, w_r = _normalized_weights(weights)
    return {
        "G": w_t * s_t + w_d * s_d + w_r * s_r,
        "components": {
            "S_T": {"point": s_t, "brier": brier_target, "prevalence": prevalence},
            "S_D": {"point": s_d, "auc_target": auc_target},
            "S_R": {"point": s_r, "auc_clean": auc_clean, "auc_target": auc_target},
        },
        "weights": {"w_T": w_t, "w_D": w_d, "w_R": w_r},
        "n": {"clean": len(clean), "target": len(target)},
        "env_labels": {"clean": clean_env, "target": target_env},
    }


def delta_g(
    before_rows: Iterable[Mapping[str, Any]],
    after_rows: Iterable[Mapping[str, Any]],
    *,
    target_env: str = "K",
    clean_env: str = "C",
    weights: tuple[float, float, float] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
) -> dict[str, Any]:
    before = g_estimate(before_rows, target_env=target_env, clean_env=clean_env, weights=weights)
    after = g_estimate(after_rows, target_env=target_env, clean_env=clean_env, weights=weights)
    before_g = float(before["G"])
    after_g = float(after["G"])
    return {
        "before": before,
        "after": after,
        "delta_G": after_g - before_g,
        "normalized_delta_G": (after_g - before_g) / max(1.0 - before_g, 1e-12),
    }


def reliability_level_sensitivity(
    rows_by_level: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    baseline_level: str | None = None,
    target_env: str = "K",
    clean_env: str = "C",
    weights: tuple[float, float, float] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
) -> dict[str, Any]:
    """Compare G estimates under counterfactual reliability-level conditions.

    The rows are evaluation outcomes produced after setting one graph component,
    source bundle, intervention, or explanation path to different reliability
    assumptions. This is sensitivity analysis: it can show that learning or
    calibration is fragile under trust assumptions, but it does not adjudicate
    the truth of the underlying scientific claim.
    """

    estimates = {
        str(level): g_estimate(rows, target_env=target_env, clean_env=clean_env, weights=weights)
        for level, rows in rows_by_level.items()
    }
    if baseline_level is None and estimates:
        baseline_level = next(iter(estimates))
    baseline = estimates.get(str(baseline_level), {"G": 0.0})
    baseline_g = float(baseline.get("G", 0.0))
    effects = {
        level: {
            "G": float(estimate.get("G", 0.0)),
            "delta_from_baseline": float(estimate.get("G", 0.0)) - baseline_g,
        }
        for level, estimate in estimates.items()
    }
    return {
        "baseline_level": baseline_level,
        "estimates": estimates,
        "effects": effects,
        "interpretation": (
            "Counterfactual reliability sensitivity for learner/model grounding effectiveness; "
            "not a truth score for graph components."
        ),
    }


def graph_with_component_reliability(
    bundle: GraphBundle,
    component_id: str,
    reliability_level: str | float,
    *,
    metadata_key: str = "counterfactual_reliability",
) -> GraphBundle:
    """Return a copy of a graph with one node or edge reliability metadata set."""

    clone = deepcopy(bundle)
    changed = False
    for node in clone.nodes:
        if node.id == component_id:
            node.metadata[metadata_key] = reliability_level
            changed = True
    for edge in clone.edges:
        if edge.id == component_id or _edge_compound_id(edge) == component_id:
            edge.metadata[metadata_key] = reliability_level
            changed = True
    clone.metadata.setdefault("counterfactuals", []).append(
        {
            "component_id": component_id,
            "metadata_key": metadata_key,
            "reliability_level": reliability_level,
            "component_found": changed,
        }
    )
    return clone


def _coerce_row(row: Mapping[str, Any]) -> dict[str, float]:
    y = int(row["y"])
    if y not in {0, 1}:
        raise ValueError("G rows require y in {0, 1}")
    p = float(row["p"])
    if p < 0.0 or p > 1.0:
        raise ValueError("G rows require p in [0, 1]")
    return {"y": float(y), "p": p}


def _brier(rows: Sequence[Mapping[str, float]]) -> float:
    return sum((float(row["p"]) - float(row["y"])) ** 2 for row in rows) / len(rows) if rows else 0.0


def _auc(rows: Sequence[Mapping[str, float]]) -> float:
    positives = [float(row["p"]) for row in rows if int(row["y"]) == 1]
    negatives = [float(row["p"]) for row in rows if int(row["y"]) == 0]
    if not positives or not negatives:
        return 0.5
    wins = 0.0
    total = len(positives) * len(negatives)
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / total


def _norm_brier(brier: float, prevalence: float) -> float:
    baseline = max(prevalence * (1.0 - prevalence), 1e-12)
    return min(max(1.0 - brier / baseline, 0.0), 1.0)


def _norm_auc(auc: float) -> float:
    return min(max((auc - 0.5) / 0.5, 0.0), 1.0)


def _robust_auc(auc_clean: float, auc_target: float) -> float:
    denominator = max(auc_clean - 0.5, 1e-12)
    return min(max(1.0 - (auc_clean - auc_target) / denominator, 0.0), 1.0)


def _normalized_weights(weights: tuple[float, float, float]) -> tuple[float, float, float]:
    total = sum(weights)
    if total <= 0:
        raise ValueError("G weights must sum to a positive value")
    return weights[0] / total, weights[1] / total, weights[2] / total


def _edge_compound_id(edge: Edge) -> str:
    return f"{edge.source}->{edge.type}->{edge.target}"

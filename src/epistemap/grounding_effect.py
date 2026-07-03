from __future__ import annotations

import csv
import json
from copy import deepcopy
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO

from .models import Edge, GraphBundle

G_ROW_FIELDS = (
    "run_id",
    "subject_id",
    "condition",
    "phase",
    "item_id",
    "claim_id",
    "env",
    "y",
    "p",
    "answer",
    "response",
    "source_anchor",
    "recognized_at",
    "contradiction_available_at",
    "recognition_lag",
    "fair_play_rating",
)


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


def g_evaluation_row(
    *,
    y: int | bool,
    p: float,
    env: str,
    run_id: str = "",
    subject_id: str = "",
    condition: str = "",
    phase: str = "",
    item_id: str = "",
    claim_id: str = "",
    answer: str = "",
    response: str = "",
    source_anchor: str = "",
    recognized_at: Any = "",
    contradiction_available_at: Any = "",
    recognition_lag: float | int | str | None = None,
    fair_play_rating: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a canonical claim-level row for practical G evaluation exports."""

    row: dict[str, Any] = {
        "run_id": run_id,
        "subject_id": subject_id,
        "condition": condition,
        "phase": phase,
        "item_id": item_id,
        "claim_id": claim_id,
        "env": str(env),
        "y": int(y),
        "p": float(p),
        "answer": answer,
        "response": response,
        "source_anchor": source_anchor,
        "recognized_at": recognized_at,
        "contradiction_available_at": contradiction_available_at,
        "recognition_lag": "" if recognition_lag is None else recognition_lag,
        "fair_play_rating": fair_play_rating,
    }
    if not row["env"]:
        raise ValueError("G evaluation rows require a non-empty env label")
    _coerce_row(row)
    if metadata:
        for key, value in metadata.items():
            if key in row:
                raise ValueError(f"metadata key collides with canonical G row field: {key}")
            row[str(key)] = value
    return row


def normalize_g_evaluation_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical G evaluation row from a mapping-like row."""

    return g_evaluation_row(
        y=int(row["y"]),
        p=float(row["p"]),
        env=str(row["env"]),
        run_id=str(row.get("run_id", "")),
        subject_id=str(row.get("subject_id", "")),
        condition=str(row.get("condition", "")),
        phase=str(row.get("phase", "")),
        item_id=str(row.get("item_id", "")),
        claim_id=str(row.get("claim_id", "")),
        answer=str(row.get("answer", "")),
        response=str(row.get("response", "")),
        source_anchor=str(row.get("source_anchor", "")),
        recognized_at=row.get("recognized_at", ""),
        contradiction_available_at=row.get("contradiction_available_at", ""),
        recognition_lag=row.get("recognition_lag", ""),
        fair_play_rating=str(row.get("fair_play_rating", "")),
        metadata={key: value for key, value in row.items() if key not in G_ROW_FIELDS},
    )


def g_rows_to_csv(rows: Iterable[Mapping[str, Any]], *, extra_fields: Sequence[str] = ()) -> str:
    """Serialize G evaluation rows to CSV with a stable canonical header."""

    materialized = [normalize_g_evaluation_row(row) for row in rows]
    extra_field_set = {str(field) for field in extra_fields}
    discovered = sorted(
        {
            str(key)
            for row in materialized
            for key in row
            if key not in G_ROW_FIELDS and key not in extra_field_set
        }
    )
    fieldnames = (
        list(G_ROW_FIELDS)
        + [str(field) for field in extra_fields if str(field) not in G_ROW_FIELDS]
        + discovered
    )
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(materialized)
    return output.getvalue()


def write_g_rows_csv(
    rows: Iterable[Mapping[str, Any]],
    destination: str | Path | TextIO,
    *,
    extra_fields: Sequence[str] = (),
) -> None:
    """Write canonical G evaluation rows to a CSV path or text file object."""

    text = g_rows_to_csv(rows, extra_fields=extra_fields)
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        return
    Path(destination).write_text(text, encoding="utf-8")


def read_g_rows_csv(source: str | Path | TextIO) -> list[dict[str, Any]]:
    """Read canonical G evaluation rows from a CSV path or text file object."""

    if hasattr(source, "read"):
        text = source.read()  # type: ignore[union-attr]
    else:
        text = Path(source).read_text(encoding="utf-8")
    reader = csv.DictReader(StringIO(text))
    return [normalize_g_evaluation_row(row) for row in reader]


def g_experiment_manifest(
    *,
    experiment_id: str,
    row_file: str,
    evaluation_target: str,
    name: str = "",
    corpus: str = "",
    conditions: Sequence[str] = (),
    phases: Sequence[str] = (),
    reliability_treatment: str = "",
    temporal_assumptions: Mapping[str, Any] | None = None,
    fair_play_policy: Mapping[str, Any] | None = None,
    row_count: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe a G row export well enough for later comparison and audit."""

    if not str(experiment_id).strip():
        raise ValueError("G experiment manifests require a non-empty experiment_id")
    if not str(row_file).strip():
        raise ValueError("G experiment manifests require a non-empty row_file")
    if not str(evaluation_target).strip():
        raise ValueError("G experiment manifests require a non-empty evaluation_target")
    manifest: dict[str, Any] = {
        "manifest_kind": "epistemap_g_experiment",
        "schema_version": "0.1",
        "experiment_id": str(experiment_id),
        "name": str(name),
        "row_file": str(row_file),
        "evaluation_target": str(evaluation_target),
        "corpus": str(corpus),
        "conditions": [str(condition) for condition in conditions],
        "phases": [str(phase) for phase in phases],
        "reliability_treatment": str(reliability_treatment),
        "temporal_assumptions": dict(temporal_assumptions or {}),
        "fair_play_policy": dict(fair_play_policy or {}),
        "row_count": row_count,
        "metadata": dict(metadata or {}),
    }
    return {key: value for key, value in manifest.items() if not _blank_manifest_value(value)}


def write_g_experiment_manifest(
    manifest: Mapping[str, Any],
    destination: str | Path | TextIO,
) -> None:
    """Write a G experiment manifest as deterministic JSON."""

    text = json.dumps(dict(manifest), indent=2, sort_keys=True) + "\n"
    if hasattr(destination, "write"):
        destination.write(text)  # type: ignore[union-attr]
        return
    Path(destination).write_text(text, encoding="utf-8")


def read_g_experiment_manifest(source: str | Path | TextIO) -> dict[str, Any]:
    """Read a G experiment manifest from a JSON path or text file object."""

    if hasattr(source, "read"):
        text = source.read()  # type: ignore[union-attr]
    else:
        text = Path(source).read_text(encoding="utf-8")
    manifest = json.loads(text)
    if manifest.get("manifest_kind") != "epistemap_g_experiment":
        raise ValueError("not an Epistemap G experiment manifest")
    return manifest


def g_experiment_summary(
    rows: Iterable[Mapping[str, Any]],
    *,
    manifest: Mapping[str, Any] | None = None,
    group_by: str = "condition",
    target_env: str = "K",
    clean_env: str = "C",
    weights: tuple[float, float, float] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
) -> dict[str, Any]:
    """Summarize G estimates for a row export, optionally grouped by a row field."""

    materialized = [normalize_g_evaluation_row(row) for row in rows]
    overall = g_estimate(materialized, target_env=target_env, clean_env=clean_env, weights=weights)
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in materialized:
        label = str(row.get(group_by, "") or "unlabeled")
        groups.setdefault(label, []).append(row)
    grouped = {
        label: g_estimate(group_rows, target_env=target_env, clean_env=clean_env, weights=weights)
        for label, group_rows in sorted(groups.items())
    }
    return {
        "summary_kind": "epistemap_g_experiment_summary",
        "manifest": dict(manifest or {}),
        "group_by": group_by,
        "overall": overall,
        "groups": grouped,
        "row_count": len(materialized),
        "interpretation": (
            "G summarizes learner/model grounding effectiveness for explicit evaluation rows; "
            "it is not a source-truth or provenance score."
        ),
    }


def g_experiment_summary_from_files(
    rows_csv: str | Path,
    *,
    manifest_json: str | Path | None = None,
    out_json: str | Path | None = None,
    group_by: str = "condition",
    target_env: str = "K",
    clean_env: str = "C",
    weights: tuple[float, float, float] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
) -> dict[str, Any]:
    """Read G row and manifest files, then write or return an experiment summary."""

    manifest = read_g_experiment_manifest(manifest_json) if manifest_json is not None else {}
    summary = g_experiment_summary(
        read_g_rows_csv(rows_csv),
        manifest=manifest,
        group_by=group_by,
        target_env=target_env,
        clean_env=clean_env,
        weights=weights,
    )
    if out_json is not None:
        _write_json(out_json, summary)
    return summary


def g_summary_comparison(
    summaries: Iterable[Mapping[str, Any]],
    *,
    baseline_id: str | None = None,
) -> dict[str, Any]:
    """Compare multiple G experiment summaries by overall G."""

    materialized = [dict(summary) for summary in summaries]
    rows = [_summary_comparison_row(summary) for summary in materialized]
    rows.sort(key=lambda row: row["G"], reverse=True)
    if baseline_id is None and rows:
        baseline_id = rows[-1]["experiment_id"]
    baseline = next((row for row in rows if row["experiment_id"] == baseline_id), None)
    baseline_g = float(baseline["G"]) if baseline is not None else 0.0
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["delta_from_baseline"] = row["G"] - baseline_g
    return {
        "comparison_kind": "epistemap_g_summary_comparison",
        "baseline_id": baseline_id,
        "summaries": rows,
        "interpretation": (
            "Compares learner/model grounding-effectiveness summaries; "
            "not a source-truth or provenance ranking."
        ),
    }


def g_summary_comparison_from_files(
    summary_jsons: Iterable[str | Path],
    *,
    baseline_id: str | None = None,
    out_json: str | Path | None = None,
) -> dict[str, Any]:
    """Read G summary JSON files, then write or return a comparison."""

    summaries = [json.loads(Path(path).read_text(encoding="utf-8")) for path in summary_jsons]
    comparison = g_summary_comparison(summaries, baseline_id=baseline_id)
    if out_json is not None:
        _write_json(out_json, comparison)
    return comparison


def g_experiment_comparison(
    experiments: Iterable[Mapping[str, Any]],
    *,
    group_by: str = "condition",
    baseline_id: str | None = None,
    target_env: str = "K",
    clean_env: str = "C",
    weights: tuple[float, float, float] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
) -> dict[str, Any]:
    """Compare experiments supplied as mappings with `rows` and optional `manifest`."""

    summaries = [
        g_experiment_summary(
            experiment["rows"],
            manifest=experiment.get("manifest", {}),
            group_by=group_by,
            target_env=target_env,
            clean_env=clean_env,
            weights=weights,
        )
        for experiment in experiments
    ]
    comparison = g_summary_comparison(summaries, baseline_id=baseline_id)
    comparison["group_by"] = group_by
    return comparison


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


def _blank_manifest_value(value: Any) -> bool:
    return value is None or value == "" or value == ()


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(dict(payload), indent=2), encoding="utf-8")


def _summary_comparison_row(summary: Mapping[str, Any]) -> dict[str, Any]:
    manifest = summary.get("manifest", {})
    if not isinstance(manifest, Mapping):
        manifest = {}
    overall = summary.get("overall", {})
    if not isinstance(overall, Mapping):
        overall = {}
    experiment_id = str(manifest.get("experiment_id", "") or manifest.get("name", "") or "unlabeled")
    row: dict[str, Any] = {
        "experiment_id": experiment_id,
        "name": str(manifest.get("name", "")),
        "evaluation_target": str(manifest.get("evaluation_target", "")),
        "corpus": str(manifest.get("corpus", "")),
        "row_count": int(summary.get("row_count", 0) or manifest.get("row_count", 0) or 0),
        "G": float(overall.get("G", 0.0)),
        "n": dict(overall.get("n", {})) if isinstance(overall.get("n", {}), Mapping) else {},
    }
    if "warning" in overall:
        row["warning"] = overall["warning"]
    return row


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

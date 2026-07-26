from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

SEMANTICALLY_RESTRICTED_DIMENSIONS = {
    "extraction_fidelity",
    "source_reliability",
    "reviewer_endorsement",
}


class CalibrationSample(BaseModel):
    subject_id: str
    predicted: float = Field(ge=0.0, le=1.0)
    observed: float = Field(ge=0.0, le=1.0)
    dimension: str = "response_correctness"
    event: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CalibrationEligibilityError(ValueError):
    pass


def brier_score(samples: list[CalibrationSample]) -> float | None:
    if not samples:
        return None
    return sum((item.predicted - item.observed) ** 2 for item in samples) / len(samples)


def log_loss(samples: list[CalibrationSample], *, epsilon: float = 1e-15) -> float | None:
    if not samples:
        return None
    total = 0.0
    for item in samples:
        predicted = min(max(item.predicted, epsilon), 1.0 - epsilon)
        total += -(item.observed * math.log(predicted) + (1.0 - item.observed) * math.log(1.0 - predicted))
    return total / len(samples)


def calibration_bins(samples: list[CalibrationSample], *, bin_count: int = 10) -> list[dict[str, Any]]:
    if bin_count <= 0:
        raise ValueError("bin_count must be positive")
    bins: list[dict[str, Any]] = []
    for index in range(bin_count):
        lower = index / bin_count
        upper = (index + 1) / bin_count
        members = [item for item in samples if _in_bin(item.predicted, lower, upper, include_upper=index == bin_count - 1)]
        bins.append(_bin_payload(lower, upper, members))
    return bins


def expected_calibration_error(samples: list[CalibrationSample], *, bin_count: int = 10) -> float | None:
    if not samples:
        return None
    total = 0.0
    for item in calibration_bins(samples, bin_count=bin_count):
        total += (item["count"] / len(samples)) * abs(item["mean_prediction"] - item["mean_observed"])
    return total


def calibration_report(
    samples: list[CalibrationSample],
    *,
    event: str,
    dimension: str = "response_correctness",
    predicted_event: str = "",
    outcome_interpretation: str = "",
    sample_selection_policy: str = "",
    candidate_set_policy: str = "",
    bin_count: int = 10,
    minimum_bin_size: int = 20,
) -> dict[str, Any]:
    predicted_event = predicted_event or event
    outcome_interpretation = outcome_interpretation or _default_outcome_interpretation(dimension)
    sample_selection_policy = sample_selection_policy or "all samples matching event and dimension"
    filtered = [item for item in samples if item.event == event and item.dimension == dimension]
    _validate_calibration_eligibility(
        filtered,
        dimension=dimension,
        predicted_event=predicted_event,
        outcome_interpretation=outcome_interpretation,
        sample_selection_policy=sample_selection_policy,
        candidate_set_policy=candidate_set_policy,
    )
    bins = calibration_bins(filtered, bin_count=bin_count)
    warnings = []
    underpowered_bins = [
        {
            "lower": item["lower"],
            "upper": item["upper"],
            "count": item["count"],
            "minimum_bin_size": minimum_bin_size,
        }
        for item in bins
        if item["count"] and item["count"] < minimum_bin_size
    ]
    if underpowered_bins:
        warnings.append("Some populated calibration bins are underpowered.")
    discrimination = _discrimination_payload(filtered)
    abstention = _abstention_payload(filtered)
    evidence_coverage = _evidence_coverage_payload(filtered)
    brier = brier_score(filtered)
    loss = log_loss(filtered)
    ece = expected_calibration_error(filtered, bin_count=bin_count)
    return {
        "report_kind": "epistemap_calibration_report",
        "event": event,
        "predicted_event": predicted_event,
        "outcome_interpretation": outcome_interpretation,
        "sample_selection_policy": sample_selection_policy,
        "candidate_set_policy": candidate_set_policy,
        "dimension": dimension,
        "sample_count": len(filtered),
        "brier_score": brier,
        "log_loss": loss,
        "expected_calibration_error": ece,
        "bins": bins,
        "calibration": {
            "brier_score": brier,
            "log_loss": loss,
            "expected_calibration_error": ece,
            "bins": bins,
            "underpowered_bins": underpowered_bins,
        },
        "discrimination": discrimination,
        "abstention": abstention,
        "evidence_coverage": evidence_coverage,
        "warnings": warnings,
        "interpretation": "Calibration requires declared predicted events and observed outcomes; missing predictions are not treated as zero.",
    }


def calibration_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Epistemap Calibration Report",
        "",
        f"- Event: `{report.get('event', '')}`",
        f"- Predicted event: `{report.get('predicted_event', '')}`",
        f"- Dimension: `{report.get('dimension', '')}`",
        f"- Outcome interpretation: `{report.get('outcome_interpretation', '')}`",
        f"- Sample selection: `{report.get('sample_selection_policy', '')}`",
        f"- Samples: `{report.get('sample_count', 0)}`",
        f"- Brier score: `{_fmt(report.get('brier_score'))}`",
        f"- Log loss: `{_fmt(report.get('log_loss'))}`",
        f"- Expected calibration error: `{_fmt(report.get('expected_calibration_error'))}`",
        "",
        "| Bin | Count | Mean prediction | Mean observed |",
        "| --- | ---: | ---: | ---: |",
    ]
    for item in report.get("bins", []):
        lines.append(
            f"| {item['lower']:.2f}-{item['upper']:.2f} | {item['count']} | "
            f"{item['mean_prediction']:.3f} | {item['mean_observed']:.3f} |"
        )
    if report.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    discrimination = report.get("discrimination", {}) or {}
    abstention = report.get("abstention", {}) or {}
    coverage = report.get("evidence_coverage", {}) or {}
    lines.extend(
        [
            "",
            "## Separation",
            "",
            f"- Discrimination AUC proxy: `{_fmt(discrimination.get('auc_proxy'))}`",
            f"- Abstentions: `{abstention.get('abstention_count', 0)}`",
            f"- Evidence coverage samples: `{coverage.get('sample_count', 0)}`",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def write_calibration_report(report: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_calibration_report_markdown(report: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(calibration_report_markdown(report), encoding="utf-8")


def _bin_payload(lower: float, upper: float, members: list[CalibrationSample]) -> dict[str, Any]:
    count = len(members)
    mean_prediction = sum(item.predicted for item in members) / count if count else 0.0
    mean_observed = sum(item.observed for item in members) / count if count else 0.0
    return {
        "lower": lower,
        "upper": upper,
        "count": count,
        "mean_prediction": mean_prediction,
        "mean_observed": mean_observed,
    }


def _validate_calibration_eligibility(
    samples: list[CalibrationSample],
    *,
    dimension: str,
    predicted_event: str,
    outcome_interpretation: str,
    sample_selection_policy: str,
    candidate_set_policy: str,
) -> None:
    if not predicted_event:
        raise CalibrationEligibilityError("calibration requires a declared predicted event")
    if not outcome_interpretation:
        raise CalibrationEligibilityError("calibration requires an outcome interpretation")
    if not sample_selection_policy:
        raise CalibrationEligibilityError("calibration requires a sample selection policy")
    if dimension == "identity_resolution":
        if not candidate_set_policy:
            raise CalibrationEligibilityError("identity_resolution calibration requires a candidate-set policy")
        if any(item.metadata.get("reviewed_outcome") is not True for item in samples):
            raise CalibrationEligibilityError("identity_resolution calibration requires reviewed match/non-match outcomes")
    if dimension in SEMANTICALLY_RESTRICTED_DIMENSIONS:
        if not all(item.metadata.get("explicit_probabilistic_interpretation") is True for item in samples):
            raise CalibrationEligibilityError(
                f"{dimension} calibration requires resolved outcomes and an explicit probabilistic interpretation"
            )


def _default_outcome_interpretation(dimension: str) -> str:
    if dimension == "response_correctness":
        return "observed=1 means the selected response is correct; observed=0 means it is incorrect"
    return ""


def _discrimination_payload(samples: list[CalibrationSample]) -> dict[str, Any]:
    positives = [item.predicted for item in samples if item.observed >= 0.5]
    negatives = [item.predicted for item in samples if item.observed < 0.5]
    mean_positive = sum(positives) / len(positives) if positives else None
    mean_negative = sum(negatives) / len(negatives) if negatives else None
    auc_proxy = None if mean_positive is None or mean_negative is None else mean_positive - mean_negative
    return {
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "mean_positive_prediction": mean_positive,
        "mean_negative_prediction": mean_negative,
        "auc_proxy": auc_proxy,
    }


def _abstention_payload(samples: list[CalibrationSample]) -> dict[str, Any]:
    abstentions = [item for item in samples if item.metadata.get("abstained") is True]
    return {
        "abstention_count": len(abstentions),
        "abstention_rate": len(abstentions) / len(samples) if samples else None,
    }


def _evidence_coverage_payload(samples: list[CalibrationSample]) -> dict[str, Any]:
    values = [
        float(item.metadata["evidence_coverage"])
        for item in samples
        if item.metadata.get("evidence_coverage") is not None
    ]
    return {
        "sample_count": len(values),
        "mean": sum(values) / len(values) if values else None,
    }


def _in_bin(value: float, lower: float, upper: float, *, include_upper: bool) -> bool:
    if include_upper:
        return lower <= value <= upper
    return lower <= value < upper


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6f}"

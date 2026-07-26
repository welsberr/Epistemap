from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class CalibrationSample(BaseModel):
    subject_id: str
    predicted: float = Field(ge=0.0, le=1.0)
    observed: float = Field(ge=0.0, le=1.0)
    dimension: str = "response_correctness"
    event: str
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    bin_count: int = 10,
    minimum_bin_size: int = 20,
) -> dict[str, Any]:
    filtered = [item for item in samples if item.event == event and item.dimension == dimension]
    bins = calibration_bins(filtered, bin_count=bin_count)
    warnings = []
    if any(item["count"] and item["count"] < minimum_bin_size for item in bins):
        warnings.append("Some populated calibration bins are underpowered.")
    return {
        "report_kind": "epistemap_calibration_report",
        "event": event,
        "dimension": dimension,
        "sample_count": len(filtered),
        "brier_score": brier_score(filtered),
        "log_loss": log_loss(filtered),
        "expected_calibration_error": expected_calibration_error(filtered, bin_count=bin_count),
        "bins": bins,
        "warnings": warnings,
        "interpretation": "Calibration requires declared predicted events and observed outcomes; missing predictions are not treated as zero.",
    }


def calibration_report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Epistemap Calibration Report",
        "",
        f"- Event: `{report.get('event', '')}`",
        f"- Dimension: `{report.get('dimension', '')}`",
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


def _in_bin(value: float, lower: float, upper: float, *, include_upper: bool) -> bool:
    if include_upper:
        return lower <= value <= upper
    return lower <= value < upper


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6f}"

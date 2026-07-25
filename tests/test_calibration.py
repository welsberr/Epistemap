from __future__ import annotations

import pytest
from pydantic import ValidationError

from epistemap import (
    CalibrationSample,
    brier_score,
    calibration_report,
    calibration_report_markdown,
    expected_calibration_error,
    log_loss,
)


def test_calibration_scores_handle_perfect_and_empty_samples():
    samples = [
        CalibrationSample(subject_id="a", predicted=1.0, observed=1.0, event="answer_correct"),
        CalibrationSample(subject_id="b", predicted=0.0, observed=0.0, event="answer_correct"),
    ]

    assert brier_score(samples) == 0.0
    assert log_loss(samples) < 1e-12
    assert brier_score([]) is None
    assert log_loss([]) is None


def test_calibration_report_identifies_overconfident_errors():
    samples = [
        CalibrationSample(subject_id="a", predicted=0.9, observed=0.0, event="answer_correct"),
        CalibrationSample(subject_id="b", predicted=0.8, observed=0.0, event="answer_correct"),
        CalibrationSample(subject_id="c", predicted=0.7, observed=1.0, event="answer_correct"),
    ]

    report = calibration_report(samples, event="answer_correct", bin_count=3, minimum_bin_size=10)

    assert report["sample_count"] == 3
    assert report["brier_score"] > 0.4
    assert expected_calibration_error(samples, bin_count=3) > 0
    assert "underpowered" in report["warnings"][0]
    assert "Epistemap Calibration Report" in calibration_report_markdown(report)


def test_calibration_sample_refuses_out_of_range_predictions():
    with pytest.raises(ValidationError):
        CalibrationSample(subject_id="bad", predicted=1.5, observed=1.0, event="answer_correct")

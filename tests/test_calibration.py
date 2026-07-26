from __future__ import annotations

import pytest
from pydantic import ValidationError

from epistemap import (
    CalibrationEligibilityError,
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
    assert report["calibration"]["underpowered_bins"][0]["minimum_bin_size"] == 10
    assert "discrimination" in report
    assert "abstention" in report
    assert "evidence_coverage" in report
    assert "Epistemap Calibration Report" in calibration_report_markdown(report)


def test_calibration_sample_refuses_out_of_range_predictions():
    with pytest.raises(ValidationError):
        CalibrationSample(subject_id="bad", predicted=1.5, observed=1.0, event="answer_correct")


def test_calibration_contract_accepts_response_correctness_empty_and_abstaining_samples():
    empty = calibration_report([], event="answer_correct")
    abstaining = calibration_report(
        [
            CalibrationSample(
                subject_id="a",
                predicted=0.5,
                observed=0.0,
                event="answer_correct",
                metadata={"abstained": True, "evidence_coverage": 0.25},
            )
        ],
        event="answer_correct",
        bin_count=2,
        minimum_bin_size=1,
    )

    assert empty["sample_count"] == 0
    assert empty["brier_score"] is None
    assert abstaining["abstention"]["abstention_count"] == 1
    assert abstaining["evidence_coverage"]["mean"] == 0.25


def test_identity_resolution_calibration_requires_reviewed_outcomes_and_candidate_policy():
    samples = [
        CalibrationSample(
            subject_id="work::candidate",
            predicted=0.9,
            observed=1.0,
            event="same_work",
            dimension="identity_resolution",
        )
    ]

    with pytest.raises(CalibrationEligibilityError, match="candidate-set policy"):
        calibration_report(
            samples,
            event="same_work",
            dimension="identity_resolution",
            outcome_interpretation="observed=1 means reviewer confirmed same work",
        )

    with pytest.raises(CalibrationEligibilityError, match="reviewed match/non-match"):
        calibration_report(
            samples,
            event="same_work",
            dimension="identity_resolution",
            outcome_interpretation="observed=1 means reviewer confirmed same work",
            candidate_set_policy="top candidate from resolver fixture",
        )

    reviewed = [samples[0].model_copy(update={"metadata": {"reviewed_outcome": True}})]
    report = calibration_report(
        reviewed,
        event="same_work",
        dimension="identity_resolution",
        outcome_interpretation="observed=1 means reviewer confirmed same work",
        candidate_set_policy="top candidate from resolver fixture",
        minimum_bin_size=1,
    )

    assert report["candidate_set_policy"] == "top candidate from resolver fixture"
    assert report["sample_count"] == 1


def test_restricted_dimensions_require_explicit_probabilistic_interpretation():
    samples = [
        CalibrationSample(
            subject_id="source::1",
            predicted=0.8,
            observed=1.0,
            event="source_reliable",
            dimension="source_reliability",
        )
    ]

    with pytest.raises(CalibrationEligibilityError, match="explicit probabilistic interpretation"):
        calibration_report(
            samples,
            event="source_reliable",
            dimension="source_reliability",
            outcome_interpretation="observed=1 means resolved external reliability outcome",
        )

    allowed = [
        samples[0].model_copy(update={"metadata": {"explicit_probabilistic_interpretation": True}})
    ]
    report = calibration_report(
        allowed,
        event="source_reliable",
        dimension="source_reliability",
        outcome_interpretation="observed=1 means resolved external reliability outcome",
        sample_selection_policy="reviewed fixture sources only",
        minimum_bin_size=1,
    )

    assert report["sample_selection_policy"] == "reviewed fixture sources only"

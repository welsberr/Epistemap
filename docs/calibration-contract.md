# Calibration Contract

Status: W4 local implementation.

Calibration reports are only meaningful when the prediction, outcome, sample
selection, and assessment dimension describe the same event. Epistemap therefore
requires every report to declare:

- `predicted_event`;
- `outcome_interpretation`;
- `sample_selection_policy`;
- `dimension`.

`response_correctness` is permitted by default. If no interpretation is
provided, Epistemap uses: `observed=1 means the selected response is correct;
observed=0 means it is incorrect`.

`identity_resolution` is permitted only when:

- reviewed match/non-match outcomes are present on every included sample using
  `metadata.reviewed_outcome=true`;
- the caller declares a `candidate_set_policy`;
- the caller declares an outcome interpretation.

`extraction_fidelity`, `source_reliability`, and `reviewer_endorsement` are
rejected unless every included sample carries
`metadata.explicit_probabilistic_interpretation=true` and the caller supplies a
resolved outcome interpretation. These dimensions are often useful assessment
dimensions, but they are not automatically calibrated events.

Reports keep legacy top-level fields such as `brier_score`, `log_loss`,
`expected_calibration_error`, and `bins`. They also separate:

- `calibration`: Brier, log loss, ECE, bins, and underpowered-bin metadata;
- `discrimination`: positive/negative counts and a simple mean-gap AUC proxy;
- `abstention`: abstention count and rate;
- `evidence_coverage`: coverage sample count and mean when supplied.

Missing predictions are not converted to zero. `CalibrationSample.predicted` is
required and bounded from 0 through 1.

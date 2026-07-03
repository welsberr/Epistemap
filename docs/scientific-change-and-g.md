# Scientific Change, G, and Knowledge Graph Operations

Epistemap should preserve a strict distinction between graph evidence,
source reliability, and learner/model grounding effectiveness.

The practical `G` metric from the biological-learning-laws and machine-learning
work is a grounding-effectiveness estimate over claim-level evaluation rows. It
is computed from:

- `S_T`: truth tracking and calibration, using normalized Brier score on target
  or shifted items;
- `S_D`: discrimination, using normalized target AUC;
- `S_R`: robustness, comparing discrimination on clean/reference items with
  target/shifted items.

`G` is useful for asking whether an intervention, graph view, mentoring
condition, or source-spine transformation improves calibrated source-grounded
performance. It is not a provenance score, source-trust score, or truth oracle.

## Reliability Sensitivity

There is merit in asking how `delta_G` changes when a graph component is treated
under different reliability assumptions. The result should be interpreted as
counterfactual sensitivity:

```text
delta_G(level) = G_after(level) - G_before
```

This can show that learner/model truth tracking is robust, fragile, improved,
or degraded when a source bundle, claim path, explanation, or concept relation
is presented under different trust assumptions. It cannot decide whether the
component is true.

Useful outputs include:

- `G` by condition;
- `delta_G` from a baseline condition;
- component shifts in `S_T`, `S_D`, and `S_R`;
- unsupported assertion, fabricated citation, and abstention rates alongside
  `G`;
- graph regions where accuracy rises but calibration or transfer does not.

## Scientific Revolutions

Kuhn-style scientific revolutions should be represented as graph
transformations, not as ordinary claim additions. A candidate transformation can
retain, revise, supersede, reject, or reframe concepts and claims. Knowledge
graph operations can help expose the consequences of that transformation, but
they should not be treated as an automatic tribunal for deciding that a
revolution should occur.

Graph operations may help evaluate whether a proposed framework:

- preserves successful evidential constraints from the prior framework;
- resolves anomalies without multiplying ad hoc unsupported claims;
- improves transfer to shifted evaluation cases;
- clarifies concept boundaries and claim dependencies;
- reduces contradiction load without suppressing legitimate uncertainty;
- generates discriminating predictions or useful reclassifications.

The guiding principle is:

> A scientific revolution should improve structured understanding under
> evidential constraint; propaganda often only redistributes doubt.

Denialist material routinely claims to be the leading edge of scientific
revolution. Epistemap should not privilege that claim rhetorically. It should
ask whether the material clarifies knowledge under evidential constraint. If an
intervention mainly increases uncertainty, lowers calibration, degrades
transfer, or adds contradictions without explanatory gain, then graph and `G`
analyses should surface that failure.

## Operational Caution

The correct operational stance is exploratory:

- use `G` for evaluation of learner/model behavior under graph interventions;
- use provenance and source-trust metadata for evidence quality;
- use graph transformations for proposed theory change;
- keep denialist or adversarial source signals explicit;
- avoid converting any single score into an authority marker.


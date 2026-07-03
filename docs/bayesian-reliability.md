# Bayesian Reliability Estimates

Epistemap includes a lightweight Bayesian reliability layer for graph evidence
summaries. The goal is to improve over opaque confidence averages while keeping
the assumptions visible.

The first model is a weighted beta-binomial update:

- support edges contribute weighted success evidence;
- challenge edges contribute weighted failure evidence;
- source confidence, grounding status, source quality, and adversarial stance
  affect evidence weight;
- explicit beta priors define the starting assumption;
- posterior mean, approximate credible interval, and effective sample size are
  reported together.

This is not a truth oracle. It is an auditable posterior support estimate under
the evidence extraction and prior assumptions used for the graph.

## Epistemic Summaries

`epistemic_summary()` now returns both:

- `reliability`: the existing heuristic compatibility score;
- `bayesian_reliability`: a posterior support estimate over support and
  challenge edges.

The Bayesian block includes:

- `prior`: alpha, beta, and prior mean;
- `posterior`: alpha, beta, mean, variance, and approximate credible interval;
- `evidence`: support/challenge weights and effective sample size;
- `stability`: a coarse label based on interval width and evidence weight;
- `prior_sensitivity`: the same evidence under skeptical, neutral, and
  supportive priors.

## Interpretation

Bayesian estimates are most useful when a graph has mixed evidence quality:
strong primary evidence, weaker secondary evidence, adversarial challenges, or
thin evidence. In those cases the output can distinguish a high posterior with
substantial evidence from a high-looking score that is fragile under prior
choice.

For scientific-change work, the sensitivity report is especially important.
Legitimate revolutions should usually improve explanatory and evidential
coherence under multiple priors as new evidence arrives. Denialist material
often depends on flattening source reliability or amplifying low-weight
challenges; that should appear as fragility, low effective sample size, or
strong prior dependence rather than stable clarification.

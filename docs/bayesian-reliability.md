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
  supportive priors;
- `classification`: a review-triage label and flags for thin evidence, wide
  intervals, prior sensitivity, and mixed support/challenge evidence.

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

## Feature Roadmap

The Bayesian layer changes the next useful Epistemap features from generic
confidence scoring toward auditable assessment workflows.

Implemented:

- compact Markdown rendering for `bayesian_reliability` blocks via
  `bayesian_reliability_markdown()` and
  `write_bayesian_reliability_markdown()`.
- review-triage labels via `classify_bayesian_reliability()`, which classifies
  posterior blocks as `stable_support`, `fragile_support`, `contested`,
  `thin_evidence`, or `prior_sensitive`.
- named prior profiles via `BAYESIAN_PRIOR_PROFILES`,
  `resolve_bayesian_prior_profile()`, `bayesian_evidence_update(...,
  prior_profile=...)`, and profile-aware `bayesian_prior_sensitivity()`.
  Current profiles are `neutral`, `skeptical`, `supportive`,
  `source_conservative`, and `adversarial_aware`.
- graph-level assessment reports via `bayesian_assessment_report()`,
  `bayesian_assessment_markdown()`, and
  `write_bayesian_assessment_markdown()`. Reports batch over claims and
  concepts, rank rows by review urgency, and summarize label and flag counts.

Near-term:

- add CLI support for graph-level epistemic reports once graph bundle loading is
  standardized for downstream repos.

Medium-term:

- let reliability priors be learned or calibrated from reviewed corpora while
  keeping explicit fallback priors available;
- track posterior change over temporal graph slices, so an assessment can show
  when a claim moved from tenable ignorance to strong support or contradiction;
- add experiment manifests that record Bayesian prior profile, evidence
  weighting policy, and graph extraction policy alongside `G` manifests;
- compare Bayesian posterior shifts with `delta_G` to see whether apparently
  stronger graph evidence actually improves learner/model grounding behavior.

Deferred:

- full Bayesian networks over claim dependencies;
- MCMC or heavyweight probabilistic programming dependencies;
- automatic promotion of claims based only on posterior score.

Those are deferred because the immediate value is transparent, reviewable
posterior assessment, not a black-box authority layer.

## Experiment Roadmap

Priority experiments should use the Bayesian layer as an explanatory variable
and `G` as a learner/model outcome measure.

1. Source-quality ablation:
   Compare posterior stability and `G` when source-quality metadata is visible,
   flattened, or adversarial-aware.

2. Denialist-material stress test:
   Build matched graph neighborhoods with genuine challenge evidence versus
   manufactured-doubt signals. Expected useful output is not simple rejection,
   but detection of low effective sample size, prior sensitivity, and failure
   to improve `G`.

3. Temporal tenability experiment:
   Use dated evidence to assess when a claim was reasonably tenable, when it
   became contradicted, and whether models or learners revise after the decisive
   evidence date.

4. Detective-story fair-play experiment:
   Measure whether posterior contradiction signals become available before the
   reveal and whether recognition timing predicts `G` improvement.

5. Notebook/mentor intervention experiment:
   Compare plain source reading, graph neighborhood reading, Bayesian
   reliability summaries, and mentor explanations that explicitly communicate
   uncertainty.

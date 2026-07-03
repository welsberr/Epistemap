# Temporal Epistemic Graphs

Temporal graph operations answer a basic scholarly question:

```text
At time T, what was supportable, contradicted, unresolved, or no longer tenable
given the evidence available by T?
```

This matters for both research history and controlled fiction experiments.
Important evidence, methods, publications, datasets, and instruments become
available at particular times. Before that point, ignorance or error may be
reasonable. After that point, continued assertion may become stale,
irresponsible, or adversarial depending on access and context.

## Metadata Vocabulary

Epistemap reads temporal metadata from nodes, edges, and provenance metadata.
Useful keys include:

- `introduced_at`
- `available_at`
- `observed_at`
- `published_at`
- `validated_at`
- `challenged_at`
- `superseded_at`
- `rejected_at`
- `timestep`

Date values may be ISO dates/datetimes such as `1953-04-25`. Narrative or
experimental sequences may use numeric `timestep` values.

## Core Operations

- `graph_at(bundle, when)`: graph slice available by `when`.
- `evidence_available_at(bundle, node_id, when)`: support/challenge/revision
  evidence available for a node by `when`.
- `claim_status_at(bundle, claim_id, when)`: `supported`, `contradicted`,
  `revised_or_superseded`, `unresolved`, or unavailable/missing.
- `first_contradiction_time(bundle, claim_id)`: earliest available challenge
  edge involving a claim.
- `tenability_window(bundle, claim_id)`: when a claim is introduced and when a
  contradiction or revision bounds its tenability.
- `stale_claims_after(bundle, when)`: active claims still present after
  contradiction or revision is available.
- `timeline_events(bundle)`: sorted dated events from graph metadata.
- `availability_lag(...)`: comparable intervals such as post-contradiction
  persistence.

## Scholarship

Temporal epistemic graphs help avoid presentism while still identifying
post-evidence failure. A claim can be tagged as historically tenable before a
method, instrument, or critical observation existed, then contradicted once the
relevant evidence becomes available.

This allows graph-based timelines to interact with knowledge:

```text
Before evidence E/date D: claim C was tenable.
After evidence E/date D: claim C requires revision or rejection.
```

## Detective-Fiction Experiments

Fair-play detective stories provide a controlled testbed. The graph can track
when a false alibi, suspect claim, or narrative misdirection first appears; when
the clue that contradicts it becomes available to the reader; and when the
denouement confirms the contradiction.

Useful measurements include:

- earliest available contradiction point;
- model or learner recognition point;
- recognition lag;
- claims kept alive after they should be untenable;
- whether graph augmentation improves `G` without relying on late hidden
  evidence.

Stories that violate the reader contract by withholding decisive evidence until
the reveal should be excluded from the gold fair-play set or used as negative
controls.

## Denialist Persistence

The same machinery applies to denialist claims. The relevant question is not
whether a claim was always unreasonable, but when the public evidence made it no
longer tenable. Continued assertion after that point is a graph-visible pattern:
post-contradiction persistence without clarifying explanatory gain.


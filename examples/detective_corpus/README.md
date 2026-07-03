# Detective Corpus Candidate Fixtures

This directory contains provisional candidate annotations for public-domain
detective stories. They are intended to exercise the Epistemap fair-play
detective corpus tooling before gold annotations are produced.

The labels are conservative working labels:

- `fair_play`: the contradiction evidence is annotated as reader-available
  before the denouement.
- `withheld_decisive_evidence`: the decisive observation is not fully available
  to the reader before the explanatory reveal, so the story is useful as a
  control rather than as a fair-play item.

Each candidate includes public source metadata, sidecar path placeholders, one
or more false or misleading claims, and one or more decisive-evidence entries.
Use `validate_detective_story_annotation()` and `detective_corpus_summary()`
before adding a story to an experiment.

Generated sidecars live under `sidecars/`. Each sidecar directory contains an
`epistemap_graph.json` temporal graph and a `fair_play_diagnostic.json` report.
The top-level `sidecars/detective_corpus_sidecars.json` manifest summarizes the
generated sidecars and their fair-play diagnostic ratings.

These fixtures are not final literary scholarship. The intended next step is
human review against the source texts, followed by stable graph and assessment
sidecars for each admitted story.

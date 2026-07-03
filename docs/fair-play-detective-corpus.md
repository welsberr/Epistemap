# Fair-Play Detective Corpus

Epistemap includes a small annotation schema for contradiction-recognition
experiments using fair-play detective fiction. The goal is to create a
controlled corpus where false claims appear before later narrative evidence
contradicts them, and where the contradiction is available to the reader before
the denouement.

The annotation helper is `detective_story_annotation()`. Each story annotation
records:

- story id, title, author, source, license, and public-domain status;
- narrative unit, such as chapter, scene, page, or timestep;
- reveal point;
- fair-play status;
- claim annotations, including false or misleading claims;
- decisive evidence annotations, including the point where contradiction becomes
  available;
- graph, assessment manifest, and validation sidecar references.

Use `validate_detective_story_annotation()` before admitting a story to an
experiment. Validation checks for missing claims, missing false-claim
annotations, missing decisive evidence, evidence that points at unknown claims,
evidence available after reveal, and evidence hidden from the reader.

Use `detective_recognition_g_row()` to convert a model or learner recognition
result into a canonical `G` evaluation row. The row records the story id, claim
id, contradiction availability point, recognition point, recognition lag, and
fair-play rating.

Use `detective_corpus_summary()` to summarize a candidate corpus before running
experiments. The summary counts validation status, fair-play status, claims, and
decisive evidence annotations.

The intended first pilot is 3-5 public-domain stories with human-reviewed
annotations. Exclude or separately classify stories where the decisive evidence
is introduced only at the reveal or is available only to the detective.

Candidate fixtures live under `examples/detective_corpus/candidates/`. These
fixtures are provisional annotations for pipeline validation and experiment
design; they are not gold labels. Each candidate includes source metadata,
sidecar path placeholders, false or misleading claims, and decisive evidence
entries. Treat warning-bearing controls, such as withheld-evidence stories, as
negative or contrast cases rather than fair-play items.

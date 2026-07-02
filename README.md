# Epistemap

Epistemap is a small shared library for provenance-aware knowledge graph
bundles. It provides a neutral node/edge schema, ID helpers, traversal
utilities, graph diagnostics, and adapters that projects can use without
coupling their internal domain models to each other.

Initial users are expected to include GroundRecall and Didactopus:

- GroundRecall can project reviewed concepts, claims, relations, and provenance
  into an Epistemap bundle.
- Didactopus can emit course/pack graphs and consume GroundRecall context
  through the same graph utilities.

The library intentionally stays below domain policy. It does not decide what a
review status means, how a learner should be scored, or how claims should be
promoted. It gives those systems a common graph representation and reusable
operations.


# Performance Decision Gate

**Decision date:** 2026-07-29  
**Decision:** Defer a Rust core.

The Python optimization pass is implemented and released in Epistemap
`v0.1.0a3`/`v0.1.0a4`. Indexed graph views, shared-index diagnostics, bridge
analysis, and batch epistemic/Bayesian reporting meet the current sparse-graph
targets. The checked-in 10× GroundRecall-shaped fixture remains comfortably
within interactive analysis times.

This is not a claim that Epistemap is production-scale or that Python is
always sufficient. The available integration fixture is sanitized and small;
there is not yet a representative full-store GroundRecall artifact, a measured
end-to-end retrieval target, or a memory-pressure profile that would justify a
lower-level rewrite.

Reopen the Rust decision only if a subsequent profile demonstrates one or more
of the following:

- a documented production latency or throughput target is missed by at least 2×;
- CPU-bound Epistemap analysis is at least 40% of end-to-end runtime;
- Python object memory prevents the required graph size;
- a stable graph-analysis core is required by non-Python consumers;
- process-based parallelism is operationally unsuitable.

Until then, prioritize graph semantics, larger sanitized integration bundles,
retrieval-quality measurements, and MCP host integration. Do not infer a
performance guarantee from the local fixture timings.

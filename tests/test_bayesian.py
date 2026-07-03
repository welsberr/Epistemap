from __future__ import annotations

from epistemap import (
    Edge,
    Node,
    bayesian_evidence_update,
    bayesian_prior_sensitivity,
    beta_binomial_posterior,
)


def test_beta_binomial_posterior_moves_toward_weighted_success() -> None:
    posterior = beta_binomial_posterior(success_weight=4.0, failure_weight=1.0)

    assert posterior["posterior"]["mean"] > 0.5
    assert posterior["posterior"]["credible_interval"]["lower"] < posterior["posterior"]["mean"]
    assert posterior["evidence"]["effective_sample_size"] == 5.0
    assert "not a truth oracle" in posterior["interpretation"]


def test_bayesian_evidence_update_downweights_low_trust_adversarial_challenge() -> None:
    nodes = {
        "obs::paper": Node(
            id="obs::paper",
            type="observation",
            status="grounded",
            metadata={"source_quality": "peer_reviewed"},
        ),
        "claim::denial": Node(
            id="claim::denial",
            type="claim",
            confidence=0.2,
            metadata={"source_quality": "low", "source_stance": "manufactured_doubt"},
        ),
    }
    posterior = bayesian_evidence_update(
        support_edges=[Edge(source="obs::paper", target="claim::main", type="supports_claim", confidence=0.9)],
        challenge_edges=[Edge(source="claim::denial", target="claim::main", type="contradicts")],
        nodes_by_id=nodes,
    )

    assert posterior["evidence"]["support_weights"][0] > posterior["evidence"]["challenge_weights"][0]
    assert posterior["posterior"]["mean"] > 0.55
    assert posterior["stability"] in {"fragile", "moderate", "stable"}


def test_bayesian_prior_sensitivity_reports_fragility_range() -> None:
    sensitivity = bayesian_prior_sensitivity(
        support_edges=[Edge(source="obs::paper", target="claim::main", type="supports_claim", confidence=0.8)],
        challenge_edges=[],
        priors={"skeptical": (1.0, 3.0), "supportive": (3.0, 1.0)},
    )

    assert sensitivity["mean_range"] > 0
    assert (
        sensitivity["estimates"]["supportive"]["posterior"]["mean"]
        > sensitivity["estimates"]["skeptical"]["posterior"]["mean"]
    )
    assert "Prior sensitivity" in sensitivity["interpretation"]

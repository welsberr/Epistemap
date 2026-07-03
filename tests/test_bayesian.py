from __future__ import annotations

from epistemap import (
    Edge,
    Node,
    bayesian_evidence_update,
    bayesian_prior_sensitivity,
    bayesian_reliability_markdown,
    beta_binomial_posterior,
    classify_bayesian_reliability,
    write_bayesian_reliability_markdown,
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


def test_bayesian_reliability_markdown_renders_posterior_and_sensitivity(tmp_path) -> None:
    reliability = bayesian_evidence_update(
        support_edges=[Edge(source="obs::paper", target="claim::main", type="supports_claim", confidence=0.8)],
        challenge_edges=[Edge(source="claim::challenge", target="claim::main", type="contradicts", confidence=0.2)],
    )
    reliability["prior_sensitivity"] = bayesian_prior_sensitivity(
        support_edges=[Edge(source="obs::paper", target="claim::main", type="supports_claim", confidence=0.8)],
        challenge_edges=[Edge(source="claim::challenge", target="claim::main", type="contradicts", confidence=0.2)],
    )
    destination = tmp_path / "bayesian.md"

    markdown = bayesian_reliability_markdown(reliability)
    write_bayesian_reliability_markdown(reliability, destination)

    assert "# Epistemap Bayesian Reliability" in markdown
    assert "Posterior mean" in markdown
    assert "Assessment label" in markdown
    assert "Prior Sensitivity" in markdown
    assert "| Support |" in markdown
    assert destination.read_text(encoding="utf-8") == markdown


def test_classify_bayesian_reliability_labels_stable_support() -> None:
    reliability = beta_binomial_posterior(success_weight=10.0, failure_weight=0.0)
    reliability["stability"] = "stable"

    classification = classify_bayesian_reliability(reliability)

    assert classification["label"] == "stable_support"
    assert classification["flags"] == []
    assert classification["metrics"]["posterior_mean"] > 0.75
    assert "not automatic promotion authority" in classification["interpretation"]


def test_classify_bayesian_reliability_labels_thin_and_prior_sensitive() -> None:
    thin = beta_binomial_posterior(success_weight=0.2, failure_weight=0.0)
    sensitive = beta_binomial_posterior(success_weight=4.0, failure_weight=1.0)
    sensitive["prior_sensitivity"] = {"mean_range": 0.3}

    assert classify_bayesian_reliability(thin)["label"] == "thin_evidence"
    sensitivity_classification = classify_bayesian_reliability(sensitive)
    assert sensitivity_classification["label"] == "prior_sensitive"
    assert "prior_sensitive" in sensitivity_classification["flags"]


def test_classify_bayesian_reliability_labels_contested_or_fragile_support() -> None:
    contested = beta_binomial_posterior(success_weight=3.0, failure_weight=3.0)
    contested["evidence"]["support_edge_count"] = 1
    contested["evidence"]["challenge_edge_count"] = 1
    fragile = beta_binomial_posterior(success_weight=4.0, failure_weight=0.6)

    contested_classification = classify_bayesian_reliability(contested)
    fragile_classification = classify_bayesian_reliability(fragile)

    assert contested_classification["label"] == "contested"
    assert "mixed_support_challenge" in contested_classification["flags"]
    assert fragile_classification["label"] in {"fragile_support", "prior_sensitive", "thin_evidence"}


def test_classify_bayesian_reliability_flags_zero_weight_challenges() -> None:
    contested = beta_binomial_posterior(success_weight=3.0, failure_weight=0.0)
    contested["evidence"]["support_edge_count"] = 1
    contested["evidence"]["challenge_edge_count"] = 1

    classification = classify_bayesian_reliability(contested)

    assert "mixed_support_challenge" in classification["flags"]
    assert classification["metrics"]["challenge_edge_count"] == 1

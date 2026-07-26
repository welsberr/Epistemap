from __future__ import annotations

import argparse
import json
from pathlib import Path

from .detective_corpus import (
    apply_detective_anchor_review_csv,
    detective_corpus_anchor_review_template,
    detective_g_collection_template,
    merge_detective_g_run_sheets,
    read_detective_story_annotation,
    unblind_detective_g_run_sheets,
    validate_detective_g_collection_csv,
    write_blinded_detective_g_run_sheets,
    write_detective_anchor_review_template_csv,
    write_detective_corpus_sidecars,
    write_detective_g_collection_template_csv,
    write_detective_g_experiment_manifest_from_csv,
    write_detective_g_run_sheets_from_csv,
)
from .epistemic import bayesian_assessment_report, write_bayesian_assessment_markdown
from .genealogy import write_genealogy_graph_bundle
from .grounding_effect import (
    g_experiment_summary_from_files,
    g_summary_comparison_from_files,
    write_g_experiment_summary_markdown,
    write_g_summary_comparison_markdown,
)
from .io import load_graph_bundle
from .installed_matrix import run_installed_matrix
from .treatment_manifest import detective_treatment_manifest, write_detective_treatment_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Epistemap command-line tools.")
    subparsers = parser.add_subparsers(dest="command")

    summary = subparsers.add_parser("g-summary", help="Summarize G rows from a CSV export.")
    summary.add_argument("rows_csv")
    summary.add_argument("--manifest", default=None, help="Optional Epistemap G experiment manifest JSON.")
    summary.add_argument("--out", default=None, help="Optional output summary JSON path.")
    summary.add_argument("--out-md", default=None, help="Optional output Markdown report path.")
    summary.add_argument("--group-by", default="condition")
    summary.add_argument("--target-env", default="K")
    summary.add_argument("--clean-env", default="C")
    summary.add_argument(
        "--require-consistent",
        action="store_true",
        help="Exit with status 2 if manifest consistency diagnostics contain warnings.",
    )

    compare = subparsers.add_parser("g-compare", help="Compare Epistemap G summary JSON files.")
    compare.add_argument("summaries", nargs="+")
    compare.add_argument("--baseline-id", default=None)
    compare.add_argument("--out", default=None, help="Optional output comparison JSON path.")
    compare.add_argument("--out-md", default=None, help="Optional output Markdown report path.")
    compare.add_argument(
        "--require-compatible",
        action="store_true",
        help="Exit with status 2 if compatibility diagnostics contain warnings.",
    )

    detective = subparsers.add_parser(
        "detective-sidecars",
        help="Write temporal graph and fair-play diagnostic sidecars from detective annotations.",
    )
    detective.add_argument("annotations", nargs="+", help="Detective annotation JSON files.")
    detective.add_argument("--out-dir", required=True, help="Directory for generated sidecars.")

    treatment = subparsers.add_parser(
        "detective-treatment",
        help="Write a default detective corpus treatment manifest.",
    )
    treatment.add_argument("--experiment-id", required=True)
    treatment.add_argument("--corpus-sidecars", required=True, help="Detective corpus sidecar manifest JSON.")
    treatment.add_argument("--out", required=True, help="Output treatment manifest JSON path.")
    treatment.add_argument("--row-file", default="g_rows.csv")
    treatment.add_argument("--name", default="")
    treatment.add_argument("--created-by", default="")

    bayesian = subparsers.add_parser(
        "bayesian-assessment",
        help="Run a graph-level Bayesian assessment report from an Epistemap graph bundle.",
    )
    bayesian.add_argument("graph_bundle", help="Epistemap graph bundle JSON.")
    bayesian.add_argument("--out", default=None, help="Optional output assessment JSON path.")
    bayesian.add_argument("--out-md", default=None, help="Optional output Markdown report path.")
    bayesian.add_argument(
        "--node-type",
        action="append",
        dest="node_types",
        help="Node type to assess. May be repeated. Defaults to concept and claim.",
    )

    installed_matrix = subparsers.add_parser(
        "installed-matrix",
        help="Run the installed cross-repository compatibility matrix.",
    )
    installed_matrix.add_argument("--manifest", default=None)
    installed_matrix.add_argument("--repo-root", default=None)
    installed_matrix.add_argument("--row-id", action="append", default=[])
    installed_matrix.add_argument("--out", default=None)
    installed_matrix.add_argument("--dry-run", action="store_true")
    installed_matrix.add_argument("--keep-envs", action="store_true")

    genealogy_gedcom = subparsers.add_parser(
        "genealogy-gedcom",
        help="Import a GEDCOM file as a private genealogy Epistemap graph bundle.",
    )
    genealogy_gedcom.add_argument("gedcom", help="GEDCOM file to import.")
    genealogy_gedcom.add_argument("--out", required=True, help="Output Epistemap graph bundle JSON path.")
    genealogy_gedcom.add_argument("--graph-id", default=None, help="Stable graph id. Defaults to the GEDCOM stem.")
    genealogy_gedcom.add_argument("--title", default=None, help="Optional graph title.")

    template = subparsers.add_parser(
        "detective-g-template",
        help="Write a blank detective contradiction-recognition G collection template CSV.",
    )
    template.add_argument("--treatment", required=True, help="Detective treatment manifest JSON.")
    template.add_argument("--corpus-sidecars", default=None, help="Detective corpus sidecar manifest JSON.")
    template.add_argument("--out", required=True, help="Output collection template CSV path.")
    template.add_argument("--env", default="K", help="Environment label for template rows.")
    template.add_argument(
        "--exclude-controls",
        action="store_true",
        help="Exclude fair-play control rows from the template.",
    )

    anchor_template = subparsers.add_parser(
        "detective-anchor-template",
        help="Write a blank human-review CSV for detective source anchors.",
    )
    anchor_template.add_argument("annotations", nargs="+", help="Detective annotation JSON files.")
    anchor_template.add_argument("--out", required=True, help="Output anchor-review CSV path.")

    apply_anchor_review = subparsers.add_parser(
        "detective-apply-anchor-review",
        help="Apply a completed detective anchor-review CSV to annotation JSON files.",
    )
    apply_anchor_review.add_argument("annotations", nargs="+", help="Detective annotation JSON files.")
    apply_anchor_review.add_argument("--review-csv", required=True, help="Completed anchor-review CSV.")
    apply_anchor_review.add_argument("--out-dir", default=None, help="Directory for updated annotation JSON files.")
    apply_anchor_review.add_argument(
        "--in-place",
        action="store_true",
        help="Update annotation JSON files in place.",
    )

    validate_g_rows = subparsers.add_parser(
        "detective-validate-g-rows",
        help="Validate detective contradiction-recognition collection rows.",
    )
    validate_g_rows.add_argument("rows_csv", help="Detective G collection or completed rows CSV.")
    validate_g_rows.add_argument("--out", default=None, help="Optional output validation JSON path.")
    validate_g_rows.add_argument(
        "--allow-template",
        action="store_true",
        help="Allow blank completion fields such as y and p.",
    )
    validate_g_rows.add_argument(
        "--require-pass",
        action="store_true",
        help="Exit with status 2 unless validation status is pass.",
    )

    detective_g_manifest = subparsers.add_parser(
        "detective-g-manifest",
        help="Write an Epistemap G experiment manifest for detective row CSV.",
    )
    detective_g_manifest.add_argument("rows_csv", help="Detective G rows CSV.")
    detective_g_manifest.add_argument("--experiment-id", required=True)
    detective_g_manifest.add_argument("--out", required=True, help="Output G experiment manifest JSON path.")
    detective_g_manifest.add_argument("--name", default="")
    detective_g_manifest.add_argument("--corpus", default="")
    detective_g_manifest.add_argument("--evaluation-target", default="detective_contradiction_recognition")
    detective_g_manifest.add_argument("--reliability-treatment", default="")

    detective_run_sheets = subparsers.add_parser(
        "detective-run-sheets",
        help="Write randomized per-subject detective G collection sheets from a template CSV.",
    )
    detective_run_sheets.add_argument("template_csv", help="Detective G collection template CSV.")
    detective_run_sheets.add_argument("--out-dir", required=True, help="Directory for generated run sheets.")
    detective_run_sheets.add_argument("--run-id-prefix", required=True)
    detective_run_sheets.add_argument("--subject-prefix", default="subject")
    detective_run_sheets.add_argument("--subjects-per-condition", type=int, default=1)
    detective_run_sheets.add_argument(
        "--condition",
        action="append",
        default=[],
        help="Condition to include. May be repeated. Defaults to all conditions in the template.",
    )
    detective_run_sheets.add_argument(
        "--phase",
        action="append",
        default=[],
        help="Phase to include. May be repeated. Defaults to all phases in the template.",
    )
    detective_run_sheets.add_argument("--seed", type=int, default=0)

    detective_merge_run_sheets = subparsers.add_parser(
        "detective-merge-run-sheets",
        help="Merge completed per-subject detective G run sheets into one rows CSV.",
    )
    detective_merge_run_sheets.add_argument("sources", nargs="+", help="Run sheet CSV files or directories.")
    detective_merge_run_sheets.add_argument("--out", required=True, help="Output merged detective G rows CSV.")
    detective_merge_run_sheets.add_argument(
        "--allow-template",
        action="store_true",
        help="Allow blank completion fields while validating the merged output.",
    )
    detective_merge_run_sheets.add_argument(
        "--require-pass",
        action="store_true",
        help="Exit with status 2 unless merged-row validation status is pass.",
    )

    detective_blind_run_sheets = subparsers.add_parser(
        "detective-blind-run-sheets",
        help="Write participant-safe run sheets plus a private rehydration key.",
    )
    detective_blind_run_sheets.add_argument("sources", nargs="+", help="Canonical run sheet CSV files or directories.")
    detective_blind_run_sheets.add_argument("--out-dir", required=True, help="Directory for blinded run sheets.")
    detective_blind_run_sheets.add_argument("--key-file", default=None, help="Optional private blinding key JSON path.")

    detective_unblind_run_sheets = subparsers.add_parser(
        "detective-unblind-run-sheets",
        help="Rehydrate completed blinded run sheets into canonical detective G rows.",
    )
    detective_unblind_run_sheets.add_argument("sources", nargs="+", help="Completed blinded run sheet CSV files or directories.")
    detective_unblind_run_sheets.add_argument("--key-file", required=True, help="Private blinding key JSON.")
    detective_unblind_run_sheets.add_argument("--out", required=True, help="Output canonical detective G rows CSV.")
    detective_unblind_run_sheets.add_argument(
        "--allow-template",
        action="store_true",
        help="Allow blank completion fields while validating the rehydrated output.",
    )
    detective_unblind_run_sheets.add_argument(
        "--require-pass",
        action="store_true",
        help="Exit with status 2 unless rehydrated-row validation status is pass.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "g-summary":
        payload = g_experiment_summary_from_files(
            args.rows_csv,
            manifest_json=args.manifest,
            out_json=args.out,
            group_by=args.group_by,
            target_env=args.target_env,
            clean_env=args.clean_env,
        )
        if args.out_md is not None:
            write_g_experiment_summary_markdown(payload, args.out_md)
    elif args.command == "g-compare":
        payload = g_summary_comparison_from_files(
            args.summaries,
            baseline_id=args.baseline_id,
            out_json=args.out,
        )
        if args.out_md is not None:
            write_g_summary_comparison_markdown(payload, args.out_md)
    elif args.command == "detective-sidecars":
        payload = write_detective_corpus_sidecars(args.annotations, args.out_dir)
    elif args.command == "detective-treatment":
        payload = detective_treatment_manifest(
            experiment_id=args.experiment_id,
            corpus_sidecar_manifest=args.corpus_sidecars,
            row_file=args.row_file,
            name=args.name,
            created_by=args.created_by,
        )
        write_detective_treatment_manifest(payload, args.out)
    elif args.command == "bayesian-assessment":
        bundle = load_graph_bundle(args.graph_bundle)
        node_types = set(args.node_types) if args.node_types else None
        payload = bayesian_assessment_report(bundle, node_types=node_types)
        if args.out is not None:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
        if args.out_md is not None:
            write_bayesian_assessment_markdown(payload, args.out_md)
    elif args.command == "installed-matrix":
        payload = run_installed_matrix(
            args.manifest or None,
            repo_root=args.repo_root,
            out_report=args.out,
            row_ids=set(args.row_id) if args.row_id else None,
            dry_run=args.dry_run,
            keep_envs=args.keep_envs,
        )
    elif args.command == "genealogy-gedcom":
        payload = write_genealogy_graph_bundle(
            args.gedcom,
            args.out,
            graph_id=args.graph_id,
            title=args.title,
        )
    elif args.command == "detective-g-template":
        treatment_path = Path(args.treatment)
        treatment_payload = json.loads(treatment_path.read_text(encoding="utf-8"))
        corpus_sidecars = args.corpus_sidecars or treatment_payload.get("corpus_sidecar_manifest")
        if not corpus_sidecars:
            raise SystemExit("detective-g-template requires --corpus-sidecars or a treatment corpus_sidecar_manifest")
        corpus_sidecar_path = Path(corpus_sidecars)
        if not corpus_sidecar_path.is_absolute() and not corpus_sidecar_path.exists():
            corpus_sidecar_path = treatment_path.parent / corpus_sidecar_path
        corpus_payload = json.loads(corpus_sidecar_path.read_text(encoding="utf-8"))
        payload = detective_g_collection_template(
            treatment_payload,
            corpus_payload,
            env=args.env,
            include_controls=not args.exclude_controls,
            sidecar_base_dir=corpus_sidecar_path.parent,
        )
        write_detective_g_collection_template_csv(payload, args.out)
    elif args.command == "detective-anchor-template":
        payload = detective_corpus_anchor_review_template(
            read_detective_story_annotation(path)
            for path in args.annotations
        )
        write_detective_anchor_review_template_csv(payload, args.out)
    elif args.command == "detective-apply-anchor-review":
        payload = apply_detective_anchor_review_csv(
            args.annotations,
            args.review_csv,
            out_dir=args.out_dir,
            in_place=args.in_place,
        )
    elif args.command == "detective-validate-g-rows":
        payload = validate_detective_g_collection_csv(
            args.rows_csv,
            require_completed=not args.allow_template,
        )
        if args.out is not None:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    elif args.command == "detective-g-manifest":
        payload = write_detective_g_experiment_manifest_from_csv(
            args.rows_csv,
            args.out,
            experiment_id=args.experiment_id,
            name=args.name,
            corpus=args.corpus,
            evaluation_target=args.evaluation_target,
            reliability_treatment=args.reliability_treatment,
        )
    elif args.command == "detective-run-sheets":
        payload = write_detective_g_run_sheets_from_csv(
            args.template_csv,
            args.out_dir,
            run_id_prefix=args.run_id_prefix,
            subject_prefix=args.subject_prefix,
            subjects_per_condition=args.subjects_per_condition,
            conditions=args.condition,
            phases=args.phase,
            seed=args.seed,
        )
    elif args.command == "detective-merge-run-sheets":
        payload = merge_detective_g_run_sheets(
            args.sources,
            args.out,
            require_completed=not args.allow_template,
        )
    elif args.command == "detective-blind-run-sheets":
        payload = write_blinded_detective_g_run_sheets(
            args.sources,
            args.out_dir,
            key_file=args.key_file,
        )
    elif args.command == "detective-unblind-run-sheets":
        payload = unblind_detective_g_run_sheets(
            args.sources,
            args.key_file,
            args.out,
            require_completed=not args.allow_template,
        )
    else:
        parser.print_help()
        return
    print(json.dumps(payload, indent=2))
    if args.command == "g-summary" and args.require_consistent and not payload["consistency"]["consistent"]:
        raise SystemExit(2)
    if args.command == "g-compare" and args.require_compatible and not payload["compatibility"]["compatible"]:
        raise SystemExit(2)
    if args.command == "detective-validate-g-rows" and args.require_pass and payload["summary"]["status"] != "pass":
        raise SystemExit(2)
    if (
        args.command == "detective-merge-run-sheets"
        and args.require_pass
        and payload["validation"]["summary"]["status"] != "pass"
    ):
        raise SystemExit(2)
    if (
        args.command == "detective-unblind-run-sheets"
        and args.require_pass
        and payload["validation"]["summary"]["status"] != "pass"
    ):
        raise SystemExit(2)
    if args.command == "installed-matrix" and not args.dry_run and not payload["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

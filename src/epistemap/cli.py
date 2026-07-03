from __future__ import annotations

import argparse
import json

from .detective_corpus import write_detective_corpus_sidecars
from .grounding_effect import (
    g_experiment_summary_from_files,
    g_summary_comparison_from_files,
    write_g_experiment_summary_markdown,
    write_g_summary_comparison_markdown,
)
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
    else:
        parser.print_help()
        return
    print(json.dumps(payload, indent=2))
    if args.command == "g-summary" and args.require_consistent and not payload["consistency"]["consistent"]:
        raise SystemExit(2)
    if args.command == "g-compare" and args.require_compatible and not payload["compatibility"]["compatible"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

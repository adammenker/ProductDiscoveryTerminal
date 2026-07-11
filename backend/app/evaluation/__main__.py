from __future__ import annotations

import argparse

from app.db.session import SessionLocal
from app.evaluation.harness import EvaluationHarness, console_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Recommendation V2 rankings.")
    parser.add_argument("--golden", help="Path to a golden labeled dataset JSON file.")
    parser.add_argument("--out", default="evaluation_reports", help="Output directory for reports.")
    parser.add_argument("--k", type=int, default=10, help="K for precision@K.")
    parser.add_argument(
        "--scoring-version",
        action="append",
        dest="scoring_versions",
        help="Restrict evaluation to a scoring version. Repeat for multiple versions.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        harness = EvaluationHarness(db)
        report = harness.run(
            k=args.k,
            golden_dataset_path=args.golden,
            scoring_versions=args.scoring_versions,
        )
        paths = harness.write_reports(report, args.out)
    print(console_summary(report))
    print(f"json={paths['json']}")
    print(f"markdown={paths['markdown']}")


if __name__ == "__main__":
    main()

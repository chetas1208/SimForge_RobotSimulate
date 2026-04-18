"""CLI entrypoint for scenario generation without requiring the backend."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.parser import RuleBasedScenarioParser
from apps.simulator.pipeline import WarehouseScenarioPipeline
from packages.shared_schema import ScenarioGenerationRequest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Track 4 warehouse simulation variants.")
    parser.add_argument("--config", default="apps/simulator/configs/warehouse_blind_corner.yaml")
    parser.add_argument("--description", default=None)
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--num-variants", type=int, default=None)
    parser.add_argument("--use-isaac", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    overrides: dict[str, object] = {}
    if args.job_id:
        overrides["job_id"] = args.job_id
    if args.num_variants is not None:
        overrides["num_variants"] = args.num_variants
    if args.use_isaac:
        overrides["use_isaac"] = True

    pipeline = WarehouseScenarioPipeline()
    if args.description:
        parser = RuleBasedScenarioParser()
        parsed = parser.parse(args.description, defaults={"num_variants": args.num_variants or 1})
        request = ScenarioGenerationRequest.from_parsed_scenario(
            parsed,
            job_id=args.job_id,
            use_isaac=args.use_isaac,
            headless=True,
        )
        artifacts = pipeline.generate(request)
    else:
        artifacts = pipeline.generate_from_path(config_path=args.config, overrides=overrides)
    for artifact in artifacts:
        print(
            f"{artifact.scenario_id} | preview={artifact.preview_video_path} | manifest={artifact.manifest_path}"
        )


if __name__ == "__main__":
    main()

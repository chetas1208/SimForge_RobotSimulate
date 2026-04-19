"""Isaac Sim standalone entrypoint for headless cluster execution.

Run this script with Isaac Sim's bundled Python:
    ./python.sh apps/simulator/isaac_standalone.py --config apps/simulator/configs/warehouse_blind_corner.yaml
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.simulator.pipeline import WarehouseScenarioPipeline
from packages.shared_schema import ScenarioGenerationRequest
from packages.utils import read_json, write_json


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _simulation_app_config() -> dict[str, object]:
    extra_args = shlex.split(os.getenv("ISAAC_EXTRA_ARGS", ""))
    headless = _env_flag("ISAAC_HEADLESS", default=True)
    return {
        "headless": headless,
        "hide_ui": headless,
        "fast_shutdown": True,
        "extra_args": extra_args,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Track 4 generation inside Isaac Sim standalone mode.")
    parser.add_argument("--config", default="apps/simulator/configs/warehouse_blind_corner.yaml")
    parser.add_argument("--description", default=None)
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--request-json", default=None)
    parser.add_argument("--summary-json", default=None)
    return parser.parse_args()


def main() -> None:
    try:
        from isaacsim import SimulationApp
    except Exception as exc:  # pragma: no cover - requires Isaac Sim runtime
        raise RuntimeError(
            "Isaac Sim runtime is not available. Run this script with Isaac Sim's ./python.sh on the GPU cluster."
        ) from exc

    args = parse_args()
    simulation_app = SimulationApp(_simulation_app_config())
    try:
        from apps.parser import RuleBasedScenarioParser

        pipeline = WarehouseScenarioPipeline()
        if args.request_json:
            request = ScenarioGenerationRequest(**read_json(args.request_json))
            artifacts = pipeline.generate(request)
        elif args.description:
            parsed = RuleBasedScenarioParser().parse(args.description)
            request = ScenarioGenerationRequest.from_parsed_scenario(
                parsed,
                job_id=args.job_id,
                use_isaac=True,
                headless=True,
            )
            artifacts = pipeline.generate(request)
        else:
            overrides: dict[str, object] = {"use_isaac": True}
            if args.job_id:
                overrides["job_id"] = args.job_id
            artifacts = pipeline.generate_from_path(config_path=args.config, overrides=overrides)

        capture_payloads: list[dict[str, object]] = []
        try:
            import omni.timeline
            import omni.usd

            timeline = omni.timeline.get_timeline_interface()
            usd_context = omni.usd.get_context()

            for artifact in artifacts:
                capture_path = Path(artifact.generation_log_path).with_name("isaac_capture.json")
                payload = {
                    "status": "captured",
                    "scene_usd_path": artifact.scene_usd_path,
                    "frames_simulated": 24,
                }
                try:
                    usd_context.open_stage(artifact.scene_usd_path)
                    timeline.play()
                    for _ in range(24):
                        simulation_app.update()
                    timeline.stop()
                except Exception as exc:  # pragma: no cover - requires Isaac Sim runtime
                    payload = {
                        "status": "fallback",
                        "scene_usd_path": artifact.scene_usd_path,
                        "error": str(exc),
                    }
                write_json(capture_path, payload)
                capture_payloads.append(payload)
        except Exception as exc:  # pragma: no cover - requires Isaac Sim runtime
            for artifact in artifacts:
                capture_path = Path(artifact.generation_log_path).with_name("isaac_capture.json")
                payload = {
                    "status": "runtime_unavailable",
                    "scene_usd_path": artifact.scene_usd_path,
                    "error": str(exc),
                }
                write_json(capture_path, payload)
                capture_payloads.append(payload)

        if args.summary_json:
            write_json(
                args.summary_json,
                {
                    "generated_variants": [artifact.model_dump(mode="json") for artifact in artifacts],
                    "isaac_captures": capture_payloads,
                },
            )

        for artifact in artifacts:
            print(f"{artifact.scenario_id} | preview={artifact.preview_video_path} | usd={artifact.scene_usd_path}")
    finally:
        simulation_app.close(wait_for_replicator=False)


if __name__ == "__main__":
    main()

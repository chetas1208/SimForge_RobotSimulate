"""Isaac Sim standalone entrypoint for headless cluster execution.

Run this script with Isaac Sim's bundled Python:
    ./python.sh apps/simulator/isaac_standalone.py --config apps/simulator/configs/warehouse_blind_corner.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.simulator.pipeline import WarehouseScenarioPipeline
from packages.utils import write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Track 4 generation inside Isaac Sim standalone mode.")
    parser.add_argument("--config", default="apps/simulator/configs/warehouse_blind_corner.yaml")
    parser.add_argument("--description", default=None)
    parser.add_argument("--job-id", default=None)
    return parser.parse_args()


def main() -> None:
    try:
        from isaacsim import SimulationApp
    except Exception as exc:  # pragma: no cover - requires Isaac Sim runtime
        raise RuntimeError(
            "Isaac Sim runtime is not available. Run this script with Isaac Sim's ./python.sh on the GPU cluster."
        ) from exc

    args = parse_args()
    simulation_app = SimulationApp({"headless": True})
    try:
        from apps.parser import RuleBasedScenarioParser
        from packages.shared_schema import ScenarioGenerationRequest

        pipeline = WarehouseScenarioPipeline()
        if args.description:
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
        except Exception as exc:  # pragma: no cover - requires Isaac Sim runtime
            for artifact in artifacts:
                capture_path = Path(artifact.generation_log_path).with_name("isaac_capture.json")
                write_json(
                    capture_path,
                    {
                        "status": "runtime_unavailable",
                        "scene_usd_path": artifact.scene_usd_path,
                        "error": str(exc),
                    },
                )

        for artifact in artifacts:
            print(f"{artifact.scenario_id} | preview={artifact.preview_video_path} | usd={artifact.scene_usd_path}")
    finally:
        simulation_app.close()


if __name__ == "__main__":
    main()

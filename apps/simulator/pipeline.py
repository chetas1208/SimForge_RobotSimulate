"""Orchestrates scene generation, OpenUSD writing, and preview rendering."""

from __future__ import annotations

from pathlib import Path

from apps.simulator.config import SimulatorSettings, load_generation_request
from apps.simulator.renderer import render_preview
from apps.simulator.scene import WarehouseBlindCornerSceneBuilder
from packages.shared_schema import GeneratedVariantArtifact, ScenarioGenerationRequest
from packages.utils import (
    build_scenario_paths,
    get_logger,
    write_json,
    write_text,
)


class WarehouseScenarioPipeline:
    """Main generator used by standalone scripts and backend adapters."""

    def __init__(self, settings: SimulatorSettings | None = None):
        self.settings = settings or SimulatorSettings()
        self.logger = get_logger("simforge.track4.simulator")
        self.builder = WarehouseBlindCornerSceneBuilder()

    def generate_from_path(
        self,
        config_path: str | None = None,
        overrides: dict | None = None,
    ) -> list[GeneratedVariantArtifact]:
        request = load_generation_request(
            config_path=config_path,
            overrides=overrides,
            settings=self.settings,
        )
        return self.generate(request)

    def generate(self, request: ScenarioGenerationRequest) -> list[GeneratedVariantArtifact]:
        artifacts: list[GeneratedVariantArtifact] = []
        for variant in self.builder.build_variants(request):
            paths = build_scenario_paths(request.job_id, variant.scenario_id)
            bundle = self.builder.simulate_variant(variant)
            preview_path, preview_asset_type = render_preview(
                bundle.annotations,
                variant,
                paths.preview_dir / f"{variant.scenario_id}_preview",
                fps=self.settings.preview_fps,
                stride=self.settings.preview_stride,
            )

            manifest_path = paths.root_dir / "scenario_manifest.json"
            scenario_config_path = paths.root_dir / "scenario_config.json"
            generation_log_path = paths.root_dir / "generation_log.json"
            scene_usd_path = paths.scene_dir / "scene.usda"
            log_path = paths.log_dir / f"{variant.scenario_id}.log"
            public_manifest_path = paths.manifest_dir / f"{variant.scenario_id}_manifest.json"

            bundle.metadata.output_dir = str(paths.root_dir)
            bundle.metadata.preview_asset_type = preview_asset_type
            bundle.manifest.artifact_paths = {
                "scenario_manifest_path": str(public_manifest_path),
                "scenario_config_path": str(scenario_config_path),
                "generation_log_path": str(generation_log_path),
                "preview_video_path": str(preview_path),
                "scene_usd_path": str(scene_usd_path),
            }

            write_json(manifest_path, bundle.manifest)
            write_json(public_manifest_path, bundle.manifest)
            write_json(scenario_config_path, bundle.scenario_config)
            write_json(generation_log_path, bundle.metadata)
            write_text(scene_usd_path, bundle.scene_usda)
            write_text(
                log_path,
                "\n".join([
                    f"job_id={request.job_id}",
                    f"scenario_id={variant.scenario_id}",
                    f"use_isaac={variant.use_isaac}",
                    f"preview_video_path={preview_path}",
                    f"manifest_path={public_manifest_path}",
                ]),
            )

            artifacts.append(
                GeneratedVariantArtifact(
                    job_id=request.job_id,
                    scenario_id=variant.scenario_id,
                    variant_index=variant.variant_index,
                    status="completed",
                    manifest_path=str(public_manifest_path),
                    scenario_config_path=str(scenario_config_path),
                    generation_log_path=str(generation_log_path),
                    preview_video_path=str(preview_path),
                    scene_usd_path=str(scene_usd_path),
                    metadata_path=str(generation_log_path),
                    annotations_path=None,
                )
            )
            self.logger.info("Generated scenario %s for job %s", variant.scenario_id, request.job_id)
        return artifacts


def generate_scenarios(
    config_path: str | None = None,
    overrides: dict | None = None,
) -> list[GeneratedVariantArtifact]:
    return WarehouseScenarioPipeline().generate_from_path(config_path=config_path, overrides=overrides)

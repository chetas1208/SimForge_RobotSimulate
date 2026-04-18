"""Config-driven warehouse scene generation for OpenUSD-compatible preview scenarios."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any

from packages.shared_schema import (
    DifficultyLevel,
    ScenarioGenerationRequest,
    ScenarioManifest,
    ScenarioMetadata,
    ScenarioVariantConfig,
)


WORLD_BOUNDS = {
    "x_min": -10.0,
    "x_max": 10.0,
    "y_min": -4.0,
    "y_max": 14.0,
}

DIFFICULTY_MULTIPLIER = {
    DifficultyLevel.EASY: 0.8,
    DifficultyLevel.MEDIUM: 1.0,
    DifficultyLevel.HARD: 1.25,
    DifficultyLevel.CRITICAL: 1.5,
}


@dataclass
class SimulatedVariant:
    manifest: ScenarioManifest
    metadata: ScenarioMetadata
    annotations: dict[str, Any]
    scene_usda: str
    scenario_config: dict[str, Any]


class WarehouseBlindCornerSceneBuilder:
    """Builds scene variants from structured scenario requests."""

    def build_variants(self, request: ScenarioGenerationRequest) -> list[ScenarioVariantConfig]:
        variants: list[ScenarioVariantConfig] = []
        difficulty_scale = DIFFICULTY_MULTIPLIER[request.difficulty]
        scene_family = f"{request.environment_preset}:{request.difficulty.value}"

        for index in range(request.num_variants):
            seed = request.base_seed + index * 1009 + 7
            rng = random.Random(seed)
            human_count = max(
                0,
                request.human_count
                + (1 if request.crossing_event and difficulty_scale > 1.1 and rng.random() > 0.65 else 0),
            )
            obstacle_count = max(0, request.obstacle_count + rng.randint(-1, 2))
            forklift_count = max(0, request.forklift_count + (1 if difficulty_scale > 1.2 and rng.random() > 0.7 else 0))
            scenario_id = f"{request.job_id}-v{index:02d}-{seed}"
            variants.append(
                ScenarioVariantConfig(
                    job_id=request.job_id,
                    scenario_id=scenario_id,
                    scenario_seed=seed,
                    scene_family=scene_family,
                    variant_index=index,
                    scenario_type=request.scenario_type,
                    environment_preset=request.environment_preset,
                    difficulty=request.difficulty,
                    lighting_level=request.lighting_level,
                    reflective_floor=request.reflective_floor or (rng.random() > 0.85),
                    human_count=human_count,
                    obstacle_count=obstacle_count,
                    forklift_count=forklift_count,
                    robot_speed_mps=round(request.robot_speed_mps * rng.uniform(0.92, 1.12), 3),
                    human_speed_mps=round(max(0.2, request.human_speed_mps * rng.uniform(0.85, 1.18)), 3),
                    blind_corner=request.blind_corner,
                    dropped_object=request.dropped_object or (rng.random() > 0.82),
                    crossing_event=request.crossing_event,
                    camera_view=request.camera_view,
                    headless=request.headless,
                    use_isaac=request.use_isaac,
                    description=request.description,
                )
            )
        return variants

    def simulate_variant(self, variant: ScenarioVariantConfig) -> SimulatedVariant:
        annotations = self._annotations(variant)
        scenario_config = variant.model_dump(mode="json")
        manifest = ScenarioManifest(
            job_id=variant.job_id,
            scenario_id=variant.scenario_id,
            scenario_seed=variant.scenario_seed,
            scene_family=variant.scene_family,
            variant_index=variant.variant_index,
            scenario_type=variant.scenario_type,
            environment_preset=variant.environment_preset,
            difficulty=variant.difficulty,
            camera_view=variant.camera_view,
            lighting_level=variant.lighting_level,
            use_isaac=variant.use_isaac,
            headless=variant.headless,
            parsed_scenario={
                "environment": variant.environment_preset,
                "lighting": variant.lighting_level.value,
                "blind_corner": variant.blind_corner,
                "pedestrian_count": variant.human_count,
                "forklift_count": variant.forklift_count,
                "camera_view": variant.camera_view.value,
                "difficulty": variant.difficulty.value,
                "description": variant.description,
            },
            variant_parameters=scenario_config,
        )
        metadata = ScenarioMetadata(
            job_id=variant.job_id,
            scenario_id=variant.scenario_id,
            variant_index=variant.variant_index,
            scenario_seed=variant.scenario_seed,
            scene_family=variant.scene_family,
            generator="isaac_headless" if variant.use_isaac else "headless_preview_renderer",
            status="completed",
            output_dir="",
            preview_asset_type="preview_video",
            notes=[
                f"human_count={variant.human_count}",
                f"forklift_count={variant.forklift_count}",
                f"obstacle_count={variant.obstacle_count}",
            ],
            runtime={
                "headless": variant.headless,
                "use_isaac": variant.use_isaac,
            },
        )
        return SimulatedVariant(
            manifest=manifest,
            metadata=metadata,
            annotations=annotations,
            scene_usda=self._build_scene_usda(variant),
            scenario_config=scenario_config,
        )

    def _annotations(self, variant: ScenarioVariantConfig) -> dict[str, Any]:
        rng = random.Random(variant.scenario_seed)
        total_frames = 120
        dt = 0.1
        robot_positions = [self._robot_position(variant, frame * dt) for frame in range(total_frames)]
        human_tracks = [
            [self._human_position(variant, idx, frame * dt, rng) for frame in range(total_frames)]
            for idx in range(variant.human_count)
        ]
        forklift_tracks = [
            [self._forklift_position(variant, idx, frame * dt, rng) for frame in range(total_frames)]
            for idx in range(variant.forklift_count)
        ]
        static_objects = self._static_objects(variant, rng)
        return {
            "time_step_s": dt,
            "frames": [
                {
                    "t": round(frame * dt, 3),
                    "robot": list(robot_positions[frame]),
                    "humans": [
                        list(position)
                        for position in (track[frame] for track in human_tracks)
                        if position is not None
                    ],
                    "forklifts": [
                        list(position)
                        for position in (track[frame] for track in forklift_tracks)
                        if position is not None
                    ],
                }
                for frame in range(total_frames)
            ],
            "static_objects": static_objects,
            "world_bounds": WORLD_BOUNDS,
        }

    def _robot_position(self, variant: ScenarioVariantConfig, time_s: float) -> tuple[float, float]:
        speed = variant.robot_speed_mps
        if not variant.blind_corner:
            return (-8.0 + (speed * time_s), 0.0)
        turn_distance = 8.0
        turn_time = turn_distance / max(speed, 0.1)
        if time_s <= turn_time:
            return (-8.0 + (speed * time_s), 0.0)
        return (0.0, min(10.0, (time_s - turn_time) * speed))

    def _human_position(
        self,
        variant: ScenarioVariantConfig,
        human_index: int,
        time_s: float,
        rng: random.Random,
    ) -> tuple[float, float] | None:
        if not variant.crossing_event:
            return None
        offset = (human_index - max(variant.human_count - 1, 0) / 2.0) * 0.9
        start_delay = 0.9 + human_index * 0.35 + rng.uniform(-0.15, 0.2)
        progress = (time_s - start_delay) * variant.human_speed_mps
        if progress < 0 or progress > 7.0:
            return None
        return (offset + rng.uniform(-0.03, 0.03), 3.8 - progress)

    def _forklift_position(
        self,
        variant: ScenarioVariantConfig,
        forklift_index: int,
        time_s: float,
        rng: random.Random,
    ) -> tuple[float, float] | None:
        start_delay = 1.4 + forklift_index * 0.6 + rng.uniform(-0.2, 0.3)
        progress = (time_s - start_delay) * max(0.7, variant.robot_speed_mps * 0.8)
        if progress < 0 or progress > 11.0:
            return None
        return (1.8 + (forklift_index * 1.2), 9.0 - progress)

    def _static_objects(self, variant: ScenarioVariantConfig, rng: random.Random) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []
        for index in range(variant.obstacle_count):
            objects.append(
                {
                    "id": f"obstacle_{index}",
                    "type": "obstacle",
                    "position": [
                        round(rng.uniform(-1.0, 2.5), 3),
                        round(rng.uniform(-0.5, 6.5), 3),
                    ],
                }
            )
        if variant.dropped_object:
            objects.append(
                {
                    "id": "dropped_object",
                    "type": "dropped_object",
                    "position": [round(rng.uniform(-0.4, 0.8), 3), round(rng.uniform(0.2, 1.8), 3)],
                }
            )
        return objects

    def _build_scene_usda(self, variant: ScenarioVariantConfig) -> str:
        lines = [
            "#usda 1.0",
            "(",
            '    defaultPrim = "World"',
            ")",
            "",
            'def Xform "World"',
            "{",
            "    customData = {",
            f'        string simforge:job_id = "{variant.job_id}"',
            f'        string simforge:scenario_id = "{variant.scenario_id}"',
            "    }",
            '    def Xform "WarehouseEnvironment" {',
            f'        custom string preset = "{variant.environment_preset}"',
            f'        custom string lighting = "{variant.lighting_level.value}"',
            "    }",
            '    def Xform "Robot" { custom string kind = "mobile_robot" }',
            '    def Xform "Pedestrians" {',
            f"        custom int count = {variant.human_count}",
            "    }",
            '    def Xform "Forklifts" {',
            f"        custom int count = {variant.forklift_count}",
            "    }",
            '    def Xform "Sensors" {',
            '        def Xform "PreviewCamera" { custom string purpose = "preview" }',
            '        def Xform "LidarMount" { custom string purpose = "future_sensor" }',
            "    }",
            "}",
        ]
        return "\n".join(lines)


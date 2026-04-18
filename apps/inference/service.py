"""Backend-callable service for description parsing, preview generation, and risk scoring."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.inference.feature_mapping import map_scenario_config_path_to_model_features
from apps.inference.model import RiskScoringModel
from apps.parser import RuleBasedScenarioParser
from apps.simulator.pipeline import WarehouseScenarioPipeline
from packages.shared_schema import (
    InferenceResponse,
    ParsedScenario,
    PipelineJobResponse,
    ScenarioGenerationRequest,
)
from packages.utils import MODELS_DIR, read_json, write_json


class WarehouseSafetyService:
    """One-stop service for parser -> simulator -> model inference."""

    def __init__(self, model_dir: str | Path, parser: RuleBasedScenarioParser | None = None):
        self.pipeline = WarehouseScenarioPipeline()
        self.model = RiskScoringModel(model_dir=model_dir)
        self.parser = parser or RuleBasedScenarioParser()

    def process_description(
        self,
        description: str,
        job_id: str | None = None,
        num_variants: int = 1,
        use_isaac: bool = False,
    ) -> PipelineJobResponse:
        parsed = self.parser.parse(description, defaults={"num_variants": num_variants})
        request = ScenarioGenerationRequest.from_parsed_scenario(
            parsed,
            job_id=job_id,
            use_isaac=use_isaac,
            headless=True,
        )
        return self.process_request(request=request, parsed_scenario=parsed)

    def process_request(
        self,
        request: ScenarioGenerationRequest,
        parsed_scenario: ParsedScenario | None = None,
    ) -> PipelineJobResponse:
        parsed = parsed_scenario or self._parsed_from_request(request)
        generated = self.pipeline.generate(request)
        results: list[InferenceResponse] = []
        for artifact in generated:
            feature_row = map_scenario_config_path_to_model_features(
                scenario_config_path=artifact.scenario_config_path,
                job_id=request.job_id,
                scenario_id=artifact.scenario_id,
            )
            feature_dump_path = Path(artifact.scenario_config_path).with_name("model_features.json")
            write_json(feature_dump_path, feature_row)
            artifact.model_features_path = str(feature_dump_path)
            artifact.lidar_features_path = str(feature_dump_path)

            prediction = self.model.predict_detail(feature_row)
            explanation, supporting_signals, recommended_actions = self.model.explain(feature_row, prediction)
            results.append(
                InferenceResponse(
                    job_id=request.job_id,
                    scenario_id=artifact.scenario_id,
                    variant_index=artifact.variant_index,
                    status="completed",
                    risk_score=prediction["risk_score"],
                    risk_label=prediction["risk_label"],
                    explanation=explanation,
                    preview_video_path=artifact.preview_video_path,
                    scenario_manifest_path=artifact.manifest_path,
                    model_version=self.model.model_version,
                    feature_schema_version=self.model.schema.version,
                    supporting_signals=supporting_signals,
                    recommended_actions=recommended_actions,
                )
            )
        return PipelineJobResponse(
            job_id=request.job_id,
            status="completed",
            parsed_scenario=parsed.model_dump(mode="json"),
            generated_variants=generated,
            results=results,
            model_version=self.model.model_version,
            feature_schema_version=self.model.schema.version,
        )

    # Backward-compatible method name used by earlier backend adapters.
    def generate_and_score(
        self,
        request: ScenarioGenerationRequest,
        parsed_scenario: ParsedScenario | None = None,
    ) -> PipelineJobResponse:
        return self.process_request(request=request, parsed_scenario=parsed_scenario)

    def score_existing_features(self, feature_row: dict[str, Any]) -> dict[str, Any]:
        prediction = self.model.predict_detail(feature_row)
        explanation, signals, actions = self.model.explain(feature_row, prediction)
        return {
            "risk_score": prediction["risk_score"],
            "risk_label": prediction["risk_label"].value,
            "explanation": explanation,
            "supporting_signals": signals,
            "recommended_actions": actions,
            "model_version": self.model.model_version,
            "feature_schema_version": self.model.schema.version,
        }

    def _parsed_from_request(self, request: ScenarioGenerationRequest) -> ParsedScenario:
        obstacle_density = "low" if request.obstacle_count <= 1 else "medium" if request.obstacle_count <= 3 else "high"
        return ParsedScenario(
            environment=request.environment_preset,
            lighting=request.lighting_level,
            blind_corner=request.blind_corner,
            pedestrian_count=request.human_count,
            forklift_count=request.forklift_count,
            obstacle_density=obstacle_density,
            camera_view=request.camera_view,
            difficulty=request.difficulty,
            reflective_floor=request.reflective_floor,
            robot_speed_mps=request.robot_speed_mps,
            pedestrian_speed_mps=request.human_speed_mps,
            num_variants=request.num_variants,
            dropped_object=request.dropped_object,
            crossing_event=request.crossing_event,
            description=request.description,
        )


# Backward-compatible alias for the older service name.
ScenarioRiskScoringService = WarehouseSafetyService


def default_model_dir() -> Path:
    candidates = sorted(path for path in MODELS_DIR.iterdir() if path.is_dir())
    if not candidates:
        raise RuntimeError("No trained model directory found under models/")
    return candidates[-1]

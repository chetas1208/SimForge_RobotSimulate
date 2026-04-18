"""Deterministic rule-based parser for user-described warehouse scenarios."""

from __future__ import annotations

import re
from typing import Any

from packages.shared_schema import (
    CameraView,
    DifficultyLevel,
    EnvironmentType,
    LightingLevel,
    ObstacleDensityLevel,
    ParsedScenario,
)


WORD_TO_INT = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


class RuleBasedScenarioParser:
    """Converts short warehouse scene descriptions into structured scenario JSON."""

    def parse(self, description: str, defaults: dict[str, Any] | None = None) -> ParsedScenario:
        text = " ".join(description.lower().strip().split())
        payload: dict[str, Any] = {
            "environment": self._environment(text),
            "lighting": self._lighting(text),
            "blind_corner": "blind corner" in text or "blind-corner" in text,
            "pedestrian_count": self._count(text, ["pedestrian", "pedestrians", "person", "people", "human", "humans"]),
            "forklift_count": self._count(text, ["forklift", "forklifts"]),
            "obstacle_density": self._obstacle_density(text),
            "camera_view": self._camera_view(text),
            "difficulty": self._difficulty(text),
            "reflective_floor": "reflective floor" in text or "shiny floor" in text,
            "dropped_object": any(term in text for term in ("dropped object", "dropped box", "fallen box", "fallen object")),
            "crossing_event": any(term in text for term in ("crossing", "crossing ahead", "crossing event", "pedestrian crossing")),
            "description": description.strip(),
        }

        if payload["pedestrian_count"] == 0 and payload["crossing_event"] and payload["forklift_count"] == 0:
            payload["pedestrian_count"] = 1

        payload["robot_speed_mps"] = self._robot_speed(payload["difficulty"])
        payload["pedestrian_speed_mps"] = self._pedestrian_speed(payload["difficulty"], payload["pedestrian_count"])
        payload["num_variants"] = 1

        if defaults:
            payload = {**defaults, **payload}

        return ParsedScenario(**payload)

    def _environment(self, text: str) -> EnvironmentType:
        if "loading zone" in text or "loading dock" in text:
            return EnvironmentType.LOADING_ZONE
        if "narrow corridor" in text or "corridor" in text:
            return EnvironmentType.NARROW_CORRIDOR
        if "blind corner" in text:
            return EnvironmentType.BLIND_CORNER_AISLE
        return EnvironmentType.WAREHOUSE_AISLE

    def _lighting(self, text: str) -> LightingLevel:
        if any(term in text for term in ("poor visibility", "very dark", "emergency light", "emergency lighting")):
            return LightingLevel.POOR if "poor visibility" in text else LightingLevel.EMERGENCY
        if any(term in text for term in ("low light", "dim", "dark")):
            return LightingLevel.LOW
        if any(term in text for term in ("bright", "well lit", "high visibility")):
            return LightingLevel.BRIGHT
        return LightingLevel.NORMAL

    def _obstacle_density(self, text: str) -> ObstacleDensityLevel:
        if any(term in text for term in ("high congestion", "heavy clutter", "dense clutter", "very cluttered")):
            return ObstacleDensityLevel.HIGH
        if any(term in text for term in ("clutter", "medium congestion", "moderate clutter")):
            return ObstacleDensityLevel.MEDIUM
        if any(term in text for term in ("clear aisle", "low clutter", "light clutter")):
            return ObstacleDensityLevel.LOW
        return ObstacleDensityLevel.MEDIUM

    def _camera_view(self, text: str) -> CameraView:
        if "first person" in text or "robot view" in text:
            return CameraView.FIRST_PERSON
        if "follow view" in text or "tracking view" in text:
            return CameraView.FOLLOW
        if "fixed angle" in text or "side view" in text:
            return CameraView.FIXED_ANGLE
        if "multi view" in text or "multi-view" in text:
            return CameraView.MULTI_VIEW
        return CameraView.OVERHEAD

    def _difficulty(self, text: str) -> DifficultyLevel:
        if any(term in text for term in ("critical", "extreme", "high risk")):
            return DifficultyLevel.CRITICAL
        if any(term in text for term in ("hard", "high congestion", "poor visibility", "blind corner")):
            return DifficultyLevel.HARD
        if any(term in text for term in ("easy", "simple", "clear aisle")):
            return DifficultyLevel.EASY
        return DifficultyLevel.MEDIUM

    def _count(self, text: str, nouns: list[str]) -> int:
        for noun in nouns:
            digit_match = re.search(rf"(\d+)\s+{noun}\b", text)
            if digit_match:
                return int(digit_match.group(1))
            if re.search(rf"\b(a|an)\s+{noun}\b", text):
                return 1
            for word, value in WORD_TO_INT.items():
                if re.search(rf"\b{word}\s+{noun}\b", text):
                    return value
        return 0

    @staticmethod
    def _robot_speed(difficulty: DifficultyLevel) -> float:
        mapping = {
            DifficultyLevel.EASY: 1.0,
            DifficultyLevel.MEDIUM: 1.2,
            DifficultyLevel.HARD: 1.35,
            DifficultyLevel.CRITICAL: 1.45,
        }
        return mapping[difficulty]

    @staticmethod
    def _pedestrian_speed(difficulty: DifficultyLevel, pedestrian_count: int) -> float:
        if pedestrian_count <= 0:
            return 0.0
        base = 1.0
        if difficulty in {DifficultyLevel.HARD, DifficultyLevel.CRITICAL}:
            base += 0.15
        return base

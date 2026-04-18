"""Validation helpers for parsed scenarios."""

from __future__ import annotations

from typing import Any

from packages.shared_schema import ParsedScenario


def validate_parsed_scenario(payload: dict[str, Any]) -> ParsedScenario:
    return ParsedScenario(**payload)


def normalize_parsed_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    return validate_parsed_scenario(payload).model_dump(mode="json")


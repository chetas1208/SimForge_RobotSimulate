"""Feature schema validation for backend inference rows."""

from __future__ import annotations

from typing import Any

from packages.shared_schema import FeatureSchema, normalize_feature_frame


def validate_feature_row(feature_row: dict[str, Any], schema: FeatureSchema) -> dict[str, Any]:
    normalized = normalize_feature_frame(feature_row, schema)
    row = normalized.iloc[0].to_dict()
    for column, (lower, upper) in schema.ranges.items():
        if column not in row:
            continue
        value = row[column]
        if isinstance(value, str):
            continue
        if value < lower:
            row[column] = lower
        elif value > upper:
            row[column] = upper
    return row


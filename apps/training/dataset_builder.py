"""Compatibility wrapper for the real-data preprocessing pipeline."""

from __future__ import annotations

from apps.training.preprocess_real_dataset import build_real_dataset, main

__all__ = ["build_real_dataset", "main"]


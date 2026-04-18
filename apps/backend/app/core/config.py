"""Application configuration from environment variables."""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./simforge.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    STORAGE_ROOT: str = os.getenv("STORAGE_ROOT", "./storage")
    SIMULATION_PROVIDER: str = os.getenv("SIMULATION_PROVIDER", "mock")
    TRACK4_MODEL_DIR: str = os.getenv("TRACK4_MODEL_DIR", "./models")
    TRACK4_SCENARIO_CONFIG: str = os.getenv(
        "TRACK4_SCENARIO_CONFIG",
        "./apps/simulator/configs/warehouse_blind_corner.yaml",
    )
    XGBOOST_DEVICE: str = os.getenv("XGBOOST_DEVICE", "cuda:0")
    HPC_HOST: str = os.getenv("HPC_HOST", "")
    HPC_USER: str = os.getenv("HPC_USER", "")
    HPC_WORKDIR: str = os.getenv("HPC_WORKDIR", "")
    ISAAC_RESULTS_DIR: str = os.getenv("ISAAC_RESULTS_DIR", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "simforge-dev-secret-key")


settings = Settings()

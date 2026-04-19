"""Application configuration from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    PREVIEW_PROVIDER: str = os.getenv("PREVIEW_PROVIDER", "renderer")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "nvidia_nim")
    NVIDIA_NIM_API_KEY: str = os.getenv("NVIDIA_NIM_API_KEY", "")
    NVIDIA_NIM_BASE_URL: str = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NVIDIA_NIM_MODEL: str = os.getenv("NVIDIA_NIM_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1")
    NVIDIA_NIM_USD_MODEL: str = os.getenv("NVIDIA_NIM_USD_MODEL", "nvidia/llama-3.3-nemotron-super-49b-v1")
    SEEDANCE_API_KEY: str = os.getenv("SEEDANCE_API_KEY", "")
    SEEDANCE_BASE_URL: str = os.getenv("SEEDANCE_BASE_URL", "https://api.seedance.ai/v1")
    XGBOOST_DEVICE: str = os.getenv("XGBOOST_DEVICE", "cuda:0")
    HPC_HOST: str = os.getenv("HPC_HOST", "")
    HPC_USER: str = os.getenv("HPC_USER", "")
    HPC_WORKDIR: str = os.getenv("HPC_WORKDIR", "")
    ISAAC_RESULTS_DIR: str = os.getenv("ISAAC_RESULTS_DIR", "")
    ISAAC_SIM_PATH: str = os.getenv("ISAAC_SIM_PATH", "")
    ISAAC_PYTHON: str = os.getenv("ISAAC_PYTHON", "")
    ISAAC_LD_LIBRARY_PATH: str = os.getenv("ISAAC_LD_LIBRARY_PATH", "")
    ISAAC_EXTRA_ARGS: str = os.getenv("ISAAC_EXTRA_ARGS", "")
    ISAAC_HEADLESS: bool = _env_flag("ISAAC_HEADLESS", default=True)
    ENABLE_DEMO_SEED: bool = _env_flag("ENABLE_DEMO_SEED", default=False)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "simforge-dev-secret-key")


settings = Settings()

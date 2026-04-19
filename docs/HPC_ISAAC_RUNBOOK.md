# SimForge Isaac HPC Runbook

This is the repo-backed path for launching the full SimForge stack on an Isaac-capable HPC node:

- FastAPI backend
- Nuxt dashboard
- Isaac runtime via `SIMULATION_PROVIDER=isaac`
- Track 4 risk scoring
- Seedance / NVIDIA NIM integrations when their keys are present in `apps/backend/.env`

## Prerequisites

- A GPU node with a working NVIDIA driver stack
- Python 3.11+ for the backend virtualenv
- Node.js 20+ for the dashboard
- Isaac Sim available through either:
  - `ISAAC_PYTHON=/path/to/isaac-sim/python.sh`, or
  - `ISAAC_SIM_PATH=/path/to/isaac-sim`, or
  - the local workspace install at `.conda/envs/isaacsim-4.5`

If your cluster uses environment modules, the launcher can load them for you:

```bash
export SIMFORGE_MODULE_INIT=/etc/profile.d/modules.sh
export SIMFORGE_CUDA_MODULE=cuda/12.1
export SIMFORGE_PYTHON_MODULE=python/3.11
export SIMFORGE_NODE_MODULE=nodejs/20
```

## Backend Env

Make sure `apps/backend/.env` contains your database, Redis, model, Seedance, and NIM settings. The launcher overrides `SIMULATION_PROVIDER` to `isaac` at runtime, so you do not need to hand-edit that value just to use Isaac mode.

Important Isaac keys:

```env
HPC_WORKDIR=/scratch/simforge
ISAAC_RESULTS_DIR=/scratch/simforge/results
ISAAC_SIM_PATH=
ISAAC_PYTHON=
ISAAC_LD_LIBRARY_PATH=
ISAAC_EXTRA_ARGS=
ISAAC_HEADLESS=true
ENABLE_DEMO_SEED=false
```

If your node shows an Omniverse driver mismatch similar to the one in this workspace, set:

```env
ISAAC_EXTRA_ARGS=--/rtx/verifyDriverVersion/enabled=false
```

## Launch

From the repo root:

```bash
./start_hpc_isaac.sh
```

What the script does:

1. Loads optional cluster modules
2. Verifies `.venv` exists
3. Resolves the Isaac runtime from env or the local `.conda` install
4. Installs backend and simulator Python dependencies
5. Installs dashboard dependencies and builds Nuxt
6. Exports `SIMULATION_PROVIDER=isaac`
7. Starts `uvicorn` on port `8000`
8. Starts the dashboard on port `3000`
9. Writes logs and PID files under `logs/`

## Access From Your Laptop

Open an SSH tunnel:

```bash
ssh -L 8000:localhost:8000 -L 3000:localhost:3000 your-user@your-hpc-node
```

Then open:

- `http://localhost:3000` for the dashboard
- `http://localhost:8000/api/health` for the backend health check

## Run Flow

After the stack is up:

1. Create a scenario in the dashboard
2. Compile variants
3. Run the scenario
4. Watch per-variant jobs on `/runs?scenarioId=<id>`
5. Compare evaluations on `/evaluation?scenarioId=<id>`
6. Inspect artifacts on `/outputs?scenarioId=<id>`
7. Download the scenario ZIP export from the dashboard or `/api/scenarios/<id>/export`

## Current Caveat

The backend now invokes the Isaac runtime path, but the repo still does not emit full Isaac-native camera/video capture yet. Preview artifacts are still produced through the existing preview generation path, while risk scoring and scenario execution flow through the Isaac-enabled backend route.

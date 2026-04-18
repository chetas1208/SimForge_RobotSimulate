# SimForge

**AI DevTool for Physical AI Simulation — Warehouse Edge-Case Scenario Generation, Orchestration, and Evaluation**

> *Track 3: AI DevTools for Video • Track 4: Physical AI + Simulation*

---

## What is SimForge?

SimForge is a developer platform for physical AI teams building warehouse and indoor logistics systems. It provides structured tools to **define**, **generate**, **simulate**, and **evaluate** safety-critical edge-case scenarios for autonomous mobile robots (AMRs).

SimForge is:
- 🔧 **A Python SDK** — Define scenarios programmatically
- 🚀 **An Orchestration Backend** — Manage jobs, variants, and artifacts via API
- 🎬 **A Simulation Runner Abstraction** — Swap between mock and Isaac Sim providers
- 📊 **A Reference Dashboard** — Inspect everything visually

### Why SimForge?

Physical AI teams testing warehouse robots face a critical gap: **rare edge cases** (blind corners, human crossings, dropped obstacles, lighting failures) are hard to reproduce, enumerate, and evaluate systematically. SimForge addresses this by providing:

- Structured scenario definitions with controlled parameter variation
- Deterministic variant generation from a single seed
- Simulation orchestration with job state management
- Heuristic evaluation with collision risk, occlusion, and severity scoring
- Full artifact pipeline with manifests, labels, and evaluation reports

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Developer Interface                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Python   │  │   CLI    │  │  Nuxt Dashboard   │  │
│  │   SDK    │  │ (Click)  │  │  (Reference App)  │  │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│       │              │                 │              │
├───────┴──────────────┴─────────────────┴──────────────┤
│                  FastAPI Backend                       │
│  Scenario CRUD • Variant Compilation • Job Queue      │
│  Artifact Storage • Evaluation Engine • Activity Log  │
├───────────────────────────────────────────────────────┤
│               Simulation Providers                     │
│  ┌─────────────────┐  ┌────────────────────────────┐  │
│  │ MockProvider     │  │ IsaacProvider (scaffold)   │  │
│  │ (local, no GPU) │  │ (remote HPC, RTX GPUs)     │  │
│  └─────────────────┘  └────────────────────────────┘  │
├───────────────────────────────────────────────────────┤
│  SQLite (MVP) │ File Storage │ Redis (optional)       │
└───────────────────────────────────────────────────────┘
```

---

## SDK Overview

```python
from simforge import Scenario, SimForgeClient

# Define a scenario
scenario = Scenario(
    name="blind-corner-human-crossing",
    environment_template="warehouse_aisle",
    robot_path_type="left_turn_blind_corner",
    human_crossing_probability=0.8,
    dropped_obstacle_level="medium",
    blocked_aisle_enabled=True,
    lighting_preset="low_light",
    camera_mode="overhead",
    variant_count=5
)

# Submit to backend
client = SimForgeClient(base_url="http://localhost:8000")
created = client.create_scenario(scenario)
variants = client.compile_scenario(created.id)
run = client.submit_scenario(created.id)

# Check results
status = client.get_run_status(run.job_ids[0])
artifacts = client.list_artifacts(job_id=run.job_ids[0])
report = client.get_evaluation(run.job_ids[0])
```

---

## CLI Overview

```bash
# Create a scenario
simforge scenario create --name "blind-corner-test" --variants 5 --human-prob 0.8

# List scenarios
simforge scenario list

# Compile variants
simforge scenario compile <scenario-id>

# Submit run
simforge run submit <scenario-id>

# Check status
simforge run status <job-id>

# List artifacts
simforge artifacts list --job-id <job-id>

# View evaluation
simforge evaluation show <job-id>
```

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/scenarios` | Create scenario |
| GET | `/api/scenarios` | List scenarios |
| GET | `/api/scenarios/{id}` | Get scenario |
| PUT | `/api/scenarios/{id}` | Update scenario |
| DELETE | `/api/scenarios/{id}` | Delete scenario |
| POST | `/api/scenarios/{id}/compile` | Compile variants |
| GET | `/api/scenarios/{id}/variants` | List variants |
| POST | `/api/scenarios/{id}/run` | Submit simulation run |
| GET | `/api/jobs` | List jobs |
| GET | `/api/jobs/{id}` | Get job details |
| POST | `/api/jobs/{id}/retry` | Retry failed job |
| GET | `/api/artifacts` | List artifacts |
| GET | `/api/jobs/{id}/artifacts` | List job artifacts |
| GET | `/api/evaluations` | List evaluations |
| GET | `/api/jobs/{id}/evaluation` | Get job evaluation |
| GET | `/api/activity` | Activity log |
| GET | `/api/settings` | Get settings |
| PUT | `/api/settings` | Update settings |

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm or pnpm

### Backend

```bash
# Install Python dependencies
cd apps/backend
pip install -r requirements.txt
pip install -e ../../packages/simforge-sdk

# Copy environment
cp .env.example .env

# Start backend (auto-creates DB and seeds demo data)
uvicorn main:app --reload --port 8000
```

### Dashboard

```bash
# Install Node dependencies
cd apps/dashboard
npm install

# Copy environment
cp .env.example .env

# Start dashboard
npm run dev
```

### Docker Services (Optional)

```bash
# Start PostgreSQL and Redis (for production-path development)
docker-compose up -d
```

---

## Mock Mode

SimForge ships with a **MockSimulationProvider** that works fully locally without any GPU or Isaac Sim installation. Mock mode:

- Simulates job progress through all state transitions (queued → preparing → running → rendering → completed)
- Generates placeholder artifacts (manifests, labels, evaluation reports)
- Produces realistic evaluation scores using heuristic analysis
- Seeds the dashboard with demo-quality data on first startup

Set `SIMULATION_PROVIDER=mock` in backend `.env` (this is the default).

---

## Isaac Sim Integration (Future)

The `IsaacSimulationProvider` scaffold is ready for integration with NVIDIA Isaac Sim on remote HPC infrastructure:

- OpenUSD-compatible manifest generation
- SSH-based remote job submission hooks
- Result collection from HPC storage
- Parameterized scene templates per environment type

Configure via:
```env
SIMULATION_PROVIDER=isaac
HPC_HOST=your-hpc.cluster.edu
HPC_USER=username
HPC_WORKDIR=/scratch/simforge
ISAAC_RESULTS_DIR=/scratch/simforge/results
```

---

## Track 4 Pipeline

The repo now also includes a Track 4 stack with:

- real-data warehouse LiDAR preprocessing and feature engineering
- GPU XGBoost risk training
- deterministic text-to-scenario parsing
- OpenUSD + Isaac-preview generation
- backend-callable inference service contracts

See [README_TRACK4.md](/home/923873155/Hackathon_18Apr/README_TRACK4.md) for the exact setup, real-dataset run order, GPU selection commands, parser examples, and backend integration flow.

---

## Folder Structure

```
simforge/
├── apps/
│   ├── backend/            # FastAPI orchestration server
│   │   ├── app/
│   │   │   ├── api/        # Route handlers
│   │   │   ├── core/       # Configuration
│   │   │   └── db/         # Models, database, seed data
│   │   └── main.py
│   ├── dashboard/          # Nuxt 3 reference dashboard
│   │   ├── components/     # Reusable UI components
│   │   ├── composables/    # API composable
│   │   ├── layouts/        # App layout with sidebar
│   │   ├── pages/          # Route pages
│   │   └── assets/css/     # Tailwind theme
│   └── runner/             # Simulation providers
│       └── providers/
│           ├── mock/       # Local mock provider
│           └── isaac/      # Isaac Sim scaffold
├── packages/
│   ├── simforge-sdk/       # Python SDK (core product)
│   │   └── simforge/       # SDK modules
│   ├── cli/                # CLI tool
│   ├── shared-types/       # TypeScript interfaces
│   └── config/             # Shared constants
├── tests/                  # SDK and API tests
├── docker-compose.yml      # Postgres + Redis
└── README.md
```

---

## Running Tests

```bash
# SDK tests
pytest tests/test_sdk.py -v

# API tests
pytest tests/test_api.py -v

# All tests
pytest tests/ -v
```

---

## Screenshots

> Dashboard screenshots will be added after first deployment.

---

## Roadmap

- [ ] Full Isaac Sim integration with OpenUSD scene generation
- [ ] Real video output rendering and preview playback
- [ ] ML-based evaluation engine replacing heuristic scoring
- [ ] Multi-environment support (loading docks, cold storage, open floor)
- [ ] Scenario template library with community contributions
- [ ] Batch comparison across scenario families
- [ ] Real-world dataset integration (warehouse LiDAR, navigation logs)
- [ ] Team collaboration features
- [ ] CI/CD pipeline for automated testing
- [ ] PyPI package publication for `simforge` SDK

---

## License

MIT

---

*Built for the Physical AI + AI DevTools hackathon. SimForge helps robotics teams test the edge cases that matter most.*

#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="${SIMFORGE_VENV_BIN:-${ROOT_DIR}/.venv/bin}"
PYTHON_BIN="${VENV_BIN}/python"
PIP_BIN="${VENV_BIN}/pip"
BACKEND_ENV="${SIMFORGE_BACKEND_ENV:-${ROOT_DIR}/apps/backend/.env}"
LOG_DIR="${SIMFORGE_LOG_DIR:-${ROOT_DIR}/logs}"
BACKEND_HOST="${SIMFORGE_BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${SIMFORGE_BACKEND_PORT:-8000}"
DASHBOARD_HOST="${SIMFORGE_DASHBOARD_HOST:-0.0.0.0}"
DASHBOARD_PORT="${SIMFORGE_DASHBOARD_PORT:-3000}"
DEFAULT_ISAAC_PYTHON="${ROOT_DIR}/.conda/envs/isaacsim-4.5/bin/python"
DEFAULT_ISAAC_LIB="${ROOT_DIR}/.conda/envs/isaacsim-4.5/lib"

load_module() {
  local module_name="$1"
  if [ -z "${module_name}" ]; then
    return
  fi
  if declare -F module >/dev/null 2>&1 || command -v module >/dev/null 2>&1; then
    module load "${module_name}"
  else
    echo "Module '${module_name}' requested but the 'module' command is unavailable."
    echo "Set PATHs manually or source your cluster's module init script via SIMFORGE_MODULE_INIT."
    exit 1
  fi
}

dotenv_value() {
  local key="$1"
  "${PYTHON_BIN}" - "$BACKEND_ENV" "$key" <<'PY'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
target = sys.argv[2]
if not env_path.exists():
    raise SystemExit(0)

for line in env_path.read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    key, value = stripped.split("=", 1)
    if key == target:
        print(value)
        break
PY
}

ensure_port_free() {
  local port="$1"
  "${PYTHON_BIN}" - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket() as sock:
    sock.settimeout(1)
    if sock.connect_ex(("127.0.0.1", port)) == 0:
        print(f"Port {port} is already in use.", file=sys.stderr)
        raise SystemExit(1)
PY
}

if [ -n "${SIMFORGE_MODULE_INIT:-}" ] && [ -f "${SIMFORGE_MODULE_INIT}" ]; then
  # shellcheck disable=SC1090
  source "${SIMFORGE_MODULE_INIT}"
fi

load_module "${SIMFORGE_CUDA_MODULE:-}"
load_module "${SIMFORGE_PYTHON_MODULE:-}"
load_module "${SIMFORGE_NODE_MODULE:-}"

if [ ! -x "${PYTHON_BIN}" ]; then
  echo "Expected virtualenv at ${VENV_BIN}"
  echo "Create it first: python3 -m venv .venv"
  exit 1
fi

if [ ! -f "${BACKEND_ENV}" ]; then
  cp "${ROOT_DIR}/apps/backend/.env.example" "${BACKEND_ENV}"
fi

ensure_port_free "${BACKEND_PORT}"
ensure_port_free "${DASHBOARD_PORT}"

ISAAC_PYTHON_BIN="${ISAAC_PYTHON:-$(dotenv_value ISAAC_PYTHON)}"
ISAAC_SIM_PATH_VALUE="${ISAAC_SIM_PATH:-$(dotenv_value ISAAC_SIM_PATH)}"
ISAAC_LD_PATH_VALUE="${ISAAC_LD_LIBRARY_PATH:-$(dotenv_value ISAAC_LD_LIBRARY_PATH)}"
ISAAC_EXTRA_ARGS_VALUE="${ISAAC_EXTRA_ARGS:-$(dotenv_value ISAAC_EXTRA_ARGS)}"

if [ -z "${ISAAC_PYTHON_BIN}" ] && [ -n "${ISAAC_SIM_PATH_VALUE}" ]; then
  ISAAC_PYTHON_BIN="${ISAAC_SIM_PATH_VALUE}/python.sh"
fi
if [ -z "${ISAAC_PYTHON_BIN}" ] && [ -x "${DEFAULT_ISAAC_PYTHON}" ]; then
  ISAAC_PYTHON_BIN="${DEFAULT_ISAAC_PYTHON}"
fi
if [ -z "${ISAAC_LD_PATH_VALUE}" ] && [ -d "${DEFAULT_ISAAC_LIB}" ]; then
  ISAAC_LD_PATH_VALUE="${DEFAULT_ISAAC_LIB}"
fi
if [ -z "${ISAAC_EXTRA_ARGS_VALUE}" ] && [ -x "${DEFAULT_ISAAC_PYTHON}" ]; then
  ISAAC_EXTRA_ARGS_VALUE="--/rtx/verifyDriverVersion/enabled=false"
fi

if [ -z "${ISAAC_PYTHON_BIN}" ] || [ ! -x "${ISAAC_PYTHON_BIN}" ]; then
  echo "Isaac runtime not found."
  echo "Set ISAAC_PYTHON or ISAAC_SIM_PATH in ${BACKEND_ENV}, or install Isaac under ${ROOT_DIR}/.conda/envs/isaacsim-4.5."
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js and npm are required to launch the dashboard."
  echo "Load a cluster module first, e.g. SIMFORGE_NODE_MODULE=nodejs/20 ./start_hpc_isaac.sh"
  exit 1
fi

mkdir -p "${LOG_DIR}"
BACKEND_LOG="${LOG_DIR}/backend_isaac.log"
DASHBOARD_LOG="${LOG_DIR}/dashboard_isaac.log"
BACKEND_PID_FILE="${LOG_DIR}/backend_isaac.pid"
DASHBOARD_PID_FILE="${LOG_DIR}/dashboard_isaac.pid"

echo "Installing Python runtime dependencies..."
"${PIP_BIN}" install -r "${ROOT_DIR}/apps/backend/requirements.txt"
"${PIP_BIN}" install -r "${ROOT_DIR}/apps/parser/requirements.txt"
"${PIP_BIN}" install -r "${ROOT_DIR}/apps/simulator/requirements.txt"
"${PIP_BIN}" install -r "${ROOT_DIR}/apps/inference/requirements.txt"
"${PIP_BIN}" install -e "${ROOT_DIR}/packages/simforge-sdk"

echo "Installing dashboard dependencies..."
cd "${ROOT_DIR}/apps/dashboard"
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

export SIMULATION_PROVIDER=isaac
export ENABLE_DEMO_SEED=false
export ISAAC_PYTHON="${ISAAC_PYTHON_BIN}"
export ISAAC_HEADLESS="${ISAAC_HEADLESS:-true}"
export NUXT_PUBLIC_API_BASE_URL="http://localhost:${BACKEND_PORT}/api"
if [ -n "${ISAAC_LD_PATH_VALUE}" ]; then
  export ISAAC_LD_LIBRARY_PATH="${ISAAC_LD_PATH_VALUE}"
fi
if [ -n "${ISAAC_EXTRA_ARGS_VALUE}" ]; then
  export ISAAC_EXTRA_ARGS="${ISAAC_EXTRA_ARGS_VALUE}"
fi

echo "Building dashboard..."
npm run build

echo "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}..."
cd "${ROOT_DIR}/apps/backend"
nohup "${VENV_BIN}/uvicorn" main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" > "${BACKEND_LOG}" 2>&1 &
echo $! > "${BACKEND_PID_FILE}"

echo "Waiting for backend health check..."
"${PYTHON_BIN}" - "${BACKEND_PORT}" <<'PY'
import json
import sys
import time
import urllib.request

port = int(sys.argv[1])
url = f"http://127.0.0.1:{port}/api/health"
last_error = None
for _ in range(30):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("status") == "ok":
            raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(1)
print(f"Backend health check failed: {last_error}", file=sys.stderr)
raise SystemExit(1)
PY

echo "Starting dashboard on ${DASHBOARD_HOST}:${DASHBOARD_PORT}..."
cd "${ROOT_DIR}/apps/dashboard"
nohup npm run start -- --host "${DASHBOARD_HOST}" --port "${DASHBOARD_PORT}" > "${DASHBOARD_LOG}" 2>&1 &
echo $! > "${DASHBOARD_PID_FILE}"

HOST_LABEL="$(hostname -f 2>/dev/null || hostname)"
echo
echo "SimForge Isaac stack is starting."
echo "Backend:   http://${HOST_LABEL}:${BACKEND_PORT}/api/health"
echo "Dashboard: http://${HOST_LABEL}:${DASHBOARD_PORT}"
echo "Backend log:   ${BACKEND_LOG}"
echo "Dashboard log: ${DASHBOARD_LOG}"
echo "Stop commands:"
echo "  kill \$(cat ${BACKEND_PID_FILE})"
echo "  kill \$(cat ${DASHBOARD_PID_FILE})"

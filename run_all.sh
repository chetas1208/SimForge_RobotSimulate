#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="${ROOT_DIR}/.venv/bin"
DASHBOARD_MODE="${SIMFORGE_DASHBOARD_MODE:-production}"

if [ ! -x "${VENV_BIN}/python" ]; then
  echo "Expected virtualenv at ${ROOT_DIR}/.venv"
  echo "Create it first: python3 -m venv .venv"
  exit 1
fi

echo "Installing Python runtime dependencies..."
"${VENV_BIN}/pip" install -r "${ROOT_DIR}/apps/backend/requirements.txt"
"${VENV_BIN}/pip" install -r "${ROOT_DIR}/apps/parser/requirements.txt"
"${VENV_BIN}/pip" install -r "${ROOT_DIR}/apps/simulator/requirements.txt"
"${VENV_BIN}/pip" install -r "${ROOT_DIR}/apps/inference/requirements.txt"
"${VENV_BIN}/pip" install -e "${ROOT_DIR}/packages/simforge-sdk"

if [ -f "${ROOT_DIR}/docker-compose.yml" ] && command -v docker-compose >/dev/null 2>&1; then
  echo "Starting optional Docker services..."
  docker-compose -f "${ROOT_DIR}/docker-compose.yml" up -d || true
fi

if [ ! -f "${ROOT_DIR}/apps/backend/.env" ]; then
  cp "${ROOT_DIR}/apps/backend/.env.example" "${ROOT_DIR}/apps/backend/.env"
fi

if [ ! -f "${ROOT_DIR}/apps/dashboard/.env" ]; then
  cp "${ROOT_DIR}/apps/dashboard/.env.example" "${ROOT_DIR}/apps/dashboard/.env"
fi

echo "Starting backend..."
cd "${ROOT_DIR}/apps/backend"
nohup "${VENV_BIN}/uvicorn" main:app --host 0.0.0.0 --port 8000 > "${ROOT_DIR}/backend.log" 2>&1 &
BACKEND_PID=$!

echo "Starting dashboard (${DASHBOARD_MODE})..."
cd "${ROOT_DIR}/apps/dashboard"
npm install
if [ "${DASHBOARD_MODE}" = "production" ]; then
  npm run build
  nohup npm run start -- --host 0.0.0.0 --port 3000 > "${ROOT_DIR}/frontend.log" 2>&1 &
else
  nohup npm run dev -- --host 0.0.0.0 --port 3000 > "${ROOT_DIR}/frontend.log" 2>&1 &
fi
DASHBOARD_PID=$!

cd "${ROOT_DIR}"
echo "Backend PID: ${BACKEND_PID}"
echo "Dashboard PID: ${DASHBOARD_PID}"
echo "Logs: ${ROOT_DIR}/backend.log and ${ROOT_DIR}/frontend.log"

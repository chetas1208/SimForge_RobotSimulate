#!/bin/bash

# Start services (Optional docker services)
echo "Starting Postgres and Redis (if Docker is available)..."
docker-compose up -d || echo "Docker not available, skipping Postgres and Redis."

# Start backend
echo "Starting Backend..."
cd apps/backend
../../.venv/bin/pip install -r requirements.txt
../../.venv/bin/pip install -e ../../packages/simforge-sdk
if [ ! -f .env ]; then
  cp .env.example .env
fi
nohup ../../.venv/bin/uvicorn main:app --reload --port 8000 > ../../backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Start dashboard (Nuxt)
echo "Starting Nuxt Dashboard..."
cd ../dashboard
npm install
if [ ! -f .env ]; then
  cp .env.example .env
fi
nohup npm run dev > ../../frontend.log 2>&1 &
DASHBOARD_PID=$!
echo "Dashboard PID: $DASHBOARD_PID"

# Start frontend (Next.js) if it exists
if [ -d "../frontend" ]; then
  echo "Starting Next.js Frontend..."
  cd ../frontend
  npm install
  nohup npm run dev > ../../nextjs.log 2>&1 &
  NEXTJS_PID=$!
  echo "Next.js PID: $NEXTJS_PID"
fi

cd ../..
echo "All services are starting!"
echo "Check backend.log, frontend.log, and nextjs.log for output."
echo "PIDs: Backend($BACKEND_PID), Dashboard($DASHBOARD_PID), Next.js($NEXTJS_PID)"

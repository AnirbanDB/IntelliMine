#!/bin/bash

# Kill background processes on exit
trap "kill 0" EXIT

echo "🚀 Starting IntelliMine: AI Mine Operations Simulator..."

# Install dependencies if node_modules don't exist
if [ ! -d "backend/venv" ]; then
    echo "Creating python environment..."
    python3 -m venv backend/venv
    source backend/venv/bin/activate
    pip install -r backend/requirements.txt
fi

# Run backend
echo "📦 Launching FastAPI backend..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Run frontend
echo "🎨 Launching React frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

wait

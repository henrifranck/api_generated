#!/bin/bash
set -e

echo "🧪 Running tests (mandatory pre-launch check)..."
if /app/run_tests.sh; then
    echo "✅ All tests passed - proceeding with startup"
else
    echo "❌ Tests failed - aborting startup"
    exit 1
fi

# Normal startup procedure
echo "⚙️ Initializing service..."
python /app/backend_pre_start.py

echo "📜 Running migrations..."
alembic upgrade head

# Step 4: Load initial data
echo "🌱 Loading initial data..."
python /app/initial_data.py

echo "🚀 Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8081 --reload
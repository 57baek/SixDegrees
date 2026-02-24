#!/usr/bin/env bash
#
# run_demo.sh — SixDegrees v1.1 presentation-mode demo runner
#
# Prerequisites:
#   - Backend running:  cd backend && uvicorn app:app --reload
#   - Frontend running: cd frontend && npm run dev
#   - TEST_EMAIL env var set to a valid SixDegrees test account email
#   - TEST_PASSWORD env var set to the corresponding password
#
# Usage:
#   TEST_EMAIL=you@example.com TEST_PASSWORD=yourpass ./scripts/run_demo.sh

echo "========================================"
echo " SixDegrees v1.1 — Full Demo Walkthrough"
echo "========================================"

# Check required env vars
if [ -z "$TEST_EMAIL" ]; then
  echo ""
  echo "ERROR: TEST_EMAIL is not set."
  echo ""
  echo "Usage: TEST_EMAIL=you@example.com TEST_PASSWORD=yourpass ./scripts/run_demo.sh"
  exit 1
fi

if [ -z "$TEST_PASSWORD" ]; then
  echo ""
  echo "ERROR: TEST_PASSWORD is not set."
  echo ""
  echo "Usage: TEST_EMAIL=you@example.com TEST_PASSWORD=yourpass ./scripts/run_demo.sh"
  exit 1
fi

echo ""
echo "Reminder: Ensure both servers are running before continuing."
echo "  Backend:  http://localhost:8000  (uvicorn app:app --reload)"
echo "  Frontend: http://localhost:5173  (npm run dev)"
echo ""

# Load SUPABASE_URL and SUPABASE_KEY from backend/.env so Playwright can
# pre-provision the test account via admin API (creates account on first run).
BACKEND_ENV="$(dirname "$0")/../backend/.env"
if [ -f "$BACKEND_ENV" ]; then
  export SUPABASE_URL SUPABASE_KEY
  SUPABASE_URL=$(grep -E "^SUPABASE_URL=" "$BACKEND_ENV" | head -1 | cut -d= -f2-)
  SUPABASE_KEY=$(grep -E "^SUPABASE_KEY=" "$BACKEND_ENV" | head -1 | cut -d= -f2-)
  echo "Supabase config loaded from backend/.env."
else
  echo "WARNING: backend/.env not found — account auto-creation will be skipped."
fi

echo ""
echo "Starting demo in 2 seconds..."
sleep 2

# Run the Playwright demo spec from the frontend/ directory
cd "$(dirname "$0")/../frontend"

TEST_EMAIL="$TEST_EMAIL" TEST_PASSWORD="$TEST_PASSWORD" \
  SUPABASE_URL="${SUPABASE_URL:-}" SUPABASE_KEY="${SUPABASE_KEY:-}" \
  npx playwright test e2e/demo.spec.js --headed --timeout=60000 --project=chromium

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo "Demo passed."
else
  echo "Demo FAILED — check output above."
fi

exit $EXIT_CODE

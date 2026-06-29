#!/usr/bin/env bash
# Folio verification script
# Runs all checks and exits non-zero on failure.
# Usage: scripts/verify.sh [--scope backend|frontend|full] [--e2e]

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────
SCOPE=""
RUN_E2E=false
RESULTS=()
FAILED=false

# ── Parse args ────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --scope) SCOPE="$2"; shift 2 ;;
    --e2e)   RUN_E2E=true; shift ;;
    *)       echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── Auto-detect scope from git diff ──────────────────────────────────
if [[ -z "$SCOPE" ]]; then
  CHANGED=$(git diff --name-only main 2>/dev/null || git diff --name-only HEAD~1 2>/dev/null || echo "")
  HAS_BACKEND=$(echo "$CHANGED" | grep -c "^backend/" || true)
  HAS_FRONTEND=$(echo "$CHANGED" | grep -c "^frontend/" || true)

  if [[ $HAS_BACKEND -gt 0 && $HAS_FRONTEND -gt 0 ]]; then
    SCOPE="full"
  elif [[ $HAS_BACKEND -gt 0 ]]; then
    SCOPE="backend"
  elif [[ $HAS_FRONTEND -gt 0 ]]; then
    SCOPE="frontend"
  else
    SCOPE="full"
  fi
fi

# ── Helper: record result ────────────────────────────────────────────
record() {
  local name="$1" status="$2" detail="${3:-}"
  if [[ "$status" == "PASS" ]]; then
    RESULTS+=("$(printf '  %-20s ✅ PASS %s' "$name" "$detail")")
  elif [[ "$status" == "FAIL" ]]; then
    RESULTS+=("$(printf '  %-20s ❌ FAIL %s' "$name" "$detail")")
    FAILED=true
  elif [[ "$status" == "SKIP" ]]; then
    RESULTS+=("$(printf '  %-20s ⏭️  SKIPPED %s' "$name" "$detail")")
  fi
}

echo ""
echo "══════════════════════════════════════"
echo "  FOLIO VERIFICATION"
echo "  Scope: $SCOPE | E2E: $RUN_E2E"
echo "══════════════════════════════════════"
echo ""

# ── Backend: pytest ───────────────────────────────────────────────────
if [[ "$SCOPE" == "backend" || "$SCOPE" == "full" ]]; then
  echo "▸ Backend: pytest"
  if [[ -d "backend/.venv" ]]; then
    set +e
    TEST_OUTPUT=$(cd backend && source .venv/bin/activate && python -m pytest -v --tb=short 2>&1)
    TEST_EXIT=$?
    set -e
    echo "$TEST_OUTPUT" | tail -5
    if [[ $TEST_EXIT -eq 0 ]]; then
      COUNT=$(echo "$TEST_OUTPUT" | grep -oP '\d+ passed' | head -1 || echo "")
      record "Backend pytest" "PASS" "($COUNT)"
    else
      record "Backend pytest" "FAIL"
    fi
  else
    record "Backend pytest" "SKIP" "(no .venv found)"
  fi
  echo ""
else
  record "Backend pytest" "SKIP" "(not in scope)"
fi

# ── Frontend: lint ────────────────────────────────────────────────────
if [[ "$SCOPE" == "frontend" || "$SCOPE" == "full" ]]; then
  echo "▸ Frontend: lint"
  if [[ -d "frontend/node_modules" ]]; then
    set +e
    cd frontend && npm run lint 2>&1 | tail -3
    LINT_EXIT=${PIPESTATUS[0]}
    cd ..
    set -e
    if [[ $LINT_EXIT -eq 0 ]]; then
      record "Frontend lint" "PASS"
    else
      record "Frontend lint" "FAIL"
    fi
  else
    record "Frontend lint" "SKIP" "(no node_modules)"
  fi
  echo ""
else
  record "Frontend lint" "SKIP" "(not in scope)"
fi

# ── Frontend: type check ─────────────────────────────────────────────
if [[ "$SCOPE" == "frontend" || "$SCOPE" == "full" ]]; then
  echo "▸ Frontend: tsc --noEmit"
  set +e
  cd frontend && npx tsc --noEmit 2>&1 | tail -5
  TSC_EXIT=${PIPESTATUS[0]}
  cd ..
  set -e
  if [[ $TSC_EXIT -eq 0 ]]; then
    record "Frontend types" "PASS"
  else
    record "Frontend types" "FAIL"
  fi
  echo ""
else
  record "Frontend types" "SKIP" "(not in scope)"
fi

# ── Frontend: vitest ─────────────────────────────────────────────────
if [[ "$SCOPE" == "frontend" || "$SCOPE" == "full" ]]; then
  echo "▸ Frontend: vitest"
  set +e
  cd frontend && npx vitest run 2>&1 | tail -10
  VITEST_EXIT=${PIPESTATUS[0]}
  cd ..
  set -e
  if [[ $VITEST_EXIT -eq 0 ]]; then
    COUNT=$(cd frontend && npx vitest run --reporter=verbose 2>&1 | grep -c "✓\|✓" || echo "?")
    record "Frontend vitest" "PASS" "($COUNT tests)"
  else
    record "Frontend vitest" "FAIL"
  fi
  echo ""
else
  record "Frontend vitest" "SKIP" "(not in scope)"
fi

# ── Frontend: build ──────────────────────────────────────────────────
if [[ "$SCOPE" == "frontend" || "$SCOPE" == "full" ]]; then
  echo "▸ Frontend: build"
  set +e
  cd frontend && npm run build 2>&1 | tail -5
  BUILD_EXIT=${PIPESTATUS[0]}
  cd ..
  set -e
  if [[ $BUILD_EXIT -eq 0 ]]; then
    record "Frontend build" "PASS"
  else
    record "Frontend build" "FAIL"
  fi
  echo ""
else
  record "Frontend build" "SKIP" "(not in scope)"
fi

# ── Playwright E2E ───────────────────────────────────────────────────
if [[ "$RUN_E2E" == true ]]; then
  echo "▸ Playwright E2E"

  # Start backend
  echo "  Starting backend server..."
  cd backend && source .venv/bin/activate
  uvicorn app.main:app --port 8000 &
  BACKEND_PID=$!
  cd ..

  # Start frontend
  echo "  Starting frontend dev server..."
  cd frontend && npm run dev -- --port 5174 &
  FRONTEND_PID=$!
  cd ..

  # Wait for servers to be ready
  echo "  Waiting for servers..."
  sleep 5

  # Run Playwright
  set +e
  cd frontend && npx playwright test --config e2e/playwright.config.ts 2>&1
  E2E_EXIT=$?
  cd ..
  set -e

  # Shutdown servers
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  wait $BACKEND_PID 2>/dev/null || true
  wait $FRONTEND_PID 2>/dev/null || true

  if [[ $E2E_EXIT -eq 0 ]]; then
    record "Playwright E2E" "PASS"
  else
    record "Playwright E2E" "FAIL"
  fi
  echo ""
else
  record "Playwright E2E" "SKIP" "(use --e2e)"
fi

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════"
echo "  VERIFICATION RESULTS"
echo "══════════════════════════════════════"
for r in "${RESULTS[@]}"; do
  echo "$r"
done
echo "══════════════════════════════════════"

if [[ "$FAILED" == true ]]; then
  echo "  RESULT: ❌ FAIL"
  echo "══════════════════════════════════════"
  exit 1
else
  echo "  RESULT: ✅ PASS"
  echo "══════════════════════════════════════"
  exit 0
fi

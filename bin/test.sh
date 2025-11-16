#!/bin/bash
# Run TaskPy test suite

set -e

# Resolve repository root from bin/
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "╔════════════════════════════════════════════════╗"
echo "║           TASKPY TEST SUITE                    ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Set PYTHONPATH to include src
export PYTHONPATH="$ROOT_DIR/src:${PYTHONPATH}"

# Run pytest
echo "🧪 Running tests..."
if ! python3 -m pytest "$ROOT_DIR/tests" -v "$@"; then
    echo ""
    echo "❌ Tests failed"
    exit 1
fi

echo ""
echo "✅ All tests passed!"

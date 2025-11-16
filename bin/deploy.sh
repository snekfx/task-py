#!/bin/bash
set -e

# Configuration
SNEK_BIN_DIR="$HOME/.local/bin/snek"
BUNDLE_DIR="$SNEK_BIN_DIR/taskpy-bundle"
SYSTEM_PYTHON="${TASKPY_PYTHON:-$(command -v python3)}"

# Resolve repository root from bin/
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Initialize pyenv if available
if [ -d "$HOME/.pyenv" ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)"
fi

# Extract version from pyproject.toml or default
VERSION=$(grep -E "^version\s*=" "$ROOT_DIR/pyproject.toml" | head -1 | cut -d'"' -f2 2>/dev/null || echo "0.1.0-dev")

# Display deployment ceremony
echo "╔════════════════════════════════════════════════╗"
echo "║              TASKPY DEPLOYMENT                 ║"
echo "╠════════════════════════════════════════════════╣"
echo "║ Package: META PROCESS v4 Task Manager          ║"
echo "║ Version: v$VERSION                             ║"
echo "║ Target:  $SNEK_BIN_DIR/taskpy                  ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Deploy taskpy via pip
echo "📋 Deploying taskpy tool..."

if [ -z "$SYSTEM_PYTHON" ]; then
    echo "✗ Could not find python3 on PATH"
    exit 1
fi

echo "🐍 Python: $($SYSTEM_PYTHON --version 2>&1)"
PIP_CMD=("$SYSTEM_PYTHON" -m pip)
"${PIP_CMD[@]}" --version >/dev/null 2>&1 || "$SYSTEM_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
echo "📦 pip: $("${PIP_CMD[@]}" --version | cut -d' ' -f1-2)"
echo ""

mkdir -p "$SNEK_BIN_DIR"
rm -rf "$BUNDLE_DIR"

echo "📦 Building bundled site-packages at $BUNDLE_DIR"
"${PIP_CMD[@]}" install --upgrade --no-deps --target "$BUNDLE_DIR" "$ROOT_DIR"

echo "📦 Creating taskpy wrapper in snek directory..."
TASKPY_TARGET="$SNEK_BIN_DIR/taskpy"
cat > "$TASKPY_TARGET" << WRAPPER_EOF
#!/usr/bin/env python3
import os
import sys

BUNDLE_DIR = "$BUNDLE_DIR"
if BUNDLE_DIR not in sys.path:
    sys.path.insert(0, BUNDLE_DIR)

from taskpy.cli import main

if __name__ == "__main__":
    sys.exit(main())
WRAPPER_EOF
chmod +x "$TASKPY_TARGET"

if [ -f "$ROOT_DIR/logo.txt" ]; then
    cp "$ROOT_DIR/logo.txt" "$SNEK_BIN_DIR/taskpy_logo.txt"
fi

echo "✅ taskpy bundled successfully"

echo "📋 Testing taskpy deployment..."
"$TASKPY_TARGET" --version

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║          DEPLOYMENT SUCCESSFUL!                ║"
echo "╚════════════════════════════════════════════════╝"
echo "  Deployed: taskpy v$VERSION                     "
echo "  Location: $SNEK_BIN_DIR/taskpy                 "
echo "  Bundle:   $BUNDLE_DIR                           "
echo "  Method:   pip --target bundle                   "
echo ""
echo "📋 taskpy task management commands:"
echo "   taskpy init                 # Initialize kanban structure"
echo "   taskpy create EPIC \"title\" # Create new task"
echo "   taskpy list                 # List tasks"
echo "   taskpy show TASK-ID         # Show task details"
echo "   taskpy promote TASK-ID      # Move task forward"
echo "   taskpy kanban               # Display kanban board"
echo "   taskpy stats                # Show statistics"
echo "   taskpy --help               # Full command reference"
echo ""
echo "🚀 Ready to manage your META PROCESS v4 workflows!"

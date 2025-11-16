#!/bin/bash
set -e

# Configuration
SNEK_BIN_DIR="$HOME/.local/bin/snek"

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

# Display Python/pip info
echo "🐍 Python: $(python --version 2>&1)"
echo "📦 pip: $(pip --version | cut -d' ' -f1-2)"
echo ""

# Create snek directory
mkdir -p "$SNEK_BIN_DIR"

# Create wrapper script in snek directory
echo "📦 Creating taskpy wrapper in snek directory..."
TASKPY_TARGET="$SNEK_BIN_DIR/taskpy"

cat > "$TASKPY_TARGET" << WRAPPER_EOF
#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os

# Add taskpy src to path
TASKPY_SRC = "$ROOT_DIR/src"
if os.path.exists(TASKPY_SRC):
    sys.path.insert(0, TASKPY_SRC)

from taskpy.cli import main

if __name__ == '__main__':
    sys.exit(main())
WRAPPER_EOF

# Make executable
chmod +x "$TASKPY_TARGET"

# Copy logo
if [ -f "$ROOT_DIR/logo.txt" ]; then
    cp "$ROOT_DIR/logo.txt" "$SNEK_BIN_DIR/taskpy_logo.txt"
fi

echo "✅ taskpy deployed successfully"

# Test the deployment
echo "📋 Testing taskpy deployment..."
if command -v taskpy >/dev/null 2>&1; then
    echo "✅ taskpy is available in PATH"
    taskpy --version
else
    echo "⚠️  Warning: taskpy not found in PATH (may need to restart shell)"
fi

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║          DEPLOYMENT SUCCESSFUL!                ║"
echo "╚════════════════════════════════════════════════╝"
echo "  Deployed: taskpy v$VERSION                     "
echo "  Location: $SNEK_BIN_DIR/taskpy                 "
echo "  Method:   wrapper → pip package                "
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

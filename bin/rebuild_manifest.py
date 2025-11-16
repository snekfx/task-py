#!/usr/bin/env python3
"""
Rebuild manifest.tsv from all task files.

This script scans all task files in the status directories and rebuilds
the manifest from scratch.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from taskpy.storage import TaskStorage
from taskpy.models import TaskStatus

def main():
    """Rebuild the manifest from all task files."""
    storage = TaskStorage(Path.cwd())

    if not storage.is_initialized():
        print("Error: TaskPy not initialized")
        sys.exit(1)

    print("Rebuilding manifest from task files...")

    # Clear manifest (keep header)
    storage._create_manifest_header()

    # Scan all status directories
    tasks_found = 0
    for status in TaskStatus:
        status_dir = storage.status_dir / status.value
        if not status_dir.exists():
            continue

        for task_file in status_dir.glob("*.md"):
            try:
                task = storage.read_task_file(task_file)
                storage._update_manifest_row(task)
                tasks_found += 1
                print(f"  Added {task.id} ({status.value})")
            except Exception as e:
                print(f"  Error reading {task_file}: {e}")

    print(f"\n✓ Rebuilt manifest with {tasks_found} tasks")

if __name__ == "__main__":
    main()

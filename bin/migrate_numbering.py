#!/usr/bin/env python3
"""
Migrate task files from 3-digit format (EPIC-001) to 2-digit format (EPIC-01).
This is a one-time migration script.
"""

import re
import sys
from pathlib import Path

# Add src to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from taskpy.storage import TaskStorage


def migrate_task_file(file_path: Path, storage: TaskStorage):
    """Migrate a single task file from 3-digit to 2-digit format."""
    # Parse the old task ID from filename
    old_id = file_path.stem  # e.g., "FEAT-001"
    match = re.match(r'^([A-Z]+)-(\d+)$', old_id)
    if not match:
        print(f"⚠️  Skipping {file_path.name} - invalid format")
        return False

    epic, num_str = match.groups()
    num = int(num_str)

    # If already 2-digit format, skip
    if num < 100 and len(num_str) == 2:
        print(f"✓ {old_id} already in 2-digit format")
        return False

    # Generate new ID
    if num <= 99:
        new_id = f"{epic}-{num:02d}"
    else:
        new_id = f"{epic}-{num:03d}"  # Already correct for 100+

    if new_id == old_id:
        print(f"✓ {old_id} already correct")
        return False

    # Read the file content
    content = file_path.read_text()

    # Update the ID in frontmatter
    content = re.sub(
        r"^id:\s*" + re.escape(old_id),
        f"id: {new_id}",
        content,
        flags=re.MULTILINE
    )

    # Update the ID in the heading (if present)
    content = re.sub(
        r"^#\s+" + re.escape(old_id),
        f"# {new_id}",
        content,
        flags=re.MULTILINE
    )

    # Create new file path
    new_path = file_path.parent / f"{new_id}.md"

    # Write new file
    new_path.write_text(content)

    # Remove old file
    file_path.unlink()

    print(f"✓ Migrated: {old_id} -> {new_id}")
    return True


def rebuild_manifest(storage: TaskStorage):
    """Rebuild the manifest from scratch."""
    print("\n📝 Rebuilding manifest...")

    # Clear manifest
    storage.manifest_file.write_text("")
    storage._create_manifest_header()

    # Scan all task files and rebuild
    count = 0
    for status_dir in storage.status_dir.iterdir():
        if not status_dir.is_dir():
            continue

        for task_file in status_dir.glob("*.md"):
            try:
                task = storage.read_task_file(task_file)
                storage._update_manifest_row(task)
                count += 1
            except Exception as e:
                print(f"⚠️  Error processing {task_file.name}: {e}")

    print(f"✓ Rebuilt manifest with {count} tasks")


def main():
    """Run the migration."""
    storage = TaskStorage(Path.cwd())

    if not storage.is_initialized():
        print("❌ TaskPy not initialized in this directory")
        sys.exit(1)

    print("╔════════════════════════════════════════════════╗")
    print("║     TASKPY NUMBERING FORMAT MIGRATION         ║")
    print("║     3-digit (EPIC-001) -> 2-digit (EPIC-01)   ║")
    print("╚════════════════════════════════════════════════╝\n")

    # Find all task files
    task_files = []
    for status_dir in storage.status_dir.iterdir():
        if not status_dir.is_dir():
            continue
        task_files.extend(status_dir.glob("*.md"))

    print(f"Found {len(task_files)} task files\n")

    # Migrate each file
    migrated = 0
    for task_file in sorted(task_files):
        if migrate_task_file(task_file, storage):
            migrated += 1

    # Rebuild manifest
    rebuild_manifest(storage)

    print(f"\n✅ Migration complete! Migrated {migrated} tasks.")


if __name__ == "__main__":
    main()

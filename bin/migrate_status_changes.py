#!/usr/bin/env python3
"""
Migrate tasks to new status system (FEAT-10).

Changes:
- Rename REVIEW status to QA
- Add STUB, BLOCKED statuses
- Add milestone and blocked_reason fields
- Migrate existing backlog tasks based on completeness
"""

import re
import sys
from pathlib import Path

# Add src to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from taskpy.storage import TaskStorage


def ensure_new_directories(storage: TaskStorage):
    """Ensure all new status directories exist."""
    (storage.status_dir / "stub").mkdir(exist_ok=True)
    (storage.status_dir / "qa").mkdir(exist_ok=True)
    (storage.status_dir / "blocked").mkdir(exist_ok=True)
    print("✓ Created new status directories (stub/, qa/, blocked/)")


def migrate_review_to_qa(storage: TaskStorage):
    """Migrate tasks from review/ to qa/ directory."""
    review_dir = storage.status_dir / "review"
    qa_dir = storage.status_dir / "qa"

    if not review_dir.exists():
        print("✓ No review/ directory found (already migrated or clean install)")
        return 0

    migrated = 0
    for task_file in review_dir.glob("*.md"):
        # Read content
        content = task_file.read_text()

        # Update status in frontmatter
        content = re.sub(
            r"^status:\s*review\s*$",
            "status: qa",
            content,
            flags=re.MULTILINE
        )

        # Write to new location
        new_path = qa_dir / task_file.name
        new_path.write_text(content)

        # Remove old file
        task_file.unlink()

        print(f"✓ Migrated {task_file.name}: review → qa")
        migrated += 1

    # Remove empty review directory
    if review_dir.exists() and not list(review_dir.iterdir()):
        review_dir.rmdir()
        print("✓ Removed empty review/ directory")

    return migrated


def assess_backlog_tasks(storage: TaskStorage):
    """
    Assess backlog tasks to see if they should be stub status.
    A task is incomplete (stub) if it has placeholder content.
    """
    backlog_dir = storage.status_dir / "backlog"
    stub_dir = storage.status_dir / "stub"

    # Ensure stub directory exists
    stub_dir.mkdir(exist_ok=True)

    if not backlog_dir.exists():
        print("✓ No backlog/ directory found")
        return 0

    moved_to_stub = 0
    for task_file in backlog_dir.glob("*.md"):
        content = task_file.read_text()

        # Check if task has placeholder content
        has_placeholder_desc = "<!-- Add task description here -->" in content
        has_placeholder_criteria = "- [ ] Criterion 1" in content or "- [ ] Criterion 2" in content
        has_minimal_desc = content.count("\n") < 30  # Very short file

        # If it has placeholders, it's incomplete
        if has_placeholder_desc and has_placeholder_criteria:
            # Update status
            content = re.sub(
                r"^status:\s*backlog\s*$",
                "status: stub",
                content,
                flags=re.MULTILINE
            )

            # Move to stub directory
            new_path = stub_dir / task_file.name
            new_path.write_text(content)
            task_file.unlink()

            print(f"✓ Moved {task_file.name} to stub (incomplete)")
            moved_to_stub += 1

    return moved_to_stub


def rebuild_manifest(storage: TaskStorage):
    """Rebuild manifest from all task files."""
    print("\n📝 Rebuilding manifest...")

    # Clear and recreate manifest with new headers
    storage.manifest_file.write_text("")
    storage._create_manifest_header()

    # Scan all tasks and rebuild
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
    print("║     TASKPY STATUS MIGRATION (FEAT-10)         ║")
    print("║     review→qa, add stub/blocked statuses      ║")
    print("╚════════════════════════════════════════════════╝\n")

    # Ensure new directories exist
    ensure_new_directories(storage)

    # Migrate review to qa
    review_migrated = migrate_review_to_qa(storage)

    # Assess backlog for incomplete tasks
    print("\n🔍 Assessing backlog tasks for completeness...")
    stub_count = assess_backlog_tasks(storage)

    # Rebuild manifest
    rebuild_manifest(storage)

    print(f"\n✅ Migration complete!")
    print(f"   - {review_migrated} tasks migrated from review → qa")
    print(f"   - {stub_count} incomplete tasks moved to stub")
    print(f"\nNew status directories created:")
    print(f"   - stub/    (incomplete/ungroomed tasks)")
    print(f"   - qa/      (testing phase, formerly review)")
    print(f"   - blocked/ (blocked tasks)")


if __name__ == "__main__":
    main()

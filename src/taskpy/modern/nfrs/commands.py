"""Command implementations for NFRs feature."""

import sys
from pathlib import Path
from taskpy.storage import TaskStorage
from taskpy.output import print_error


def cmd_nfrs(args):
    """List NFRs."""
    storage = TaskStorage(Path.cwd())

    if not storage.is_initialized():
        print_error("TaskPy not initialized. Run: taskpy init")
        sys.exit(1)

    nfrs = storage.load_nfrs()

    if args.defaults:
        nfrs = {nfr_id: nfr for nfr_id, nfr in nfrs.items() if nfr.default}

    for nfr_id, nfr in sorted(nfrs.items()):
        default_marker = " [DEFAULT]" if nfr.default else ""
        print(f"{nfr_id}{default_marker}: {nfr.title}")
        print(f"  {nfr.description}")
        if nfr.verification:
            print(f"  Verification: {nfr.verification}")
        print()

"""Command implementations for NFRs feature."""

import sys
from taskpy.modern.shared.messages import print_error
from taskpy.modern.shared.tasks import ensure_initialized, load_nfrs


def cmd_nfrs(args):
    """List NFRs."""
    ensure_initialized()

    nfrs = load_nfrs()

    if args.defaults:
        nfrs = {nfr_id: nfr for nfr_id, nfr in nfrs.items() if nfr.get('default', False)}

    for nfr_id, nfr in sorted(nfrs.items()):
        default_marker = " [DEFAULT]" if nfr.get('default', False) else ""
        print(f"{nfr_id}{default_marker}: {nfr.get('title', '')}")
        print(f"  {nfr.get('description', '')}")
        if nfr.get('verification'):
            print(f"  Verification: {nfr.get('verification')}")
        print()

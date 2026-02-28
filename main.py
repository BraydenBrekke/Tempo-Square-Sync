#!/usr/bin/env python3
"""Tempo → Square Timecard Sync

Pull timesheet data from Tempo for Jira and create timecards in Square
for payroll processing.

Usage:
    python main.py                          # Sync last 30 days (incremental)
    python main.py --from 2026-02-01 --to 2026-02-28
    python main.py --dry-run                # Preview without creating timecards
    python main.py --list-team-members      # Show Square team members for mapping
"""

import argparse
import logging
import sys

from config import load_config
from sync import run_sync
from square_client import SquareClient


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def list_team_members(config: dict):
    """Print Square team members to help set up employee mapping."""
    square = SquareClient(
        access_token=config["square"]["access_token"],
        environment=config["square"].get("environment", "sandbox"),
    )
    members = square.list_team_members()

    if not members:
        print("No team members found in Square.")
        return

    print(f"\nSquare Team Members ({len(members)}):")
    print("-" * 60)
    for m in members:
        name = f"{m.get('given_name', '')} {m.get('family_name', '')}".strip()
        member_id = m.get("id", "unknown")
        status = m.get("status", "unknown")
        print(f"  {name:<30} {member_id}  ({status})")
    print()
    print("Add these IDs to config.yaml under employee_mapping.")


def main():
    parser = argparse.ArgumentParser(
        description="Sync Tempo worklogs to Square timecards"
    )
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview sync without creating timecards",
    )
    parser.add_argument(
        "--list-team-members",
        action="store_true",
        help="List Square team members for mapping setup",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()
    setup_logging(args.verbose)

    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.list_team_members:
        list_team_members(config)
        return

    result = run_sync(
        config=config,
        from_date=args.from_date,
        to_date=args.to_date,
        dry_run=args.dry_run,
    )

    if result["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

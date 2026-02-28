import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jira_client import JiraClient
from tempo_client import TempoClient
from square_client import SquareClient

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / ".sync_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_sync": None, "synced_worklog_ids": []}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def resolve_team_member_id(
    worklog: dict,
    jira: JiraClient,
    email_map: dict[str, str],
    email_cache: dict[str, str | None],
) -> str | None:
    """Resolve a Tempo worklog author to a Square team member ID via email.

    Uses Jira to look up the author's email, then matches against the
    Square email map. Results are cached in email_cache.
    """
    author_id = worklog["author"]["accountId"]
    display_name = worklog["author"].get("displayName", "unknown")

    # Check cache first
    if author_id not in email_cache:
        try:
            email_cache[author_id] = jira.get_user_email(author_id)
        except Exception as e:
            logger.error(f"Failed to fetch email for {display_name} ({author_id}): {e}")
            email_cache[author_id] = None

    email = email_cache[author_id]
    if not email:
        logger.warning(f"No email found for Tempo user {display_name} ({author_id}). Skipping.")
        return None

    team_member_id = email_map.get(email.lower())
    if not team_member_id:
        logger.warning(
            f"No Square team member with email {email} "
            f"(Tempo user {display_name}). Skipping."
        )
        return None

    return team_member_id


def tempo_worklog_to_timecard(
    worklog: dict,
    team_member_id: str,
    location_id: str,
) -> dict:
    """Convert a Tempo worklog into Square timecard parameters."""

    # Build start and end timestamps from Tempo data
    start_date = worklog["startDate"]  # "2026-02-27"
    start_time = worklog.get("startTime", "09:00:00")  # "09:00:00" or may be absent
    time_spent_seconds = worklog["timeSpentSeconds"]

    # Parse into datetime (Tempo doesn't include timezone — treat as local)
    start_dt = datetime.fromisoformat(f"{start_date}T{start_time}")
    end_dt = start_dt + timedelta(seconds=time_spent_seconds)

    return {
        "location_id": location_id,
        "team_member_id": team_member_id,
        "start_at": start_dt.isoformat(),
        "end_at": end_dt.isoformat(),
    }


def run_sync(
    config: dict,
    from_date: str | None = None,
    to_date: str | None = None,
    dry_run: bool = False,
):
    """Pull worklogs from Tempo and create timecards in Square.

    Args:
        config: Loaded config dict
        from_date: Start date (YYYY-MM-DD). Defaults to 30 days ago.
        to_date: End date (YYYY-MM-DD). Defaults to today.
        dry_run: If True, log what would be created without calling Square.
    """
    state = load_state()

    today = datetime.now().strftime("%Y-%m-%d")
    if not from_date:
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not to_date:
        to_date = today

    tempo = TempoClient(
        api_token=config["tempo"]["api_token"],
        base_url=config["tempo"].get("base_url", "https://api.tempo.io/4"),
    )
    jira = JiraClient(
        base_url=config["jira"]["base_url"],
        email=config["jira"]["email"],
        api_token=config["jira"]["api_token"],
    )
    square = SquareClient(
        access_token=config["square"]["access_token"],
        environment=config["square"].get("environment", "sandbox"),
    )

    # Build email → Square team member ID mapping
    email_map = square.get_team_member_email_map()
    logger.info(f"Loaded {len(email_map)} Square team members by email")
    email_cache: dict[str, str | None] = {}

    # Use updatedFrom for incremental sync if we've synced before
    updated_from = state.get("last_sync")
    logger.info(
        f"Fetching Tempo worklogs from={from_date} to={to_date}"
        + (f" updatedFrom={updated_from}" if updated_from else "")
    )

    # Fetch worklogs, optionally filtered by project
    filter_projects = config.get("filter_projects", [])
    all_worklogs = []

    if filter_projects:
        for project in filter_projects:
            worklogs = tempo.get_worklogs(
                from_date=from_date,
                to_date=to_date,
                project=project,
                updated_from=updated_from,
            )
            all_worklogs.extend(worklogs)
    else:
        all_worklogs = tempo.get_worklogs(
            from_date=from_date,
            to_date=to_date,
            updated_from=updated_from,
        )

    logger.info(f"Found {len(all_worklogs)} worklogs from Tempo")

    # Filter out already-synced worklogs
    synced_ids = set(state.get("synced_worklog_ids", []))
    new_worklogs = [w for w in all_worklogs if w["tempoWorklogId"] not in synced_ids]
    logger.info(f"{len(new_worklogs)} new worklogs to sync")

    created = 0
    skipped = 0
    errors = 0

    for worklog in new_worklogs:
        team_member_id = resolve_team_member_id(
            worklog=worklog,
            jira=jira,
            email_map=email_map,
            email_cache=email_cache,
        )

        if not team_member_id:
            skipped += 1
            continue

        timecard_params = tempo_worklog_to_timecard(
            worklog=worklog,
            team_member_id=team_member_id,
            location_id=config["square"]["location_id"],
        )

        wlog_id = worklog["tempoWorklogId"]
        author = worklog["author"].get("displayName", "unknown")
        hours = worklog["timeSpentSeconds"] / 3600

        if dry_run:
            logger.info(
                f"[DRY RUN] Would create timecard: {author} — "
                f"{hours:.1f}h on {worklog['startDate']}"
            )
            created += 1
            continue

        try:
            result = square.create_timecard(**timecard_params)
            timecard_id = result.get("timecard", {}).get("id", "unknown")
            logger.info(
                f"Created timecard {timecard_id}: {author} — "
                f"{hours:.1f}h on {worklog['startDate']}"
            )
            synced_ids.add(wlog_id)
            created += 1
        except Exception as e:
            logger.error(f"Failed to create timecard for worklog {wlog_id}: {e}")
            errors += 1

    # Save state
    if not dry_run:
        state["last_sync"] = datetime.now(timezone.utc).isoformat()
        state["synced_worklog_ids"] = list(synced_ids)
        save_state(state)

    logger.info(f"Sync complete: {created} created, {skipped} skipped, {errors} errors")
    return {"created": created, "skipped": skipped, "errors": errors}

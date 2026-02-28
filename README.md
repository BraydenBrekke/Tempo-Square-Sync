# tempo-square-sync

Pulls timesheet worklogs from Tempo (for Jira) and creates timecards in Square for payroll processing. Employees are automatically matched between systems by email address.

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A [Tempo API token](https://tempo-io.atlassian.net/wiki/spaces/KB/pages/199065601/How+to+use+Tempo+Cloud+REST+APIs)
- A [Jira Cloud API token](https://id.atlassian.com/manage-profile/security/api-tokens) (used to look up user emails)
- A [Square access token](https://developer.squareup.com/docs/build-basics/access-tokens) with Labor write permissions

## Setup

1. Install dependencies:

   ```
   uv sync
   ```

2. Create your config file:

   ```
   cp config.example.yaml config.yaml
   ```

3. Fill in `config.yaml`:

   ```yaml
   tempo:
     api_token: "your-tempo-api-token"
     base_url: "https://api.tempo.io/4"

   square:
     access_token: "your-square-access-token"
     environment: "sandbox"  # or "production"
     location_id: "your-square-location-id"

   jira:
     base_url: "https://yoursite.atlassian.net"
     email: "you@company.com"
     api_token: "your-jira-api-token"

   # Optional: only sync worklogs from specific Jira projects
   filter_projects: []
   ```

4. Verify your Square team members have email addresses set (these are used to match against Jira/Tempo users):

   ```
   uv run python main.py --list-team-members
   ```

   Make sure each team member's email in Square matches their Atlassian account email.

## Usage

```
# Sync the last 30 days (incremental — skips already-synced worklogs)
uv run python main.py

# Sync a specific date range
uv run python main.py --from 2026-02-01 --to 2026-02-28

# Preview what would be synced without creating timecards
uv run python main.py --dry-run

# Show Square team members and their emails
uv run python main.py --list-team-members

# Verbose logging
uv run python main.py -v
```

## How it works

1. Fetches worklogs from Tempo for the given date range
2. For each worklog author, looks up their email via the Jira Cloud API
3. Matches that email to a Square team member
4. Creates a timecard in Square with the worklog's start time and duration
5. Hourly rates are determined by each team member's configuration in Square — this script does not override them

Sync state is saved to `.sync_state.json` so subsequent runs only process new or updated worklogs.

## Options

| Flag | Description |
|---|---|
| `--from YYYY-MM-DD` | Start date (default: 30 days ago) |
| `--to YYYY-MM-DD` | End date (default: today) |
| `--dry-run` | Preview without creating timecards |
| `--list-team-members` | List Square team members and emails |
| `--config PATH` | Path to config file (default: `config.yaml`) |
| `-v`, `--verbose` | Enable debug logging |

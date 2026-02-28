import requests
from datetime import datetime


class TempoClient:
    def __init__(self, api_token: str, base_url: str = "https://api.tempo.io/4"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
            }
        )

    def get_worklogs(
        self,
        from_date: str,
        to_date: str,
        project: str | None = None,
        updated_from: str | None = None,
    ) -> list[dict]:
        """Fetch worklogs from Tempo, handling pagination.

        Args:
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            project: Optional Jira project key to filter by
            updated_from: Optional ISO timestamp to only get worklogs updated after this time
        """
        params = {
            "from": from_date,
            "to": to_date,
            "limit": 1000,
            "offset": 0,
        }
        if project:
            params["project"] = project
        if updated_from:
            params["updatedFrom"] = updated_from

        all_worklogs = []

        while True:
            resp = self.session.get(f"{self.base_url}/worklogs", params=params)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            all_worklogs.extend(results)

            metadata = data.get("metadata", {})
            total = metadata.get("count", 0)

            if len(all_worklogs) >= total:
                break

            params["offset"] += params["limit"]

        return all_worklogs

    def get_timesheet_approval(
        self, account_id: str, from_date: str, to_date: str
    ) -> dict:
        """Check timesheet approval status for a user."""
        resp = self.session.get(
            f"{self.base_url}/timesheet-approvals/user/{account_id}",
            params={"from": from_date, "to": to_date},
        )
        resp.raise_for_status()
        return resp.json()

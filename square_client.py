import uuid
import requests
from datetime import datetime


SQUARE_SANDBOX_URL = "https://connect.squareupsandbox.com/v2"
SQUARE_PRODUCTION_URL = "https://connect.squareup.com/v2"


class SquareClient:
    def __init__(self, access_token: str, environment: str = "sandbox"):
        if environment == "production":
            self.base_url = SQUARE_PRODUCTION_URL
        else:
            self.base_url = SQUARE_SANDBOX_URL

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Square-Version": "2025-05-21",
            }
        )

    def create_timecard(
        self,
        location_id: str,
        team_member_id: str,
        start_at: str,
        end_at: str,
        job_title: str | None = None,
        hourly_rate: int | None = None,
        currency: str = "USD",
    ) -> dict:
        """Create a timecard in Square.

        Args:
            location_id: Square location ID
            team_member_id: Square team member ID
            start_at: ISO 8601 timestamp for shift start (e.g. "2026-02-27T09:00:00-07:00")
            end_at: ISO 8601 timestamp for shift end
            job_title: Optional job title for the wage record
            hourly_rate: Optional hourly rate in cents (e.g. 5000 = $50.00). 0 or None to use Square default.
            currency: Currency code (default USD)
        """
        timecard = {
            "location_id": location_id,
            "team_member_id": team_member_id,
            "start_at": start_at,
            "end_at": end_at,
        }

        if job_title or (hourly_rate and hourly_rate > 0):
            wage = {}
            if job_title:
                wage["title"] = job_title
            if hourly_rate and hourly_rate > 0:
                wage["hourly_rate"] = {
                    "amount": hourly_rate,
                    "currency": currency,
                }
            timecard["wage"] = wage

        payload = {
            "idempotency_key": str(uuid.uuid4()),
            "timecard": timecard,
        }

        resp = self.session.post(f"{self.base_url}/labor/timecards", json=payload)
        resp.raise_for_status()
        return resp.json()

    def list_team_members(self) -> list[dict]:
        """List all active team members. Useful for setting up employee mapping."""
        members = []
        cursor = None

        while True:
            payload = {"limit": 100}
            if cursor:
                payload["cursor"] = cursor

            resp = self.session.post(
                f"{self.base_url}/team-members/search", json=payload
            )
            resp.raise_for_status()
            data = resp.json()

            members.extend(data.get("team_members", []))

            cursor = data.get("cursor")
            if not cursor:
                break

        return members

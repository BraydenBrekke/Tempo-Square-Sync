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
    ) -> dict:
        """Create a timecard in Square. Wage/rate uses the team member's Square config."""
        payload = {
            "idempotency_key": str(uuid.uuid4()),
            "timecard": {
                "location_id": location_id,
                "team_member_id": team_member_id,
                "start_at": start_at,
                "end_at": end_at,
            },
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

    def get_team_member_email_map(self) -> dict[str, str]:
        """Build a mapping of lowercase email → Square team member ID."""
        email_map: dict[str, str] = {}
        for member in self.list_team_members():
            email = member.get("email_address")
            member_id = member.get("id")
            if email and member_id:
                email_map[email.lower()] = member_id
        return email_map

import logging

import requests

logger = logging.getLogger(__name__)


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({"Accept": "application/json"})

    def get_user_email(self, account_id: str) -> str | None:
        """Look up a Jira user's email address by their Atlassian account ID."""
        resp = self.session.get(
            f"{self.base_url}/rest/api/3/user",
            params={"accountId": account_id},
        )
        resp.raise_for_status()
        return resp.json().get("emailAddress")

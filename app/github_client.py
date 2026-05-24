from __future__ import annotations

import base64
import os
from typing import Any

import requests

from .models import RepoMetadata


class GitHubClient:
    def __init__(self, token: str | None = None, timeout: int = 20) -> None:
        self.token = token if token is not None else os.getenv("GITHUB_TOKEN", "")
        self.timeout = timeout
        self.base_url = "https://api.github.com"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-ai-radar-local",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def search_repositories(self, query: str, per_page: int = 10) -> list[RepoMetadata]:
        data = self._get(
            "/search/repositories",
            {"q": query, "per_page": per_page},
        )
        return [RepoMetadata.from_github(item) for item in data.get("items", [])]

    def get_readme(self, full_name: str) -> str:
        try:
            data = self._get(f"/repos/{full_name}/readme")
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in {403, 429}:
                raise
            return ""
        content = data.get("content", "")
        if not content:
            return ""
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def get_tree(self, full_name: str, branch: str) -> list[str]:
        try:
            data = self._get(f"/repos/{full_name}/git/trees/{branch}", {"recursive": "1"})
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in {403, 429}:
                raise
            return []
        return [
            item.get("path", "")
            for item in data.get("tree", [])
            if item.get("type") == "blob" and item.get("path")
        ]

    def get_file_text(self, full_name: str, path: str, branch: str) -> str:
        try:
            data = self._get(f"/repos/{full_name}/contents/{path}", {"ref": branch})
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in {403, 429}:
                raise
            return ""
        if data.get("encoding") != "base64" or not data.get("content"):
            return ""
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        except Exception:
            return ""

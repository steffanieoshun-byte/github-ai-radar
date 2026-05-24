from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchIntent:
    keyword: str
    scan_count: int
    scan_mode: str
    title: str = ""
    directions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "scan_count": self.scan_count,
            "scan_mode": self.scan_mode,
            "title": self.title,
            "directions": self.directions,
        }


@dataclass(frozen=True)
class RepoMetadata:
    full_name: str
    html_url: str
    description: str
    stars: int
    forks: int
    language: str
    topics: list[str]
    updated_at: str
    default_branch: str

    @classmethod
    def from_github(cls, item: dict[str, Any]) -> "RepoMetadata":
        return cls(
            full_name=item.get("full_name", ""),
            html_url=item.get("html_url", ""),
            description=item.get("description") or "",
            stars=int(item.get("stargazers_count") or 0),
            forks=int(item.get("forks_count") or 0),
            language=item.get("language") or "",
            topics=list(item.get("topics") or []),
            updated_at=item.get("updated_at") or item.get("pushed_at") or "",
            default_branch=item.get("default_branch") or "main",
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "repo_full_name": self.full_name,
            "repo_url": self.html_url,
            "description": self.description,
            "stars": self.stars,
            "forks": self.forks,
            "language": self.language,
            "topics": self.topics,
            "updated_at": self.updated_at,
            "default_branch": self.default_branch,
        }


@dataclass(frozen=True)
class SelectedFile:
    path: str
    reason: str
    content: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "reason": self.reason, "content": self.content[:4000]}

"""
Registers available research tools (web search, GitHub API, etc.) and
routes a query to the right one by platform, with a doctor() health-check
method per tool. Used when a task requires looking something up (e.g. "find
repo X") before acting on it. Deliberately does NOT include cookie-based
login automation for third-party social platforms -- that would cross into
the signup/verification boundary in context.md's hard boundaries and
docs/TRD.md §6. See docs/PHASES.md Part 4.1 and docs/CODE_LOGIC.md §7
(pattern extracted from reviewing Agent-Reach).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


class ResearchTool(ABC):
    """Every research tool implements this so ResearchRouter never depends
    on a specific backend. `handles()` decides eligibility for a given
    platform; `search()` performs the lookup; `doctor()` reports whether
    the tool is actually usable right now (e.g. backend configured)."""

    name: str

    @abstractmethod
    def handles(self, platform: str) -> bool:
        ...

    @abstractmethod
    def search(self, query: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def doctor(self) -> dict[str, Any]:
        """Returns {'healthy': bool, 'detail': str}."""
        ...


@dataclass
class WebSearchTool(ResearchTool):
    """General-purpose web search. No search backend is bundled here --
    `search_fn` is injected (e.g. a wrapper around a search API/service) so
    this module has no hard network dependency of its own."""

    search_fn: Callable[[str], list[dict[str, Any]]] | None = None
    name: str = field(default="web_search")

    def handles(self, platform: str) -> bool:
        return platform in ("web", "general", "")

    def search(self, query: str) -> list[dict[str, Any]]:
        if self.search_fn is None:
            raise RuntimeError("WebSearchTool has no search_fn configured.")
        return self.search_fn(query)

    def doctor(self) -> dict[str, Any]:
        healthy = self.search_fn is not None
        return {
            "healthy": healthy,
            "detail": "search_fn configured" if healthy else "no search_fn configured",
        }


@dataclass
class GitHubApiTool(ResearchTool):
    """Routes GitHub-platform research queries (e.g. "find repo X") to an
    injected GitHub REST/search API wrapper. No cookie-based login is ever
    performed here -- only read-only API lookups (search/repos/issues),
    consistent with context.md's hard boundaries."""

    fetch_fn: Callable[[str], list[dict[str, Any]]] | None = None
    name: str = field(default="github_api")

    def handles(self, platform: str) -> bool:
        return platform == "github"

    def search(self, query: str) -> list[dict[str, Any]]:
        if self.fetch_fn is None:
            raise RuntimeError("GitHubApiTool has no fetch_fn configured.")
        return self.fetch_fn(query)

    def doctor(self) -> dict[str, Any]:
        healthy = self.fetch_fn is not None
        return {
            "healthy": healthy,
            "detail": "fetch_fn configured" if healthy else "no fetch_fn configured",
        }


class NoResearchToolAvailable(Exception):
    pass


class ResearchRouter:
    """Registers ResearchTool instances and routes a query to the first one
    whose `handles(platform)` returns True, in registration order -- so
    callers control priority simply by the order they register tools in."""

    def __init__(self, tools: list[ResearchTool] | None = None) -> None:
        self._tools: list[ResearchTool] = list(tools) if tools else []

    def register(self, tool: ResearchTool) -> None:
        self._tools.append(tool)

    def route(self, query: str, platform: str = "") -> list[dict[str, Any]]:
        for tool in self._tools:
            if tool.handles(platform):
                return tool.search(query)
        raise NoResearchToolAvailable(
            f"No registered research tool handles platform={platform!r}. "
            f"Registered tools: {[t.name for t in self._tools]}"
        )

    def doctor(self) -> dict[str, dict[str, Any]]:
        """Health-check every registered tool, keyed by tool name."""
        return {tool.name: tool.doctor() for tool in self._tools}

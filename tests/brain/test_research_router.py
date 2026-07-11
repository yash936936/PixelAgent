import pytest

from src.brain.research_router import (
    GitHubApiTool,
    NoResearchToolAvailable,
    ResearchRouter,
    WebSearchTool,
)


def test_web_search_tool_handles_web_and_general():
    tool = WebSearchTool(search_fn=lambda q: [{"title": q}])
    assert tool.handles("web")
    assert tool.handles("general")
    assert tool.handles("")
    assert not tool.handles("github")


def test_web_search_tool_search_calls_injected_fn():
    tool = WebSearchTool(search_fn=lambda q: [{"title": q}])
    results = tool.search("playwright docs")
    assert results == [{"title": "playwright docs"}]


def test_web_search_tool_raises_without_backend():
    tool = WebSearchTool()
    with pytest.raises(RuntimeError):
        tool.search("anything")


def test_web_search_tool_doctor_reports_health():
    assert WebSearchTool().doctor()["healthy"] is False
    assert WebSearchTool(search_fn=lambda q: []).doctor()["healthy"] is True


def test_github_api_tool_only_handles_github_platform():
    tool = GitHubApiTool(fetch_fn=lambda q: [])
    assert tool.handles("github")
    assert not tool.handles("web")


def test_github_api_tool_search_calls_injected_fn():
    tool = GitHubApiTool(fetch_fn=lambda q: [{"repo": q}])
    assert tool.search("pixel-agent") == [{"repo": "pixel-agent"}]


def test_router_routes_to_first_matching_tool():
    web_tool = WebSearchTool(search_fn=lambda q: [{"source": "web"}])
    github_tool = GitHubApiTool(fetch_fn=lambda q: [{"source": "github"}])
    router = ResearchRouter([web_tool, github_tool])

    assert router.route("query", platform="web") == [{"source": "web"}]
    assert router.route("query", platform="github") == [{"source": "github"}]


def test_router_raises_when_no_tool_handles_platform():
    router = ResearchRouter([GitHubApiTool(fetch_fn=lambda q: [])])
    with pytest.raises(NoResearchToolAvailable):
        router.route("query", platform="unknown_platform")


def test_router_register_appends_tool():
    router = ResearchRouter()
    tool = WebSearchTool(search_fn=lambda q: [])
    router.register(tool)
    assert router.route("query", platform="web") == []


def test_router_doctor_reports_all_tools():
    router = ResearchRouter(
        [WebSearchTool(search_fn=lambda q: []), GitHubApiTool()]
    )
    report = router.doctor()
    assert report["web_search"]["healthy"] is True
    assert report["github_api"]["healthy"] is False

from backend.webhook_trigger import (
    get_branch_mapping_value,
    matches_branch_rule,
    resolve_pipeline_webhook_branch,
)


def test_plain_branch_rule_is_exact_match_only():
    assert matches_branch_rule("dev", "dev")
    assert not matches_branch_rule("dev1", "dev")
    assert not matches_branch_rule("dev2", "dev")


def test_wildcard_branch_rule_requires_explicit_wildcard():
    assert matches_branch_rule("dev1", "dev*")
    assert matches_branch_rule("dev2", "dev*")
    assert matches_branch_rule("release/1.0", "release/*")
    assert not matches_branch_rule("release-1.0", "release/*")


def test_configured_branch_strategy_ignores_other_branches():
    result = resolve_pipeline_webhook_branch(
        "use_configured",
        webhook_branch="dev1",
        configured_branch="dev",
    )

    assert not result["ok"]
    assert result["ignored"]
    assert result["reason"] == "not_configured_branch"


def test_configured_branch_strategy_builds_configured_branch():
    result = resolve_pipeline_webhook_branch(
        "use_configured",
        webhook_branch="refs/heads/dev",
        configured_branch="dev",
    )

    assert result["ok"]
    assert result["branch"] == "dev"


def test_selected_branch_rules_support_exact_and_wildcard():
    assert resolve_pipeline_webhook_branch(
        "select_branches",
        webhook_branch="dev",
        configured_branch="main",
        allowed_branches=["dev", "release/*"],
    )["ok"]
    assert resolve_pipeline_webhook_branch(
        "select_branches",
        webhook_branch="release/1.0",
        configured_branch="main",
        allowed_branches=["dev", "release/*"],
    )["ok"]
    assert resolve_pipeline_webhook_branch(
        "select_branches",
        webhook_branch="dev1",
        configured_branch="main",
        allowed_branches=["dev", "release/*"],
    )["ignored"]


def test_branch_tag_mapping_prefers_exact_match_then_wildcard():
    mapping = {"dev*": "wildcard", "dev": "exact"}

    assert get_branch_mapping_value("dev", mapping) == "exact"
    assert get_branch_mapping_value("dev1", mapping) == "wildcard"

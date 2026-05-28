# backend/webhook_trigger.py
"""Webhook 触发工具函数"""
import json
import logging
import asyncio
from fnmatch import fnmatchcase
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)


def normalize_branch_name(branch: Optional[str]) -> str:
    """Normalize Git branch refs before matching."""
    if not branch:
        return ""
    branch = str(branch).strip()
    if branch.startswith("refs/heads/"):
        return branch[len("refs/heads/") :]
    return branch


def branch_rule_has_wildcard(rule: str) -> bool:
    return any(token in rule for token in ("*", "?", "["))


def matches_branch_rule(branch: Optional[str], rule: Optional[str]) -> bool:
    """
    Match a branch against a single rule.

    Plain text is exact-match only. Wildcard matching is enabled only when the
    rule explicitly contains shell-style wildcard characters.
    """
    normalized_branch = normalize_branch_name(branch)
    normalized_rule = normalize_branch_name(rule)
    if not normalized_branch or not normalized_rule:
        return False
    if normalized_branch == normalized_rule:
        return True
    if not branch_rule_has_wildcard(normalized_rule):
        return False
    return fnmatchcase(normalized_branch, normalized_rule)


def matches_any_branch_rule(branch: Optional[str], rules: Optional[List[str]]) -> bool:
    if not branch or not rules:
        return False
    return any(matches_branch_rule(branch, rule) for rule in rules if rule)


def get_branch_mapping_value(branch: Optional[str], mapping: Optional[dict]):
    """Return mapping value with exact matches taking precedence over wildcard rules."""
    normalized_branch = normalize_branch_name(branch)
    if not normalized_branch or not mapping:
        return None

    normalized_exact_lookup = {}
    for rule, value in mapping.items():
        normalized_rule = normalize_branch_name(rule)
        if normalized_rule and not branch_rule_has_wildcard(normalized_rule):
            normalized_exact_lookup[normalized_rule] = value

    if normalized_branch in normalized_exact_lookup:
        return normalized_exact_lookup[normalized_branch]

    for rule, value in mapping.items():
        if matches_branch_rule(normalized_branch, rule):
            return value

    return None


def resolve_pipeline_webhook_branch(
    strategy: str,
    webhook_branch: Optional[str],
    configured_branch: Optional[str],
    allowed_branches: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Resolve whether a pipeline webhook should trigger and which branch to build.

    The result uses:
    - ok=True with branch when a build should be created.
    - ignored=True when the webhook is valid but the pushed branch is not allowed.
    - error when required branch data is missing.
    """
    strategy = strategy or "use_push"

    if strategy == "select_branches":
        if not webhook_branch:
            return {"ok": False, "error": "missing_webhook_branch"}
        if matches_any_branch_rule(webhook_branch, allowed_branches):
            return {"ok": True, "branch": normalize_branch_name(webhook_branch)}
        return {"ok": False, "ignored": True, "reason": "branch_not_allowed"}

    if strategy == "filter_match":
        if not webhook_branch:
            return {"ok": False, "error": "missing_webhook_branch"}
        if matches_branch_rule(webhook_branch, configured_branch):
            return {"ok": True, "branch": normalize_branch_name(webhook_branch)}
        return {"ok": False, "ignored": True, "reason": "branch_not_matched"}

    if strategy == "use_configured":
        if not webhook_branch:
            return {"ok": False, "error": "missing_webhook_branch"}
        if normalize_branch_name(webhook_branch) == normalize_branch_name(
            configured_branch
        ):
            return {"ok": True, "branch": normalize_branch_name(configured_branch)}
        return {"ok": False, "ignored": True, "reason": "not_configured_branch"}

    if not webhook_branch:
        return {"ok": False, "error": "missing_webhook_branch"}
    return {"ok": True, "branch": normalize_branch_name(webhook_branch)}


async def trigger_webhook(
    url: str,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    触发 Webhook HTTP 请求

    Args:
        url: Webhook URL
        method: HTTP 方法（POST, PUT等）
        headers: 请求头（可选）
        body: 请求体（可选）
        timeout: 超时时间（秒）

    Returns:
        包含 success, status_code, response_text 的字典
    """
    try:
        # 设置默认请求头
        request_headers = {"Content-Type": "application/json"}
        if headers:
            request_headers.update(headers)

        # 发送HTTP请求
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "POST":
                response = await client.post(url, headers=request_headers, content=body)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=request_headers, content=body)
            elif method.upper() == "PATCH":
                response = await client.patch(
                    url, headers=request_headers, content=body
                )
            else:
                logger.warning(f"不支持的HTTP方法: {method}，使用POST")
                response = await client.post(url, headers=request_headers, content=body)

            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response_text": response.text[:500],  # 限制响应文本长度
            }
    except httpx.TimeoutException:
        logger.error(f"Webhook 请求超时: {url}")
        return {
            "success": False,
            "status_code": None,
            "response_text": "Request timeout",
            "error": "timeout",
        }
    except httpx.RequestError as e:
        logger.error(f"Webhook 请求失败: {url}, 错误: {str(e)}")
        return {
            "success": False,
            "status_code": None,
            "response_text": str(e),
            "error": "request_error",
        }
    except Exception as e:
        logger.exception(f"Webhook 触发异常: {url}, 错误: {str(e)}")
        return {
            "success": False,
            "status_code": None,
            "response_text": str(e),
            "error": "unknown_error",
        }


def render_template(template: str, context: Dict[str, Any]) -> str:
    """
    渲染模板字符串（支持变量替换）

    Args:
        template: 模板字符串，支持 {variable} 格式的变量
        context: 变量上下文

    Returns:
        渲染后的字符串
    """
    try:
        result = template
        for key, value in context.items():
            placeholder = "{" + key + "}"
            # 将值转换为字符串
            str_value = str(value) if value is not None else ""
            result = result.replace(placeholder, str_value)
        return result
    except Exception as e:
        logger.error(f"模板渲染失败: {e}")
        return template


def match_branch(
    branch: str, strategy: str, allowed_branches: List[str]
) -> bool:
    """
    判断任务分支是否匹配 Webhook 的分支策略

    Args:
        branch: 当前任务分支
        strategy: 分支策略 ("all" / "select_branches" / "filter_match")
        allowed_branches: 允许的分支列表

    Returns:
        是否匹配
    """
    if strategy != "select_branches" and strategy != "filter_match":
        return True

    if not branch:
        return False

    if not allowed_branches:
        return False

    return matches_any_branch_rule(branch, allowed_branches)

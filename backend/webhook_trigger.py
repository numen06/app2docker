# backend/webhook_trigger.py
"""Webhook 触发工具函数"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


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

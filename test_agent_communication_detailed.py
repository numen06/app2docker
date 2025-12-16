#!/usr/bin/env python3
"""
详细测试主程序和Agent之间的通信流程
模拟实际环境中的各种场景和问题
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 模拟全局变量（与实际代码保持一致）
active_connections: Dict[str, Any] = {}
deploy_result_futures: Dict[str, asyncio.Future] = {}


def print_section(title: str):
    """打印分隔线"""
    try:
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80 + "\n")
    except UnicodeEncodeError:
        # Windows GBK编码问题，移除emoji
        title_clean = title.encode("ascii", "ignore").decode("ascii")
        print("\n" + "=" * 80)
        print(f"  {title_clean}")
        print("=" * 80 + "\n")


async def test_scenario_1_normal_flow():
    """场景1：正常流程"""
    print_section("场景1：正常流程测试")

    # 模拟连接
    host_id = "test-host-1"
    task_id = "task-001"
    target_name = "target-1"
    future_key = f"{task_id}:{target_name}"

    # 1. 主程序创建Future
    future = asyncio.Future()
    deploy_result_futures[future_key] = future
    logger.info(f"✅ [主程序] 创建Future: {future_key}")
    logger.info(f"   当前Future keys: {list(deploy_result_futures.keys())}")

    # 2. Agent发送running消息
    await asyncio.sleep(0.1)
    logger.info(f"📤 [Agent] 发送running消息: task_id={task_id}, target={target_name}")

    # 3. Agent发送completed消息
    await asyncio.sleep(0.2)
    result_dict = {
        "success": True,
        "message": "部署成功",
        "status": "completed",
        "result": {"output": "container-id-123"},
    }

    # 4. 主程序处理消息并设置Future
    if future_key in deploy_result_futures:
        future = deploy_result_futures.pop(future_key)
        if not future.done():
            future.set_result(result_dict)
            logger.info(f"✅ [主程序] 已设置Future结果: {future_key}")
        else:
            logger.warning(f"⚠️ [主程序] Future已完成: {future_key}")
    else:
        logger.error(f"❌ [主程序] Future不存在: {future_key}")
        logger.error(f"   当前Future keys: {list(deploy_result_futures.keys())}")
        return False

    # 5. 验证结果
    try:
        result = await asyncio.wait_for(future, timeout=1.0)
        logger.info(f"✅ [主程序] 收到结果: success={result.get('success')}")
        return True
    except asyncio.TimeoutError:
        logger.error(f"❌ [主程序] 等待结果超时")
        return False


async def test_scenario_2_future_not_created():
    """场景2：Future未创建（模拟时序问题）"""
    print_section("场景2：Future未创建（时序问题）")

    host_id = "test-host-2"
    task_id = "task-002"
    target_name = "target-2"
    future_key = f"{task_id}:{target_name}"

    # Agent先发送completed消息（Future还未创建）
    logger.info(
        f"📤 [Agent] 发送completed消息（Future未创建）: task_id={task_id}, target={target_name}"
    )
    result_dict = {
        "success": True,
        "message": "部署成功",
        "status": "completed",
        "result": {"output": "container-id-456"},
    }

    # 主程序尝试设置Future结果
    if future_key in deploy_result_futures:
        future = deploy_result_futures.pop(future_key)
        future.set_result(result_dict)
        logger.info(f"✅ [主程序] 已设置Future结果")
    else:
        logger.warning(f"⚠️ [主程序] Future不存在: {future_key}")
        logger.warning(f"   当前Future keys: {list(deploy_result_futures.keys())}")
        logger.warning(f"   这是正常情况：Agent可能在主程序创建Future之前就完成了任务")

    # 现在创建Future（模拟主程序稍后创建）
    await asyncio.sleep(0.1)
    future = asyncio.Future()
    deploy_result_futures[future_key] = future
    logger.info(f"📝 [主程序] 创建Future（延迟）: {future_key}")

    # 此时Future已经创建，但结果已经发送过了
    logger.warning(f"⚠️ [问题] Future创建时，结果已经发送过了，Future会一直等待")

    return False  # 这种情况会导致超时


async def test_scenario_3_key_mismatch():
    """场景3：Future key不匹配"""
    print_section("场景3：Future key不匹配")

    host_id = "test-host-3"
    task_id = "task-003"
    target_name = "target-3"

    # 主程序创建Future（使用正确的key）
    future_key_correct = f"{task_id}:{target_name}"
    future = asyncio.Future()
    deploy_result_futures[future_key_correct] = future
    logger.info(f"✅ [主程序] 创建Future: {future_key_correct}")

    # Agent发送消息（使用错误的key，比如缺少target_name）
    future_key_wrong = task_id  # 错误：缺少target_name
    logger.info(f"📤 [Agent] 发送completed消息: future_key={future_key_wrong} (错误)")
    logger.info(f"   期望的key: {future_key_correct}")

    result_dict = {"success": True, "message": "部署成功", "status": "completed"}

    # 主程序尝试设置Future结果
    if future_key_wrong in deploy_result_futures:
        future = deploy_result_futures.pop(future_key_wrong)
        future.set_result(result_dict)
        logger.info(f"✅ [主程序] 已设置Future结果")
    else:
        logger.error(f"❌ [主程序] Future不存在: {future_key_wrong}")
        logger.error(f"   期望的key: {future_key_correct}")
        logger.error(f"   当前Future keys: {list(deploy_result_futures.keys())}")

    return False  # key不匹配会导致Future一直等待


async def test_scenario_4_multiple_running_messages():
    """场景4：多个running消息"""
    print_section("场景4：多个running消息（正常情况）")

    host_id = "test-host-4"
    task_id = "task-004"
    target_name = "target-4"
    future_key = f"{task_id}:{target_name}"

    # 主程序创建Future
    future = asyncio.Future()
    deploy_result_futures[future_key] = future
    logger.info(f"✅ [主程序] 创建Future: {future_key}")

    # Agent发送多个running消息
    running_messages = [
        "部署任务已开始",
        "开始执行部署操作...",
        "命令执行成功，输出: container-id-789",
    ]

    for msg in running_messages:
        await asyncio.sleep(0.1)
        logger.info(f"📤 [Agent] 发送running消息: {msg}")
        # running消息不应该触发Future完成
        if future.done():
            logger.error(f"❌ [错误] running消息不应该触发Future完成")
            return False

    # 最后发送completed消息
    await asyncio.sleep(0.1)
    result_dict = {"success": True, "message": "部署成功", "status": "completed"}

    if future_key in deploy_result_futures:
        future = deploy_result_futures.pop(future_key)
        future.set_result(result_dict)
        logger.info(f"✅ [主程序] 已设置Future结果")

    # 验证结果
    try:
        result = await asyncio.wait_for(future, timeout=1.0)
        logger.info(f"✅ [主程序] 收到结果: success={result.get('success')}")
        return True
    except asyncio.TimeoutError:
        logger.error(f"❌ [主程序] 等待结果超时")
        return False


async def test_scenario_5_message_order():
    """场景5：消息顺序问题"""
    print_section("场景5：消息顺序问题（completed在running之前）")

    host_id = "test-host-5"
    task_id = "task-005"
    target_name = "target-5"
    future_key = f"{task_id}:{target_name}"

    # 主程序创建Future
    future = asyncio.Future()
    deploy_result_futures[future_key] = future
    logger.info(f"✅ [主程序] 创建Future: {future_key}")

    # Agent先发送completed消息（异常情况）
    await asyncio.sleep(0.1)
    logger.warning(f"⚠️ [Agent] 先发送completed消息（异常顺序）")
    result_dict = {"success": True, "message": "部署成功", "status": "completed"}

    if future_key in deploy_result_futures:
        future = deploy_result_futures.pop(future_key)
        future.set_result(result_dict)
        logger.info(f"✅ [主程序] 已设置Future结果")

    # 然后发送running消息（应该被忽略）
    await asyncio.sleep(0.1)
    logger.info(f"📤 [Agent] 发送running消息（应该被忽略）")

    # 验证结果
    try:
        result = await asyncio.wait_for(future, timeout=1.0)
        logger.info(f"✅ [主程序] 收到结果: success={result.get('success')}")
        logger.info(f"   注意：即使消息顺序异常，只要Future设置了结果，就能正常工作")
        return True
    except asyncio.TimeoutError:
        logger.error(f"❌ [主程序] 等待结果超时")
        return False


async def main():
    """运行所有测试场景"""
    print_section("开始详细测试主程序和Agent之间的通信流程")

    results = []

    # 运行各个测试场景
    results.append(("场景1：正常流程", await test_scenario_1_normal_flow()))
    results.append(("场景2：Future未创建", await test_scenario_2_future_not_created()))
    results.append(("场景3：key不匹配", await test_scenario_3_key_mismatch()))
    results.append(
        ("场景4：多个running消息", await test_scenario_4_multiple_running_messages())
    )
    results.append(("场景5：消息顺序问题", await test_scenario_5_message_order()))

    # 打印测试结果
    print_section("测试结果汇总")
    for scenario, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {scenario}: {status}")

    print_section("问题诊断建议")
    print(
        """
    如果实际环境中出现问题，请检查：
    
    1. Future key是否匹配：
       - 主程序创建Future时使用的key格式
       - Agent发送消息时使用的task_id和target_name
       - 确保格式一致：f"{task_id}:{target_name}"
    
    2. 时序问题：
       - Agent是否在Future创建之前就发送了completed消息
       - 如果是，需要等待Future创建后再发送结果
    
    3. 消息发送：
       - Agent是否成功发送了所有消息（running和completed）
       - 主程序是否收到了所有消息
       - 检查WebSocket连接状态
    
    4. Future处理：
       - completed/failed消息是否正确设置了Future结果
       - running消息不应该触发Future完成
    """
    )


if __name__ == "__main__":
    asyncio.run(main())

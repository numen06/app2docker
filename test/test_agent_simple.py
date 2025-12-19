#!/usr/bin/env python3
"""
简化版测试：模拟主程序和Agent之间的通信流程
"""
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 模拟全局变量
deploy_result_futures = {}


async def test_normal_flow():
    """测试正常流程"""
    print("\n" + "=" * 60)
    print("测试1: 正常流程")
    print("=" * 60)

    task_id = "task-001"
    target_name = "target-1"
    future_key = f"{task_id}:{target_name}"

    # 1. 主程序创建Future
    future = asyncio.Future()
    deploy_result_futures[future_key] = future
    logger.info(f"[主程序] 创建Future: {future_key}")
    logger.info(f"  当前Future keys: {list(deploy_result_futures.keys())}")

    # 2. 模拟Agent发送completed消息
    await asyncio.sleep(0.1)
    logger.info(f"[Agent] 发送completed消息: task_id={task_id}, target={target_name}")

    # 3. 主程序处理消息
    result_dict = {"success": True, "message": "部署成功", "status": "completed"}

    if future_key in deploy_result_futures:
        future = deploy_result_futures.pop(future_key)
        if not future.done():
            future.set_result(result_dict)
            logger.info(f"[主程序] 已设置Future结果: {future_key}")
        else:
            logger.warning(f"[主程序] Future已完成: {future_key}")
            return False
    else:
        logger.error(f"[主程序] Future不存在: {future_key}")
        logger.error(f"  当前Future keys: {list(deploy_result_futures.keys())}")
        return False

    # 4. 验证结果
    try:
        result = await asyncio.wait_for(future, timeout=1.0)
        logger.info(f"[主程序] 收到结果: success={result.get('success')}")
        return True
    except asyncio.TimeoutError:
        logger.error(f"[主程序] 等待结果超时")
        return False


async def test_future_not_created():
    """测试Future未创建的情况"""
    print("\n" + "=" * 60)
    print("测试2: Future未创建（时序问题）")
    print("=" * 60)

    task_id = "task-002"
    target_name = "target-2"
    future_key = f"{task_id}:{target_name}"

    # Agent先发送completed消息（Future还未创建）
    logger.info(f"[Agent] 发送completed消息（Future未创建）")
    result_dict = {"success": True, "message": "部署成功", "status": "completed"}

    if future_key in deploy_result_futures:
        future = deploy_result_futures.pop(future_key)
        future.set_result(result_dict)
        logger.info(f"[主程序] 已设置Future结果")
    else:
        logger.warning(f"[主程序] Future不存在: {future_key}")
        logger.warning(f"  这是问题：Agent在Future创建之前就发送了结果")

    # 现在创建Future（延迟）
    await asyncio.sleep(0.1)
    future = asyncio.Future()
    deploy_result_futures[future_key] = future
    logger.info(f"[主程序] 创建Future（延迟）: {future_key}")

    # 此时Future已经创建，但结果已经发送过了
    logger.warning(f"[问题] Future创建时，结果已经发送过了，Future会一直等待")

    try:
        result = await asyncio.wait_for(future, timeout=1.0)
        return True
    except asyncio.TimeoutError:
        logger.error(f"[主程序] 等待结果超时 - 这是预期的失败")
        return False


async def test_key_mismatch():
    """测试key不匹配"""
    print("\n" + "=" * 60)
    print("测试3: Future key不匹配")
    print("=" * 60)

    task_id = "task-003"
    target_name = "target-3"

    # 主程序创建Future（正确的key）
    future_key_correct = f"{task_id}:{target_name}"
    future = asyncio.Future()
    deploy_result_futures[future_key_correct] = future
    logger.info(f"[主程序] 创建Future: {future_key_correct}")

    # Agent发送消息（错误的key）
    future_key_wrong = task_id  # 错误：缺少target_name
    logger.info(f"[Agent] 发送completed消息: future_key={future_key_wrong} (错误)")
    logger.info(f"  期望的key: {future_key_correct}")

    result_dict = {"success": True, "message": "部署成功", "status": "completed"}

    if future_key_wrong in deploy_result_futures:
        future = deploy_result_futures.pop(future_key_wrong)
        future.set_result(result_dict)
        logger.info(f"[主程序] 已设置Future结果")
    else:
        logger.error(f"[主程序] Future不存在: {future_key_wrong}")
        logger.error(f"  期望的key: {future_key_correct}")
        logger.error(f"  当前Future keys: {list(deploy_result_futures.keys())}")

    try:
        result = await asyncio.wait_for(future, timeout=1.0)
        return True
    except asyncio.TimeoutError:
        logger.error(f"[主程序] 等待结果超时 - key不匹配导致")
        return False


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试主程序和Agent之间的通信流程")
    print("=" * 60)

    results = []
    results.append(("正常流程", await test_normal_flow()))
    results.append(("Future未创建", await test_future_not_created()))
    results.append(("key不匹配", await test_key_mismatch()))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for scenario, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {scenario}: {status}")

    print("\n" + "=" * 60)
    print("问题诊断建议")
    print("=" * 60)
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

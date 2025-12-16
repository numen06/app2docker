#!/usr/bin/env python3
"""
测试主程序和Agent之间的通信流程
模拟任务发送、执行和返回的完整流程
"""
import asyncio
import json
import logging
from typing import Dict, Any
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 模拟的全局变量
active_connections: Dict[str, Any] = {}
deploy_result_futures: Dict[str, asyncio.Future] = {}


class MockWebSocket:
    """模拟WebSocket连接"""

    def __init__(self, host_id: str):
        self.host_id = host_id
        self.messages = []
        self.closed = False

    async def send(self, data: str):
        """发送消息"""
        if self.closed:
            raise Exception("WebSocket已关闭")
        message = json.loads(data)
        self.messages.append(message)
        logger.info(f"[MockWebSocket] {self.host_id} 发送消息: {message.get('type')}")

    async def recv(self):
        """接收消息（模拟）"""
        await asyncio.sleep(0.1)
        return json.dumps(
            {"type": "heartbeat", "timestamp": datetime.now().timestamp()}
        )

    async def close(self):
        """关闭连接"""
        self.closed = True


class MockConnectionManager:
    """模拟连接管理器"""

    def __init__(self):
        self.active_connections = {}

    def get_connected_hosts(self):
        """获取已连接的主机"""
        return set(self.active_connections.keys())

    async def send_message(self, host_id: str, message: dict) -> bool:
        """发送消息到Agent"""
        if host_id in self.active_connections:
            websocket = self.active_connections[host_id]
            try:
                await websocket.send(json.dumps(message))
                logger.info(
                    f"[主程序] ✅ 消息已发送到 {host_id}: {message.get('type')}"
                )
                return True
            except Exception as e:
                logger.error(f"[主程序] ❌ 发送消息失败: {e}")
                return False
        else:
            logger.error(f"[主程序] ❌ 主机未连接: {host_id}")
            return False

    def create_deploy_result_future(self, future_key: str) -> asyncio.Future:
        """创建等待结果的Future"""
        future = asyncio.Future()
        deploy_result_futures[future_key] = future
        logger.info(f"[主程序] 创建Future: {future_key}")
        return future

    def set_deploy_result(self, future_key: str, result: Dict[str, Any]):
        """设置部署结果"""
        if future_key in deploy_result_futures:
            future = deploy_result_futures.pop(future_key)
            if not future.done():
                future.set_result(result)
                logger.info(
                    f"[主程序] ✅ 已设置Future结果: {future_key}, success={result.get('success')}"
                )
            else:
                logger.warning(f"[主程序] ⚠️ Future已完成: {future_key}")
        else:
            logger.warning(
                f"[主程序] ⚠️ Future不存在: {future_key}, 当前Future keys: {list(deploy_result_futures.keys())}"
            )


class MockAgentWebSocketClient:
    """模拟Agent端的WebSocket客户端"""

    def __init__(self, host_id: str, server_websocket: MockWebSocket):
        self.host_id = host_id
        self.server_websocket = server_websocket
        self.connected = True

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """发送消息到主程序"""
        if not self.connected:
            logger.error(f"[Agent] ❌ WebSocket未连接")
            return False

        try:
            await self.server_websocket.send(json.dumps(message))
            logger.info(f"[Agent] ✅ 消息已发送: {message.get('type')}")
            return True
        except Exception as e:
            logger.error(f"[Agent] ❌ 发送消息失败: {e}")
            return False


async def simulate_main_program(
    connection_manager: MockConnectionManager, host_id: str
):
    """模拟主程序端：发送任务并等待结果"""
    logger.info("=" * 60)
    logger.info("🚀 [主程序] 开始模拟部署任务")
    logger.info("=" * 60)

    task_id = "test-task-123"
    target_name = "test-deploy"

    # 1. 创建Future
    future_key = f"{task_id}:{target_name}"
    result_future = connection_manager.create_deploy_result_future(future_key)
    logger.info(f"[主程序] 已创建Future: {future_key}")

    # 2. 发送部署任务
    deploy_message = {
        "type": "deploy",
        "task_id": task_id,
        "target_name": target_name,
        "deploy_config": {
            "deploy_mode": "docker_run",
            "command": "-d --name=test docker.jajachina.com/public/nginx",
        },
        "context": {},
    }

    logger.info(f"[主程序] 准备发送部署任务: task_id={task_id}, target={target_name}")
    success = await connection_manager.send_message(host_id, deploy_message)

    if not success:
        logger.error(f"[主程序] ❌ 发送任务失败")
        return

    logger.info(f"[主程序] ✅ 任务已发送，等待执行结果...")

    # 3. 等待结果（最多等待10秒）
    try:
        result = await asyncio.wait_for(result_future, timeout=10.0)
        logger.info(
            f"[主程序] ✅ 收到结果: success={result.get('success')}, message={result.get('message')}"
        )
        logger.info(f"[主程序] 完整结果: {result}")
    except asyncio.TimeoutError:
        logger.error(f"[主程序] ❌ 等待结果超时")
    except Exception as e:
        logger.error(f"[主程序] ❌ 等待结果异常: {e}")


async def simulate_agent(
    agent_client: MockAgentWebSocketClient, task_id: str, target_name: str
):
    """模拟Agent端：接收任务、执行、返回结果"""
    logger.info("=" * 60)
    logger.info("🤖 [Agent] 开始模拟任务执行")
    logger.info("=" * 60)

    # 模拟接收任务（实际中是通过WebSocket接收的）
    logger.info(f"[Agent] 收到部署任务: task_id={task_id}, target={target_name}")

    # 1. 发送running状态（任务开始）
    running_message = {
        "type": "deploy_result",
        "task_id": task_id,
        "target_name": target_name,
        "status": "running",
        "message": "部署任务已开始",
    }
    await agent_client.send_message(running_message)
    await asyncio.sleep(0.1)  # 模拟处理时间

    # 2. 发送running状态（开始执行）
    await agent_client.send_message(
        {
            "type": "deploy_result",
            "task_id": task_id,
            "target_name": target_name,
            "status": "running",
            "message": "开始执行部署操作...",
        }
    )
    await asyncio.sleep(0.1)

    # 3. 模拟执行部署（这里只是模拟，实际会执行docker命令）
    logger.info(
        f"[Agent] 执行部署命令: docker run -d --name=test docker.jajachina.com/public/nginx"
    )
    await asyncio.sleep(0.5)  # 模拟执行时间

    # 4. 发送running状态（执行成功）
    await agent_client.send_message(
        {
            "type": "deploy_result",
            "task_id": task_id,
            "target_name": target_name,
            "status": "running",
            "message": "命令执行成功，输出: 7fa52dc2401ecdfa3fa92a048fc4414dc91f3e80637fdb2d90c449f537f03383",
        }
    )
    await asyncio.sleep(0.1)

    # 5. 发送completed状态（最终结果）
    completed_message = {
        "type": "deploy_result",
        "task_id": task_id,
        "target_name": target_name,
        "status": "completed",
        "message": "部署成功",
        "result": {
            "success": True,
            "message": "部署成功",
            "output": "7fa52dc2401ecdfa3fa92a048fc4414dc91f3e80637fdb2d90c449f537f03383\n",
            "command": "docker run -d --name=test docker.jajachina.com/public/nginx",
        },
    }
    await agent_client.send_message(completed_message)
    logger.info(f"[Agent] ✅ 部署完成，结果已发送")


async def simulate_websocket_handler(
    connection_manager: MockConnectionManager,
    host_id: str,
    agent_websocket: MockWebSocket,
):
    """模拟主程序端的WebSocket处理器：接收Agent消息并处理"""
    logger.info("=" * 60)
    logger.info("📡 [WebSocket处理器] 开始接收消息")
    logger.info("=" * 60)

    while True:
        # 检查是否有新消息
        if agent_websocket.messages:
            message = agent_websocket.messages.pop(0)
            message_type = message.get("type")

            logger.info(f"[WebSocket处理器] 收到消息: type={message_type}")

            if message_type == "deploy_result":
                task_id = message.get("task_id")
                target_name = message.get("target_name", "")
                deploy_status = message.get("status")
                deploy_message = message.get("message")
                deploy_result = message.get("result")

                logger.info(
                    f"[WebSocket处理器] 部署任务结果: task_id={task_id}, target={target_name}, status={deploy_status}"
                )

                if deploy_status in ["completed", "failed"]:
                    # 构建结果字典
                    result_dict = {
                        "success": bool(deploy_status == "completed"),
                        "message": deploy_message or "",
                        "status": deploy_status,
                        "result": deploy_result,
                        "error": message.get("error"),
                    }

                    # 使用 task_id:target_name 作为 Future 的 key
                    future_key = f"{task_id}:{target_name}"

                    logger.info(
                        f"[WebSocket处理器] 准备设置Future结果: future_key={future_key}"
                    )
                    connection_manager.set_deploy_result(future_key, result_dict)

                    if deploy_status == "completed":
                        logger.info(f"[WebSocket处理器] ✅ 任务完成")
                        break
                elif deploy_status == "running":
                    logger.info(f"[WebSocket处理器] 📥 任务进行中: {deploy_message}")

        await asyncio.sleep(0.1)


async def main():
    """主测试函数"""
    logger.info("=" * 80)
    logger.info("🧪 开始测试主程序和Agent之间的通信流程")
    logger.info("=" * 80)

    host_id = "test-host-123"

    # 创建模拟的WebSocket连接
    agent_websocket = MockWebSocket(host_id)

    # 创建连接管理器
    connection_manager = MockConnectionManager()
    connection_manager.active_connections[host_id] = agent_websocket

    # 创建Agent客户端
    agent_client = MockAgentWebSocketClient(host_id, agent_websocket)

    task_id = "test-task-123"
    target_name = "test-deploy"

    # 同时运行主程序和Agent的模拟
    await asyncio.gather(
        simulate_main_program(connection_manager, host_id),
        asyncio.sleep(0.2),  # 稍微延迟，让主程序先发送任务
        simulate_agent(agent_client, task_id, target_name),
        simulate_websocket_handler(connection_manager, host_id, agent_websocket),
        return_exceptions=True,
    )

    logger.info("=" * 80)
    logger.info("✅ 测试完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

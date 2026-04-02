# backend/websocket_handler.py
"""
WebSocket处理器
处理Agent主机的WebSocket连接和消息
"""
import json
import asyncio
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from backend.agent_host_manager import AgentHostManager
from backend.pending_host_manager import pending_host_manager
from backend.agent_secret_manager import AgentSecretManager

# 存储活跃的连接
active_connections: Dict[str, WebSocket] = {}

# 存储等待部署结果的任务（task_id -> Future）
deploy_result_futures: Dict[str, asyncio.Future] = {}

# 存储等待「部署状态检查」结果的 Future（check_id -> Future）
check_deploy_result_futures: Dict[str, asyncio.Future] = {}


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.manager = AgentHostManager()

    async def connect(self, websocket: WebSocket, token: str) -> bool:
        """连接WebSocket并验证token"""
        # 验证token
        host = self.manager.get_agent_host_by_token(token)
        if not host:
            await websocket.close(code=1008, reason="Invalid token")
            return False

        host_id = host["host_id"]

        # 如果已有连接，先关闭旧连接并从active_connections中删除
        if host_id in active_connections:
            try:
                old_ws = active_connections[host_id]
                # 先从active_connections中删除，避免时序问题
                del active_connections[host_id]
                # 然后尝试关闭旧连接
                await old_ws.close(code=1000, reason="New connection")
            except Exception as e:
                # 旧连接可能已经断开，忽略错误
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"[WebSocket] 关闭旧连接时出错（可忽略）: {e}")

        # 接受连接
        await websocket.accept()

        # 保存连接
        active_connections[host_id] = websocket

        # 更新主机状态
        self.manager.update_host_status(host_id, "online")

        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"[WebSocket] Agent主机连接成功: host_id={host_id}, name={host['name']}, "
            f"当前连接的主机: {list(active_connections.keys())}"
        )
        print(f"✅ Agent主机连接成功: {host_id} ({host['name']})")
        return True

    def disconnect(self, host_id: str):
        """断开连接"""
        import logging

        logger = logging.getLogger(__name__)

        if host_id in active_connections:
            del active_connections[host_id]
            # 更新主机状态
            self.manager.update_host_status(host_id, "offline")
            logger.info(
                f"[WebSocket] Agent主机断开连接: host_id={host_id}, "
                f"当前连接的主机: {list(active_connections.keys())}"
            )
            print(f"✅ Agent主机断开连接: {host_id}")

        # 清理该主机相关的所有等待结果（通过查找所有相关的task_id）
        # 注意：这里我们无法直接知道哪些task_id属于这个host_id
        # 所以保留Future，让它们超时或由执行器清理

    async def send_message(self, host_id: str, message: dict):
        """向指定主机发送消息（带重试机制）"""
        import logging

        logger = logging.getLogger(__name__)

        # 记录当前连接状态
        connected_hosts = list(active_connections.keys())
        logger.debug(
            f"[WebSocket] 尝试发送消息: host_id={host_id}, "
            f"当前连接的主机: {connected_hosts}, "
            f"消息类型: {message.get('type')}"
        )

        if host_id in active_connections:
            websocket = active_connections[host_id]
            # 重试机制：最多重试2次
            max_retries = 2
            last_error = None

            for attempt in range(max_retries):
                try:
                    await websocket.send_json(message)
                    if attempt > 0:
                        logger.info(
                            f"[WebSocket] 消息发送成功（重试 {attempt} 次后）: host_id={host_id}, type={message.get('type')}"
                        )
                    else:
                        logger.debug(
                            f"[WebSocket] 消息发送成功: host_id={host_id}, type={message.get('type')}"
                        )
                    return True
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        # 短暂等待后重试
                        import asyncio

                        await asyncio.sleep(0.1)
                        # 检查连接是否还存在
                        if host_id not in active_connections:
                            logger.warning(
                                f"[WebSocket] 连接已断开，停止重试: host_id={host_id}"
                            )
                            break
                    else:
                        logger.error(
                            f"[WebSocket] 发送消息失败（{max_retries}次尝试后）: host_id={host_id}, error={e}"
                        )

            # 所有重试都失败，断开连接
            logger.error(
                f"[WebSocket] 发送消息最终失败: host_id={host_id}, error={last_error}"
            )
            self.disconnect(host_id)
            return False
        else:
            logger.warning(
                f"[WebSocket] 主机未连接: host_id={host_id}, "
                f"当前连接的主机: {connected_hosts}"
            )
            return False

    def create_deploy_result_future(self, task_id: str) -> asyncio.Future:
        """
        创建等待部署结果的Future

        Args:
            task_id: 任务ID（可能是task_id或future_key）

        Returns:
            Future对象，用于等待部署结果
        """
        import logging

        logger = logging.getLogger(__name__)

        future = asyncio.Future()
        deploy_result_futures[task_id] = future

        logger.info(
            f"[WebSocket] 创建Future: task_id={task_id}, "
            f"当前等待的Future数量: {len(deploy_result_futures)}, "
            f"所有Future keys: {list(deploy_result_futures.keys())}"
        )

        return future

    def set_deploy_result(self, task_id: str, result: Dict[str, Any]):
        """
        设置部署结果，通知等待的执行器

        Args:
            task_id: 任务ID（可能是task_id或deploy_task_id）
            result: 部署结果字典
        """
        import logging

        logger = logging.getLogger(__name__)

        if task_id in deploy_result_futures:
            future = deploy_result_futures.pop(task_id)
            if not future.done():
                future.set_result(result)
                logger.info(
                    f"[WebSocket] ✅ 已设置部署结果并通知执行器: task_id={task_id}, "
                    f"success={result.get('success')}, message={result.get('message', '')[:50]}"
                )
                print(
                    f"✅ 已设置部署结果并通知执行器: task_id={task_id}, success={result.get('success')}, message={result.get('message', '')[:50]}"
                )
            else:
                logger.warning(
                    f"[WebSocket] ⚠️ Future已完成，无法设置结果: task_id={task_id}"
                )
                print(f"⚠️ Future已完成，无法设置结果: task_id={task_id}")
        else:
            logger.warning(
                f"[WebSocket] ⚠️ 未找到等待的Future: task_id={task_id}, "
                f"当前等待的Future数量: {len(deploy_result_futures)}, "
                f"前10个: {list(deploy_result_futures.keys())[:10]}"
            )
            print(
                f"⚠️ 未找到等待的Future: task_id={task_id}, 当前等待的Future数量: {len(deploy_result_futures)}, 前5个: {list(deploy_result_futures.keys())[:5]}"
            )

    def cancel_deploy_result_future(self, task_id: str):
        """
        取消等待部署结果的Future

        Args:
            task_id: 任务ID
        """
        if task_id in deploy_result_futures:
            future = deploy_result_futures.pop(task_id)
            if not future.done():
                future.cancel()

    def create_check_deploy_future(self, check_id: str) -> asyncio.Future:
        """创建等待 check_deploy 结果的 Future。"""
        import logging

        logger = logging.getLogger(__name__)
        future = asyncio.Future()
        check_deploy_result_futures[check_id] = future
        logger.debug(
            f"[WebSocket] 创建 check_deploy Future: check_id={check_id}, "
            f"当前数量: {len(check_deploy_result_futures)}"
        )
        return future

    def set_check_deploy_result(self, check_id: str, result: Dict[str, Any]):
        """由 Agent 上报 check_deploy_result 时调用，唤醒等待方。"""
        import logging

        logger = logging.getLogger(__name__)
        if check_id in check_deploy_result_futures:
            future = check_deploy_result_futures.pop(check_id)
            if not future.done():
                future.set_result(result)
                logger.debug(
                    f"[WebSocket] check_deploy 结果已送达: check_id={check_id}"
                )
        else:
            logger.warning(
                f"[WebSocket] 未找到 check_deploy Future: check_id={check_id}"
            )

    def cancel_check_deploy_future(self, check_id: str):
        if check_id in check_deploy_result_futures:
            future = check_deploy_result_futures.pop(check_id)
            if not future.done():
                future.cancel()

    async def broadcast(self, message: dict):
        """向所有连接的主机广播消息"""
        disconnected = []
        for host_id, websocket in active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"⚠️ 广播消息失败 ({host_id}): {e}")
                disconnected.append(host_id)

        # 清理断开的连接
        for host_id in disconnected:
            self.disconnect(host_id)

    def get_connected_hosts(self) -> Set[str]:
        """获取所有已连接的主机ID"""
        return set(active_connections.keys())


# 全局连接管理器实例
connection_manager = ConnectionManager()


async def handle_agent_websocket(
    websocket: WebSocket,
    secret_key: Optional[str] = None,
    agent_token: Optional[str] = None,
    token: Optional[str] = None,
):
    """
    处理Agent WebSocket连接

    Args:
        websocket: WebSocket连接
        secret_key: 密钥（新方式）
        agent_token: Agent唯一标识（新方式，可选）
        token: 旧token（向后兼容）
    """
    manager = AgentHostManager()
    secret_manager = AgentSecretManager()
    import logging

    logger = logging.getLogger(__name__)

    # 向后兼容：如果没有secret_key但有token，使用旧方式
    if not secret_key and token:
        # 旧方式：直接使用token验证
        host = manager.get_agent_host_by_token(token)
        is_pending = False
        host_id = None
        host_name = None
        agent_unique_id = None

        if not host:
            # Token不存在，记录为待加入主机
            logger.info(
                f"[WebSocket] 未知token，记录为待加入主机: token={token[:16]}..."
            )
            print(f"⏳ 未知token，记录为待加入主机: token={token[:16]}...")

            # 接受连接
            await websocket.accept()

            # 记录到待加入列表
            pending_host = pending_host_manager.add_pending_host(
                agent_token=token,
                websocket=websocket,
                host_info={},
                docker_info={},
            )

            # 如果存在旧连接，先关闭旧连接（避免重复连接导致的问题）
            old_websocket = pending_host.get("_old_websocket")
            if old_websocket:
                try:
                    await old_websocket.close(code=1000, reason="New connection")
                    logger.debug(
                        f"[WebSocket] 已关闭待加入主机的旧连接: token={token[:16]}..."
                    )
                except Exception as e:
                    logger.debug(f"[WebSocket] 关闭旧连接时出错（可忽略）: {e}")
                # 清理标记
                if "_old_websocket" in pending_host:
                    del pending_host["_old_websocket"]

            # 发送待加入状态消息
            try:
                await websocket.send_json(
                    {
                        "type": "pending",
                        "message": "主机已连接，等待管理员批准加入",
                        "status": "pending",
                    }
                )
            except WebSocketDisconnect:
                logger.warning(
                    f"[WebSocket] 客户端在发送待加入消息前断开: token={token[:16]}..."
                )
                pending_host_manager.remove_pending_host(token)
                return
            except Exception as e:
                logger.warning(
                    f"[WebSocket] 发送待加入消息失败: token={token[:16]}..., error={e}"
                )
                pending_host_manager.remove_pending_host(token)
                return

            is_pending = True
            agent_unique_id = token
            logger.info(
                f"[WebSocket] 待加入主机已连接: token={token[:16]}...，等待主机信息"
            )
            print(f"⏳ 待加入主机已连接: token={token[:16]}...，等待主机信息")
        else:
            # Token存在，正常流程
            host_id = host["host_id"]
            host_name = host.get("name")
            agent_unique_id = host.get("agent_unique_id") or host.get("token")

            # 连接
            if not await connection_manager.connect(websocket, token):
                return

            # 发送欢迎消息
            try:
                await websocket.send_json(
                    {"type": "welcome", "message": "连接成功", "host_id": host_id}
                )
            except WebSocketDisconnect:
                logger.warning(
                    f"[WebSocket] 客户端在发送欢迎消息前断开: host_id={host_id}"
                )
                return
            except Exception as e:
                logger.warning(
                    f"[WebSocket] 发送欢迎消息失败: host_id={host_id}, error={e}"
                )
                return

            logger.info(
                f"[WebSocket] 开始接收消息循环: host_id={host_id}, name={host_name}"
            )
            print(f"📡 开始接收消息循环: host_id={host_id}, name={host_name}")
    else:
        # 新方式：使用密钥验证
        if not secret_key:
            await websocket.close(code=1008, reason="Missing secret_key")
            logger.warning("[WebSocket] 连接被拒绝：缺少secret_key")
            return

        # 验证密钥
        if not secret_manager.validate_secret(secret_key):
            await websocket.close(code=1008, reason="Invalid or disabled secret_key")
            logger.warning(
                f"[WebSocket] 连接被拒绝：无效或已禁用的密钥: {secret_key[:16]}..."
            )
            return

        logger.info(f"[WebSocket] 密钥验证成功: {secret_key[:16]}...")

        is_pending = False
        host_id = None
        host_name = None
        agent_unique_id = agent_token

        # 如果提供了agent_token，查找对应主机
        if agent_token:
            # 先通过token查找（向后兼容）
            host = manager.get_agent_host_by_token(agent_token)
            if not host:
                # 通过唯一标识查找
                host = manager.get_agent_host_by_unique_id(agent_token)

            if host:
                # 主机已存在，正常连接（connection_manager.connect 会调用 accept）
                host_id = host["host_id"]
                host_name = host.get("name")
                agent_unique_id = host.get("agent_unique_id") or host.get("token")

                # 连接（这里会调用 websocket.accept()）
                if not await connection_manager.connect(websocket, host.get("token")):
                    return

                # 发送欢迎消息
                try:
                    await websocket.send_json(
                        {"type": "welcome", "message": "连接成功", "host_id": host_id}
                    )
                except WebSocketDisconnect:
                    logger.warning(
                        f"[WebSocket] 客户端在发送欢迎消息前断开: host_id={host_id}"
                    )
                    return
                except Exception as e:
                    logger.warning(
                        f"[WebSocket] 发送欢迎消息失败: host_id={host_id}, error={e}"
                    )
                    return

                logger.info(
                    f"[WebSocket] 开始接收消息循环: host_id={host_id}, name={host_name}"
                )
                print(f"📡 开始接收消息循环: host_id={host_id}, name={host_name}")
            else:
                # 主机不存在，加入待加入列表
                is_pending = True
                pending_host = pending_host_manager.add_pending_host(
                    agent_token=agent_token,
                    websocket=websocket,
                    host_info={},
                    docker_info={},
                )

                # 如果存在旧连接，先关闭旧连接（避免重复连接导致的问题）
                old_websocket = pending_host.get("_old_websocket")
                if old_websocket:
                    try:
                        await old_websocket.close(code=1000, reason="New connection")
                        logger.debug(
                            f"[WebSocket] 已关闭待加入主机的旧连接: agent_token={agent_token[:16] if agent_token else 'None'}..."
                        )
                    except Exception as e:
                        logger.debug(f"[WebSocket] 关闭旧连接时出错（可忽略）: {e}")
                    # 清理标记
                    if "_old_websocket" in pending_host:
                        del pending_host["_old_websocket"]

                # 发送待加入状态消息
                try:
                    await websocket.send_json(
                        {
                            "type": "pending",
                            "message": "主机已连接，等待管理员批准加入",
                            "status": "pending",
                        }
                    )
                except WebSocketDisconnect:
                    logger.warning(
                        f"[WebSocket] 客户端在发送待加入消息前断开: agent_token={agent_token[:16] if agent_token else 'None'}..."
                    )
                    pending_host_manager.remove_pending_host(agent_token)
                    return
                except Exception as e:
                    logger.warning(
                        f"[WebSocket] 发送待加入消息失败: agent_token={agent_token[:16] if agent_token else 'None'}..., error={e}"
                    )
                    pending_host_manager.remove_pending_host(agent_token)
                    return

                logger.info(
                    f"[WebSocket] 待加入主机已连接: agent_token={agent_token[:16] if agent_token else 'None'}...，等待主机信息"
                )
                print(
                    f"⏳ 待加入主机已连接: agent_token={agent_token[:16] if agent_token else 'None'}...，等待主机信息"
                )
        else:
            # 没有提供agent_token，等待Agent发送主机信息（需要先 accept 连接）
            await websocket.accept()
            is_pending = True
            logger.info("[WebSocket] 等待Agent发送主机信息和唯一标识")
            print("⏳ 等待Agent发送主机信息和唯一标识")

    try:
        while True:
            try:
                # 接收消息
                logger.debug(f"[WebSocket] 等待接收消息: host_id={host_id}")
                data = await websocket.receive_text()
                logger.debug(
                    f"[WebSocket] 📥 收到原始消息: host_id={host_id}, size={len(data)} bytes"
                )

                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    logger.debug(
                        f"[WebSocket] 消息解析成功: host_id={host_id}, type={message_type}"
                    )
                except json.JSONDecodeError as e:
                    logger.error(
                        f"[WebSocket] JSON解析失败: host_id={host_id}, error={e}, data={data[:200]}"
                    )
                    print(f"❌ JSON解析失败 ({host_id}): {e}, data={data[:200]}")
                    await websocket.send_json(
                        {"type": "error", "message": "无效的JSON格式"}
                    )
                    continue

                message_type = message.get("type")
                logger.debug(
                    f"[WebSocket] 开始处理消息: {'pending' if is_pending else f'host_id={host_id}'}, type={message_type}"
                )

                if message_type == "heartbeat":
                    # 心跳消息
                    host_info = message.get("host_info", {})
                    docker_info = message.get("docker_info", {})

                    # 如果待加入且没有agent_token，尝试从消息中获取唯一标识
                    if is_pending and not agent_unique_id:
                        # 尝试从host_info或docker_info中获取唯一标识
                        unique_id_from_info = (
                            host_info.get("unique_id")
                            or docker_info.get("system_id")
                            or docker_info.get("id")
                        )
                        if unique_id_from_info:
                            agent_unique_id = unique_id_from_info
                            # 更新待加入主机的唯一标识
                            pending_host = (
                                pending_host_manager.get_pending_host_by_agent_token(
                                    None
                                )
                            )
                            if pending_host:
                                # 需要重新添加，使用新的唯一标识
                                pending_host_manager.remove_pending_host_by_websocket(
                                    websocket
                                )
                                pending_host_manager.add_pending_host(
                                    agent_token=agent_unique_id,
                                    websocket=websocket,
                                    host_info=host_info,
                                    docker_info=docker_info,
                                )
                                logger.info(
                                    f"[WebSocket] 获取到唯一标识: {agent_unique_id[:16]}..."
                                )

                    if is_pending:
                        # 待加入主机的心跳：更新待加入列表中的信息
                        if agent_unique_id:
                            pending_host_manager.update_pending_host_heartbeat(
                                agent_token=agent_unique_id,
                                host_info=host_info,
                                docker_info=docker_info,
                            )
                            logger.debug(
                                f"[WebSocket] 待加入主机心跳已更新: agent_token={agent_unique_id[:16] if agent_unique_id else 'None'}..."
                            )
                    else:
                        # 已加入主机的心跳：正常更新状态
                        if host_id:
                            manager.update_host_status(
                                host_id,
                                "online",
                                host_info=host_info,
                                docker_info=docker_info,
                            )

                    # 回复心跳
                    await websocket.send_json(
                        {"type": "heartbeat_ack", "timestamp": message.get("timestamp")}
                    )

                elif message_type == "host_info":
                    # 主机信息上报
                    host_info = message.get("host_info", {})
                    docker_info = message.get("docker_info", {})

                    # 如果待加入且没有agent_token，尝试从消息中获取唯一标识
                    if is_pending and not agent_unique_id:
                        unique_id_from_info = (
                            host_info.get("unique_id")
                            or docker_info.get("system_id")
                            or docker_info.get("id")
                            or message.get("agent_token")
                        )
                        if unique_id_from_info:
                            agent_unique_id = unique_id_from_info
                            # 更新待加入主机的唯一标识
                            pending_host_manager.remove_pending_host_by_websocket(
                                websocket
                            )
                            pending_host = pending_host_manager.add_pending_host(
                                agent_token=agent_unique_id,
                                websocket=websocket,
                                host_info=host_info,
                                docker_info=docker_info,
                            )
                            # 如果存在旧连接，先关闭旧连接
                            old_websocket = pending_host.get("_old_websocket")
                            if old_websocket:
                                try:
                                    await old_websocket.close(
                                        code=1000, reason="New connection"
                                    )
                                    logger.debug(
                                        f"[WebSocket] 已关闭待加入主机的旧连接: agent_token={agent_unique_id[:16]}..."
                                    )
                                except Exception as e:
                                    logger.debug(
                                        f"[WebSocket] 关闭旧连接时出错（可忽略）: {e}"
                                    )
                                # 清理标记
                                if "_old_websocket" in pending_host:
                                    del pending_host["_old_websocket"]
                            logger.info(
                                f"[WebSocket] 获取到唯一标识: {agent_unique_id[:16]}..."
                            )

                    if is_pending:
                        # 待加入主机信息上报：更新待加入列表
                        if agent_unique_id:
                            pending_host_manager.update_pending_host_heartbeat(
                                agent_token=agent_unique_id,
                                host_info=host_info,
                                docker_info=docker_info,
                            )
                            logger.info(
                                f"[WebSocket] 待加入主机信息已更新: agent_token={agent_unique_id[:16] if agent_unique_id else 'None'}..."
                            )
                            print(
                                f"⏳ 待加入主机信息已更新: agent_token={agent_unique_id[:16] if agent_unique_id else 'None'}..."
                            )
                    else:
                        # 已加入主机信息上报：正常更新
                        if host_id:
                            manager.update_host_status(
                                host_id,
                                "online",
                                host_info=host_info,
                                docker_info=docker_info,
                            )

                    await websocket.send_json(
                        {"type": "host_info_ack", "message": "主机信息已更新"}
                    )

                elif message_type == "command_result":
                    # 命令执行结果
                    if is_pending:
                        # 待加入主机不应该收到命令，忽略
                        logger.warning(
                            f"[WebSocket] 待加入主机收到命令结果，忽略: token={token[:16]}..."
                        )
                    else:
                        command_id = message.get("command_id")
                        result = message.get("result")
                        # 这里可以处理命令执行结果
                        print(f"📥 收到命令执行结果 ({host_id}): {command_id}")

                elif message_type == "deploy_result":
                    # 部署任务执行结果
                    if is_pending:
                        # 待加入主机不应该收到部署结果，忽略
                        logger.warning(
                            f"[WebSocket] 待加入主机收到部署结果，忽略: token={token[:16]}..."
                        )
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "主机尚未批准加入，无法处理部署任务",
                            }
                        )
                        continue

                    # 已加入主机的部署结果处理
                    task_id = message.get("task_id")  # 任务ID（用于匹配）
                    target_name = message.get("target_name", "")  # 目标名称
                    deploy_status = message.get("status")
                    deploy_message = message.get("message")
                    deploy_result = message.get("result")

                    logger.info(
                        f"[WebSocket] 📥 收到部署任务结果: host_id={host_id}, "
                        f"task_id={task_id}, target={target_name}, status={deploy_status}, message={deploy_message}"
                    )
                    logger.info(f"[WebSocket] 收到的完整消息: {message}")
                    # 计算future_key，用于调试
                    future_key_for_debug = f"{task_id}:{target_name}"
                    logger.info(
                        f"[WebSocket] 计算得到的future_key: {future_key_for_debug}"
                    )
                    print(
                        f"📥 收到部署任务结果 ({host_id}): task_id={task_id}, target={target_name}, 状态: {deploy_status}, 消息: {deploy_message}"
                    )

                    # 处理所有状态：running, completed, failed
                    # running状态：只记录日志，不触发Future完成
                    # completed/failed状态：触发Future完成，结束等待
                    if deploy_status in ["completed", "failed"]:
                        # 构建统一的结果格式
                        # 优先使用消息顶层的error字段，如果没有则从result中获取
                        error_msg = message.get("error")
                        if not error_msg and deploy_result:
                            error_msg = deploy_result.get("error")

                        result_dict = {
                            "success": bool(
                                deploy_status == "completed"
                            ),  # 确保是布尔值
                            "message": deploy_message or "",
                            "status": deploy_status,
                            "result": deploy_result,
                            "error": error_msg,
                        }

                        # 使用 task_id:target_name 作为 Future 的 key（因为同一任务可能有多个目标）
                        future_key = f"{task_id}:{target_name}"

                        import logging

                        logger = logging.getLogger(__name__)

                        logger.info(
                            f"[WebSocket] 📥 通知等待的执行器: task_id={task_id}, target={target_name}, "
                            f"future_key={future_key}, success={result_dict.get('success')} "
                            f"(type: {type(result_dict.get('success'))}), message={result_dict.get('message')}"
                        )
                        print(
                            f"📥 通知等待的执行器: task_id={task_id}, target={target_name}, future_key={future_key}, success={result_dict.get('success')} (type: {type(result_dict.get('success'))}), message={result_dict.get('message')}"
                        )

                        # 检查 Future 是否存在
                        logger.info(
                            f"[WebSocket] 检查Future: future_key={future_key}, "
                            f"当前等待的Future数量: {len(deploy_result_futures)}, "
                            f"所有Future keys: {list(deploy_result_futures.keys())}"
                        )

                        if future_key not in deploy_result_futures:
                            logger.warning(
                                f"[WebSocket] ⚠️ Future不存在: future_key={future_key}, "
                                f"当前等待的Future数量: {len(deploy_result_futures)}, "
                                f"所有Future keys: {list(deploy_result_futures.keys())}"
                            )
                            print(
                                f"⚠️ 警告: future_key={future_key} 的Future不存在，可能已超时或已处理"
                            )
                            print(
                                f"   期望的key: {future_key}, "
                                f"实际存在的keys: {list(deploy_result_futures.keys())}"
                            )
                        else:
                            logger.info(
                                f"[WebSocket] ✅ 找到Future: future_key={future_key}, "
                                f"准备设置结果"
                            )
                            print(f"✅ 找到Future: future_key={future_key}")

                        # 通知等待的执行器（使用 future_key）
                        connection_manager.set_deploy_result(future_key, result_dict)

                        logger.info(
                            f"[WebSocket] ✅ 已通知执行器: task_id={task_id}, target={target_name}, "
                            f"future_key={future_key}, result_dict keys: {list(result_dict.keys())}"
                        )
                        print(
                            f"✅ 已通知执行器: task_id={task_id}, target={target_name}, future_key={future_key}, result_dict keys: {list(result_dict.keys())}"
                        )
                    elif deploy_status == "running":
                        # running状态：只记录日志，不触发Future完成
                        logger.info(
                            f"[WebSocket] 📥 收到running状态消息: task_id={task_id}, target={target_name}, message={deploy_message}"
                        )
                        print(
                            f"📥 部署任务进行中: task_id={task_id}, target={target_name}, message={deploy_message}"
                        )
                        # 不处理running状态，继续等待最终结果

                        # 更新部署任务日志（使用BuildTaskManager）
                        # 注意：这里只更新日志，不更新任务状态（任务状态由DeployTaskManager统一管理）
                        try:
                            from backend.handlers import BuildTaskManager

                            build_manager = BuildTaskManager()
                            logger.info(
                                f"[WebSocket] BuildTaskManager已创建，准备更新日志: task_id={task_id}"
                            )

                            # 如果消息中没有target_name，尝试从任务配置中查找
                            if not target_name:
                                logger.info(
                                    f"[WebSocket] target_name为空，尝试从任务配置中查找: task_id={task_id}"
                                )
                                task = build_manager.get_task(task_id)
                                if task and task.get("task_type") == "deploy":
                                    task_config = task.get("task_config", {})
                                    config = task_config.get("config", {})
                                    targets = config.get("targets", [])
                                    for target in targets:
                                        # 支持新的host_type和host_name字段
                                        target_host_type = target.get("host_type")
                                        target_host_name = target.get("host_name")
                                        if (
                                            target_host_type == "agent"
                                            and target_host_name == host.get("name")
                                        ):
                                            target_name = target.get("name")
                                            break
                                        # 向后兼容：支持旧的mode和agent字段
                                        if target.get("mode") == "agent":
                                            agent_name = target.get("agent", {}).get(
                                                "name"
                                            )
                                            if agent_name == host.get("name"):
                                                target_name = target.get("name")
                                                break

                            # 添加running状态的日志
                            if deploy_message:
                                logger.info(
                                    f"[WebSocket] 准备添加running日志: task_id={task_id}, message={deploy_message}"
                                )
                                build_manager.add_log(
                                    task_id,
                                    f"[Agent] {deploy_message}\n",
                                )
                                logger.info(
                                    f"[WebSocket] ✅ running日志已添加: task_id={task_id}"
                                )

                        except Exception as e:
                            logger.error(f"[WebSocket] ⚠️ 更新部署任务日志失败: {e}")
                            import traceback

                            traceback.print_exc()

                    # 回复确认（无论什么状态都回复）
                    await websocket.send_json(
                        {
                            "type": "deploy_result_ack",
                            "task_id": task_id,
                            "message": "部署结果已接收",
                        }
                    )

                elif message_type == "check_deploy_result":
                    if is_pending:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "主机尚未批准加入，无法处理检查请求",
                            }
                        )
                        continue
                    check_id = message.get("check_id")
                    if not check_id:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "check_deploy_result 缺少 check_id",
                            }
                        )
                        continue
                    result_payload = {
                        "success": bool(message.get("success", False)),
                        "checked": message.get("checked", True),
                        "message": message.get("message", ""),
                        "exists": message.get("exists"),
                        "running": message.get("running"),
                        "exit_code": message.get("exit_code"),
                    }
                    connection_manager.set_check_deploy_result(check_id, result_payload)
                    await websocket.send_json(
                        {
                            "type": "check_deploy_result_ack",
                            "check_id": check_id,
                            "message": "检查已接收",
                        }
                    )

                else:
                    # 未知消息类型
                    await websocket.send_json(
                        {"type": "error", "message": f"未知的消息类型: {message_type}"}
                    )

            except WebSocketDisconnect:
                logger.warning(
                    f"[WebSocket] WebSocket断开连接: {'pending' if is_pending else f'host_id={host_id}'}"
                )
                break
            except Exception as e:
                import traceback

                logger.exception(
                    f"[WebSocket] 处理消息时出错: {'pending' if is_pending else f'host_id={host_id}'}, error={e}"
                )
                print(f"⚠️ 处理消息时出错 ({'pending' if is_pending else host_id}): {e}")
                traceback.print_exc()
                try:
                    await websocket.send_json(
                        {"type": "error", "message": f"处理消息失败: {str(e)}"}
                    )
                except:
                    logger.error(
                        f"[WebSocket] 无法发送错误消息: {'pending' if is_pending else f'host_id={host_id}'}"
                    )
                    break

    except WebSocketDisconnect:
        logger.info(
            f"[WebSocket] WebSocket断开连接: {'pending' if is_pending else f'host_id={host_id}'}"
        )
    except Exception as e:
        import traceback

        logger.exception(
            f"[WebSocket] WebSocket连接错误: {'pending' if is_pending else f'host_id={host_id}'}, error={e}"
        )
        print(f"⚠️ WebSocket连接错误 ({'pending' if is_pending else host_id}): {e}")
        traceback.print_exc()
    finally:
        # 断开连接
        if is_pending:
            # 待加入主机断开：从待加入列表中移除
            if agent_unique_id:
                pending_host_manager.remove_pending_host(agent_unique_id)
                logger.info(
                    f"[WebSocket] 待加入主机已断开: agent_token={agent_unique_id[:16] if agent_unique_id else 'None'}..."
                )
                print(
                    f"⏳ 待加入主机已断开: agent_token={agent_unique_id[:16] if agent_unique_id else 'None'}..."
                )
            else:
                # 通过websocket移除
                pending_host_manager.remove_pending_host_by_websocket(websocket)
                logger.info(f"[WebSocket] 待加入主机已断开（无唯一标识）")
        else:
            # 已加入主机断开：正常清理
            if host_id:
                logger.info(f"[WebSocket] 清理连接: host_id={host_id}")
                connection_manager.disconnect(host_id)

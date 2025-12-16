# backend/websocket_handler.py
"""
WebSocket处理器
处理Agent主机的WebSocket连接和消息
"""
import json
import asyncio
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
from backend.agent_host_manager import AgentHostManager

# 存储活跃的连接
active_connections: Dict[str, WebSocket] = {}

# 存储等待部署结果的任务（task_id -> Future）
deploy_result_futures: Dict[str, asyncio.Future] = {}


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

        # 如果已有连接，先关闭旧连接
        if host_id in active_connections:
            try:
                old_ws = active_connections[host_id]
                await old_ws.close(code=1000, reason="New connection")
            except:
                pass

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
        """向指定主机发送消息"""
        import logging

        logger = logging.getLogger(__name__)

        # 记录当前连接状态
        connected_hosts = list(active_connections.keys())
        logger.info(
            f"[WebSocket] 尝试发送消息: host_id={host_id}, "
            f"当前连接的主机: {connected_hosts}, "
            f"消息类型: {message.get('type')}"
        )

        if host_id in active_connections:
            websocket = active_connections[host_id]
            try:
                await websocket.send_json(message)
                logger.info(
                    f"[WebSocket] 消息发送成功: host_id={host_id}, type={message.get('type')}"
                )
                return True
            except Exception as e:
                logger.error(f"[WebSocket] 发送消息失败: host_id={host_id}, error={e}")
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
            task_id: 任务ID

        Returns:
            Future对象，用于等待部署结果
        """
        future = asyncio.Future()
        deploy_result_futures[task_id] = future
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


async def handle_agent_websocket(websocket: WebSocket, token: str):
    """处理Agent WebSocket连接"""
    manager = AgentHostManager()

    # 验证token并连接
    host = manager.get_agent_host_by_token(token)
    if not host:
        await websocket.close(code=1008, reason="Invalid token")
        return

    host_id = host["host_id"]

    # 连接
    if not await connection_manager.connect(websocket, token):
        return

    try:
        # 发送欢迎消息
        await websocket.send_json(
            {"type": "welcome", "message": "连接成功", "host_id": host_id}
        )

        # 处理消息
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[WebSocket] 开始接收消息循环: host_id={host_id}, name={host.get('name')}")
        print(f"📡 开始接收消息循环: host_id={host_id}, name={host.get('name')}")
        
        while True:
            try:
                # 接收消息
                logger.info(f"[WebSocket] 等待接收消息: host_id={host_id}")
                data = await websocket.receive_text()
                logger.info(f"[WebSocket] 📥 收到原始消息: host_id={host_id}, size={len(data)} bytes")
                print(f"📥 收到原始消息 ({host_id}): size={len(data)} bytes, preview={data[:100]}")

                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    logger.info(f"[WebSocket] 消息解析成功: host_id={host_id}, type={message_type}")
                    print(f"✅ 消息解析成功 ({host_id}): type={message_type}")
                except json.JSONDecodeError as e:
                    logger.error(f"[WebSocket] JSON解析失败: host_id={host_id}, error={e}, data={data[:200]}")
                    print(f"❌ JSON解析失败 ({host_id}): {e}, data={data[:200]}")
                    await websocket.send_json(
                        {"type": "error", "message": "无效的JSON格式"}
                    )
                    continue

                message_type = message.get("type")
                logger.info(f"[WebSocket] 开始处理消息: host_id={host_id}, type={message_type}")
                print(f"🔄 开始处理消息 ({host_id}): type={message_type}")

                if message_type == "heartbeat":
                    # 心跳消息
                    host_info = message.get("host_info", {})
                    docker_info = message.get("docker_info", {})

                    # 更新主机状态和信息
                    manager.update_host_status(
                        host_id, "online", host_info=host_info, docker_info=docker_info
                    )

                    # 回复心跳
                    await websocket.send_json(
                        {"type": "heartbeat_ack", "timestamp": message.get("timestamp")}
                    )

                elif message_type == "host_info":
                    # 主机信息上报
                    host_info = message.get("host_info", {})
                    docker_info = message.get("docker_info", {})

                    manager.update_host_status(
                        host_id, "online", host_info=host_info, docker_info=docker_info
                    )

                    await websocket.send_json(
                        {"type": "host_info_ack", "message": "主机信息已更新"}
                    )

                elif message_type == "command_result":
                    # 命令执行结果
                    command_id = message.get("command_id")
                    result = message.get("result")
                    # 这里可以处理命令执行结果
                    print(f"📥 收到命令执行结果 ({host_id}): {command_id}")

                elif message_type == "deploy_result":
                    # 部署任务执行结果
                    import logging

                    logger = logging.getLogger(__name__)

                    task_id = message.get("task_id")  # 任务ID（用于匹配）
                    target_name = message.get("target_name", "")  # 目标名称
                    deploy_status = message.get("status")
                    deploy_message = message.get("message")
                    deploy_result = message.get("result")

                    logger.info(
                        f"[WebSocket] 📥 收到部署任务结果: host_id={host_id}, "
                        f"task_id={task_id}, target={target_name}, status={deploy_status}"
                    )
                    print(
                        f"📥 收到部署任务结果 ({host_id}): task_id={task_id}, target={target_name}, 状态: {deploy_status}"
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
                        if future_key not in deploy_result_futures:
                            logger.warning(
                                f"[WebSocket] ⚠️ Future不存在: future_key={future_key}, "
                                f"当前等待的Future数量: {len(deploy_result_futures)}, "
                                f"前10个: {list(deploy_result_futures.keys())[:10]}"
                            )
                            print(
                                f"⚠️ 警告: future_key={future_key} 的Future不存在，可能已超时或已处理"
                            )
                        else:
                            logger.info(
                                f"[WebSocket] ✅ 找到Future: future_key={future_key}, "
                                f"准备设置结果"
                            )

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
                        print(
                            f"📥 部署任务进行中: task_id={task_id}, target={target_name}"
                        )
                        # 不处理running状态，继续等待最终结果

                        # 更新部署任务状态（使用BuildTaskManager）
                        # 注意：这里只更新日志，不更新任务状态（任务状态由DeployTaskManager统一管理）
                        try:
                            from backend.handlers import BuildTaskManager

                            build_manager = BuildTaskManager()

                            # 如果消息中没有target_name，尝试从任务配置中查找
                            if not target_name:
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

                            # 添加日志
                            if deploy_status == "completed":
                                build_manager.add_log(
                                    task_id,
                                    f"✅ 目标 {target_name} 部署成功: {deploy_message}\n",
                                )
                            elif deploy_status == "failed":
                                error_msg = message.get("error", deploy_message)
                                build_manager.add_log(
                                    task_id,
                                    f"❌ 目标 {target_name} 部署失败: {error_msg}\n",
                                )

                            # 更新任务状态（注意：这里不应该立即设置为completed，因为可能有多个目标）
                            # 任务状态的更新应该由DeployTaskManager统一管理
                        except Exception as e:
                            print(f"⚠️ 更新部署任务状态失败: {e}")
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

                else:
                    # 未知消息类型
                    await websocket.send_json(
                        {"type": "error", "message": f"未知的消息类型: {message_type}"}
                    )

            except WebSocketDisconnect:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[WebSocket] WebSocket断开连接: host_id={host_id}")
                break
            except Exception as e:
                import logging
                import traceback
                logger = logging.getLogger(__name__)
                logger.exception(
                    f"[WebSocket] 处理消息时出错: host_id={host_id}, error={e}"
                )
                print(f"⚠️ 处理消息时出错 ({host_id}): {e}")
                traceback.print_exc()
                try:
                    await websocket.send_json(
                        {"type": "error", "message": f"处理消息失败: {str(e)}"}
                    )
                except:
                    logger.error(f"[WebSocket] 无法发送错误消息: host_id={host_id}")
                    break

    except WebSocketDisconnect:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[WebSocket] WebSocket断开连接: host_id={host_id}")
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.exception(f"[WebSocket] WebSocket连接错误: host_id={host_id}, error={e}")
        print(f"⚠️ WebSocket连接错误 ({host_id}): {e}")
        traceback.print_exc()
    finally:
        # 断开连接
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[WebSocket] 清理连接: host_id={host_id}")
        connection_manager.disconnect(host_id)

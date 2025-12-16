# backend/deploy_executors/agent_executor.py
"""
Agent 主机执行器
通过 WebSocket 发送部署任务到 Agent
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Callable

from backend.deploy_executors.base import DeployExecutor
from backend.websocket_handler import connection_manager

logger = logging.getLogger(__name__)


class AgentExecutor(DeployExecutor):
    """Agent 主机执行器"""

    def __init__(self, host_info: Dict[str, Any]):
        """
        初始化 Agent 执行器

        Args:
            host_info: 主机信息字典，必须包含：
                - host_id: 主机ID
                - name: 主机名称
                - status: 主机状态（online/offline）
        """
        super().__init__(host_info)
        self.host_id = host_info.get("host_id")
        if not self.host_id:
            raise ValueError("host_info 必须包含 host_id")

    def can_execute(self) -> bool:
        """
        检查是否可以执行

        Returns:
            是否可以执行（主机是否在线）
        """
        return self.host_info.get("status") == "online"

    async def execute(
        self,
        deploy_config: Dict[str, Any],
        task_id: str,
        target_name: str,
        context: Optional[Dict[str, Any]] = None,
        update_status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        执行部署任务（通过 WebSocket 发送到 Agent）

        Args:
            deploy_config: 部署配置（已适配的命令/脚本）
            task_id: 任务ID
            target_name: 目标名称
            context: 模板变量上下文（可选）
            update_status_callback: 状态更新回调函数（可选）

        Returns:
            执行结果字典
        """
        if not self.can_execute():
            return {
                "success": False,
                "message": f"主机离线: {self.host_name}",
                "host_type": "agent",
                "deploy_method": "websocket",
            }

        logger.info(f"[Agent] 开始部署: task_id={task_id}, host={self.host_name}")

        # 记录命令信息
        if update_status_callback:
            steps = deploy_config.get("steps")
            if steps and isinstance(steps, list):
                update_status_callback(
                    f"[Agent] 部署配置（多步骤模式，共 {len(steps)} 个步骤）"
                )
                for idx, step in enumerate(steps, 1):
                    step_name = step.get("name", f"步骤 {idx}")
                    step_command = step.get("command", "").strip()
                    if step_command:
                        update_status_callback(
                            f"[Agent] 步骤 {idx}: {step_name} - {step_command}"
                        )
            else:
                deploy_mode = deploy_config.get("deploy_mode") or deploy_config.get(
                    "type", "docker_run"
                )
                command = deploy_config.get("command", "")
                compose_content = deploy_config.get("compose_content", "")

                if deploy_mode == "docker_compose":
                    if command:
                        update_status_callback(
                            f"[Agent] 执行命令: docker-compose {command}"
                        )
                    if compose_content:
                        compose_preview = compose_content.split("\n")[:5]
                        update_status_callback(
                            f"[Agent] docker-compose.yml 内容预览:\n"
                            + "\n".join([f"  {line}" for line in compose_preview])
                        )
                else:
                    if command:
                        update_status_callback(
                            f"[Agent] 执行命令: docker run {command}"
                        )

            update_status_callback(f"[Agent] 正在发送部署任务到 {self.host_name}...")

        # 为每个目标创建唯一的部署任务ID（避免多个目标使用相同task_id导致Future冲突）
        # 格式：{task_id}:{target_name}，确保每个目标有唯一的标识
        deploy_task_id = f"{task_id}:{target_name}"

        logger.info(
            f"[Agent] 创建部署任务: task_id={task_id}, deploy_task_id={deploy_task_id}, target_name={target_name}"
        )

        # 构建部署消息（推送给Agent的统一格式）
        deploy_message = {
            "type": "deploy",
            "task_id": task_id,  # 保留原始task_id用于日志记录
            "deploy_task_id": deploy_task_id,  # 唯一的部署任务ID（Agent必须原样返回）
            "deploy_config": deploy_config,  # 统一的docker配置格式
            "context": context or {},  # 模板变量上下文
            "target_name": target_name,
        }

        # 发送部署任务到 Agent
        logger.info(
            f"[Agent] 发送部署消息: host_id={self.host_id}, host_name={self.host_name}, "
            f"deploy_task_id={deploy_task_id}, task_id={task_id}, target_name={target_name}"
        )

        # 检查连接状态，如果未连接则等待一段时间（最多等待15秒）
        # 同时检查数据库状态和active_connections
        from backend.agent_host_manager import AgentHostManager

        agent_manager = AgentHostManager()

        max_wait_time = 15.0  # 最多等待15秒
        wait_interval = 0.5  # 每0.5秒检查一次
        waited_time = 0.0

        # 直接导入active_connections字典进行检查（与send_message方法保持一致）
        from backend.websocket_handler import active_connections

        while waited_time < max_wait_time:
            # 直接检查active_connections字典（与send_message方法保持一致）
            is_connected = self.host_id in active_connections

            # 检查数据库状态
            host_info = agent_manager.get_agent_host(self.host_id)
            db_status = host_info.get("status") if host_info else "unknown"

            if is_connected:
                logger.info(
                    f"[Agent] 主机已连接: host_id={self.host_id}, host_name={self.host_name}, "
                    f"等待时间: {waited_time:.1f}秒, 数据库状态: {db_status}, "
                    f"active_connections keys: {list(active_connections.keys())}"
                )
                break

            if waited_time == 0:
                logger.warning(
                    f"[Agent] 主机未连接，等待连接建立: host_id={self.host_id}, host_name={self.host_name}, "
                    f"数据库状态: {db_status}, active_connections keys: {list(active_connections.keys())}"
                )

            await asyncio.sleep(wait_interval)
            waited_time += wait_interval

        # 再次检查连接状态（直接检查active_connections，与send_message方法保持一致）
        host_info = agent_manager.get_agent_host(self.host_id)
        db_status = host_info.get("status") if host_info else "unknown"

        if self.host_id not in active_connections:
            logger.error(
                f"[Agent] 主机未连接（等待{waited_time:.1f}秒后）: host_id={self.host_id}, host_name={self.host_name}, "
                f"数据库状态: {db_status}, active_connections keys: {list(active_connections.keys())}"
            )

            # 如果数据库状态是online但active_connections中没有，说明连接可能刚断开
            if db_status == "online":
                error_msg = (
                    f"无法发送任务到 Agent: {self.host_name} (host_id: {self.host_id})。"
                    f"数据库显示主机在线，但WebSocket连接不存在。"
                    f"可能是连接刚断开，请检查Agent是否正常运行。"
                )
            else:
                error_msg = (
                    f"无法发送任务到 Agent: {self.host_name} (host_id: {self.host_id})，"
                    f"主机未连接（数据库状态: {db_status}）"
                )

            return {
                "success": False,
                "message": error_msg,
                "host_type": "agent",
                "deploy_method": "websocket",
                "host_id": self.host_id,
            }

        # 先创建等待结果的Future（使用 task_id + target_name 作为唯一标识）
        # 必须在发送消息之前创建，避免Agent在Future创建之前就发送了结果
        future_key = f"{task_id}:{target_name}"

        logger.info(
            f"[Agent] 准备创建等待Future: task_id={task_id}, target_name={target_name}, future_key={future_key}"
        )

        result_future = connection_manager.create_deploy_result_future(future_key)

        # 验证Future是否创建成功
        from backend.websocket_handler import deploy_result_futures

        if future_key in deploy_result_futures:
            logger.info(
                f"[Agent] ✅ Future创建成功: future_key={future_key}, "
                f"当前等待的Future数量: {len(deploy_result_futures)}, "
                f"所有Future keys: {list(deploy_result_futures.keys())}"
            )
        else:
            logger.error(
                f"[Agent] ❌ Future创建失败: future_key={future_key}, "
                f"当前等待的Future数量: {len(deploy_result_futures)}"
            )

        # 发送消息（在Future创建之后）
        success = await connection_manager.send_message(self.host_id, deploy_message)

        if not success:
            logger.error(
                f"[Agent] 发送消息失败: host_id={self.host_id}, host_name={self.host_name}, "
                f"active_connections keys: {list(active_connections.keys())}"
            )
            # 发送失败时，取消Future
            connection_manager.cancel_deploy_result_future(future_key)
            return {
                "success": False,
                "message": f"无法发送任务到 Agent: {self.host_name} (host_id: {self.host_id})，消息发送失败",
                "host_type": "agent",
                "deploy_method": "websocket",
                "host_id": self.host_id,
            }

        logger.info(
            f"[Agent] 消息发送成功: host_id={self.host_id}, host_name={self.host_name}"
        )

        # 记录等待状态
        if update_status_callback:
            update_status_callback(f"[Agent] 任务已发送，等待执行结果...")

        try:
            # 等待Agent返回执行结果（最多等待5分钟）
            # Agent会持续反馈状态（running -> completed/failed），只有completed/failed才会触发Future完成
            logger.info(
                f"[Agent] 开始等待结果: task_id={task_id}, target_name={target_name}, future_key={future_key}"
            )
            logger.info(
                f"[Agent] 等待Future完成: task_id={task_id}, target_name={target_name}, future_key={future_key}, "
                f"Future状态: done={result_future.done()}, cancelled={result_future.cancelled()}"
            )

            # 在等待期间，定期检查任务状态（避免任务被停止后还在等待）
            async def check_task_status():
                """定期检查任务状态"""
                from backend.handlers import BuildTaskManager

                build_manager = BuildTaskManager()
                while not result_future.done():
                    await asyncio.sleep(1)  # 每秒检查一次
                    task = build_manager.get_task(task_id)
                    if task and task.get("status") == "stopped":
                        logger.warning(f"[Agent] 检测到任务已停止: task_id={task_id}")
                        if not result_future.done():
                            result_future.cancel()
                            logger.info(
                                f"[Agent] 已取消Future: future_key={future_key}"
                            )
                        break

            # 启动任务状态检查任务
            status_check_task = asyncio.create_task(check_task_status())

            try:
                result = await asyncio.wait_for(result_future, timeout=300.0)
            finally:
                # 取消状态检查任务
                if not status_check_task.done():
                    status_check_task.cancel()
                    try:
                        await status_check_task
                    except asyncio.CancelledError:
                        pass
            logger.info(
                f"[Agent] ✅ Future已完成，收到结果: task_id={task_id}, target_name={target_name}, "
                f"success={result.get('success')}, result_type={type(result)}, result_keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}"
            )
            logger.info(f"[Agent] 完整结果内容: {result}")

            # 确保result是字典类型
            if not isinstance(result, dict):
                logger.error(
                    f"[Agent] ❌ 收到非字典类型的结果: type={type(result)}, value={result}"
                )
                result = {"success": False, "message": f"结果格式错误: {type(result)}"}

            # 确保success字段存在且是布尔值
            original_success = result.get("success")
            if "success" not in result:
                logger.warning(f"[Agent] ⚠️ 结果中缺少success字段: {result}")
                result["success"] = False
            else:
                result["success"] = bool(result["success"])
                if original_success != result["success"]:
                    logger.warning(
                        f"[Agent] ⚠️ success字段类型转换: {original_success} ({type(original_success)}) -> {result['success']} (bool)"
                    )

            # 添加主机类型和部署方法信息
            result.setdefault("host_type", "agent")
            result.setdefault("deploy_method", "websocket")
            result.setdefault("host_id", self.host_id)

            logger.info(
                f"[Agent] ✅ 最终返回结果: task_id={task_id}, target_name={target_name}, "
                f"success={result.get('success')} (type: {type(result.get('success'))}), "
                f"message={result.get('message')}, result_keys={list(result.keys())}"
            )

            return result

        except asyncio.CancelledError:
            # Future被取消（可能是任务被停止）
            connection_manager.cancel_deploy_result_future(future_key)
            error_msg = f"任务已被取消或停止"
            logger.warning(
                f"[Agent] {error_msg}: task_id={task_id}, target_name={target_name}"
            )
            if update_status_callback:
                update_status_callback(f"[Agent] ⚠️ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "host_type": "agent",
                "deploy_method": "websocket",
                "host_id": self.host_id,
            }
        except asyncio.TimeoutError:
            # 超时：取消Future
            connection_manager.cancel_deploy_result_future(future_key)
            error_msg = f"等待Agent执行结果超时（超过5分钟）"
            logger.error(
                f"[Agent] {error_msg}: task_id={task_id}, target_name={target_name}"
            )
            if update_status_callback:
                update_status_callback(f"[Agent] ❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "host_type": "agent",
                "deploy_method": "websocket",
                "host_id": self.host_id,
            }
        except Exception as e:
            # 其他异常：取消Future
            connection_manager.cancel_deploy_result_future(future_key)
            error_msg = f"等待Agent执行结果时发生异常: {str(e)}"
            logger.exception(
                f"[Agent] {error_msg}: task_id={task_id}, target_name={target_name}"
            )
            if update_status_callback:
                update_status_callback(f"[Agent] ❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "host_type": "agent",
                "deploy_method": "websocket",
                "host_id": self.host_id,
                "error": str(e),
            }

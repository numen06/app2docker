# backend/deploy_task_manager.py
"""
部署任务管理器
管理部署任务的生命周期，通过 WebSocket 分发任务到 Agent，跟踪任务执行状态
"""
import os
import uuid
import yaml
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from backend.deploy_config_parser import DeployConfigParser
from backend.websocket_handler import connection_manager
from backend.agent_host_manager import AgentHostManager
from backend.host_manager import HostManager
from backend.ssh_deploy_executor import SSHDeployExecutor
from backend.database import get_db_session
from backend.models import AgentHost, Host
from backend.deploy_executors.factory import ExecutorFactory
from backend.command_adapter import CommandAdapter

logger = logging.getLogger(__name__)


def extract_registry_from_image(image_name: str) -> Optional[str]:
    """
    从镜像名称中提取 registry 地址

    Args:
        image_name: 镜像名称，例如:
            - docker.jajachina.com/public/nginx
            - registry.cn-hangzhou.aliyuncs.com/namespace/app:tag
            - nginx (默认 docker.io)

    Returns:
        registry 地址，如果无法提取则返回 None（表示使用默认 docker.io）
    """
    if not image_name:
        return None

    # 移除 tag（如果有）
    image_without_tag = image_name.split(":")[0]
    parts = image_without_tag.split("/")

    # 如果包含点或冒号，可能是 registry 地址
    # 例如: docker.jajachina.com/public/nginx -> docker.jajachina.com
    if len(parts) > 1 and ("." in parts[0] or ":" in parts[0]):
        return parts[0]

    # 默认是 docker.io（返回 None 表示使用默认）
    return None


class DeployTaskManager:
    """部署任务管理器（简化版，只负责执行逻辑）"""

    def __init__(self):
        """初始化部署任务管理器"""
        self.parser = DeployConfigParser()
        self.agent_manager = AgentHostManager()
        self.host_manager = HostManager()
        self.ssh_executor = SSHDeployExecutor()
        self.executor_factory = ExecutorFactory()
        self.command_adapter = CommandAdapter()

    def _resolve_deploy_channel(
        self, deploy_config: Dict[str, Any], target: Dict[str, Any], host_type: str
    ) -> str:
        """解析发布通道，优先使用 deploy.channel，其次根据目标主机类型推断。"""
        channel = deploy_config.get("channel")
        if channel in ["agent", "portainer", "ssh"]:
            return channel

        target_host_type = target.get("host_type")
        if target_host_type in ["agent", "portainer", "ssh"]:
            return target_host_type

        if host_type in ["agent", "portainer", "ssh"]:
            return host_type

        return "agent"

    async def execute_task_with_manager(
        self,
        task_id: str,
        config_content: str,
        config: Dict[str, Any],
        registry: Optional[str] = None,
        tag: Optional[str] = None,
        target_names: Optional[List[str]] = None,
        task_manager=None,
    ) -> Dict[str, Any]:
        """
        执行部署任务（使用task_manager进行状态管理）

        Args:
            task_id: 任务ID
            config_content: YAML配置内容
            config: 解析后的配置字典
            registry: 镜像仓库地址（可选）
            tag: 镜像标签（可选）
            target_names: 要执行的目标名称列表（如果为 None，则执行所有目标）
            task_manager: 任务管理器实例，用于更新状态和日志

        Returns:
            执行结果字典
        """
        if not task_manager:
            return {"success": False, "message": "task_manager参数是必需的"}

        # 构建部署上下文
        context = self.parser.build_deploy_context(
            config, registry=registry, tag=tag, task_id=task_id
        )

        # 获取部署配置（统一格式）
        deploy_config = self.parser.get_deploy_config(config)
        
        # #region agent log
        try:
            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                import json, time
                compose_content_debug = deploy_config.get("compose_content", "")
                # 检查 config 中 deploy 部分的 compose_content
                deploy_section = config.get("deploy", {})
                deploy_compose_content = deploy_section.get("compose_content", "") if isinstance(deploy_section, dict) else ""
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"deploy_task_manager.py:execute_task_with_manager:GET_DEPLOY_CONFIG","message":"获取部署配置","data":{"deploy_type":deploy_config.get("type"),"compose_content_length":len(compose_content_debug) if compose_content_debug else 0,"compose_content_preview":compose_content_debug[:200] if compose_content_debug else "","compose_content_full":compose_content_debug if compose_content_debug else "","config_deploy_compose_length":len(deploy_compose_content) if deploy_compose_content else 0,"config_deploy_compose_preview":deploy_compose_content[:200] if deploy_compose_content else ""},"timestamp":int(time.time()*1000)}) + "\n")
        except: pass
        # #endregion

        # 获取要执行的目标
        targets = config.get("targets", [])
        if target_names:
            targets = [t for t in targets if t.get("name") in target_names]

        # 添加日志
        task_manager.add_log(
            task_id, f"🚀 开始执行部署任务，共 {len(targets)} 个目标\n"
        )

        # 执行每个目标
        results = {}
        for target in targets:
            target_name = target.get("name")

            # 添加日志
            task_manager.add_log(task_id, f"📦 开始部署目标: {target_name}\n")

            try:
                # 使用新的执行器架构
                logger.info(
                    f"[DeployTaskManager] 开始执行目标: {target_name}, task_id={task_id}"
                )
                result = await self._execute_target_with_executor(
                    task_id, target, deploy_config, context, task_manager=task_manager
                )

                logger.info(
                    f"[DeployTaskManager] 目标 {target_name} 执行完成，收到结果: "
                    f"type={type(result)}, is_dict={isinstance(result, dict)}, "
                    f"keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}"
                )

                results[target_name] = result

                # 确保result是字典类型
                if not isinstance(result, dict):
                    logger.error(
                        f"❌ 目标 {target_name} 返回非字典类型的结果: type={type(result)}, value={result}"
                    )
                    result = {
                        "success": False,
                        "message": f"结果格式错误: {type(result)}",
                    }
                    results[target_name] = result

                # 确保success字段存在且是布尔值
                if "success" not in result:
                    logger.warning(
                        f"⚠️ 目标 {target_name} 结果中缺少success字段: {result}"
                    )
                    result["success"] = False
                else:
                    original_success = result["success"]
                    result["success"] = bool(result["success"])
                    if original_success != result["success"]:
                        logger.warning(
                            f"⚠️ 目标 {target_name} success字段类型转换: {original_success} ({type(original_success)}) -> {result['success']} (bool)"
                        )

                logger.info(
                    f"✅ 目标 {target_name} 执行结果: success={result.get('success')} (type: {type(result.get('success'))}), "
                    f"message={result.get('message', '')[:100]}, result_keys={list(result.keys())}"
                )

                # 添加日志
                if result.get("success"):
                    task_manager.add_log(
                        task_id,
                        f"✅ 目标 {target_name} 部署成功: {result.get('message', '')}\n",
                    )
                else:
                    task_manager.add_log(
                        task_id,
                        f"❌ 目标 {target_name} 部署失败: {result.get('message', '')}\n",
                    )

            except Exception as e:
                import traceback

                logger.exception(f"❌ 执行目标 {target_name} 时发生异常: {e}")
                traceback.print_exc()
                error_result = {
                    "success": False,
                    "message": f"执行异常: {str(e)}",
                    "error": str(e),
                }
                results[target_name] = error_result
                task_manager.add_log(
                    task_id, f"❌ 目标 {target_name} 执行异常: {str(e)}\n"
                )
                logger.error(
                    f"❌ 目标 {target_name} 异常结果: {error_result}, "
                    f"success={error_result.get('success')}, type={type(error_result.get('success'))}"
                )

        # 检查整体状态
        # 确保所有结果都有success字段且不是None
        all_completed = True
        missing_results = []
        for target_name, result in results.items():
            if not isinstance(result, dict):
                logger.error(
                    f"目标 {target_name} 结果不是字典: {type(result)}, value={result}"
                )
                all_completed = False
                missing_results.append(f"{target_name}: 不是字典类型")
                break
            if "success" not in result or result.get("success") is None:
                logger.warning(
                    f"目标 {target_name} 结果中success字段缺失或为None: {result}"
                )
                all_completed = False
                missing_results.append(f"{target_name}: success字段缺失或为None")
                break

        logger.info(
            f"部署任务检查: task_id={task_id}, 目标数量={len(results)}, all_completed={all_completed}"
        )
        logger.info(f"  所有目标名称: {list(results.keys())}")
        for target_name, result in results.items():
            logger.info(
                f"  目标 {target_name}: success={result.get('success')}, success_type={type(result.get('success'))}, "
                f"message={result.get('message', '')[:50]}, result_keys={list(result.keys()) if isinstance(result, dict) else 'N/A'}"
            )

        if missing_results:
            logger.warning(f"  缺失或无效的结果: {missing_results}")

        if all_completed:
            has_failed = any(not r.get("success", False) for r in results.values())
            if has_failed:
                task_manager.add_log(task_id, f"⚠️ 部署任务完成，部分目标失败\n")
                # 更新任务状态为失败
                task_manager.update_task_status(
                    task_id, "failed", error="部分目标部署失败"
                )
                logger.info(f"✅ 任务状态已更新为失败: task_id={task_id}")
            else:
                task_manager.add_log(task_id, f"✅ 部署任务完成，所有目标成功\n")
                # 更新任务状态为完成
                task_manager.update_task_status(task_id, "completed")
                logger.info(f"✅ 任务状态已更新为完成: task_id={task_id}")
        else:
            logger.warning(
                f"❌ 任务未完成: task_id={task_id}, 部分目标结果未返回或格式错误"
            )
            logger.warning(f"  结果详情: {results}")
            if missing_results:
                logger.warning(f"  问题: {missing_results}")
            task_manager.add_log(task_id, f"⚠️ 部分目标结果未返回，任务可能仍在执行中\n")

        return {"success": True, "task_id": task_id, "results": results}

    async def _execute_target_with_executor(
        self,
        task_id: str,
        target: Dict[str, Any],
        deploy_config: Dict[str, Any],
        context: Dict[str, Any],
        task_manager=None,
    ) -> Dict[str, Any]:
        """
        使用执行器执行目标（新架构）

        Args:
            task_id: 任务ID
            target: 目标配置
            deploy_config: 部署配置（统一格式）
            context: 模板变量上下文

        Returns:
            执行结果字典（统一格式）
        """
        target_name = target.get("name")

        # 确定主机类型和名称
        host_type = target.get("host_type")
        host_name = target.get("host_name")

        # 向后兼容：如果没有host_type，使用旧的mode字段
        if not host_type:
            mode = target.get("mode", "agent")
            if mode == "agent":
                # 需要查询实际的主机类型
                agent_config = target.get("agent", {})
                host_name = agent_config.get("name")
                # 查询主机类型
                agent_hosts = self.agent_manager.list_agent_hosts()
                for host in agent_hosts:
                    if host.get("name") == host_name:
                        host_type = host.get("host_type", "agent")
                        break
                if not host_type:
                    host_type = "agent"
            elif mode == "ssh":
                host_type = "ssh"
                host_name = target.get("host")
            else:
                return {
                    "success": False,
                    "message": f"未知的部署模式: {mode}",
                    "host_type": "unknown",
                    "deploy_mode": mode,
                }

        if not host_name:
            return {
                "success": False,
                "message": f"目标 {target_name} 的主机名称未指定",
                "host_type": host_type,
            }

        deploy_channel = self._resolve_deploy_channel(deploy_config, target, host_type)
        has_explicit_channel = deploy_config.get("channel") in [
            "agent",
            "portainer",
            "ssh",
        ]
        if has_explicit_channel and deploy_channel != host_type:
            return {
                "success": False,
                "message": (
                    f"发布通道与目标主机类型不匹配: channel={deploy_channel}, "
                    f"host_type={host_type}, host={host_name}"
                ),
                "host_type": host_type,
                "host_name": host_name,
            }

        # 创建执行器
        executor = self.executor_factory.create_executor(host_type, host_name)
        if not executor:
            return {
                "success": False,
                "message": f"无法创建执行器: 主机 {host_name} ({host_type}) 不存在或配置错误",
                "host_type": host_type,
                "host_name": host_name,
            }

        # 检查是否可以执行
        if not executor.can_execute():
            return {
                "success": False,
                "message": f"主机不可用: {host_name}",
                "host_type": host_type,
                "host_name": host_name,
            }

        # 验证 Compose 模式支持（如果是 Compose 模式）
        deploy_type = deploy_config.get("type", "docker_run")
        if deploy_type == "docker_compose":
            compose_mode = deploy_config.get("compose_mode", "docker-compose")

            # 获取主机信息
            host_info = None
            if host_type == "agent" or host_type == "portainer":
                # 从列表中查找主机
                agent_hosts = self.agent_manager.list_agent_hosts()
                for host in agent_hosts:
                    if host.get("name") == host_name:
                        host_info = host
                        break
            elif host_type == "ssh":
                from backend.host_manager import HostManager

                host_manager = HostManager()
                ssh_hosts = host_manager.list_hosts()
                for host in ssh_hosts:
                    if host.get("name") == host_name:
                        host_info = host
                        break

            if host_info:
                docker_info = host_info.get("docker_info", {})
                # Portainer 通道统一按 Stack 发布，不依赖 compose_mode 的本机能力探测
                if host_type == "portainer":
                    logger.info(
                        "[DeployTaskManager] Portainer 通道跳过 compose_mode 能力检查，统一按 Stack 发布: "
                        f"task_id={task_id}, host={host_name}, compose_mode={compose_mode}"
                    )
                    if task_manager:
                        task_manager.add_log(
                            task_id,
                            "ℹ️ Portainer 通道已忽略 compose_mode 能力检查，统一按 Stack 发布\n",
                        )
                elif compose_mode == "docker-compose":
                    compose_supported = docker_info.get("compose_supported")
                    if compose_supported is False:
                        if task_manager:
                            task_manager.add_log(
                                task_id,
                                f"⚠️ 主机 {host_name} 不支持 docker-compose 模式，部署将失败\n",
                            )
                        return {
                            "success": False,
                            "message": f"主机 {host_name} 不支持 docker-compose 模式",
                            "host_type": host_type,
                            "host_name": host_name,
                        }
                elif compose_mode == "docker-stack":
                    stack_supported = docker_info.get("stack_supported")
                    if stack_supported is not True:
                        if task_manager:
                            task_manager.add_log(
                                task_id,
                                f"⚠️ 主机 {host_name} 不支持 docker stack 模式（需要 Docker Swarm 环境），部署将失败\n",
                            )
                        return {
                            "success": False,
                            "message": f"主机 {host_name} 不支持 docker stack 模式（需要 Docker Swarm 环境）",
                            "host_type": host_type,
                            "host_name": host_name,
                        }

        # 检查是否为多步骤模式
        steps = deploy_config.get("steps")
        if steps and isinstance(steps, list):
            # 多步骤模式：直接传递steps，不进行命令适配
            adapted_config = {
                "steps": steps,
                "redeploy": deploy_config.get("redeploy", False),
                "channel": deploy_channel,
            }
        else:
            # 单命令模式：适配命令（根据主机类型）
            deploy_type = deploy_config.get("type", "docker_run")
            command = deploy_config.get("command", "")
            compose_content = deploy_config.get("compose_content", "")

            # 检查是否有主机特定的覆盖配置
            overrides = target.get("overrides", {})
            if overrides.get("command"):
                command = overrides["command"]
            if overrides.get("compose_content"):
                compose_content = overrides["compose_content"]

            # 适配命令（将 compose_mode 和 redeploy_strategy 传递到 context）
            enhanced_context = context.copy() if context else {}
            if "compose_mode" in deploy_config:
                enhanced_context["compose_mode"] = deploy_config["compose_mode"]
            if "redeploy_strategy" in deploy_config:
                enhanced_context["redeploy_strategy"] = deploy_config[
                    "redeploy_strategy"
                ]

            try:
                adapted_config = self.command_adapter.adapt_command(
                    command=command,
                    deploy_type=deploy_type,
                    host_type=host_type,
                    compose_content=compose_content,
                    context=enhanced_context,
                )
            except Exception as e:
                logger.error(f"适配命令失败: {e}")
                return {
                    "success": False,
                    "message": f"适配命令失败: {str(e)}",
                    "host_type": host_type,
                    "error": str(e),
                }

            # 合并redeploy等配置
            if deploy_config.get("redeploy"):
                adapted_config["redeploy"] = True
            adapted_config["channel"] = deploy_channel
            # 合并 compose_mode 和 redeploy_strategy（如果存在）
            if "compose_mode" in deploy_config:
                adapted_config["compose_mode"] = deploy_config["compose_mode"]
            if "redeploy_strategy" in deploy_config:
                adapted_config["redeploy_strategy"] = deploy_config["redeploy_strategy"]
            if "stack_strategy" in deploy_config:
                adapted_config["stack_strategy"] = deploy_config["stack_strategy"]
            if "stack_id" in deploy_config:
                adapted_config["stack_id"] = deploy_config["stack_id"]
            if "stack_name" in deploy_config:
                adapted_config["stack_name"] = deploy_config["stack_name"]
            # 合并应用名称（用于 Docker Compose 项目名称）
            if context and isinstance(context.get("app"), dict):
                app_name = context.get("app", {}).get("name", "")
                if app_name:
                    adapted_config["app_name"] = app_name
            # 合并 compose_mode 和 redeploy_strategy（如果存在）
            if "compose_mode" in deploy_config:
                adapted_config["compose_mode"] = deploy_config["compose_mode"]
            if "redeploy_strategy" in deploy_config:
                adapted_config["redeploy_strategy"] = deploy_config["redeploy_strategy"]
            if "stack_strategy" in deploy_config:
                adapted_config["stack_strategy"] = deploy_config["stack_strategy"]
            if "stack_id" in deploy_config:
                adapted_config["stack_id"] = deploy_config["stack_id"]
            if "stack_name" in deploy_config:
                adapted_config["stack_name"] = deploy_config["stack_name"]

        # 创建状态更新回调
        def update_status_callback(message: str):
            if task_manager:
                task_manager.add_log(task_id, f"{message}\n")

        # 在执行前记录命令信息
        if task_manager:
            steps = adapted_config.get("steps")
            if steps and isinstance(steps, list):
                # 多步骤模式：记录所有步骤的命令
                task_manager.add_log(
                    task_id, f"📋 部署配置（多步骤模式，共 {len(steps)} 个步骤）：\n"
                )
                for idx, step in enumerate(steps, 1):
                    step_name = step.get("name", f"步骤 {idx}")
                    step_command = step.get("command", "").strip()
                    if step_command:
                        task_manager.add_log(task_id, f"  步骤 {idx}: {step_name}\n")
                        task_manager.add_log(task_id, f"    命令: {step_command}\n")
            else:
                # 单命令模式：记录命令
                deploy_type = adapted_config.get("deploy_mode") or adapted_config.get(
                    "type", "docker_run"
                )
                command = adapted_config.get("command", "")
                compose_content = adapted_config.get("compose_content", "")

                if deploy_type == "docker_compose":
                    compose_mode = adapted_config.get("compose_mode", "docker-compose")
                    mode_name = (
                        "Docker Stack"
                        if compose_mode == "docker-stack"
                        else "Docker Compose"
                    )
                    task_manager.add_log(
                        task_id, f"📋 部署配置（{mode_name} 模式）：\n"
                    )
                    if command:
                        if compose_mode == "docker-stack":
                            task_manager.add_log(
                                task_id, f"  命令: docker stack deploy {command}\n"
                            )
                        else:
                            task_manager.add_log(
                                task_id, f"  命令: docker-compose {command}\n"
                            )
                    if compose_content:
                        # 只显示前几行，避免日志过长
                        compose_lines = compose_content.split("\n")[:10]
                        task_manager.add_log(
                            task_id, f"  docker-compose.yml 内容（前10行）：\n"
                        )
                        for line in compose_lines:
                            task_manager.add_log(task_id, f"    {line}\n")
                        if len(compose_content.split("\n")) > 10:
                            task_manager.add_log(
                                task_id,
                                f"    ... (共 {len(compose_content.split('\n'))} 行)\n",
                            )
                else:
                    task_manager.add_log(task_id, f"📋 部署配置（Docker Run 模式）：\n")
                    if command:
                        task_manager.add_log(task_id, f"  命令: docker run {command}\n")

        # 查找并添加 registry 认证信息
        registry_auth_info = None
        try:
            # 从部署配置中提取镜像名称
            image_name = None

            # 尝试从 adapted_config 中获取镜像名称
            if adapted_config.get("deploy_mode") == "docker_run":
                # Docker Run 模式：从 image 字段获取
                image_name = adapted_config.get("image")
                # 如果没有，尝试从 command 中解析
                if not image_name:
                    command_str = adapted_config.get("command", "")
                    if command_str:
                        # 使用 command_adapter 的解析逻辑
                        from backend.command_adapter import CommandAdapter

                        parsed = CommandAdapter._parse_docker_run_command(command_str)
                        image_name = parsed.get("image")
            elif adapted_config.get("deploy_mode") == "docker_compose":
                # Docker Compose 模式：从 compose_content 中解析
                compose_content = adapted_config.get("compose_content", "")
                if compose_content:
                    try:
                        import yaml

                        compose_config = yaml.safe_load(compose_content)
                        services = compose_config.get("services", {})
                        # 查找第一个服务的镜像
                        for service_name, service_config in services.items():
                            if "image" in service_config:
                                image_name = service_config["image"]
                                break
                    except Exception as e:
                        logger.debug(f"解析 compose_content 失败: {e}")

            # 如果还没有找到，尝试从 context 中构建
            if not image_name and context:
                registry = context.get("registry", "docker.io")
                tag = context.get("tag", "latest")
                app_name = ""
                if isinstance(context.get("app"), dict):
                    app_name = context.get("app", {}).get("name", "")
                elif context.get("app_name"):
                    app_name = context.get("app_name", "")

                if app_name:
                    if registry and registry != "docker.io":
                        image_name = f"{registry}/{app_name}:{tag}"
                    else:
                        image_name = f"{app_name}:{tag}"

            # 如果找到了镜像名称，提取 registry 并查找认证配置
            if image_name:
                registry_address = extract_registry_from_image(image_name)
                if registry_address:
                    # 查找匹配的 registry 配置
                    from backend.config import get_all_registries

                    registries = get_all_registries()

                    for registry_config in registries:
                        registry_host = registry_config.get("registry", "")
                        username = registry_config.get("username", "")
                        password = registry_config.get("password", "")

                        # 匹配逻辑：检查 registry 地址是否匹配
                        if (
                            registry_host == registry_address
                            or registry_address.startswith(registry_host)
                            or registry_host.startswith(registry_address)
                        ):
                            if username and password:
                                registry_auth_info = {
                                    "registry": registry_address,
                                    "username": username,
                                    "password": password,
                                }
                                logger.info(
                                    f"找到匹配的 registry 认证配置: {registry_address}, username: {username}"
                                )
                                if task_manager:
                                    task_manager.add_log(
                                        task_id,
                                        f"🔐 找到 registry 认证配置: {registry_address}\n",
                                    )
                                break

                    if not registry_auth_info:
                        logger.debug(f"未找到 registry 认证配置: {registry_address}")
                else:
                    logger.debug(f"无法从镜像名称提取 registry: {image_name}")
            else:
                logger.debug("无法从部署配置中提取镜像名称")
        except Exception as e:
            logger.warning(f"查找 registry 认证配置时出错: {e}")
            # 不阻止部署，继续执行

        # 将认证信息添加到 context
        if registry_auth_info:
            if not context:
                context = {}
            context["registry_auth"] = registry_auth_info

        # 执行部署
        try:
            result = await executor.execute(
                deploy_config=adapted_config,
                task_id=task_id,
                target_name=target_name,
                context=context,
                update_status_callback=update_status_callback,
            )
            return result
        except Exception as e:
            import traceback

            logger.exception(f"执行器执行失败: {e}")
            if task_manager:
                task_manager.add_log(task_id, f"❌ 执行器执行失败: {str(e)}\n")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "host_type": host_type,
                "host_name": host_name,
                "error": str(e),
            }

    async def _execute_target_unified(
        self,
        task_id: str,
        target: Dict[str, Any],
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        统一的目标执行接口（向后兼容，内部调用新方法）

        Args:
            task_id: 任务ID
            target: 目标配置
            config: 部署配置
            context: 模板变量上下文

        Returns:
            执行结果字典（统一格式）
        """
        deploy_config = self.parser.get_deploy_config(config)
        return await self._execute_target_with_executor(
            task_id, target, deploy_config, context
        )

    async def _execute_agent_target(
        self,
        task_id: str,
        target: Dict[str, Any],
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        执行 Agent 目标部署

        Args:
            task_id: 任务ID
            target: 目标配置
            config: 部署配置
            context: 模板变量上下文

        Returns:
            执行结果字典
        """
        agent_config = target.get("agent", {})
        agent_name = agent_config.get("name")

        # 查找 Agent 主机
        agent_hosts = self.agent_manager.list_agent_hosts()
        agent_host = None
        for host in agent_hosts:
            if host.get("name") == agent_name:
                agent_host = host
                break

        if not agent_host:
            return {"success": False, "message": f"Agent 主机不存在: {agent_name}"}

        host_id = agent_host.get("host_id")

        # 检查主机是否在线
        if agent_host.get("status") != "online":
            return {"success": False, "message": f"主机离线: {agent_name}"}

        host_type = agent_host.get("host_type", "agent")

        # 渲染目标配置（统一处理：无论来源是表单还是YAML，都转换为统一的配置格式）
        rendered_target = self.parser.render_target_config(target, context)
        docker_config = rendered_target.get("docker", {})

        # 根据主机类型选择部署方式（统一接口，不同实现）
        if host_type == "portainer":
            # Portainer 类型：使用 Portainer API 部署
            logger.info(f"[Portainer] 开始部署: task_id={task_id}, host={agent_name}")
            result = await self._execute_portainer_target(
                agent_host, task_id, docker_config, context, target.get("name")
            )
            result["host_type"] = "portainer"
            result["deploy_method"] = "portainer_api"
            return result
        else:
            # Agent 类型：通过 WebSocket 发送任务
            logger.info(f"[Agent] 开始部署: task_id={task_id}, host={agent_name}")

            # 构建部署消息（推送给Agent的统一格式）
            # deploy_config 包含完整的docker配置，Agent会根据此配置执行部署
            deploy_message = {
                "type": "deploy",
                "task_id": task_id,
                "deploy_config": docker_config,  # 统一的docker配置格式
                "context": context,  # 模板变量上下文
                "target_name": target.get("name"),
            }

            # 发送部署任务到 Agent
            success = await connection_manager.send_message(host_id, deploy_message)

            if not success:
                return {
                    "success": False,
                    "message": f"无法发送任务到 Agent: {agent_name}",
                    "host_type": "agent",
                    "deploy_method": "websocket",
                    "host_id": host_id,
                }

            return {
                "success": True,
                "message": f"任务已发送到 Agent: {agent_name}",
                "host_type": "agent",
                "deploy_method": "websocket",
                "host_id": host_id,
            }

    async def _execute_ssh_target(
        self,
        task_id: str,
        target: Dict[str, Any],
        config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        执行 SSH 目标部署

        Args:
            task_id: 任务ID
            target: 目标配置
            config: 部署配置
            context: 模板变量上下文

        Returns:
            执行结果字典
        """
        logger.info(
            f"[SSH] 开始执行 SSH 部署任务: task_id={task_id}, target={target.get('name')}"
        )

        try:
            # 注意：此方法已不再使用，保留仅用于向后兼容

            # 获取 SSH 主机配置
            host_name = target.get("host")
            if not host_name:
                return {"success": False, "message": "SSH 主机名称未指定"}

            # 从数据库获取 SSH 主机信息
            db = get_db_session()
            try:
                host_obj = db.query(Host).filter(Host.name == host_name).first()
                if not host_obj:
                    return {"success": False, "message": f"SSH 主机不存在: {host_name}"}

                # 使用 get_host_full 获取解密后的密码和密钥
                from backend.host_manager import HostManager

                host_manager = HostManager()
                host_full = host_manager.get_host_full(host_obj.host_id)

                if not host_full:
                    return {"success": False, "message": f"SSH 主机不存在: {host_name}"}

                # 构建 SSH 主机配置（使用解密后的密码）
                host_config = {
                    "host": host_obj.host,
                    "port": host_obj.port or 22,
                    "username": host_obj.username,
                    "password": host_full.get("password"),  # 已解密
                    "private_key": host_full.get("private_key"),  # 已解密
                    "key_password": host_full.get("key_password"),  # 已解密
                }
            finally:
                db.close()

            # 渲染目标配置
            rendered_target = self.parser.render_target_config(target, context)
            docker_config = rendered_target.get("docker", {})

            logger.info(
                f"[SSH] 主机配置: {host_name} ({host_config['host']}:{host_config['port']})"
            )

            # 获取部署模式
            deploy_mode = docker_config.get("deploy_mode", "docker_run")

            # 使用 SSH 部署执行器执行部署
            result = self.ssh_executor.execute_deploy(
                host_config=host_config,
                docker_config=docker_config,
                deploy_mode=deploy_mode,
            )

            # 统一结果格式：添加主机类型和部署方法标识
            result["host_type"] = "ssh"
            result["deploy_method"] = "ssh_direct"
            result["host_name"] = host_name

            logger.info(f"[SSH] 部署结果: {result}")

            # 更新任务状态（统一格式）
            status_msg = result.get(
                "message", "部署成功" if result.get("success") else "部署失败"
            )

            # 构建详细的状态消息（包含错误详情）
            if not result.get("success"):
                error_detail = result.get("error", "")
                output_detail = result.get("output", "")
                if error_detail:
                    status_msg = f"{status_msg}\n错误详情: {error_detail[:500]}"
                elif output_detail:
                    status_msg = f"{status_msg}\n输出: {output_detail[:500]}"

            if result.get("success"):
                logger.info(
                    f"[SSH] 部署成功: task_id={task_id}, target={target.get('name')}, host={host_name}"
                )
            else:
                # 记录完整的错误信息
                error_info = {
                    "message": result.get("message", "部署失败"),
                    "error": result.get("error", ""),
                    "output": result.get("output", ""),
                    "exit_status": result.get("exit_status", ""),
                    "command": result.get("command", ""),
                }
                logger.error(
                    f"[SSH] 部署失败: task_id={task_id}, target={target.get('name')}, host={host_name}, details={error_info}"
                )

            return result

        except Exception as e:
            import traceback

            error_msg = f"SSH 部署失败: {str(e)}"
            logger.exception(
                f"[SSH] 部署异常: task_id={task_id}, target={target.get('name')}"
            )
            traceback.print_exc()

            # 返回错误结果
            error_result = {
                "success": False,
                "message": error_msg,
                "host_type": "ssh",
                "deploy_method": "ssh_direct",
                "error": str(e),
            }

            return error_result

    async def _execute_portainer_target(
        self,
        agent_host: Dict[str, Any],
        task_id: str,
        docker_config: Dict[str, Any],
        context: Dict[str, Any],
        target_name: str,
    ) -> Dict[str, Any]:
        """
        执行 Portainer 目标部署

        Args:
            agent_host: Portainer 主机信息
            task_id: 任务ID
            docker_config: Docker 配置
            context: 模板变量上下文
            target_name: 目标名称

        Returns:
            执行结果字典
        """
        from backend.portainer_client import PortainerClient

        logger.info(
            f"[Portainer] 开始执行 Portainer 部署任务: task_id={task_id}, target={target_name}, host={agent_host.get('name')}"
        )

        try:
            # 注意：此方法已不再使用，保留仅用于向后兼容
            # 从数据库获取完整的 Portainer 信息（包括 API Key）
            db = get_db_session()
            try:
                host_obj = (
                    db.query(AgentHost)
                    .filter(AgentHost.host_id == agent_host.get("host_id"))
                    .first()
                )
                if not host_obj or not host_obj.portainer_api_key:
                    return {
                        "success": False,
                        "message": "Portainer API Key 未配置",
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": agent_host.get("name"),
                    }
                portainer_api_key = host_obj.portainer_api_key
            finally:
                db.close()

            # 创建 Portainer 客户端
            logger.info(
                f"[Portainer] 创建 Portainer 客户端: URL={agent_host.get('portainer_url')}, EndpointID={agent_host.get('portainer_endpoint_id')}"
            )

            client = PortainerClient(
                agent_host.get("portainer_url"),
                portainer_api_key,
                agent_host.get("portainer_endpoint_id"),
            )

            deploy_mode = docker_config.get("deploy_mode", "docker_run")
            redeploy = docker_config.get("redeploy", False)

            logger.info(f"部署模式: {deploy_mode}, 重新发布: {redeploy}")

            # 如果需要重新发布，先清理
            if redeploy:
                logger.info(f"开始清理已有部署...")
                if deploy_mode == "docker_compose":
                    # 尝试删除 Stack
                    stack_name = docker_config.get("stack_name") or (
                        f"{context.get('app', {}).get('name', 'app')}-{target_name}"
                    )
                    try:
                        client._request(
                            "DELETE",
                            f"/stacks",
                            params={
                                "endpointId": agent_host.get("portainer_endpoint_id"),
                                "name": stack_name,
                            },
                        )
                    except:
                        pass
                else:
                    # 尝试删除容器
                    container_name = docker_config.get("container_name", "")
                    if container_name:
                        # 从命令中提取容器名
                        command = docker_config.get("command", "")
                        if command and "--name" in command:
                            import shlex

                            cmd_parts = shlex.split(command)
                            name_idx = cmd_parts.index("--name")
                            if name_idx + 1 < len(cmd_parts):
                                container_name = cmd_parts[name_idx + 1]

                        try:
                            client.remove_container(container_name, force=True)
                            logger.info(f"已删除容器: {container_name}")
                        except Exception as e:
                            logger.warning(f"删除容器失败（可能不存在）: {e}")

            # 执行部署
            logger.info(f"开始执行部署: mode={deploy_mode}")

            if deploy_mode == "docker_compose":
                # Docker Compose 部署
                stack_name = docker_config.get("stack_name") or (
                    f"{context.get('app', {}).get('name', 'app')}-{target_name}"
                )
                compose_content = docker_config.get("compose_content", "")

                if not compose_content:
                    return {
                        "success": False,
                        "message": "Docker Compose 模式需要提供 compose_content",
                    }

                logger.info(f"部署 Docker Compose Stack: {stack_name}")

                # 使用重试机制执行部署（Portainer 可能不稳定）
                result = None
                max_retries = 3
                last_error = None

                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            wait_time = attempt * 2  # 2秒, 4秒
                            logger.info(
                                f"第 {attempt + 1} 次尝试部署 Stack（等待 {wait_time} 秒后重试）..."
                            )
                            import asyncio

                            await asyncio.sleep(wait_time)

                        result = client.deploy_stack(stack_name, compose_content)
                        logger.info(f"Docker Compose 部署结果: {result}")
                        break  # 成功，退出重试循环

                    except Exception as e:
                        last_error = str(e)
                        error_msg = last_error.lower()

                        # 如果是连接重置错误，可以重试
                        if (
                            "connection reset" in error_msg
                            or "connection aborted" in error_msg
                        ):
                            if attempt < max_retries - 1:
                                logger.warning(
                                    f"Stack 部署时连接被重置（尝试 {attempt + 1}/{max_retries}）: {e}"
                                )
                                continue  # 继续重试
                            else:
                                # 最后一次重试也失败
                                logger.error(
                                    f"Stack 部署失败（{max_retries}次重试后）: {e}"
                                )
                                result = {
                                    "success": False,
                                    "message": f"Stack 部署失败：连接被重置（已重试 {max_retries} 次），可能是 Portainer 服务器不稳定或网络问题",
                                }
                        else:
                            # 其他错误，不重试
                            logger.error(
                                f"[Portainer] Stack 部署失败（不可重试的错误）: {e}"
                            )
                            result = {
                                "success": False,
                                "message": f"Stack 部署失败: {last_error}",
                                "host_type": "portainer",
                                "deploy_method": "portainer_api",
                                "host_name": target_name,
                            }
                            break

                if result is None:
                    result = {
                        "success": False,
                        "message": f"Stack 部署失败: {last_error or '未知错误'}",
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": target_name,
                    }

                # 统一结果格式
                if result:
                    result.setdefault("host_type", "portainer")
                    result.setdefault("deploy_method", "portainer_api")
                    result.setdefault("host_name", target_name)

                # 记录日志
                if result.get("success"):
                    logger.info(
                        f"[Portainer] Stack 部署成功: task_id={task_id}, target={target_name}"
                    )
                else:
                    logger.error(
                        f"[Portainer] Stack 部署失败: task_id={task_id}, target={target_name}, error={result.get('message')}"
                    )

                return result
            else:
                # Docker Run 部署
                container_name = docker_config.get(
                    "container_name",
                    f"{context.get('app', {}).get('name', 'app')}-{target_name}",
                )
                image_template = docker_config.get("image_template", "")

                # 渲染镜像名称
                if image_template:
                    image = image_template
                    for key, value in context.items():
                        placeholder = f"{{{{ {key} }}}}"
                        image = image.replace(placeholder, str(value))
                else:
                    image = ""

                if not image:
                    # 尝试从命令中提取镜像
                    command = docker_config.get("command", "")
                    if command:
                        import shlex
                        import re

                        # 处理多行命令和反斜杠续行符
                        command = re.sub(r"\\\s*\n\s*", " ", command)
                        command = re.sub(r"\\\\\s*\n\s*", " ", command)
                        command = re.sub(r"\s+", " ", command).strip()
                        cmd_parts = shlex.split(command)
                        # 镜像通常是最后一个参数
                        image = cmd_parts[-1] if cmd_parts else ""

                if not image:
                    error_msg = "无法确定镜像名称"
                    logger.error(error_msg)
                    error_result = {
                        "success": False,
                        "message": error_msg,
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": target_name,
                    }
                    return error_result

                logger.info(
                    f"[Portainer] 部署 Docker 容器: name={container_name}, image={image}"
                )

                # 解析命令参数
                command = docker_config.get("command", "")
                # 如果提供了 command，优先使用 command 中的参数
                # 否则使用单独的配置项
                if command:
                    # command 中已经包含了所有参数（-e, -v, -p 等），不需要额外传递
                    ports = None
                    env = None
                    volumes = None
                    restart_policy = None  # 会从 command 中解析
                else:
                    # 没有 command，使用配置项
                    ports = docker_config.get("ports", [])
                    env = docker_config.get("env", [])
                    volumes = docker_config.get("volumes", [])
                    restart_policy = docker_config.get("restart_policy", "always")

                # 使用重试机制执行部署（Portainer 可能不稳定）
                result = None
                max_retries = 3
                last_error = None

                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            wait_time = attempt * 2  # 2秒, 4秒
                            logger.info(
                                f"第 {attempt + 1} 次尝试部署（等待 {wait_time} 秒后重试）..."
                            )
                            import asyncio

                            await asyncio.sleep(wait_time)

                        result = client.deploy_container(
                            container_name,
                            image,
                            command=command if command else None,
                            ports=ports,
                            env=env,
                            volumes=volumes,
                            restart_policy=restart_policy,
                        )

                        logger.info(f"Docker Run 部署结果: {result}")
                        break  # 成功，退出重试循环

                    except Exception as e:
                        last_error = str(e)
                        error_msg = last_error.lower()

                        # 如果是连接重置错误，可以重试
                        if (
                            "connection reset" in error_msg
                            or "connection aborted" in error_msg
                        ):
                            if attempt < max_retries - 1:
                                logger.warning(
                                    f"[Portainer] 部署时连接被重置（尝试 {attempt + 1}/{max_retries}）: {e}"
                                )
                                continue  # 继续重试
                            else:
                                # 最后一次重试也失败
                                logger.error(
                                    f"[Portainer] 部署失败（{max_retries}次重试后）: {e}"
                                )
                                result = {
                                    "success": False,
                                    "message": f"部署失败：连接被重置（已重试 {max_retries} 次），可能是 Portainer 服务器不稳定或网络问题",
                                    "host_type": "portainer",
                                    "deploy_method": "portainer_api",
                                    "host_name": target_name,
                                }
                        else:
                            # 其他错误，不重试
                            logger.error(f"[Portainer] 部署失败（不可重试的错误）: {e}")
                            result = {
                                "success": False,
                                "message": f"部署失败: {last_error}",
                                "host_type": "portainer",
                                "deploy_method": "portainer_api",
                                "host_name": target_name,
                            }
                            break

                if result is None:
                    result = {
                        "success": False,
                        "message": f"部署失败: {last_error or '未知错误'}",
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": target_name,
                    }

            # 统一结果格式：添加主机类型和部署方法标识
            if result:
                result.setdefault("host_type", "portainer")
                result.setdefault("deploy_method", "portainer_api")
                result.setdefault("host_name", target_name)

            # 记录日志
            if result.get("success"):
                logger.info(
                    f"[Portainer] 部署成功: task_id={task_id}, target={target_name}"
                )
            else:
                logger.error(
                    f"[Portainer] 部署失败: task_id={task_id}, target={target_name}, error={result.get('message')}"
                )

            return result

        except Exception as e:
            import traceback

            error_msg = f"Portainer 部署失败: {str(e)}"
            logger.exception(
                f"Portainer 部署失败: task_id={task_id}, target={target_name}"
            )
            traceback.print_exc()

            return {"success": False, "message": error_msg}

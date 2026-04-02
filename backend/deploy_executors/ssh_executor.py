# backend/deploy_executors/ssh_executor.py
"""
SSH 主机执行器
通过 SSH 连接执行部署命令
"""
import asyncio
import logging
import shlex
from typing import Dict, Any, Optional, Callable

from backend.deploy_executors.base import DeployExecutor
from backend.ssh_deploy_executor import SSHDeployExecutor
from backend.database import get_db_session
from backend.models import Host

logger = logging.getLogger(__name__)


class SSHExecutor(DeployExecutor):
    """SSH 主机执行器"""

    def __init__(self, host_info: Dict[str, Any]):
        """
        初始化 SSH 执行器

        Args:
            host_info: 主机信息字典，必须包含：
                - name: 主机名称（用于从数据库查询）
        """
        super().__init__(host_info)
        self.host_name = host_info.get("name")
        if not self.host_name:
            raise ValueError("host_info 必须包含 name")

        self.ssh_executor = SSHDeployExecutor()
        self._host_config = None

    def _get_host_config(self) -> Dict[str, Any]:
        """
        从数据库获取SSH主机配置

        Returns:
            SSH主机配置字典
        """
        if self._host_config is not None:
            return self._host_config

        db = get_db_session()
        try:
            host_obj = db.query(Host).filter(Host.name == self.host_name).first()
            if not host_obj:
                raise ValueError(f"SSH 主机不存在: {self.host_name}")

            # 使用 get_host_full 获取解密后的密码和密钥
            from backend.host_manager import HostManager

            host_manager = HostManager()
            host_full = host_manager.get_host_full(host_obj.host_id)  # 使用 host_id

            if not host_full:
                raise ValueError(f"SSH 主机不存在: {self.host_name}")

            self._host_config = {
                "host": host_obj.host,
                "port": host_obj.port or 22,
                "username": host_obj.username,
                "password": host_full.get("password"),  # 已解密
                "private_key": host_full.get("private_key"),  # 已解密
                "key_password": host_full.get("key_password"),  # 已解密
            }

            return self._host_config
        finally:
            db.close()

    def can_execute(self) -> bool:
        """
        检查是否可以执行

        Returns:
            是否可以执行（主机是否存在）
        """
        try:
            self._get_host_config()
            return True
        except:
            return False

    async def execute(
        self,
        deploy_config: Dict[str, Any],
        task_id: str,
        target_name: str,
        context: Optional[Dict[str, Any]] = None,
        update_status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        执行部署任务（通过 SSH）

        Args:
            deploy_config: 部署配置（已适配的命令/脚本）
            task_id: 任务ID
            target_name: 目标名称
            context: 模板变量上下文（可选）
            update_status_callback: 状态更新回调函数（可选）

        Returns:
            执行结果字典
        """
        logger.info(
            f"[SSH] 开始执行 SSH 部署任务: task_id={task_id}, target={target_name}, host={self.host_name}"
        )

        try:
            if update_status_callback:
                update_status_callback("[SSH] 正在连接 SSH 主机...")

            host_config = self._get_host_config()

            logger.info(
                f"[SSH] 主机配置: {self.host_name} ({host_config['host']}:{host_config['port']})"
            )

            # 检查是否为多步骤模式
            steps = deploy_config.get("steps")
            if steps and isinstance(steps, list):
                # 多步骤模式：依次执行每个步骤
                if update_status_callback:
                    update_status_callback(
                        f"[SSH] 开始执行多步骤部署，共 {len(steps)} 个步骤..."
                    )

                result = self._execute_multi_steps(
                    host_config=host_config,
                    steps=steps,
                    redeploy=deploy_config.get("redeploy", False),
                    update_status_callback=update_status_callback,
                )
            else:
                # 单命令模式：使用原有的执行逻辑
                deploy_mode = deploy_config.get("deploy_mode", "docker_run")

                # 记录命令信息
                if update_status_callback:
                    command = deploy_config.get("command", "")
                    compose_content = deploy_config.get("compose_content", "")
                    compose_mode = deploy_config.get("compose_mode", "docker-compose")

                    if deploy_mode == "docker_compose":
                        if command:
                            if compose_mode == "docker-stack":
                                update_status_callback(
                                    f"[SSH] 执行命令: docker stack deploy {command}"
                                )
                            else:
                                update_status_callback(
                                    f"[SSH] 执行命令: docker-compose {command}"
                                )
                        if compose_content:
                            compose_preview = compose_content.split("\n")[:5]
                            update_status_callback(
                                f"[SSH] docker-compose.yml 内容预览:\n"
                                + "\n".join([f"  {line}" for line in compose_preview])
                            )
                    else:
                        if command:
                            update_status_callback(
                                f"[SSH] 执行命令: docker run {command}"
                            )
                    update_status_callback(f"[SSH] 正在执行部署到 {self.host_name}...")

                # 使用 SSH 部署执行器执行部署
                result = self.ssh_executor.execute_deploy(
                    host_config=host_config,
                    docker_config=deploy_config,
                    deploy_mode=deploy_mode,
                )

            # 统一结果格式：添加主机类型和部署方法标识
            result["host_type"] = "ssh"
            result["deploy_method"] = "ssh_direct"
            result["host_name"] = self.host_name

            logger.info(f"[SSH] 部署结果: {result}")

            return result

        except Exception as e:
            import traceback

            error_msg = f"SSH 部署失败: {str(e)}"
            logger.exception(f"[SSH] 部署异常: task_id={task_id}, target={target_name}")
            traceback.print_exc()

            return {
                "success": False,
                "message": error_msg,
                "host_type": "ssh",
                "deploy_method": "ssh_direct",
                "error": str(e),
            }

    def _execute_multi_steps(
        self,
        host_config: Dict[str, Any],
        steps: list,
        redeploy: bool = False,
        update_status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        执行多步骤部署

        Args:
            host_config: SSH主机配置
            steps: 步骤列表，每个步骤包含 name 和 command
            redeploy: 是否重新部署
            update_status_callback: 状态更新回调函数

        Returns:
            执行结果字典
        """
        import paramiko
        from io import StringIO

        try:
            # 创建 SSH 客户端
            ssh_client = self.ssh_executor._create_ssh_client(
                host=host_config.get("host"),
                port=host_config.get("port", 22),
                username=host_config.get("username"),
                password=host_config.get("password"),
                private_key=host_config.get("private_key"),
                key_password=host_config.get("key_password"),
            )

            try:
                all_outputs = []
                failed_step = None

                for idx, step in enumerate(steps, 1):
                    step_name = step.get("name", f"步骤 {idx}")
                    step_command = step.get("command", "").strip()

                    if not step_command:
                        logger.warning(f"步骤 {idx} ({step_name}) 的命令为空，跳过")
                        continue

                    if update_status_callback:
                        update_status_callback(
                            f"[步骤 {idx}/{len(steps)}] {step_name}: {step_command}"
                        )

                    logger.info(
                        f"[SSH] 执行步骤 {idx}/{len(steps)}: {step_name} - {step_command}"
                    )

                    # 执行命令
                    stdin, stdout, stderr = ssh_client.exec_command(step_command)
                    exit_status = stdout.channel.recv_exit_status()
                    stdout_text = stdout.read().decode("utf-8", errors="ignore")
                    stderr_text = stderr.read().decode("utf-8", errors="ignore")

                    step_output = {
                        "step": idx,
                        "name": step_name,
                        "command": step_command,
                        "exit_status": exit_status,
                        "stdout": stdout_text,
                        "stderr": stderr_text,
                    }
                    all_outputs.append(step_output)

                    # 记录日志
                    logger.info(f"[SSH] 步骤 {idx} 执行完成: exit_status={exit_status}")
                    if stdout_text:
                        logger.info(f"[SSH] 步骤 {idx} stdout: {stdout_text[:200]}")
                    if stderr_text:
                        logger.warning(f"[SSH] 步骤 {idx} stderr: {stderr_text[:200]}")

                    # 如果步骤失败，检查错误类型
                    if exit_status != 0:
                        error_text = stderr_text.lower() if stderr_text else ""
                        stdout_lower = stdout_text.lower() if stdout_text else ""

                        # 对于某些命令（如 docker kill、stop、rm），失败是可以接受的
                        if (
                            "kill" in step_command.lower()
                            or "stop" in step_command.lower()
                            or "rm" in step_command.lower()
                        ):
                            logger.info(f"[SSH] 步骤 {idx} 失败但可接受（清理操作）")
                        # 检查是否是容器名称冲突错误
                        elif (
                            "container name" in error_text
                            and "already in use" in error_text
                        ):
                            logger.warning(
                                f"[SSH] 步骤 {idx} 检测到容器名称冲突，尝试自动清理..."
                            )

                            # 尝试从错误信息中提取容器名称
                            import re

                            container_name_match = re.search(
                                r'container name[^"]*"([^"]+)"', error_text
                            )
                            if not container_name_match:
                                # 尝试从命令中提取容器名称
                                name_match = re.search(
                                    r"--name[=\s]+([^\s]+)", step_command
                                )
                                if name_match:
                                    container_name = name_match.group(1)
                                else:
                                    container_name = None
                            else:
                                container_name = container_name_match.group(1)

                            if container_name:
                                # 尝试删除冲突的容器
                                cleanup_cmd = f"docker rm -f {container_name} || true"
                                logger.info(f"[SSH] 执行清理命令: {cleanup_cmd}")

                                try:
                                    stdin_cleanup, stdout_cleanup, stderr_cleanup = (
                                        ssh_client.exec_command(cleanup_cmd)
                                    )
                                    cleanup_exit = (
                                        stdout_cleanup.channel.recv_exit_status()
                                    )
                                    cleanup_output = stdout_cleanup.read().decode(
                                        "utf-8", errors="ignore"
                                    )
                                    logger.info(
                                        f"[SSH] 清理命令执行结果: exit_status={cleanup_exit}, output={cleanup_output}"
                                    )

                                    if update_status_callback:
                                        update_status_callback(
                                            f"[自动清理] 已删除冲突容器 {container_name}，重新执行步骤 {idx}..."
                                        )

                                    # 重新执行失败的步骤
                                    logger.info(
                                        f"[SSH] 重新执行步骤 {idx}: {step_command}"
                                    )
                                    stdin_retry, stdout_retry, stderr_retry = (
                                        ssh_client.exec_command(step_command)
                                    )
                                    retry_exit_status = (
                                        stdout_retry.channel.recv_exit_status()
                                    )
                                    retry_stdout_text = stdout_retry.read().decode(
                                        "utf-8", errors="ignore"
                                    )
                                    retry_stderr_text = stderr_retry.read().decode(
                                        "utf-8", errors="ignore"
                                    )

                                    # 更新步骤输出
                                    step_output = {
                                        "step": idx,
                                        "name": step_name,
                                        "command": step_command,
                                        "exit_status": retry_exit_status,
                                        "stdout": retry_stdout_text,
                                        "stderr": retry_stderr_text,
                                        "auto_cleaned": True,
                                        "cleanup_command": cleanup_cmd,
                                    }
                                    all_outputs[-1] = step_output  # 替换之前的输出

                                    if retry_exit_status != 0:
                                        logger.error(
                                            f"[SSH] 步骤 {idx} 重试后仍然失败: exit_status={retry_exit_status}"
                                        )
                                        failed_step = step_output
                                        break
                                    else:
                                        logger.info(f"[SSH] 步骤 {idx} 重试后成功")
                                        continue
                                except Exception as cleanup_error:
                                    logger.error(f"[SSH] 自动清理失败: {cleanup_error}")
                                    failed_step = step_output
                                    break
                            else:
                                logger.warning(f"[SSH] 无法从错误信息中提取容器名称")
                                failed_step = step_output
                                break
                        else:
                            # 其他类型的错误，停止执行
                            logger.error(
                                f"[SSH] 步骤 {idx} ({step_name}) 执行失败: exit_status={exit_status}"
                            )
                            failed_step = step_output
                            break

                # 关闭SSH连接
                ssh_client.close()

                # 构建结果
                if failed_step:
                    error_msg = (
                        f"步骤 {failed_step['step']} ({failed_step['name']}) 执行失败"
                    )
                    if failed_step["stderr"]:
                        error_msg += f": {failed_step['stderr'].strip()}"

                    return {
                        "success": False,
                        "message": error_msg,
                        "output": "\n".join(
                            [
                                f"[步骤 {o['step']}] {o['name']}\n{o['stdout']}"
                                for o in all_outputs
                            ]
                        ),
                        "error": failed_step["stderr"],
                        "exit_status": failed_step["exit_status"],
                        "steps": all_outputs,
                    }
                else:
                    return {
                        "success": True,
                        "message": f"多步骤部署成功，共执行 {len(steps)} 个步骤",
                        "output": "\n".join(
                            [
                                f"[步骤 {o['step']}] {o['name']}\n{o['stdout']}"
                                for o in all_outputs
                            ]
                        ),
                        "steps": all_outputs,
                    }

            except Exception as e:
                ssh_client.close()
                raise

        except Exception as e:
            import traceback

            error_msg = f"多步骤部署失败: {str(e)}"
            logger.exception(f"[SSH] 多步骤部署异常: {error_msg}")
            return {"success": False, "message": error_msg, "error": str(e)}

    async def check_deploy_status(
        self,
        deploy_config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """SSH 上执行 docker inspect / 解析 compose 中的容器名做检查。"""
        ctx = context or {}
        out: Dict[str, Any] = {
            "success": False,
            "checked": True,
            "message": "",
            "host_type": "ssh",
            "deploy_method": "ssh_direct",
            "host_name": self.host_name,
        }
        if not self.can_execute():
            out["checked"] = False
            out["message"] = "SSH 主机不可用"
            return out

        if deploy_config.get("steps"):
            out["message"] = "多步骤 SSH 部署无法自动确认状态"
            return out

        def _remote_inspect_container(ssh_client, container_name: str) -> Dict[str, Any]:
            qname = shlex.quote(container_name)
            cmd = (
                "docker inspect -f '{{.State.Running}}|{{.State.ExitCode}}|{{.State.Status}}' "
                + qname
            )
            stdin, stdout, stderr = ssh_client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            so = stdout.read().decode("utf-8", errors="ignore").strip()
            se = stderr.read().decode("utf-8", errors="ignore").strip()
            if exit_status != 0:
                return {
                    "exists": False,
                    "success": False,
                    "message": f"容器不存在或 inspect 失败: {container_name} ({se or so})",
                }
            parts = so.split("|", 2)
            running = (parts[0].strip().lower() == "true") if parts else False
            try:
                ec = int(parts[1].strip()) if len(parts) > 1 else 0
            except ValueError:
                ec = -1
            status_s = parts[2].strip() if len(parts) > 2 else ""
            if running:
                return {
                    "exists": True,
                    "success": True,
                    "running": True,
                    "message": f"容器运行中: {container_name} ({status_s})",
                }
            if ec == 0:
                return {
                    "exists": True,
                    "success": True,
                    "message": f"容器已退出(0): {container_name}",
                }
            return {
                "exists": True,
                "success": False,
                "message": f"容器未运行或异常退出: {container_name}, exit={ec}",
            }

        def _sync_check() -> Dict[str, Any]:
            host_config = self._get_host_config()
            ssh_client = self.ssh_executor._create_ssh_client(
                host=host_config.get("host"),
                port=host_config.get("port", 22),
                username=host_config.get("username"),
                password=host_config.get("password"),
                private_key=host_config.get("private_key"),
                key_password=host_config.get("key_password"),
            )
            try:
                deploy_mode = deploy_config.get("deploy_mode", "docker_run")
                if deploy_mode == "docker_run":
                    name = (deploy_config.get("container_name") or "").strip()
                    if not name:
                        cmd_str = (deploy_config.get("command") or "").strip()
                        if cmd_str:
                            import re

                            cmd_str = re.sub(r"\\\s*\n\s*", " ", cmd_str)
                            cmd_str = re.sub(r"\s+", " ", cmd_str).strip()
                            try:
                                parts = shlex.split(cmd_str)
                            except ValueError:
                                parts = cmd_str.split()
                            if "--name" in parts:
                                ni = parts.index("--name")
                                if ni + 1 < len(parts):
                                    name = parts[ni + 1]
                    if not name:
                        return {**out, "message": "无法解析 SSH docker run 容器名"}
                    r = _remote_inspect_container(ssh_client, name)
                    return {**out, **r}

                if deploy_mode == "docker_compose":
                    import yaml

                    content = deploy_config.get("compose_content") or ""
                    names: list = []
                    try:
                        cfg = yaml.safe_load(content) if content else None
                        if isinstance(cfg, dict):
                            for _, svc in (cfg.get("services") or {}).items():
                                if isinstance(svc, dict) and svc.get("container_name"):
                                    names.append(str(svc["container_name"]))
                    except Exception as e:
                        logger.debug("解析 compose_content 失败: %s", e)
                    if not names:
                        return {
                            **out,
                            "message": "SSH Compose 无法从 compose 解析 container_name，无法自动检查",
                        }
                    worst = {"success": True, "message": ""}
                    msgs = []
                    for n in names:
                        r = _remote_inspect_container(ssh_client, n)
                        msgs.append(r.get("message", ""))
                        if not r.get("success"):
                            worst["success"] = False
                    worst["message"] = "; ".join(msgs)
                    return {**out, **worst}

                return {**out, "message": f"不支持的 SSH 部署模式: {deploy_mode}"}
            finally:
                try:
                    ssh_client.close()
                except Exception:
                    pass

        return await asyncio.to_thread(_sync_check)

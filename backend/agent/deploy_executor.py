# backend/agent/deploy_executor.py
"""
部署执行器
负责解析 YAML 部署配置，执行 docker run 或 docker-compose 部署
"""
import os
import re
import json
import subprocess
import yaml
import logging
import shlex
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DeployExecutor:
    """部署执行器"""

    def __init__(self, work_dir: str = "/tmp/app2docker-deploy"):
        """
        初始化部署执行器

        Args:
            work_dir: 工作目录，用于存储临时文件（如 docker-compose.yml）
        """
        self.work_dir = work_dir
        os.makedirs(work_dir, exist_ok=True)

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        渲染模板字符串（支持 {{ variable }} 格式）

        Args:
            template: 模板字符串
            context: 变量上下文

        Returns:
            渲染后的字符串
        """
        result = template
        for key, value in context.items():
            placeholder = f"{{{{ {key} }}}}"
            result = result.replace(placeholder, str(value))
        return result

    def _cleanup_existing_deployment(
        self, docker_config: Dict[str, Any], deploy_mode: str, context: Dict[str, Any]
    ) -> None:
        """
        清理已有的部署（停止并删除容器或服务）

        Args:
            docker_config: Docker 配置
            deploy_mode: 部署模式
            context: 模板变量上下文
        """
        try:
            if deploy_mode == "docker_compose":
                # Docker Compose 模式：根据 compose_mode 和 redeploy_strategy 处理
                compose_mode = docker_config.get("compose_mode", "docker-compose")
                redeploy_strategy = docker_config.get(
                    "redeploy_strategy", "update_existing"
                )

                # 只有在 remove_and_redeploy 策略时才执行清理
                if redeploy_strategy != "remove_and_redeploy":
                    logger.info(f"重新发布策略为 {redeploy_strategy}，跳过清理步骤")
                    return

                if "compose_content" in docker_config:
                    task_id = context.get("task_id", "default")
                    compose_file = os.path.join(
                        self.work_dir, f"docker-compose-{task_id}.yml"
                    )

                    # 如果文件不存在，先创建它（用于 down/rm 命令）
                    if not os.path.exists(compose_file):
                        with open(compose_file, "w", encoding="utf-8") as f:
                            f.write(docker_config["compose_content"])

                    if compose_mode == "docker-stack":
                        # Docker Stack 模式：删除 Stack
                        app_name = (
                            context.get("app", {}).get("name", "app")
                            if isinstance(context.get("app"), dict)
                            else "app"
                        )
                        stack_name = f"{app_name}-{task_id}"
                        # 确保 Stack 名称符合 Docker Stack 命名规范
                        import re

                        stack_name = re.sub(r"[^a-z0-9-]", "-", stack_name.lower())

                        cmd = ["docker", "stack", "rm", stack_name]
                        logger.info(f"清理已有 Stack: {' '.join(cmd)}")
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=60
                        )
                        if result.stdout:
                            logger.info(f"清理输出: {result.stdout}")
                        if result.returncode == 0:
                            logger.info(f"已删除 Stack: {stack_name}")
                        else:
                            logger.warning(f"删除 Stack 时出现警告: {result.stderr}")
                        # 等待 Stack 完全删除
                        import time

                        time.sleep(2)
                    else:
                        # Docker Compose 模式：执行 down 命令
                        cmd = ["docker-compose", "-f", compose_file, "down", "-v"]
                        logger.info(f"清理已有部署: {' '.join(cmd)}")
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=60
                        )
                        if result.stdout:
                            logger.info(f"清理输出: {result.stdout}")
                        if result.returncode == 0:
                            logger.info("已停止并删除已有的 Docker Compose 服务")
                        else:
                            logger.warning(
                                f"清理 Docker Compose 服务时出现警告: {result.stderr}"
                            )
                else:
                    # 如果没有 compose_content，尝试从命令中提取服务名
                    command_str = docker_config.get("command", "").strip()
                    if command_str:
                        import shlex

                        cmd_parts = shlex.split(command_str)
                        # 尝试找到服务名（通常在 up 命令之后）
                        if "up" in cmd_parts:
                            up_idx = cmd_parts.index("up")
                            if up_idx + 1 < len(cmd_parts):
                                service_name = cmd_parts[up_idx + 1]
                                cmd = ["docker-compose", "stop", service_name]
                                subprocess.run(cmd, capture_output=True, timeout=30)
                                cmd = ["docker-compose", "rm", "-f", service_name]
                                subprocess.run(cmd, capture_output=True, timeout=30)
            else:
                # Docker Run 模式：从命令中提取容器名并删除
                command_str = docker_config.get("command", "").strip()
                if not command_str:
                    # 尝试从配置中获取容器名
                    container_name = docker_config.get("container_name", "")
                    if container_name:
                        container_name = self._render_template(container_name, context)
                    else:
                        return
                else:
                    # 从命令中提取容器名（--name 参数）
                    import shlex

                    cmd_parts = shlex.split(command_str)
                    container_name = None

                    # 支持两种格式：--name test 或 --name=test
                    if "--name" in cmd_parts:
                        name_idx = cmd_parts.index("--name")
                        if name_idx + 1 < len(cmd_parts):
                            container_name = cmd_parts[name_idx + 1]
                    else:
                        # 检查 --name=value 格式
                        for part in cmd_parts:
                            if part.startswith("--name="):
                                container_name = part.split("=", 1)[1]
                                break

                    if not container_name:
                        logger.warning(f"无法从命令中提取容器名: {command_str}")
                        return

                    logger.info(f"从命令中提取到容器名: {container_name}")

                # 停止并删除容器
                logger.info(f"清理已有容器: {container_name}")

                # 停止容器
                stop_cmd = ["docker", "stop", container_name]
                logger.info(f"执行命令: {' '.join(stop_cmd)}")
                stop_result = subprocess.run(
                    stop_cmd, capture_output=True, text=True, timeout=30
                )
                if stop_result.stdout:
                    logger.info(f"停止容器输出: {stop_result.stdout}")
                if stop_result.stderr:
                    logger.warning(f"停止容器警告: {stop_result.stderr}")

                # 删除容器（无论停止是否成功）
                rm_cmd = ["docker", "rm", "-f", container_name]
                logger.info(f"执行命令: {' '.join(rm_cmd)}")
                rm_result = subprocess.run(
                    rm_cmd, capture_output=True, text=True, timeout=30
                )
                if rm_result.stdout:
                    logger.info(f"删除容器输出: {rm_result.stdout}")

                if rm_result.returncode == 0:
                    logger.info(f"已删除容器: {container_name}")
                else:
                    logger.warning(f"删除容器时出现警告: {rm_result.stderr}")

        except Exception as e:
            logger.warning(f"清理已有部署时出现异常（继续部署）: {str(e)}")
            # 不抛出异常，允许继续部署

    def _build_docker_run_command(
        self, docker_config: Dict[str, Any], context: Dict[str, Any]
    ) -> List[str]:
        """
        构建 docker run 命令

        Args:
            docker_config: Docker 配置
            context: 模板变量上下文

        Returns:
            docker run 命令参数列表
        """
        cmd = ["docker", "run", "-d"]

        # 容器名称
        container_name = self._render_template(
            docker_config.get("container_name", ""), context
        )
        if container_name:
            cmd.extend(["--name", container_name])

        # 重启策略
        restart_policy = docker_config.get("restart_policy", "no")
        if restart_policy != "no":
            cmd.extend(["--restart", restart_policy])

        # 端口映射
        ports = docker_config.get("ports", [])
        for port_mapping in ports:
            cmd.extend(["-p", port_mapping])

        # 环境变量
        env_vars = docker_config.get("env", [])
        for env_var in env_vars:
            # 支持模板变量
            env_value = self._render_template(env_var, context)
            cmd.extend(["-e", env_value])

        # 卷映射
        volumes = docker_config.get("volumes", [])
        for volume_mapping in volumes:
            cmd.extend(["-v", volume_mapping])

        # 镜像名称（必须）
        image_template = docker_config.get("image_template", "")
        if not image_template:
            raise ValueError("docker.image_template 是必需的")

        image_name = self._render_template(image_template, context)
        cmd.append(image_name)

        # 命令参数（如果有）
        command = docker_config.get("command")
        if command:
            if isinstance(command, str):
                cmd.extend(command.split())
            elif isinstance(command, list):
                cmd.extend(command)

        return cmd

    def _create_docker_compose_file(
        self, docker_config: Dict[str, Any], context: Dict[str, Any], task_id: str
    ) -> str:
        """
        创建 docker-compose.yml 文件

        Args:
            docker_config: Docker 配置
            context: 模板变量上下文
            task_id: 任务ID（用于生成文件名）

        Returns:
            docker-compose.yml 文件路径
        """
        compose_file = os.path.join(self.work_dir, f"docker-compose-{task_id}.yml")

        # 渲染镜像名称
        image_template = docker_config.get("image_template", "")
        if not image_template:
            raise ValueError("docker.image_template 是必需的")

        image_name = self._render_template(image_template, context)

        # 构建服务配置
        service_config = {
            "image": image_name,
            "container_name": self._render_template(
                docker_config.get("container_name", ""), context
            ),
            "restart": docker_config.get("restart_policy", "no"),
        }

        # 端口映射
        ports = docker_config.get("ports", [])
        if ports:
            service_config["ports"] = ports

        # 环境变量
        env_vars = docker_config.get("env", [])
        if env_vars:
            env_dict = {}
            for env_var in env_vars:
                env_value = self._render_template(env_var, context)
                if "=" in env_value:
                    key, value = env_value.split("=", 1)
                    env_dict[key] = value
                else:
                    env_dict[env_value] = ""
            service_config["environment"] = env_dict

        # 卷映射
        volumes = docker_config.get("volumes", [])
        if volumes:
            service_config["volumes"] = volumes

        # 命令
        command = docker_config.get("command")
        if command:
            if isinstance(command, str):
                service_config["command"] = command.split()
            elif isinstance(command, list):
                service_config["command"] = command

        # 健康检查
        health_check = docker_config.get("health_check")
        if health_check:
            service_config["healthcheck"] = {
                "test": f"curl -f {health_check.get('url', 'http://localhost:8000/health')} || exit 1",
                "interval": "30s",
                "timeout": health_check.get("timeout", "10s"),
                "retries": 3,
                "start_period": "40s",
            }

        # 构建完整的 compose 配置（Docker Compose v2 不再需要 version 字段）
        compose_config = {"services": {"app": service_config}}

        # 写入文件
        with open(compose_file, "w", encoding="utf-8") as f:
            yaml.dump(compose_config, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"创建 docker-compose.yml: {compose_file}")
        return compose_file

    def execute_deploy(
        self,
        deploy_config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        deploy_mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行部署任务

        Args:
            deploy_config: 部署配置（包含 docker 配置）
            context: 模板变量上下文（registry, app.name, tag 等）
            deploy_mode: 部署模式（docker_run 或 docker_compose），如果为 None 则从配置中获取

        Returns:
            执行结果字典
        """
        if context is None:
            context = {}

        # 检查是否有 registry 认证信息，如果有则先执行 docker login
        registry_auth = context.get("registry_auth")
        if registry_auth:
            registry = registry_auth.get("registry")
            username = registry_auth.get("username")
            password = registry_auth.get("password")

            if registry and username and password:
                logger.info(
                    f"执行 docker login: registry={registry}, username={username}"
                )
                try:
                    login_cmd = [
                        "docker",
                        "login",
                        "-u",
                        username,
                        "-p",
                        password,
                        registry,
                    ]
                    login_result = subprocess.run(
                        login_cmd, capture_output=True, text=True, timeout=30
                    )

                    if login_result.returncode != 0:
                        error_msg = (
                            login_result.stderr
                            or login_result.stdout
                            or "Docker login 失败"
                        )
                        logger.error(f"Docker login 失败: {error_msg}")
                        return {
                            "success": False,
                            "message": f"Docker login 失败: {error_msg}",
                            "error": error_msg,
                        }
                    else:
                        logger.info(f"Docker login 成功: {registry}")
                except subprocess.TimeoutExpired:
                    logger.error(f"Docker login 超时: {registry}")
                    return {
                        "success": False,
                        "message": f"Docker login 超时（超过30秒）",
                        "error": "Docker login 超时",
                    }
                except Exception as e:
                    logger.error(f"Docker login 异常: {e}")
                    return {
                        "success": False,
                        "message": f"Docker login 异常: {str(e)}",
                        "error": str(e),
                    }
            else:
                logger.warning(
                    f"Registry 认证信息不完整: registry={registry}, username={username}, password={'已设置' if password else '未设置'}"
                )

        # 兼容两种格式：
        # 1. 新格式：{"docker": {...}}
        # 2. 旧格式：{...} (直接就是docker配置)
        docker_config = deploy_config.get("docker")
        if docker_config is None:
            # 如果没有docker键，说明配置本身就是docker配置
            docker_config = deploy_config

        if not docker_config or not isinstance(docker_config, dict):
            raise ValueError("部署配置中缺少 docker 配置")

        if deploy_mode is None:
            deploy_mode = docker_config.get("deploy_mode", "docker_run")

        # 检查是否需要重新发布
        redeploy = docker_config.get("redeploy", False)
        redeploy_strategy = docker_config.get("redeploy_strategy", "update_existing")

        logger.info(
            f"redeploy 配置: {redeploy}, redeploy_strategy: {redeploy_strategy}, deploy_mode: {deploy_mode}"
        )

        try:
            # 如果需要重新发布且策略为 remove_and_redeploy，先停止并删除已有的容器/服务
            if redeploy and redeploy_strategy == "remove_and_redeploy":
                logger.info("开始清理已有部署（策略: remove_and_redeploy）...")
                self._cleanup_existing_deployment(docker_config, deploy_mode, context)
                logger.info("清理已有部署完成")

            # 检查是否有直接命令（用户输入的原始命令）
            if "command" in docker_config:
                # 直接执行用户输入的命令
                command_str = docker_config.get("command", "").strip()
                if not command_str:
                    raise ValueError("命令不能为空")

                if deploy_mode == "docker_compose":
                    # Docker Compose 模式：需要先创建 compose 文件
                    if "compose_content" in docker_config:
                        compose_mode = docker_config.get(
                            "compose_mode", "docker-compose"
                        )
                        task_id = context.get("task_id", "default")
                        compose_file = os.path.join(
                            self.work_dir, f"docker-compose-{task_id}.yml"
                        )

                        # 写入 compose 内容
                        with open(compose_file, "w", encoding="utf-8") as f:
                            f.write(docker_config["compose_content"])

                        logger.info(f"创建 docker-compose.yml: {compose_file}")

                        if compose_mode == "docker-stack":
                            # Docker Stack 模式：使用 docker stack deploy
                            app_name = (
                                context.get("app", {}).get("name", "app")
                                if isinstance(context.get("app"), dict)
                                else "app"
                            )
                            stack_name = f"{app_name}-{task_id}"
                            # 确保 Stack 名称符合 Docker Stack 命名规范
                            import re

                            stack_name = re.sub(r"[^a-z0-9-]", "-", stack_name.lower())

                            # 解析命令（可能包含 -c 或 --compose-file 参数）
                            import shlex

                            cmd_parts = shlex.split(command_str) if command_str else []

                            # 构建 docker stack deploy 命令
                            # 格式：docker stack deploy -c <compose-file> <stack-name> [OPTIONS]
                            if command_str:
                                # 如果命令中包含 -c 或 --compose-file，使用用户提供的命令
                                if "-c" in cmd_parts or "--compose-file" in cmd_parts:
                                    cmd = (
                                        ["docker", "stack", "deploy"]
                                        + cmd_parts
                                        + [stack_name]
                                    )
                                else:
                                    # 否则，将命令作为额外参数
                                    cmd = (
                                        [
                                            "docker",
                                            "stack",
                                            "deploy",
                                            "-c",
                                            compose_file,
                                        ]
                                        + cmd_parts
                                        + [stack_name]
                                    )
                            else:
                                cmd = [
                                    "docker",
                                    "stack",
                                    "deploy",
                                    "-c",
                                    compose_file,
                                    stack_name,
                                ]
                        else:
                            # Docker Compose 模式：使用 docker-compose
                            # 解析命令（可能包含 -f 参数）
                            import shlex

                            cmd_parts = shlex.split(command_str)

                            # 如果命令中没有 -f 参数，在开头添加它（-f 必须在 docker-compose 之后，子命令之前）
                            if "-f" not in cmd_parts:
                                cmd_parts.insert(0, "-f")
                                cmd_parts.insert(1, compose_file)
                            else:
                                # 替换 -f 后面的文件路径
                                f_idx = cmd_parts.index("-f")
                                if f_idx + 1 < len(cmd_parts):
                                    cmd_parts[f_idx + 1] = compose_file
                                else:
                                    cmd_parts.insert(f_idx + 1, compose_file)

                            # 添加项目名称参数（使用应用名称）
                            app_name = (
                                context.get("app", {}).get("name", "")
                                if isinstance(context.get("app"), dict)
                                else ""
                            )
                            if app_name:
                                # 确保项目名称符合 Docker Compose 命名规范（小写字母、数字、连字符）
                                import re

                                project_name = re.sub(
                                    r"[^a-z0-9-]", "-", app_name.lower()
                                )
                                # 如果命令中没有 -p 或 --project-name 参数，添加它
                                if (
                                    "-p" not in cmd_parts
                                    and "--project-name" not in cmd_parts
                                ):
                                    cmd_parts.insert(0, "-p")
                                    cmd_parts.insert(1, project_name)
                                    logger.info(
                                        f"使用应用名称作为项目名称: {project_name}"
                                    )

                            # 构建完整命令：docker-compose -p <project-name> -f <file> <command>
                            cmd = ["docker-compose"] + cmd_parts
                    else:
                        raise ValueError("Docker Compose 模式需要提供 compose_content")
                else:
                    # Docker Run 模式：直接执行命令
                    # 处理多行命令和反斜杠续行符
                    # 将反斜杠+换行符替换为空格，然后合并所有行
                    # 先统一处理：将反斜杠+换行符替换为空格
                    import re

                    # 处理单个反斜杠续行符
                    command_str = re.sub(r"\\\s*\n\s*", " ", command_str)
                    # 处理双反斜杠续行符（YAML 转义）
                    command_str = re.sub(r"\\\\\s*\n\s*", " ", command_str)
                    # 清理多余的空格
                    command_str = re.sub(r"\s+", " ", command_str).strip()

                    import shlex

                    cmd_parts = shlex.split(command_str)
                    # 确保命令以 docker run 开头
                    if cmd_parts and cmd_parts[0] != "run":
                        cmd = ["docker", "run"] + cmd_parts
                    else:
                        cmd = ["docker"] + cmd_parts

                logger.info(f"执行命令: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300, shell=False
                )

                # 记录详细的执行结果
                logger.info(f"命令执行完成: returncode={result.returncode}")
                if result.stdout:
                    logger.info(f"命令输出 (stdout): {result.stdout}")
                if result.stderr:
                    logger.info(f"命令错误输出 (stderr): {result.stderr}")

                # 检查 stderr 中是否只是警告（Docker Compose 会将警告输出到 stderr）
                is_warning_only = False
                if result.stderr:
                    stderr_lower = result.stderr.lower()
                    # 常见的警告关键词
                    is_warning_only = any(
                        keyword in stderr_lower
                        for keyword in [
                            "level=warning",
                            "warning:",
                            "obsolete",
                            "deprecated",
                            "ignoring deprecated",
                        ]
                    )

                    if is_warning_only and result.returncode == 0:
                        # 只是警告，不影响成功
                        logger.warning(f"命令警告: {result.stderr}")
                    else:
                        logger.warning(f"命令错误输出: {result.stderr}")

                if result.returncode == 0:
                    # 即使有警告信息，只要返回码是 0，就认为成功
                    message = "部署成功"
                    if result.stderr:
                        # 如果有警告信息，在消息中提及
                        stderr_lower = result.stderr.lower()
                        if any(
                            keyword in stderr_lower
                            for keyword in [
                                "level=warning",
                                "warning:",
                                "obsolete",
                                "deprecated",
                            ]
                        ):
                            message = "部署成功（有警告信息）"

                    return {
                        "success": True,
                        "message": message,
                        "output": result.stdout,
                        "warning": (
                            result.stderr
                            if result.stderr
                            and any(
                                keyword in result.stderr.lower()
                                for keyword in [
                                    "level=warning",
                                    "warning:",
                                    "obsolete",
                                    "deprecated",
                                ]
                            )
                            else None
                        ),
                        "command": " ".join(cmd),
                        "returncode": result.returncode,
                    }
                else:
                    logger.error(f"命令执行失败 (返回码: {result.returncode})")
                    logger.info(f"错误信息 (stderr): {result.stderr}")
                    logger.info(f"输出信息 (stdout): {result.stdout}")

                    # 检查是否是容器名称冲突错误
                    error_text = (result.stderr or result.stdout or "").lower()
                    logger.info(f"检查错误文本: {error_text[:200]}")

                    is_container_conflict = any(
                        keyword in error_text
                        for keyword in [
                            "container name",
                            "already in use",
                            "conflict",
                            "container.*already",
                        ]
                    )

                    logger.info(
                        f"容器名称冲突检测结果: is_container_conflict={is_container_conflict}, deploy_mode={deploy_mode}"
                    )

                    # 如果是容器名称冲突，尝试自动清理（支持 docker_run 和 docker_compose）
                    if is_container_conflict:
                        logger.warning("检测到容器名称冲突，尝试自动清理...")

                        # 从错误信息中提取容器名称
                        import re

                        error_content = result.stderr or result.stdout or ""
                        logger.info(
                            f"尝试从错误信息中提取容器名称: {error_content[:300]}"
                        )

                        # 尝试多种格式匹配容器名称
                        container_name = None

                        # 格式1: container name "/test"
                        container_name_match = re.search(
                            r'container name\s+"([^"]+)"', error_content, re.IGNORECASE
                        )
                        if container_name_match:
                            container_name = container_name_match.group(1).strip()
                            logger.info(
                                f"从错误信息中提取到容器名称 (格式1): {container_name}"
                            )

                        # 格式2: The container name "/test" is already in use
                        if not container_name:
                            container_name_match = re.search(
                                r'the container name\s+"([^"]+)"',
                                error_content,
                                re.IGNORECASE,
                            )
                            if container_name_match:
                                container_name = container_name_match.group(1).strip()
                                logger.info(
                                    f"从错误信息中提取到容器名称 (格式2): {container_name}"
                                )

                        # 如果还是没找到，尝试从命令或配置中提取容器名称
                        if not container_name:
                            if deploy_mode == "docker_compose":
                                # Docker Compose 模式：从 compose 文件中提取
                                if "compose_content" in docker_config:
                                    compose_content = docker_config["compose_content"]
                                    # 查找 container_name
                                    container_match = re.search(
                                        r'container_name:\s*["\']?([^"\'\n\s]+)',
                                        compose_content,
                                        re.IGNORECASE,
                                    )
                                    if container_match:
                                        container_name = container_match.group(
                                            1
                                        ).strip()
                                        logger.info(
                                            f"从 compose 文件中提取到容器名称: {container_name}"
                                        )
                                    else:
                                        logger.warning(
                                            "无法从 compose 文件中提取容器名称"
                                        )
                                else:
                                    logger.warning(
                                        "compose_content 不存在，无法提取容器名称"
                                    )
                            else:
                                # Docker Run 模式：从命令中提取 --name 参数
                                command_str = docker_config.get("command", "")
                                if command_str:
                                    # 查找 --name=value 或 --name value 格式
                                    name_match = re.search(
                                        r"--name[=\s]+([^\s]+)",
                                        command_str,
                                        re.IGNORECASE,
                                    )
                                    if name_match:
                                        container_name = name_match.group(1).strip()
                                        logger.info(
                                            f"从命令中提取到容器名称: {container_name}"
                                        )
                                    else:
                                        logger.warning("无法从命令中提取容器名称")
                                else:
                                    logger.warning("命令不存在，无法提取容器名称")

                        if container_name:
                            logger.info(f"尝试删除冲突的容器: {container_name}")
                            try:
                                # 停止并删除容器
                                stop_cmd = ["docker", "stop", container_name]
                                stop_result = subprocess.run(
                                    stop_cmd, capture_output=True, text=True, timeout=30
                                )

                                rm_cmd = ["docker", "rm", "-f", container_name]
                                rm_result = subprocess.run(
                                    rm_cmd, capture_output=True, text=True, timeout=30
                                )

                                if (
                                    rm_result.returncode == 0
                                    or "no such container"
                                    in (rm_result.stderr or "").lower()
                                ):
                                    logger.info(
                                        f"已删除冲突容器: {container_name}，重新执行部署..."
                                    )
                                    # 重新执行部署命令
                                    retry_result = subprocess.run(
                                        cmd,
                                        capture_output=True,
                                        text=True,
                                        timeout=300,
                                        shell=False,
                                    )

                                    logger.info(
                                        f"重试命令执行完成: returncode={retry_result.returncode}"
                                    )
                                    if retry_result.returncode == 0:
                                        # 重试成功
                                        message = "部署成功（已自动清理冲突容器）"
                                        if retry_result.stderr:
                                            stderr_lower = retry_result.stderr.lower()
                                            if any(
                                                keyword in stderr_lower
                                                for keyword in [
                                                    "level=warning",
                                                    "warning:",
                                                    "obsolete",
                                                    "deprecated",
                                                ]
                                            ):
                                                message = "部署成功（已自动清理冲突容器，有警告信息）"

                                        return {
                                            "success": True,
                                            "message": message,
                                            "output": retry_result.stdout,
                                            "warning": (
                                                retry_result.stderr
                                                if retry_result.stderr
                                                and any(
                                                    keyword
                                                    in retry_result.stderr.lower()
                                                    for keyword in [
                                                        "level=warning",
                                                        "warning:",
                                                        "obsolete",
                                                        "deprecated",
                                                    ]
                                                )
                                                else None
                                            ),
                                            "command": " ".join(cmd),
                                            "returncode": retry_result.returncode,
                                            "auto_cleaned": True,
                                            "cleaned_container": container_name,
                                        }
                                    else:
                                        logger.error(
                                            f"重试后仍然失败: {retry_result.stderr}"
                                        )
                                else:
                                    logger.warning(f"删除容器失败: {rm_result.stderr}")
                            except Exception as cleanup_error:
                                logger.error(f"自动清理容器时发生异常: {cleanup_error}")

                    # 构建详细的错误消息
                    error_msg = "部署失败"
                    if result.stderr:
                        # 过滤掉警告信息，只保留真正的错误
                        error_lines = []
                        for line in result.stderr.split("\n"):
                            line_lower = line.lower()
                            # 跳过警告行
                            if not any(
                                keyword in line_lower
                                for keyword in [
                                    "level=warning",
                                    "warning:",
                                    "obsolete",
                                    "deprecated",
                                    "ignoring deprecated",
                                ]
                            ):
                                error_lines.append(line)

                        if error_lines:
                            error_msg = f"部署失败: {' '.join(error_lines).strip()}"
                        else:
                            # 如果过滤后没有错误，使用原始错误信息
                            error_msg = f"部署失败: {result.stderr.strip()}"
                    elif result.stdout:
                        error_msg = f"部署失败: {result.stdout.strip()}"

                    return {
                        "success": False,
                        "message": error_msg,
                        "error": result.stderr,
                        "output": result.stdout,
                        "command": " ".join(cmd),
                        "returncode": result.returncode,
                    }

            # 如果没有直接命令，使用配置构建命令（原有逻辑）
            if deploy_mode == "docker_compose":
                # 使用 docker-compose 或 docker stack deploy 部署
                compose_mode = docker_config.get("compose_mode", "docker-compose")
                task_id = context.get("task_id", "default")
                compose_file = self._create_docker_compose_file(
                    docker_config, context, task_id
                )

                if compose_mode == "docker-stack":
                    # Docker Stack 模式：使用 docker stack deploy
                    app_name = (
                        context.get("app", {}).get("name", "app")
                        if isinstance(context.get("app"), dict)
                        else "app"
                    )
                    stack_name = f"{app_name}-{task_id}"
                    # 确保 Stack 名称符合 Docker Stack 命名规范
                    import re

                    stack_name = re.sub(r"[^a-z0-9-]", "-", stack_name.lower())

                    # 执行 docker stack deploy
                    cmd = ["docker", "stack", "deploy", "-c", compose_file, stack_name]
                else:
                    # Docker Compose 模式：执行 docker-compose up
                    cmd = ["docker-compose", "-f", compose_file, "up", "-d"]

                logger.info(f"执行命令: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300
                )

                # 输出命令执行结果到日志
                if result.stdout:
                    logger.info(f"命令输出: {result.stdout}")
                if result.stderr:
                    # 检查 stderr 中是否只是警告（Docker Compose 会将警告输出到 stderr）
                    stderr_lower = result.stderr.lower()
                    # 常见的警告关键词
                    is_warning_only = any(
                        keyword in stderr_lower
                        for keyword in [
                            "level=warning",
                            "warning:",
                            "obsolete",
                            "deprecated",
                            "ignoring deprecated",
                        ]
                    )

                    if is_warning_only and result.returncode == 0:
                        # 只是警告，不影响成功
                        logger.warning(f"命令警告: {result.stderr}")
                    else:
                        logger.warning(f"命令错误输出: {result.stderr}")

                if result.returncode == 0:
                    # 即使有警告信息，只要返回码是 0，就认为成功
                    message = "部署成功"
                    if result.stderr:
                        # 如果有警告信息，在消息中提及
                        stderr_lower = result.stderr.lower()
                        if any(
                            keyword in stderr_lower
                            for keyword in [
                                "level=warning",
                                "warning:",
                                "obsolete",
                                "deprecated",
                            ]
                        ):
                            message = "部署成功（有警告信息）"

                    return {
                        "success": True,
                        "message": message,
                        "output": result.stdout,
                        "warning": (
                            result.stderr
                            if result.stderr
                            and any(
                                keyword in result.stderr.lower()
                                for keyword in [
                                    "level=warning",
                                    "warning:",
                                    "obsolete",
                                    "deprecated",
                                ]
                            )
                            else None
                        ),
                        "compose_file": compose_file,
                        "returncode": result.returncode,
                    }
                else:
                    logger.error(f"部署失败 (返回码: {result.returncode})")

                    # 检查是否是容器名称冲突错误
                    error_text = (result.stderr or result.stdout or "").lower()
                    is_container_conflict = any(
                        keyword in error_text
                        for keyword in [
                            "container name",
                            "already in use",
                            "conflict",
                            "container.*already",
                        ]
                    )

                    # 如果是容器名称冲突，尝试自动清理
                    if is_container_conflict:
                        logger.warning("检测到容器名称冲突，尝试自动清理...")

                        # 从错误信息中提取容器名称
                        import re

                        error_content = result.stderr or result.stdout or ""
                        logger.info(
                            f"尝试从错误信息中提取容器名称: {error_content[:300]}"
                        )

                        # 尝试多种格式匹配容器名称
                        container_name = None

                        # 格式1: container name "/test"
                        container_name_match = re.search(
                            r'container name\s+"([^"]+)"', error_content, re.IGNORECASE
                        )
                        if container_name_match:
                            container_name = container_name_match.group(1).strip()
                            logger.info(
                                f"从错误信息中提取到容器名称 (格式1): {container_name}"
                            )

                        # 格式2: The container name "/test" is already in use
                        if not container_name:
                            container_name_match = re.search(
                                r'the container name\s+"([^"]+)"',
                                error_content,
                                re.IGNORECASE,
                            )
                            if container_name_match:
                                container_name = container_name_match.group(1).strip()
                                logger.info(
                                    f"从错误信息中提取到容器名称 (格式2): {container_name}"
                                )

                        # 如果还是没找到，尝试从命令或配置中提取容器名称
                        if not container_name:
                            if deploy_mode == "docker_compose":
                                # Docker Compose 模式：从 compose 文件中提取
                                if "compose_content" in docker_config:
                                    compose_content = docker_config["compose_content"]
                                    # 查找 container_name
                                    container_match = re.search(
                                        r'container_name:\s*["\']?([^"\'\n\s]+)',
                                        compose_content,
                                        re.IGNORECASE,
                                    )
                                    if container_match:
                                        container_name = container_match.group(
                                            1
                                        ).strip()
                                        logger.info(
                                            f"从 compose 文件中提取到容器名称: {container_name}"
                                        )
                                    else:
                                        logger.warning(
                                            "无法从 compose 文件中提取容器名称"
                                        )
                                else:
                                    logger.warning(
                                        "compose_content 不存在，无法提取容器名称"
                                    )
                            else:
                                # Docker Run 模式：从命令中提取 --name 参数
                                command_str = docker_config.get("command", "")
                                if command_str:
                                    # 查找 --name=value 或 --name value 格式
                                    name_match = re.search(
                                        r"--name[=\s]+([^\s]+)",
                                        command_str,
                                        re.IGNORECASE,
                                    )
                                    if name_match:
                                        container_name = name_match.group(1).strip()
                                        logger.info(
                                            f"从命令中提取到容器名称: {container_name}"
                                        )
                                    else:
                                        logger.warning("无法从命令中提取容器名称")
                                else:
                                    logger.warning("命令不存在，无法提取容器名称")

                        if container_name:
                            logger.info(f"尝试删除冲突的容器: {container_name}")
                            try:
                                # 停止并删除容器
                                stop_cmd = ["docker", "stop", container_name]
                                stop_result = subprocess.run(
                                    stop_cmd, capture_output=True, text=True, timeout=30
                                )

                                rm_cmd = ["docker", "rm", "-f", container_name]
                                rm_result = subprocess.run(
                                    rm_cmd, capture_output=True, text=True, timeout=30
                                )

                                if (
                                    rm_result.returncode == 0
                                    or "no such container"
                                    in (rm_result.stderr or "").lower()
                                ):
                                    logger.info(
                                        f"已删除冲突容器: {container_name}，重新执行部署..."
                                    )
                                    # 重新执行部署命令
                                    retry_result = subprocess.run(
                                        cmd, capture_output=True, text=True, timeout=300
                                    )

                                    logger.info(
                                        f"重试命令执行完成: returncode={retry_result.returncode}"
                                    )
                                    if retry_result.returncode == 0:
                                        # 重试成功
                                        message = "部署成功（已自动清理冲突容器）"
                                        if retry_result.stderr:
                                            stderr_lower = retry_result.stderr.lower()
                                            if any(
                                                keyword in stderr_lower
                                                for keyword in [
                                                    "level=warning",
                                                    "warning:",
                                                    "obsolete",
                                                    "deprecated",
                                                ]
                                            ):
                                                message = "部署成功（已自动清理冲突容器，有警告信息）"

                                        return {
                                            "success": True,
                                            "message": message,
                                            "output": retry_result.stdout,
                                            "warning": (
                                                retry_result.stderr
                                                if retry_result.stderr
                                                and any(
                                                    keyword
                                                    in retry_result.stderr.lower()
                                                    for keyword in [
                                                        "level=warning",
                                                        "warning:",
                                                        "obsolete",
                                                        "deprecated",
                                                    ]
                                                )
                                                else None
                                            ),
                                            "compose_file": compose_file,
                                            "returncode": retry_result.returncode,
                                            "auto_cleaned": True,
                                            "cleaned_container": container_name,
                                        }
                                    else:
                                        logger.error(
                                            f"重试后仍然失败: {retry_result.stderr}"
                                        )
                                else:
                                    logger.warning(f"删除容器失败: {rm_result.stderr}")
                            except Exception as cleanup_error:
                                logger.error(f"自动清理容器时发生异常: {cleanup_error}")

                    # 构建详细的错误消息
                    error_msg = "部署失败"
                    if result.stderr:
                        # 过滤掉警告信息，只保留真正的错误
                        error_lines = []
                        for line in result.stderr.split("\n"):
                            line_lower = line.lower()
                            # 跳过警告行
                            if not any(
                                keyword in line_lower
                                for keyword in [
                                    "level=warning",
                                    "warning:",
                                    "obsolete",
                                    "deprecated",
                                    "ignoring deprecated",
                                ]
                            ):
                                error_lines.append(line)

                        if error_lines:
                            error_msg = f"部署失败: {' '.join(error_lines).strip()}"
                        else:
                            # 如果过滤后没有错误，使用原始错误信息
                            error_msg = f"部署失败: {result.stderr.strip()}"
                    elif result.stdout:
                        error_msg = f"部署失败: {result.stdout.strip()}"

                    return {
                        "success": False,
                        "message": error_msg,
                        "error": result.stderr,
                        "output": result.stdout,
                        "compose_file": compose_file,
                        "returncode": result.returncode,
                    }

            else:
                # 使用 docker run 部署
                cmd = self._build_docker_run_command(docker_config, context)

                logger.info(f"执行命令: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=300
                )

                # 输出命令执行结果到日志
                if result.stdout:
                    logger.info(f"命令输出: {result.stdout}")
                if result.stderr:
                    logger.warning(f"命令错误输出: {result.stderr}")

                if result.returncode == 0:
                    container_id = result.stdout.strip()
                    logger.info(f"部署成功，容器ID: {container_id}")
                    return {
                        "success": True,
                        "message": "部署成功",
                        "container_id": container_id,
                        "output": result.stdout,
                    }
                else:
                    logger.error(f"部署失败 (返回码: {result.returncode})")
                    return {
                        "success": False,
                        "message": "部署失败",
                        "error": result.stderr,
                        "output": result.stdout,
                    }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "部署超时",
                "error": "命令执行超过 300 秒",
            }
        except Exception as e:
            logger.exception("部署执行异常")
            return {"success": False, "message": "部署异常", "error": str(e)}

    def check_deployment_status(
        self,
        deploy_config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        检查当前主机上部署是否仍存在且处于健康状态（用于主程序重启后恢复判断）。

        Returns:
            dict: success, checked, message, exists, running, exit_code(optional)
        """
        ctx = context or {}
        base = {
            "success": False,
            "checked": True,
            "exists": False,
            "running": False,
            "message": "",
        }

        steps = deploy_config.get("steps")
        if steps and isinstance(steps, list):
            base["message"] = "多步骤部署无法自动确认远端状态"
            return base

        deploy_mode = (
            deploy_config.get("deploy_mode")
            or deploy_config.get("type")
            or "docker_run"
        )

        try:
            if deploy_mode == "docker_run":
                name = (deploy_config.get("container_name") or "").strip()
                if name:
                    name = self._render_template(name, ctx)
                if not name:
                    cmd_str = (deploy_config.get("command") or "").strip()
                    if cmd_str:
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
                    base["message"] = "无法解析容器名称，无法检查部署状态"
                    return base

                return self._check_single_container_status(name, base)

            if deploy_mode == "docker_compose":
                compose_mode = deploy_config.get("compose_mode", "docker-compose")
                task_id = ctx.get("task_id", "default")

                if compose_mode == "docker-stack":
                    app_name = (
                        ctx.get("app", {}).get("name", "app")
                        if isinstance(ctx.get("app"), dict)
                        else "app"
                    )
                    stack_name = re.sub(
                        r"[^a-z0-9-]", "-", f"{app_name}-{task_id}".lower()
                    )
                    if deploy_config.get("stack_name"):
                        stack_name = self._render_template(
                            str(deploy_config["stack_name"]), ctx
                        )
                    return self._check_docker_stack_status(stack_name, base)

                # docker-compose：优先使用已有 compose 文件，否则从 compose_content 写入临时文件
                compose_file = os.path.join(
                    self.work_dir, f"docker-compose-{task_id}.yml"
                )
                compose_content = deploy_config.get("compose_content") or ""
                if not os.path.isfile(compose_file) and compose_content.strip():
                    os.makedirs(self.work_dir, exist_ok=True)
                    with open(compose_file, "w", encoding="utf-8") as f:
                        f.write(compose_content)

                if not os.path.isfile(compose_file):
                    base["message"] = "未找到 compose 文件且配置中无 compose_content，无法检查"
                    return base

                return self._check_compose_project_status(compose_file, base)

            base["message"] = f"不支持的部署模式用于状态检查: {deploy_mode}"
            return base

        except Exception as e:
            logger.exception("check_deployment_status 异常")
            base["message"] = f"检查部署状态时异常: {e}"
            return base

    def _check_single_container_status(
        self, container_name: str, base: Dict[str, Any]
    ) -> Dict[str, Any]:
        """根据 docker inspect 判断单个容器。"""
        fmt = "{{.State.Running}}|{{.State.ExitCode}}|{{.State.Status}}"
        result = subprocess.run(
            ["docker", "inspect", "-f", fmt, container_name],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            base["exists"] = False
            base["running"] = False
            base["success"] = False
            base["message"] = (
                f"容器不存在或无法检查: {container_name} ({result.stderr.strip() or 'inspect 失败'})"
            )
            return base

        base["exists"] = True
        parts = (result.stdout or "").strip().split("|", 2)
        running_s = parts[0].strip().lower() if parts else "false"
        exit_code_s = parts[1].strip() if len(parts) > 1 else "0"
        status_s = parts[2].strip() if len(parts) > 2 else ""

        base["running"] = running_s == "true"
        try:
            exit_code = int(exit_code_s)
        except ValueError:
            exit_code = -1
        base["exit_code"] = exit_code

        if base["running"]:
            base["success"] = True
            base["message"] = f"容器正在运行: {container_name} ({status_s})"
            return base

        if exit_code == 0:
            base["success"] = True
            base["message"] = (
                f"容器已退出且退出码为 0: {container_name} ({status_s})"
            )
            return base

        base["success"] = False
        base["message"] = (
            f"容器未运行或异常退出: {container_name}, exit={exit_code} ({status_s})"
        )
        return base

    def _check_docker_stack_status(
        self, stack_name: str, base: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查 Swarm stack 是否有正常副本。"""
        result = subprocess.run(
            ["docker", "stack", "services", stack_name, "--format", "{{.Replicas}}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0 or not (result.stdout or "").strip():
            base["exists"] = False
            base["success"] = False
            base["message"] = (
                f"Stack 不存在或无服务: {stack_name} ({result.stderr.strip() or result.stdout})"
            )
            return base

        base["exists"] = True
        lines = [ln.strip() for ln in result.stdout.strip().splitlines() if ln.strip()]
        all_ok = True
        for line in lines:
            if "/" not in line:
                continue
            a, b = line.split("/", 1)
            try:
                if int(a.strip()) < int(b.strip()) or int(b.strip()) == 0:
                    all_ok = False
            except ValueError:
                all_ok = False

        base["running"] = all_ok
        base["success"] = all_ok
        base["message"] = (
            f"Stack {stack_name} 副本: {lines} — {'正常' if all_ok else '未全部就绪'}"
        )
        return base

    def _check_compose_project_status(
        self, compose_file: str, base: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用 docker compose / docker-compose ps 检查项目容器。"""
        for compose_cmd in (
            ["docker", "compose", "-f", compose_file, "ps", "-a", "--format", "json"],
            ["docker-compose", "-f", compose_file, "ps", "-a", "--format", "json"],
        ):
            result = subprocess.run(
                compose_cmd, capture_output=True, text=True, timeout=90
            )
            if result.returncode != 0 or not (result.stdout or "").strip():
                continue
            try:
                # 可能多行 JSON 或 JSON 数组
                raw = result.stdout.strip()
                items: List[Dict[str, Any]] = []
                if raw.startswith("["):
                    items = json.loads(raw)
                else:
                    for line in raw.splitlines():
                        line = line.strip()
                        if line:
                            items.append(json.loads(line))
                if not items:
                    base["message"] = "Compose 项目下无容器记录"
                    base["exists"] = False
                    base["success"] = False
                    return base

                base["exists"] = True
                any_running = False
                for it in items:
                    state = (it.get("State") or it.get("Status") or "").lower()
                    if "running" in state or state == "running":
                        any_running = True

                if any_running:
                    base["running"] = True
                    base["success"] = True
                    base["message"] = "Compose 服务中有容器正在运行"
                    return base

                # 无运行中：若至少有一个已退出且为 0，视为成功（一次性任务）
                exited_zero = any(
                    "exited (0)" in (it.get("State") or it.get("Status") or "").lower()
                    or "dead" in (it.get("State") or "").lower()
                    for it in items
                )
                # 简化：若无 running，检查是否全部 Exited (0)
                statuses = [
                    (it.get("State") or it.get("Status") or "").lower() for it in items
                ]
                if statuses and all(
                    "exited (0)" in s or s.endswith("exit 0") for s in statuses
                ):
                    base["success"] = True
                    base["message"] = "Compose 容器均已正常退出(0)"
                    return base

                if exited_zero and len(items) == 1:
                    base["success"] = True
                    base["message"] = "Compose 容器已退出且状态正常"
                    return base

                base["success"] = False
                base["message"] = f"Compose 状态未满足运行或正常退出: {statuses}"
                return base
            except json.JSONDecodeError:
                continue

        # 回退：文本 ps
        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "ps"],
            capture_output=True,
            text=True,
            timeout=90,
        )
        out = (result.stdout or "") + (result.stderr or "")
        if "Up" in out:
            base["exists"] = True
            base["running"] = True
            base["success"] = True
            base["message"] = "docker-compose ps 显示有服务 Up"
            return base
        if "Exit 0" in out:
            base["exists"] = True
            base["success"] = True
            base["message"] = "docker-compose ps 显示 Exit 0"
            return base

        base["exists"] = "Name" in out or len(out) > 20
        base["success"] = False
        base["message"] = "无法确认 Compose 部署状态（无 Up / Exit 0）"
        return base

    def stop_deploy(
        self, container_name: str, deploy_mode: str = "docker_run"
    ) -> Dict[str, Any]:
        """
        停止部署的容器

        Args:
            container_name: 容器名称
            deploy_mode: 部署模式（docker_run 或 docker_compose）

        Returns:
            执行结果字典
        """
        try:
            if deploy_mode == "docker_compose":
                # 查找对应的 compose 文件
                compose_files = list(Path(self.work_dir).glob("docker-compose-*.yml"))
                for compose_file in compose_files:
                    # 读取 compose 文件检查容器名称
                    with open(compose_file, "r", encoding="utf-8") as f:
                        compose_config = yaml.safe_load(f)
                        service = compose_config.get("services", {}).get("app", {})
                        if service.get("container_name") == container_name:
                            cmd = ["docker-compose", "-f", str(compose_file), "down"]
                            result = subprocess.run(
                                cmd, capture_output=True, text=True, timeout=60
                            )
                            return {
                                "success": result.returncode == 0,
                                "message": (
                                    "停止成功" if result.returncode == 0 else "停止失败"
                                ),
                                "output": result.stdout,
                                "error": (
                                    result.stderr if result.returncode != 0 else None
                                ),
                            }

                return {"success": False, "message": "未找到对应的 compose 文件"}

            else:
                # 使用 docker stop 和 docker rm
                cmd_stop = ["docker", "stop", container_name]
                cmd_rm = ["docker", "rm", container_name]

                result_stop = subprocess.run(
                    cmd_stop, capture_output=True, text=True, timeout=60
                )

                result_rm = subprocess.run(
                    cmd_rm, capture_output=True, text=True, timeout=60
                )

                success = result_stop.returncode == 0 and result_rm.returncode == 0
                return {
                    "success": success,
                    "message": "停止成功" if success else "停止失败",
                    "output": f"{result_stop.stdout}\n{result_rm.stdout}",
                    "error": (
                        result_stop.stderr
                        if result_stop.returncode != 0
                        else result_rm.stderr
                    ),
                }

        except Exception as e:
            logger.exception("停止部署异常")
            return {"success": False, "message": "停止异常", "error": str(e)}

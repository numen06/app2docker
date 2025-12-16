# backend/ssh_deploy_executor.py
"""
SSH 部署执行器
通过 SSH 连接执行 Docker 部署
"""
import paramiko
import logging
from typing import Dict, Any, Optional
from io import StringIO

logger = logging.getLogger(__name__)


class SSHDeployExecutor:
    """SSH 部署执行器"""
    
    def __init__(self):
        """初始化 SSH 部署执行器"""
        pass
    
    def _create_ssh_client(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        key_password: Optional[str] = None
    ) -> paramiko.SSHClient:
        """
        创建 SSH 客户端
        
        Args:
            host: 主机地址
            port: SSH 端口
            username: 用户名
            password: 密码（可选）
            private_key: SSH 私钥（可选）
            key_password: 私钥密码（可选）
        
        Returns:
            SSH 客户端
        """
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if private_key:
                # 使用私钥认证
                key_obj = None
                try:
                    # 尝试解析私钥
                    key_obj = paramiko.RSAKey.from_private_key(
                        StringIO(private_key),
                        password=key_password if key_password else None
                    )
                except:
                    try:
                        key_obj = paramiko.Ed25519Key.from_private_key(
                            StringIO(private_key),
                            password=key_password if key_password else None
                        )
                    except:
                        key_obj = paramiko.ECDSAKey.from_private_key(
                            StringIO(private_key),
                            password=key_password if key_password else None
                        )
                
                ssh_client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    pkey=key_obj,
                    timeout=10
                )
            elif password:
                # 使用密码认证
                ssh_client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10
                )
            else:
                raise ValueError("请提供密码或SSH私钥")
            
            return ssh_client
        
        except Exception as e:
            ssh_client.close()
            raise
    
    def execute_deploy(
        self,
        host_config: Dict[str, Any],
        docker_config: Dict[str, Any],
        deploy_mode: str = "docker_run"
    ) -> Dict[str, Any]:
        """
        通过 SSH 执行部署
        
        Args:
            host_config: SSH 主机配置（host, port, username, password/private_key等）
            docker_config: Docker 配置
            deploy_mode: 部署模式（docker_run 或 docker_compose）
        
        Returns:
            执行结果字典
        """
        try:
            # 创建 SSH 客户端
            ssh_client = self._create_ssh_client(
                host=host_config.get("host"),
                port=host_config.get("port", 22),
                username=host_config.get("username"),
                password=host_config.get("password"),
                private_key=host_config.get("private_key"),
                key_password=host_config.get("key_password")
            )
            
            try:
                if deploy_mode == "docker_compose":
                    # Docker Compose 模式
                    compose_content = docker_config.get("compose_content", "")
                    if not compose_content:
                        return {
                            "success": False,
                            "message": "Docker Compose 模式需要提供 compose_content"
                        }
                    
                    # 获取 Compose 模式（docker-compose 或 docker-stack）
                    compose_mode = docker_config.get("compose_mode", "docker-compose")
                    redeploy_strategy = docker_config.get("redeploy_strategy", "update_existing")
                    redeploy = docker_config.get("redeploy", False)
                    
                    # 生成 Stack/项目名称（优先使用应用名称，否则使用配置的 stack_name）
                    app_name = docker_config.get("app_name") or docker_config.get("stack_name", "app")
                    # 确保名称符合 Docker 命名规范（小写字母、数字、连字符）
                    import re
                    project_name = re.sub(r'[^a-z0-9-]', '-', app_name.lower())
                    
                    # 对于 docker-compose，使用 project_name；对于 docker-stack，使用 project_name 作为 stack_name
                    stack_name = project_name
                    
                    # 根据 redeploy_strategy 处理重新发布
                    if redeploy and redeploy_strategy == "remove_and_redeploy":
                        if compose_mode == "docker-stack":
                            # Docker Stack 模式：删除 Stack
                            logger.info(f"删除已有 Stack: {stack_name}")
                            stdin, stdout, stderr = ssh_client.exec_command(
                                f"docker stack rm {stack_name} || true"
                            )
                            stdout.channel.recv_exit_status()
                            # 等待 Stack 完全删除
                            import time
                            time.sleep(2)
                        else:
                            # Docker Compose 模式：停止并删除
                            logger.info(f"停止并删除已有 Compose Stack: {stack_name}")
                            stdin, stdout, stderr = ssh_client.exec_command(
                                f"docker-compose -f /tmp/{stack_name}/docker-compose.yml down -v || true"
                            )
                            stdout.channel.recv_exit_status()
                    
                    # 创建临时目录
                    stdin, stdout, stderr = ssh_client.exec_command(
                        f"mkdir -p /tmp/{stack_name}"
                    )
                    stdout.channel.recv_exit_status()
                    
                    # 写入 docker-compose.yml
                    sftp = ssh_client.open_sftp()
                    compose_file = f"/tmp/{stack_name}/docker-compose.yml"
                    remote_file = sftp.file(compose_file, "w")
                    remote_file.write(compose_content)
                    remote_file.close()
                    sftp.close()
                    
                    # 如果是 docker-stack 模式，检查 compose 文件中是否有不兼容的选项
                    if compose_mode == "docker-stack":
                        # docker stack deploy 不支持 container_name，会显示警告
                        if "container_name" in compose_content:
                            logger.warning("docker stack deploy 不支持 container_name 选项，该选项将被忽略")
                    
                    # 根据 compose_mode 执行不同的命令
                    if compose_mode == "docker-stack":
                        # Docker Stack 模式：使用 docker stack deploy
                        command = docker_config.get("command", "")
                        # 构建 docker stack deploy 命令
                        # 命令格式：docker stack deploy -c <compose-file> <stack-name> [OPTIONS]
                        if command:
                            # 如果命令中包含 -c 或 --compose-file，需要替换文件路径
                            import shlex
                            cmd_parts = shlex.split(command)
                            
                            # 检查并替换 -c 或 --compose-file 参数
                            has_compose_file = False
                            for i, part in enumerate(cmd_parts):
                                if part == "-c" and i + 1 < len(cmd_parts):
                                    cmd_parts[i + 1] = compose_file
                                    has_compose_file = True
                                    break
                                elif part == "--compose-file" and i + 1 < len(cmd_parts):
                                    cmd_parts[i + 1] = compose_file
                                    has_compose_file = True
                                    break
                            
                            if has_compose_file:
                                # 已经有 -c 或 --compose-file，直接使用（stack_name 必须在最后）
                                stack_command = f"docker stack deploy {' '.join(cmd_parts)} {stack_name}"
                            else:
                                # 没有 -c 或 --compose-file，添加它（stack_name 必须在最后）
                                stack_command = f"docker stack deploy -c {compose_file} {' '.join(cmd_parts)} {stack_name}"
                        else:
                            # 默认命令：使用 -c 参数（stack_name 必须在最后）
                            import shlex
                            stack_command = f"docker stack deploy -c {shlex.quote(compose_file)} {shlex.quote(stack_name)}"
                        
                        logger.info(f"执行 SSH Stack 命令: {stack_command}")
                        stdin, stdout, stderr = ssh_client.exec_command(stack_command)
                    else:
                        # Docker Compose 模式：使用 docker-compose
                        command = docker_config.get("command", "up -d")
                        # 添加项目名称参数（-p 或 --project-name）
                        # 检查命令中是否已包含项目名称参数
                        import shlex
                        cmd_parts = shlex.split(command)
                        if "-p" not in cmd_parts and "--project-name" not in cmd_parts:
                            # 添加项目名称参数
                            compose_command = f"cd /tmp/{stack_name} && docker-compose -p {project_name} {command}"
                        else:
                            compose_command = f"cd /tmp/{stack_name} && docker-compose {command}"
                        logger.info(f"执行 SSH Compose 命令: {compose_command}")
                        logger.info(f"使用项目名称: {project_name}")
                        stdin, stdout, stderr = ssh_client.exec_command(compose_command)
                        stack_command = compose_command
                    
                    exit_status = stdout.channel.recv_exit_status()
                    stdout_text = stdout.read().decode("utf-8", errors='ignore')
                    stderr_text = stderr.read().decode("utf-8", errors='ignore')
                    
                    # 记录详细的执行结果
                    logger.info(f"SSH {compose_mode} 命令执行完成: exit_status={exit_status}")
                    if stdout_text:
                        logger.info(f"SSH {compose_mode} stdout: {stdout_text[:500]}")
                    if stderr_text:
                        logger.warning(f"SSH {compose_mode} stderr: {stderr_text[:500]}")
                    
                    if exit_status == 0:
                        return {
                            "success": True,
                            "message": f"{'Stack' if compose_mode == 'docker-stack' else 'Compose'} 部署成功",
                            "output": stdout_text,
                            "command": stack_command
                        }
                    else:
                        # 构建详细的错误消息
                        error_message = f"{'Stack' if compose_mode == 'docker-stack' else 'Compose'} 部署失败"
                        if stderr_text:
                            error_message = f"{error_message}: {stderr_text.strip()}"
                        elif stdout_text:
                            error_message = f"{error_message}: {stdout_text.strip()}"
                        
                        logger.error(f"SSH {compose_mode} 部署失败: exit_status={exit_status}, error={stderr_text}, output={stdout_text}")
                        return {
                            "success": False,
                            "message": error_message,
                            "error": stderr_text,
                            "output": stdout_text,
                            "exit_status": exit_status,
                            "command": stack_command
                        }
                else:
                    # Docker Run 模式
                    command_str = docker_config.get("command", "").strip()
                    
                    # 如果命令包含"docker run"前缀，保留它（SSH需要完整命令）
                    # 如果命令不包含"docker run"前缀，添加它
                    if command_str and not command_str.startswith("docker"):
                        command_str = f"docker run {command_str}"
                    elif command_str.startswith("docker run"):
                        # 已经是完整命令，保持不变
                        pass
                    elif command_str.startswith("docker"):
                        # 可能是"docker"开头但后面不是"run"，检查一下
                        parts = command_str.split(None, 1)
                        if len(parts) == 1 or parts[1].startswith("-"):
                            # 只有"docker"或"docker"后面直接跟参数，添加"run"
                            command_str = f"docker run {parts[1] if len(parts) > 1 else ''}"
                    
                    # 如果没有 command，尝试从配置构建命令
                    if not command_str:
                        # 从配置构建 docker run 命令
                        image_template = docker_config.get("image_template", "")
                        container_name = docker_config.get("container_name", "")
                        ports = docker_config.get("ports", [])
                        env = docker_config.get("env", [])
                        volumes = docker_config.get("volumes", [])
                        restart_policy = docker_config.get("restart_policy", "always")
                        
                        if not image_template:
                            return {
                                "success": False,
                                "message": "Docker Run 模式需要提供 command 或 image_template"
                            }
                        
                        # 构建 docker run 命令
                        cmd_parts = ["docker", "run", "-d"]
                        
                        if container_name:
                            cmd_parts.extend(["--name", container_name])
                        
                        if restart_policy:
                            cmd_parts.extend(["--restart", restart_policy])
                        
                        for port in ports:
                            cmd_parts.extend(["-p", port])
                        
                        for env_var in env:
                            cmd_parts.extend(["-e", env_var])
                        
                        for volume in volumes:
                            cmd_parts.extend(["-v", volume])
                        
                        cmd_parts.append(image_template)
                        
                        command_str = " ".join(cmd_parts)
                    
                    # 处理多行命令和反斜杠续行符
                    import re
                    command_str = re.sub(r'\\\s*\n\s*', ' ', command_str)
                    command_str = re.sub(r'\\\\\s*\n\s*', ' ', command_str)
                    command_str = re.sub(r'\s+', ' ', command_str).strip()
                    
                    # 检查是否需要重新发布
                    redeploy = docker_config.get("redeploy", False)
                    
                    # 从命令中提取容器名
                    import shlex
                    cmd_parts = shlex.split(command_str)
                    container_name = None
                    
                    # 跳过"docker"和"run"（如果存在）
                    start_idx = 0
                    if len(cmd_parts) >= 2 and cmd_parts[0] == "docker" and cmd_parts[1] == "run":
                        start_idx = 2
                    
                    # 在剩余部分查找--name
                    if "--name" in cmd_parts[start_idx:]:
                        name_idx = cmd_parts.index("--name", start_idx)
                        if name_idx + 1 < len(cmd_parts):
                            container_name = cmd_parts[name_idx + 1]
                    
                    # 如果还没找到，尝试从 docker_config 获取
                    if not container_name:
                        container_name = docker_config.get("container_name")
                    
                    # 如果redeploy为true但没找到容器名，尝试从命令中提取（使用正则表达式）
                    if redeploy and not container_name:
                        # 尝试使用正则表达式提取 --name=value 或 --name value 格式
                        name_match = re.search(r'--name[=\s]+([^\s]+)', command_str)
                        if name_match:
                            container_name = name_match.group(1)
                    
                    if redeploy and container_name:
                        # 停止并删除已有容器
                        logger.info(f"清理已有容器: {container_name}")
                        stdin, stdout, stderr = ssh_client.exec_command(
                            f"docker stop {container_name} || true"
                        )
                        stdout.channel.recv_exit_status()
                        stdin, stdout, stderr = ssh_client.exec_command(
                            f"docker rm -f {container_name} || true"
                        )
                        stdout.channel.recv_exit_status()
                    
                    # 执行 docker run 命令
                    logger.info(f"执行 SSH 命令: {command_str}")
                    stdin, stdout, stderr = ssh_client.exec_command(
                        command_str
                    )
                    
                    exit_status = stdout.channel.recv_exit_status()
                    stdout_text = stdout.read().decode("utf-8", errors='ignore')
                    stderr_text = stderr.read().decode("utf-8", errors='ignore')
                    
                    # 记录详细的执行结果
                    logger.info(f"SSH 命令执行完成: exit_status={exit_status}")
                    if stdout_text:
                        logger.info(f"SSH 命令 stdout: {stdout_text[:500]}")  # 限制长度
                    if stderr_text:
                        logger.warning(f"SSH 命令 stderr: {stderr_text[:500]}")  # 限制长度
                    
                    if exit_status == 0:
                        return {
                            "success": True,
                            "message": "容器部署成功",
                            "output": stdout_text,
                            "command": command_str
                        }
                    else:
                        # 构建详细的错误消息
                        error_message = "容器部署失败"
                        if stderr_text:
                            error_message = f"容器部署失败: {stderr_text.strip()}"
                        elif stdout_text:
                            error_message = f"容器部署失败: {stdout_text.strip()}"
                        
                        logger.error(f"SSH 部署失败: exit_status={exit_status}, error={stderr_text}, output={stdout_text}")
                        return {
                            "success": False,
                            "message": error_message,
                            "error": stderr_text,
                            "output": stdout_text,
                            "exit_status": exit_status,
                            "command": command_str
                        }
            
            finally:
                ssh_client.close()
        
        except Exception as e:
            import traceback
            logger.exception("SSH 部署执行异常")
            return {
                "success": False,
                "message": f"SSH 部署失败: {str(e)}",
                "error": traceback.format_exc()
            }


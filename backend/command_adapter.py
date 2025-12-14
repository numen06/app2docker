# backend/command_adapter.py
"""
命令适配器
将统一格式的命令/脚本适配为不同主机类型需要的格式
"""
import re
import shlex
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CommandAdapter:
    """命令适配器"""
    
    @staticmethod
    def adapt_command(
        command: str,
        deploy_type: str,
        host_type: str,
        compose_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        适配命令为指定主机类型需要的格式
        
        Args:
            command: 统一格式的命令
            deploy_type: 部署类型（docker_run 或 docker_compose）
            host_type: 主机类型（agent、portainer、ssh）
            compose_content: Docker Compose文件内容（当deploy_type=docker_compose时）
            context: 模板变量上下文（可选）
        
        Returns:
            适配后的配置字典，格式根据host_type不同而不同
        """
        if deploy_type == "docker_run":
            return CommandAdapter._adapt_docker_run(command, host_type, context)
        elif deploy_type == "docker_compose":
            return CommandAdapter._adapt_docker_compose(
                command, compose_content or "", host_type, context
            )
        else:
            raise ValueError(f"未知的部署类型: {deploy_type}")
    
    @staticmethod
    def _adapt_docker_run(
        command: str,
        host_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        适配Docker Run命令
        
        Args:
            command: docker run的参数（可能包含"docker run"前缀）
            host_type: 主机类型
            context: 模板变量上下文
        
        Returns:
            适配后的配置字典
        """
        # 如果命令包含"docker run"前缀，先去掉它
        command = command.strip()
        if command.startswith("docker run"):
            # 去掉"docker run"前缀，保留后面的参数
            command = command[10:].strip()  # "docker run"长度为10
        elif command.startswith("docker"):
            # 可能是"docker"开头但后面不是"run"，尝试去掉"docker"
            parts = command.split(None, 2)
            if len(parts) >= 2 and parts[1] == "run":
                command = parts[2] if len(parts) > 2 else ""
        
        # 解析命令参数
        parsed = CommandAdapter._parse_docker_run_command(command)
        
        if host_type == "agent":
            # Agent格式：直接传递命令和解析后的参数
            return {
                "deploy_mode": "docker_run",
                "command": command,
                "container_name": parsed.get("container_name"),
                "image": parsed.get("image"),
                "ports": parsed.get("ports", []),
                "env": parsed.get("env", []),
                "volumes": parsed.get("volumes", []),
                "restart_policy": parsed.get("restart_policy", "always")
            }
        
        elif host_type == "portainer":
            # Portainer格式：需要分离参数
            return {
                "deploy_mode": "docker_run",
                "command": command,  # Portainer也支持直接使用command
                "container_name": parsed.get("container_name"),
                "image_template": parsed.get("image", ""),
                "ports": parsed.get("ports", []),
                "env": parsed.get("env", []),
                "volumes": parsed.get("volumes", []),
                "restart_policy": parsed.get("restart_policy", "always")
            }
        
        elif host_type == "ssh":
            # SSH格式：直接使用命令字符串
            return {
                "deploy_mode": "docker_run",
                "command": command
            }
        
        else:
            raise ValueError(f"未知的主机类型: {host_type}")
    
    @staticmethod
    def _adapt_docker_compose(
        command: str,
        compose_content: str,
        host_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        适配Docker Compose命令
        
        Args:
            command: docker-compose命令（如"up -d"）
            compose_content: docker-compose.yml内容
            host_type: 主机类型
            context: 模板变量上下文
        
        Returns:
            适配后的配置字典
        """
        if host_type == "agent":
            return {
                "deploy_mode": "docker_compose",
                "command": command,
                "compose_content": compose_content
            }
        
        elif host_type == "portainer":
            return {
                "deploy_mode": "docker_compose",
                "command": command,
                "compose_content": compose_content
            }
        
        elif host_type == "ssh":
            return {
                "deploy_mode": "docker_compose",
                "command": command,
                "compose_content": compose_content
            }
        
        else:
            raise ValueError(f"未知的主机类型: {host_type}")
    
    @staticmethod
    def _parse_docker_run_command(command: str) -> Dict[str, Any]:
        """
        解析docker run命令参数
        
        Args:
            command: docker run的参数字符串
        
        Returns:
            解析后的参数字典
        """
        result = {
            "container_name": None,
            "image": None,
            "ports": [],
            "env": [],
            "volumes": [],
            "restart_policy": "always"
        }
        
        # 处理多行命令和反斜杠续行符
        command = re.sub(r'\\\s*\n\s*', ' ', command)
        command = re.sub(r'\\\\\s*\n\s*', ' ', command)
        command = re.sub(r'\s+', ' ', command).strip()
        
        try:
            # 使用shlex解析命令
            parts = shlex.split(command)
            
            i = 0
            while i < len(parts):
                part = parts[i]
                
                # 解析--name
                if part == "--name" and i + 1 < len(parts):
                    result["container_name"] = parts[i + 1]
                    i += 2
                    continue
                
                # 解析-p或--publish
                if part in ["-p", "--publish"] and i + 1 < len(parts):
                    result["ports"].append(parts[i + 1])
                    i += 2
                    continue
                
                # 解析-e或--env
                if part in ["-e", "--env"] and i + 1 < len(parts):
                    result["env"].append(parts[i + 1])
                    i += 2
                    continue
                
                # 解析-v或--volume
                if part in ["-v", "--volume"] and i + 1 < len(parts):
                    result["volumes"].append(parts[i + 1])
                    i += 2
                    continue
                
                # 解析--restart
                if part == "--restart" and i + 1 < len(parts):
                    result["restart_policy"] = parts[i + 1]
                    i += 2
                    continue
                
                # 解析-d或--detach
                if part in ["-d", "--detach"]:
                    i += 1
                    continue
                
                # 其他参数，可能是镜像名称（通常是最后一个）
                if not part.startswith("-"):
                    # 可能是镜像名称
                    if not result["image"]:
                        result["image"] = part
                
                i += 1
            
            # 如果没找到镜像，尝试从最后获取
            if not result["image"] and parts:
                # 镜像通常是最后一个非选项参数
                for part in reversed(parts):
                    if not part.startswith("-") and ":" in part:
                        result["image"] = part
                        break
            
        except Exception as e:
            logger.warning(f"解析docker run命令失败: {e}, 使用原始命令")
            # 如果解析失败，尝试简单提取镜像名称
            if not result["image"]:
                # 尝试匹配镜像格式
                image_match = re.search(r'([\w\.\-:\/]+(?::[\w\.\-]+)?)$', command)
                if image_match:
                    result["image"] = image_match.group(1)
        
        return result


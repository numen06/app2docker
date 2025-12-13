# backend/agent/deploy_executor.py
"""
部署执行器
负责解析 YAML 部署配置，执行 docker run 或 docker-compose 部署
"""
import os
import subprocess
import yaml
import logging
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
    
    def _build_docker_run_command(
        self,
        docker_config: Dict[str, Any],
        context: Dict[str, Any]
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
            docker_config.get("container_name", ""),
            context
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
        self,
        docker_config: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str
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
                docker_config.get("container_name", ""),
                context
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
                "start_period": "40s"
            }
        
        # 构建完整的 compose 配置
        compose_config = {
            "version": "3.8",
            "services": {
                "app": service_config
            }
        }
        
        # 写入文件
        with open(compose_file, "w", encoding="utf-8") as f:
            yaml.dump(compose_config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"创建 docker-compose.yml: {compose_file}")
        return compose_file
    
    def execute_deploy(
        self,
        deploy_config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        deploy_mode: Optional[str] = None
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
        
        docker_config = deploy_config.get("docker", {})
        if not docker_config:
            raise ValueError("部署配置中缺少 docker 配置")
        
        if deploy_mode is None:
            deploy_mode = deploy_config.get("deploy_mode", "docker_run")
        
        try:
            if deploy_mode == "docker_compose":
                # 使用 docker-compose 部署
                task_id = context.get("task_id", "default")
                compose_file = self._create_docker_compose_file(
                    docker_config,
                    context,
                    task_id
                )
                
                # 执行 docker-compose up
                cmd = ["docker-compose", "-f", compose_file, "up", "-d"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "message": "部署成功",
                        "output": result.stdout,
                        "compose_file": compose_file
                    }
                else:
                    return {
                        "success": False,
                        "message": "部署失败",
                        "error": result.stderr,
                        "output": result.stdout
                    }
            
            else:
                # 使用 docker run 部署
                cmd = self._build_docker_run_command(docker_config, context)
                
                logger.info(f"执行命令: {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode == 0:
                    container_id = result.stdout.strip()
                    return {
                        "success": True,
                        "message": "部署成功",
                        "container_id": container_id,
                        "output": result.stdout
                    }
                else:
                    return {
                        "success": False,
                        "message": "部署失败",
                        "error": result.stderr,
                        "output": result.stdout
                    }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "部署超时",
                "error": "命令执行超过 300 秒"
            }
        except Exception as e:
            logger.exception("部署执行异常")
            return {
                "success": False,
                "message": "部署异常",
                "error": str(e)
            }
    
    def stop_deploy(
        self,
        container_name: str,
        deploy_mode: str = "docker_run"
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
                                cmd,
                                capture_output=True,
                                text=True,
                                timeout=60
                            )
                            return {
                                "success": result.returncode == 0,
                                "message": "停止成功" if result.returncode == 0 else "停止失败",
                                "output": result.stdout,
                                "error": result.stderr if result.returncode != 0 else None
                            }
                
                return {
                    "success": False,
                    "message": "未找到对应的 compose 文件"
                }
            
            else:
                # 使用 docker stop 和 docker rm
                cmd_stop = ["docker", "stop", container_name]
                cmd_rm = ["docker", "rm", container_name]
                
                result_stop = subprocess.run(
                    cmd_stop,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                result_rm = subprocess.run(
                    cmd_rm,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                success = result_stop.returncode == 0 and result_rm.returncode == 0
                return {
                    "success": success,
                    "message": "停止成功" if success else "停止失败",
                    "output": f"{result_stop.stdout}\n{result_rm.stdout}",
                    "error": result_stop.stderr if result_stop.returncode != 0 else result_rm.stderr
                }
        
        except Exception as e:
            logger.exception("停止部署异常")
            return {
                "success": False,
                "message": "停止异常",
                "error": str(e)
            }


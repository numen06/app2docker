# backend/deploy_executors/portainer_executor.py
"""
Portainer 主机执行器
通过 Portainer API 执行部署
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Callable

from backend.deploy_executors.base import DeployExecutor
from backend.portainer_client import PortainerClient
from backend.database import get_db_session
from backend.models import AgentHost

logger = logging.getLogger(__name__)


class PortainerExecutor(DeployExecutor):
    """Portainer 主机执行器"""
    
    def __init__(self, host_info: Dict[str, Any]):
        """
        初始化 Portainer 执行器
        
        Args:
            host_info: 主机信息字典，必须包含：
                - host_id: 主机ID
                - name: 主机名称
                - portainer_url: Portainer URL
                - portainer_endpoint_id: Portainer Endpoint ID
                - status: 主机状态（online/offline）
        """
        super().__init__(host_info)
        self.host_id = host_info.get("host_id")
        self.portainer_url = host_info.get("portainer_url")
        self.portainer_endpoint_id = host_info.get("portainer_endpoint_id")
        
        if not self.host_id:
            raise ValueError("host_info 必须包含 host_id")
        if not self.portainer_url:
            raise ValueError("host_info 必须包含 portainer_url")
        if not self.portainer_endpoint_id:
            raise ValueError("host_info 必须包含 portainer_endpoint_id")
    
    def can_execute(self) -> bool:
        """
        检查是否可以执行
        
        Returns:
            是否可以执行（主机是否在线且有API Key）
        """
        if self.host_info.get("status") != "online":
            return False
        
        # 检查是否有API Key
        db = get_db_session()
        try:
            host_obj = db.query(AgentHost).filter(AgentHost.host_id == self.host_id).first()
            return host_obj is not None and host_obj.portainer_api_key is not None
        finally:
            db.close()
    
    def _get_portainer_client(self) -> PortainerClient:
        """
        获取 Portainer 客户端
        
        Returns:
            PortainerClient 实例
        """
        # 从数据库获取 API Key
        db = get_db_session()
        try:
            host_obj = db.query(AgentHost).filter(AgentHost.host_id == self.host_id).first()
            if not host_obj or not host_obj.portainer_api_key:
                raise ValueError("Portainer API Key 未配置")
            api_key = host_obj.portainer_api_key
        finally:
            db.close()
        
        return PortainerClient(
            self.portainer_url,
            api_key,
            self.portainer_endpoint_id
        )
    
    async def execute(
        self,
        deploy_config: Dict[str, Any],
        task_id: str,
        target_name: str,
        context: Optional[Dict[str, Any]] = None,
        update_status_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        执行部署任务（通过 Portainer API）
        
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
                "message": "Portainer 主机离线或 API Key 未配置",
                "host_type": "portainer",
                "deploy_method": "portainer_api"
            }
        
        logger.info(f"[Portainer] 开始执行 Portainer 部署任务: task_id={task_id}, target={target_name}, host={self.host_name}")
        
        try:
            client = self._get_portainer_client()
            deploy_mode = deploy_config.get("deploy_mode", "docker_run")
            redeploy = deploy_config.get("redeploy", False)
            
            logger.info(f"部署模式: {deploy_mode}, 重新发布: {redeploy}")
            
            # 如果需要重新发布，先清理
            if redeploy:
                logger.info(f"开始清理已有部署...")
                if update_status_callback:
                    update_status_callback("正在清理已有部署...")
                
                if deploy_mode == "docker_compose":
                    # 尝试删除 Stack
                    stack_name = f"{context.get('app', {}).get('name', 'app') if context else 'app'}-{target_name}"
                    try:
                        client._request('DELETE', f'/stacks', params={
                            "endpointId": self.portainer_endpoint_id,
                            "name": stack_name
                        })
                    except:
                        pass
                else:
                    # 尝试删除容器
                    container_name = deploy_config.get("container_name", "")
                    if container_name:
                        # 从命令中提取容器名
                        command = deploy_config.get("command", "")
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
            if update_status_callback:
                update_status_callback(f"正在执行 {deploy_mode} 部署...")
            
            if deploy_mode == "docker_compose":
                # Docker Compose 部署
                stack_name = f"{context.get('app', {}).get('name', 'app') if context else 'app'}-{target_name}"
                compose_content = deploy_config.get("compose_content", "")
                
                if not compose_content:
                    return {
                        "success": False,
                        "message": "Docker Compose 模式需要提供 compose_content",
                        "host_type": "portainer",
                        "deploy_method": "portainer_api"
                    }
                
                logger.info(f"部署 Docker Compose Stack: {stack_name}")
                
                # 使用重试机制执行部署
                result = None
                max_retries = 3
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            wait_time = attempt * 2
                            logger.info(f"第 {attempt + 1} 次尝试部署 Stack（等待 {wait_time} 秒后重试）...")
                            if update_status_callback:
                                update_status_callback(f"Stack 部署失败，{wait_time}秒后重试（{attempt + 1}/{max_retries}）...")
                            await asyncio.sleep(wait_time)
                        
                        result = client.deploy_stack(stack_name, compose_content)
                        logger.info(f"Docker Compose 部署结果: {result}")
                        break
                        
                    except Exception as e:
                        last_error = str(e)
                        error_msg = last_error.lower()
                        
                        if "connection reset" in error_msg or "connection aborted" in error_msg:
                            if attempt < max_retries - 1:
                                logger.warning(f"Stack 部署时连接被重置（尝试 {attempt + 1}/{max_retries}）: {e}")
                                continue
                            else:
                                logger.error(f"Stack 部署失败（{max_retries}次重试后）: {e}")
                                result = {
                                    "success": False,
                                    "message": f"Stack 部署失败：连接被重置（已重试 {max_retries} 次），可能是 Portainer 服务器不稳定或网络问题"
                                }
                        else:
                            logger.error(f"[Portainer] Stack 部署失败（不可重试的错误）: {e}")
                            result = {
                                "success": False,
                                "message": f"Stack 部署失败: {last_error}",
                                "host_type": "portainer",
                                "deploy_method": "portainer_api",
                                "host_name": target_name
                            }
                            break
                
                if result is None:
                    result = {
                        "success": False,
                        "message": f"Stack 部署失败: {last_error or '未知错误'}",
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": target_name
                    }
                
                # 统一结果格式
                if result:
                    result.setdefault("host_type", "portainer")
                    result.setdefault("deploy_method", "portainer_api")
                    result.setdefault("host_name", target_name)
                
                return result
            else:
                # Docker Run 部署
                container_name = deploy_config.get("container_name", f"{context.get('app', {}).get('name', 'app') if context else 'app'}-{target_name}")
                image_template = deploy_config.get("image_template", "")
                command = deploy_config.get("command", "")
                
                # 从命令中提取镜像（如果未提供image_template）
                if not image_template and command:
                    import shlex
                    import re
                    command_clean = re.sub(r'\\\s*\n\s*', ' ', command)
                    command_clean = re.sub(r'\\\\\s*\n\s*', ' ', command_clean)
                    command_clean = re.sub(r'\s+', ' ', command_clean).strip()
                    cmd_parts = shlex.split(command_clean)
                    image_template = cmd_parts[-1] if cmd_parts else ""
                
                if not image_template:
                    return {
                        "success": False,
                        "message": "无法确定镜像名称",
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": target_name
                    }
                
                logger.info(f"[Portainer] 部署 Docker 容器: name={container_name}, image={image_template}")
                
                # 解析命令参数
                ports = deploy_config.get("ports", [])
                env = deploy_config.get("env", [])
                volumes = deploy_config.get("volumes", [])
                restart_policy = deploy_config.get("restart_policy", "always")
                
                # 使用重试机制执行部署
                result = None
                max_retries = 3
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        if attempt > 0:
                            wait_time = attempt * 2
                            logger.info(f"第 {attempt + 1} 次尝试部署（等待 {wait_time} 秒后重试）...")
                            if update_status_callback:
                                update_status_callback(f"部署失败，{wait_time}秒后重试（{attempt + 1}/{max_retries}）...")
                            await asyncio.sleep(wait_time)
                        
                        result = client.deploy_container(
                            container_name,
                            image_template,
                            command=command if command else None,
                            ports=ports,
                            env=env,
                            volumes=volumes,
                            restart_policy=restart_policy
                        )
                        
                        logger.info(f"Docker Run 部署结果: {result}")
                        break
                        
                    except Exception as e:
                        last_error = str(e)
                        error_msg = last_error.lower()
                        
                        if "connection reset" in error_msg or "connection aborted" in error_msg:
                            if attempt < max_retries - 1:
                                logger.warning(f"[Portainer] 部署时连接被重置（尝试 {attempt + 1}/{max_retries}）: {e}")
                                continue
                            else:
                                logger.error(f"[Portainer] 部署失败（{max_retries}次重试后）: {e}")
                                result = {
                                    "success": False,
                                    "message": f"部署失败：连接被重置（已重试 {max_retries} 次），可能是 Portainer 服务器不稳定或网络问题",
                                    "host_type": "portainer",
                                    "deploy_method": "portainer_api",
                                    "host_name": target_name
                                }
                        else:
                            logger.error(f"[Portainer] 部署失败（不可重试的错误）: {e}")
                            result = {
                                "success": False,
                                "message": f"部署失败: {last_error}",
                                "host_type": "portainer",
                                "deploy_method": "portainer_api",
                                "host_name": target_name
                            }
                            break
                
                if result is None:
                    result = {
                        "success": False,
                        "message": f"部署失败: {last_error or '未知错误'}",
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": target_name
                    }
                
                # 统一结果格式
                if result:
                    result.setdefault("host_type", "portainer")
                    result.setdefault("deploy_method", "portainer_api")
                    result.setdefault("host_name", target_name)
                
                return result
        
        except Exception as e:
            import traceback
            error_msg = f"Portainer 部署失败: {str(e)}"
            logger.exception(f"Portainer 部署失败: task_id={task_id}, target={target_name}")
            traceback.print_exc()
            
            return {
                "success": False,
                "message": error_msg,
                "host_type": "portainer",
                "deploy_method": "portainer_api",
                "error": str(e)
            }


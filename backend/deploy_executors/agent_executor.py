# backend/deploy_executors/agent_executor.py
"""
Agent 主机执行器
通过 WebSocket 发送部署任务到 Agent
"""
import logging
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
        update_status_callback: Optional[Callable[[str], None]] = None
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
                "deploy_method": "websocket"
            }
        
        logger.info(f"[Agent] 开始部署: task_id={task_id}, host={self.host_name}")
        
        # 记录命令信息
        if update_status_callback:
            steps = deploy_config.get("steps")
            if steps and isinstance(steps, list):
                update_status_callback(f"[Agent] 部署配置（多步骤模式，共 {len(steps)} 个步骤）")
                for idx, step in enumerate(steps, 1):
                    step_name = step.get("name", f"步骤 {idx}")
                    step_command = step.get("command", "").strip()
                    if step_command:
                        update_status_callback(f"[Agent] 步骤 {idx}: {step_name} - {step_command}")
            else:
                deploy_mode = deploy_config.get("deploy_mode") or deploy_config.get("type", "docker_run")
                command = deploy_config.get("command", "")
                compose_content = deploy_config.get("compose_content", "")
                
                if deploy_mode == "docker_compose":
                    if command:
                        update_status_callback(f"[Agent] 执行命令: docker-compose {command}")
                    if compose_content:
                        compose_preview = compose_content.split('\n')[:5]
                        update_status_callback(f"[Agent] docker-compose.yml 内容预览:\n" + "\n".join([f"  {line}" for line in compose_preview]))
                else:
                    if command:
                        update_status_callback(f"[Agent] 执行命令: docker run {command}")
            
            update_status_callback(f"[Agent] 正在发送部署任务到 {self.host_name}...")
        
        # 构建部署消息（推送给Agent的统一格式）
        deploy_message = {
            "type": "deploy",
            "task_id": task_id,
            "deploy_config": deploy_config,  # 统一的docker配置格式
            "context": context or {},  # 模板变量上下文
            "target_name": target_name
        }
        
        # 发送部署任务到 Agent
        success = await connection_manager.send_message(self.host_id, deploy_message)
        
        if not success:
            return {
                "success": False,
                "message": f"无法发送任务到 Agent: {self.host_name}",
                "host_type": "agent",
                "deploy_method": "websocket",
                "host_id": self.host_id
            }
        
        return {
            "success": True,
            "message": f"任务已发送到 Agent: {self.host_name}",
            "host_type": "agent",
            "deploy_method": "websocket",
            "host_id": self.host_id
        }


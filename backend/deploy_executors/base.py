# backend/deploy_executors/base.py
"""
部署执行器基类
定义统一的执行接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DeployExecutor(ABC):
    """部署执行器抽象基类"""
    
    def __init__(self, host_info: Dict[str, Any]):
        """
        初始化执行器
        
        Args:
            host_info: 主机信息字典，包含主机类型、连接信息等
        """
        self.host_info = host_info
        self.host_type = host_info.get("host_type", "unknown")
        self.host_name = host_info.get("name", "unknown")
    
    @abstractmethod
    async def execute(
        self,
        deploy_config: Dict[str, Any],
        task_id: str,
        target_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行部署任务
        
        Args:
            deploy_config: 部署配置（已适配的命令/脚本）
            task_id: 任务ID
            target_name: 目标名称
            context: 模板变量上下文（可选）
        
        Returns:
            执行结果字典，格式：
            {
                "success": bool,
                "message": str,
                "host_type": str,
                "deploy_method": str,
                "error": str (可选),
                "output": str (可选)
            }
        """
        pass
    
    @abstractmethod
    def can_execute(self) -> bool:
        """
        检查是否可以执行（如主机是否在线等）
        
        Returns:
            是否可以执行
        """
        pass
    
    def get_host_info(self) -> Dict[str, Any]:
        """
        获取主机信息
        
        Returns:
            主机信息字典
        """
        return self.host_info


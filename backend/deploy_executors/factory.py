# backend/deploy_executors/factory.py
"""
执行器工厂
根据主机类型创建对应的执行器
"""
import logging
from typing import Dict, Any, Optional

from backend.deploy_executors.base import DeployExecutor
from backend.deploy_executors.agent_executor import AgentExecutor
from backend.deploy_executors.portainer_executor import PortainerExecutor
from backend.deploy_executors.ssh_executor import SSHExecutor
from backend.agent_host_manager import AgentHostManager
from backend.host_manager import HostManager

logger = logging.getLogger(__name__)


class ExecutorFactory:
    """执行器工厂"""
    
    def __init__(self):
        """初始化工厂"""
        self.agent_manager = AgentHostManager()
        self.host_manager = HostManager()
    
    def create_executor(
        self,
        host_type: str,
        host_name: str
    ) -> Optional[DeployExecutor]:
        """
        创建执行器
        
        Args:
            host_type: 主机类型（agent、portainer、ssh）
            host_name: 主机名称
        
        Returns:
            执行器实例，如果主机不存在则返回None
        """
        if host_type == "agent":
            return self._create_agent_executor(host_name)
        elif host_type == "portainer":
            return self._create_portainer_executor(host_name)
        elif host_type == "ssh":
            return self._create_ssh_executor(host_name)
        else:
            logger.error(f"未知的主机类型: {host_type}")
            return None
    
    def _create_agent_executor(self, host_name: str) -> Optional[AgentExecutor]:
        """创建Agent执行器"""
        agent_hosts = self.agent_manager.list_agent_hosts()
        agent_host = None
        
        for host in agent_hosts:
            if host.get("name") == host_name and host.get("host_type") == "agent":
                agent_host = host
                break
        
        if not agent_host:
            logger.error(f"Agent 主机不存在: {host_name}")
            return None
        
        try:
            return AgentExecutor(agent_host)
        except Exception as e:
            logger.error(f"创建 Agent 执行器失败: {e}")
            return None
    
    def _create_portainer_executor(self, host_name: str) -> Optional[PortainerExecutor]:
        """创建Portainer执行器"""
        agent_hosts = self.agent_manager.list_agent_hosts()
        portainer_host = None
        
        for host in agent_hosts:
            if host.get("name") == host_name and host.get("host_type") == "portainer":
                portainer_host = host
                break
        
        if not portainer_host:
            logger.error(f"Portainer 主机不存在: {host_name}")
            return None
        
        try:
            return PortainerExecutor(portainer_host)
        except Exception as e:
            logger.error(f"创建 Portainer 执行器失败: {e}")
            return None
    
    def _create_ssh_executor(self, host_name: str) -> Optional[SSHExecutor]:
        """创建SSH执行器"""
        ssh_hosts = self.host_manager.list_hosts()
        ssh_host = None
        
        for host in ssh_hosts:
            if host.get("name") == host_name:
                ssh_host = host
                break
        
        if not ssh_host:
            logger.error(f"SSH 主机不存在: {host_name}")
            return None
        
        try:
            return SSHExecutor(ssh_host)
        except Exception as e:
            logger.error(f"创建 SSH 执行器失败: {e}")
            return None


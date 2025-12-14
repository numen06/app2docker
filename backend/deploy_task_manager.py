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


class DeployTaskManager:
    """部署任务管理器"""
    
    def __init__(self, tasks_dir: str = "data/deploy_tasks"):
        """
        初始化部署任务管理器
        
        Args:
            tasks_dir: 任务存储目录
        """
        self.tasks_dir = tasks_dir
        os.makedirs(tasks_dir, exist_ok=True)
        
        self.parser = DeployConfigParser()
        self.agent_manager = AgentHostManager()
        self.host_manager = HostManager()
        self.ssh_executor = SSHDeployExecutor()
        self.executor_factory = ExecutorFactory()
        self.command_adapter = CommandAdapter()
    
    def _get_task_file(self, task_id: str) -> str:
        """获取任务文件路径"""
        return os.path.join(self.tasks_dir, f"{task_id}.yaml")
    
    def _get_task_status_file(self, task_id: str) -> str:
        """获取任务状态文件路径"""
        return os.path.join(self.tasks_dir, f"{task_id}.status.json")
    
    def create_task(
        self,
        config_content: str,
        registry: Optional[str] = None,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建部署任务
        
        Args:
            config_content: YAML 配置内容
            registry: 镜像仓库地址（可选）
            tag: 镜像标签（可选）
        
        Returns:
            任务信息字典
        """
        # 解析配置
        config = self.parser.parse_yaml_content(config_content)
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 保存任务配置
        task_file = self._get_task_file(task_id)
        with open(task_file, "w", encoding="utf-8") as f:
            f.write(config_content)
        
        # 创建任务状态
        status = {
            "task_id": task_id,
            "status": "pending",  # pending, running, completed, failed
            "created_at": datetime.now().isoformat(),
            "registry": registry,
            "tag": tag,
            "targets": [],
            "results": {}
        }
        
        # 初始化每个目标的状态
        targets = config.get("targets", [])
        for target in targets:
            target_name = target.get("name")
            status["targets"].append({
                "name": target_name,
                "mode": target.get("mode"),
                "status": "pending",
                "agent_name": target.get("agent", {}).get("name") if target.get("mode") == "agent" else None,
                "host": target.get("host") if target.get("mode") == "ssh" else None,
            })
        
        # 保存状态
        status_file = self._get_task_status_file(task_id)
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        
        return {
            "task_id": task_id,
            "status": status,
            "config": config
        }
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务信息字典，如果不存在则返回 None
        """
        task_file = self._get_task_file(task_id)
        status_file = self._get_task_status_file(task_id)
        
        if not os.path.exists(task_file):
            return None
        
        # 读取配置
        with open(task_file, "r", encoding="utf-8") as f:
            config_content = f.read()
        config = self.parser.parse_yaml_content(config_content)
        
        # 读取状态
        status = {}
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                status = json.load(f)
        
        return {
            "task_id": task_id,
            "config": config,
            "status": status,
            "config_content": config_content
        }
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        列出所有任务
        
        Returns:
            任务列表
        """
        tasks = []
        
        for file_path in Path(self.tasks_dir).glob("*.yaml"):
            task_id = file_path.stem
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        
        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x.get("status", {}).get("created_at", ""), reverse=True)
        
        return tasks
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否删除成功
        """
        task_file = self._get_task_file(task_id)
        status_file = self._get_task_status_file(task_id)
        
        try:
            if os.path.exists(task_file):
                os.remove(task_file)
            if os.path.exists(status_file):
                os.remove(status_file)
            return True
        except Exception as e:
            print(f"删除任务失败: {e}")
            return False
    
    def update_task_status(
        self,
        task_id: str,
        target_name: Optional[str] = None,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None
    ):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            target_name: 目标名称（如果更新特定目标的状态）
            status: 状态（pending, running, completed, failed）
            result: 执行结果
        """
        status_file = self._get_task_status_file(task_id)
        
        if not os.path.exists(status_file):
            return
        
        # 读取当前状态
        with open(status_file, "r", encoding="utf-8") as f:
            task_status = json.load(f)
        
        # 更新状态
        if target_name:
            # 更新特定目标的状态
            for target in task_status.get("targets", []):
                if target.get("name") == target_name:
                    if status:
                        target["status"] = status
                    if result:
                        target["result"] = result
                    if message:
                        if "messages" not in target:
                            target["messages"] = []
                        target["messages"].append({
                            "time": datetime.now().isoformat(),
                            "message": message
                        })
                    target["updated_at"] = datetime.now().isoformat()
                    break
            
            # 检查是否所有目标都已完成
            all_completed = all(
                t.get("status") in ["completed", "failed"]
                for t in task_status.get("targets", [])
            )
            if all_completed:
                # 检查是否有失败的
                has_failed = any(
                    t.get("status") == "failed"
                    for t in task_status.get("targets", [])
                )
                task_status["status"] = "failed" if has_failed else "completed"
                task_status["completed_at"] = datetime.now().isoformat()
        else:
            # 更新整体状态
            if status:
                task_status["status"] = status
            if result:
                task_status["result"] = result
        
        # 保存状态
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(task_status, f, ensure_ascii=False, indent=2)
    
    async def execute_task(
        self,
        task_id: str,
        target_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        执行部署任务
        
        Args:
            task_id: 任务ID
            target_names: 要执行的目标名称列表（如果为 None，则执行所有目标）
        
        Returns:
            执行结果字典
        """
        # 获取任务信息
        task = self.get_task(task_id)
        if not task:
            return {
                "success": False,
                "message": f"任务不存在: {task_id}"
            }
        
        config = task["config"]
        status = task["status"]
        
        # 构建部署上下文
        context = self.parser.build_deploy_context(
            config,
            registry=status.get("registry"),
            tag=status.get("tag"),
            task_id=task_id
        )
        
        # 获取部署配置（统一格式）
        deploy_config = self.parser.get_deploy_config(config)
        
        # 获取要执行的目标
        targets = config.get("targets", [])
        if target_names:
            targets = [t for t in targets if t.get("name") in target_names]
        
        # 如果任务已完成或失败，重置要执行的目标状态为 pending
        current_status = status.get("status")
        if current_status in ["completed", "failed"]:
            for target in targets:
                target_name = target.get("name")
                # 重置目标状态为 pending
                self.update_task_status(
                    task_id,
                    target_name=target_name,
                    status="pending",
                    result=None,
                    message="任务已重置，准备重新执行"
                )
        
        # 更新任务状态为运行中
        self.update_task_status(task_id, status="running")
        
        # 执行每个目标
        results = {}
        for target in targets:
            target_name = target.get("name")
            
            # 更新目标状态为运行中
            self.update_task_status(task_id, target_name=target_name, status="running")
            
            try:
                # 使用新的执行器架构
                result = await self._execute_target_with_executor(
                    task_id,
                    target,
                    deploy_config,
                    context
                )
                
                results[target_name] = result
                
                # 更新目标状态
                self.update_task_status(
                    task_id,
                    target_name=target_name,
                    status="completed" if result.get("success") else "failed",
                    result=result,
                    message=result.get("message", "")
                )
            
            except Exception as e:
                import traceback
                logger.exception(f"执行目标 {target_name} 时发生异常")
                error_result = {
                    "success": False,
                    "message": f"执行异常: {str(e)}",
                    "error": str(e)
                }
                results[target_name] = error_result
                self.update_task_status(
                    task_id,
                    target_name=target_name,
                    status="failed",
                    result=error_result,
                    message=f"执行异常: {str(e)}"
                )
        
        # 检查整体状态
        all_completed = all(
            r.get("success") is not None
            for r in results.values()
        )
        
        if all_completed:
            has_failed = any(
                not r.get("success", False)
                for r in results.values()
            )
            self.update_task_status(
                task_id,
                status="failed" if has_failed else "completed"
            )
        
        return {
            "success": True,
            "task_id": task_id,
            "results": results
        }
    
    async def _execute_target_with_executor(
        self,
        task_id: str,
        target: Dict[str, Any],
        deploy_config: Dict[str, Any],
        context: Dict[str, Any]
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
                    "deploy_mode": mode
                }
        
        if not host_name:
            return {
                "success": False,
                "message": f"目标 {target_name} 的主机名称未指定",
                "host_type": host_type
            }
        
        # 创建执行器
        executor = self.executor_factory.create_executor(host_type, host_name)
        if not executor:
            return {
                "success": False,
                "message": f"无法创建执行器: 主机 {host_name} ({host_type}) 不存在或配置错误",
                "host_type": host_type,
                "host_name": host_name
            }
        
        # 检查是否可以执行
        if not executor.can_execute():
            return {
                "success": False,
                "message": f"主机不可用: {host_name}",
                "host_type": host_type,
                "host_name": host_name
            }
        
        # 检查是否为多步骤模式
        steps = deploy_config.get("steps")
        if steps and isinstance(steps, list):
            # 多步骤模式：直接传递steps，不进行命令适配
            adapted_config = {
                "steps": steps,
                "redeploy": deploy_config.get("redeploy", False)
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
            
            # 适配命令
            try:
                adapted_config = self.command_adapter.adapt_command(
                    command=command,
                    deploy_type=deploy_type,
                    host_type=host_type,
                    compose_content=compose_content,
                    context=context
                )
            except Exception as e:
                logger.error(f"适配命令失败: {e}")
                return {
                    "success": False,
                    "message": f"适配命令失败: {str(e)}",
                    "host_type": host_type,
                    "error": str(e)
                }
            
            # 合并redeploy等配置
            if deploy_config.get("redeploy"):
                adapted_config["redeploy"] = True
        
        # 创建状态更新回调
        def update_status_callback(message: str):
            self.update_task_status(
                task_id,
                target_name=target_name,
                status="running",
                message=message
            )
        
        # 执行部署
        try:
            result = await executor.execute(
                deploy_config=adapted_config,
                task_id=task_id,
                target_name=target_name,
                context=context,
                update_status_callback=update_status_callback
            )
            return result
        except Exception as e:
            import traceback
            logger.exception(f"执行器执行失败: {e}")
            return {
                "success": False,
                "message": f"执行失败: {str(e)}",
                "host_type": host_type,
                "host_name": host_name,
                "error": str(e)
            }
    
    async def _execute_target_unified(
        self,
        task_id: str,
        target: Dict[str, Any],
        config: Dict[str, Any],
        context: Dict[str, Any]
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
            task_id,
            target,
            deploy_config,
            context
        )
    
    async def _execute_agent_target(
        self,
        task_id: str,
        target: Dict[str, Any],
        config: Dict[str, Any],
        context: Dict[str, Any]
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
            return {
                "success": False,
                "message": f"Agent 主机不存在: {agent_name}"
            }
        
        host_id = agent_host.get("host_id")
        
        # 检查主机是否在线
        if agent_host.get("status") != "online":
            return {
                "success": False,
                "message": f"主机离线: {agent_name}"
            }
        
        host_type = agent_host.get("host_type", "agent")
        
        # 渲染目标配置（统一处理：无论来源是表单还是YAML，都转换为统一的配置格式）
        rendered_target = self.parser.render_target_config(target, context)
        docker_config = rendered_target.get("docker", {})
        
        # 根据主机类型选择部署方式（统一接口，不同实现）
        if host_type == "portainer":
            # Portainer 类型：使用 Portainer API 部署
            logger.info(f"[Portainer] 开始部署: task_id={task_id}, host={agent_name}")
            result = await self._execute_portainer_target(
                agent_host,
                task_id,
                docker_config,
                context,
                target.get("name")
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
                "target_name": target.get("name")
            }
            
            # 发送部署任务到 Agent
            success = await connection_manager.send_message(host_id, deploy_message)
            
            if not success:
                return {
                    "success": False,
                    "message": f"无法发送任务到 Agent: {agent_name}",
                    "host_type": "agent",
                    "deploy_method": "websocket",
                    "host_id": host_id
                }
            
            return {
                "success": True,
                "message": f"任务已发送到 Agent: {agent_name}",
                "host_type": "agent",
                "deploy_method": "websocket",
                "host_id": host_id
            }
    
    async def _execute_ssh_target(
        self,
        task_id: str,
        target: Dict[str, Any],
        config: Dict[str, Any],
        context: Dict[str, Any]
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
        logger.info(f"[SSH] 开始执行 SSH 部署任务: task_id={task_id}, target={target.get('name')}")
        
        try:
            # 更新任务状态为运行中（明确标识主机类型）
            self.update_task_status(
                task_id, 
                target_name=target.get("name"), 
                status="running", 
                message="[SSH] 正在连接 SSH 主机..."
            )
            
            # 获取 SSH 主机配置
            host_name = target.get("host")
            if not host_name:
                return {
                    "success": False,
                    "message": "SSH 主机名称未指定"
                }
            
            # 从数据库获取 SSH 主机信息
            db = get_db_session()
            try:
                host_obj = db.query(Host).filter(Host.name == host_name).first()
                if not host_obj:
                    return {
                        "success": False,
                        "message": f"SSH 主机不存在: {host_name}"
                    }
                
                # 构建 SSH 主机配置
                host_config = {
                    "host": host_obj.host,
                    "port": host_obj.port or 22,
                    "username": host_obj.username,
                    "password": host_obj.password,  # 已加密
                    "private_key": host_obj.private_key,  # 已加密
                    "key_password": host_obj.key_password  # 已加密
                }
            finally:
                db.close()
            
            # 渲染目标配置
            rendered_target = self.parser.render_target_config(target, context)
            docker_config = rendered_target.get("docker", {})
            
            logger.info(f"[SSH] 主机配置: {host_name} ({host_config['host']}:{host_config['port']})")
            self.update_task_status(
                task_id, 
                target_name=target.get("name"), 
                status="running", 
                message=f"[SSH] 正在执行部署到 {host_name}..."
            )
            
            # 获取部署模式
            deploy_mode = docker_config.get("deploy_mode", "docker_run")
            
            # 使用 SSH 部署执行器执行部署
            result = self.ssh_executor.execute_deploy(
                host_config=host_config,
                docker_config=docker_config,
                deploy_mode=deploy_mode
            )
            
            # 统一结果格式：添加主机类型和部署方法标识
            result["host_type"] = "ssh"
            result["deploy_method"] = "ssh_direct"
            result["host_name"] = host_name
            
            logger.info(f"[SSH] 部署结果: {result}")
            
            # 更新任务状态（统一格式）
            status_msg = result.get("message", "部署成功" if result.get("success") else "部署失败")
            
            # 构建详细的状态消息（包含错误详情）
            if not result.get("success"):
                error_detail = result.get("error", "")
                output_detail = result.get("output", "")
                if error_detail:
                    status_msg = f"{status_msg}\n错误详情: {error_detail[:500]}"
                elif output_detail:
                    status_msg = f"{status_msg}\n输出: {output_detail[:500]}"
            
            if result.get("success"):
                logger.info(f"[SSH] 部署成功: task_id={task_id}, target={target.get('name')}, host={host_name}")
                self.update_task_status(
                    task_id, 
                    target_name=target.get("name"), 
                    status="completed", 
                    result=result,
                    message=f"[SSH] {status_msg}"
                )
            else:
                # 记录完整的错误信息
                error_info = {
                    "message": result.get("message", "部署失败"),
                    "error": result.get("error", ""),
                    "output": result.get("output", ""),
                    "exit_status": result.get("exit_status", ""),
                    "command": result.get("command", "")
                }
                logger.error(f"[SSH] 部署失败: task_id={task_id}, target={target.get('name')}, host={host_name}, details={error_info}")
                self.update_task_status(
                    task_id, 
                    target_name=target.get("name"), 
                    status="failed", 
                    result=result,
                    message=f"[SSH] {status_msg}"
                )
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"SSH 部署失败: {str(e)}"
            logger.exception(f"[SSH] 部署异常: task_id={task_id}, target={target.get('name')}")
            traceback.print_exc()
            
            # 更新任务状态为失败（统一格式）
            error_result = {
                "success": False,
                "message": error_msg,
                "host_type": "ssh",
                "deploy_method": "ssh_direct",
                "error": str(e)
            }
            self.update_task_status(
                task_id, 
                target_name=target.get("name"), 
                status="failed", 
                result=error_result,
                message=f"[SSH] {error_msg}"
            )
            
            return error_result
    
    async def _execute_portainer_target(
        self,
        agent_host: Dict[str, Any],
        task_id: str,
        docker_config: Dict[str, Any],
        context: Dict[str, Any],
        target_name: str
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
        
        logger.info(f"[Portainer] 开始执行 Portainer 部署任务: task_id={task_id}, target={target_name}, host={agent_host.get('name')}")
        
        try:
            # 更新任务状态为运行中（明确标识主机类型）
            self.update_task_status(task_id, target_name=target_name, status="running", message="[Portainer] 正在连接 Portainer...")
            # 从数据库获取完整的 Portainer 信息（包括 API Key）
            db = get_db_session()
            try:
                host_obj = db.query(AgentHost).filter(AgentHost.host_id == agent_host.get("host_id")).first()
                if not host_obj or not host_obj.portainer_api_key:
                    return {
                        "success": False,
                        "message": "Portainer API Key 未配置",
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": agent_host.get("name")
                    }
                portainer_api_key = host_obj.portainer_api_key
            finally:
                db.close()
            
            # 创建 Portainer 客户端
            logger.info(f"[Portainer] 创建 Portainer 客户端: URL={agent_host.get('portainer_url')}, EndpointID={agent_host.get('portainer_endpoint_id')}")
            self.update_task_status(task_id, target_name=target_name, status="running", message="[Portainer] 正在创建 Portainer 客户端...")
            
            client = PortainerClient(
                agent_host.get("portainer_url"),
                portainer_api_key,
                agent_host.get("portainer_endpoint_id")
            )
            
            deploy_mode = docker_config.get("deploy_mode", "docker_run")
            redeploy = docker_config.get("redeploy", False)
            
            logger.info(f"部署模式: {deploy_mode}, 重新发布: {redeploy}")
            
            # 如果需要重新发布，先清理
            if redeploy:
                logger.info(f"开始清理已有部署...")
                self.update_task_status(task_id, target_name=target_name, status="running", message="正在清理已有部署...")
                if deploy_mode == "docker_compose":
                    # 尝试删除 Stack
                    stack_name = f"{context.get('app', {}).get('name', 'app')}-{target_name}"
                    try:
                        client._request('DELETE', f'/stacks', params={"endpointId": agent_host.get("portainer_endpoint_id"), "name": stack_name})
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
            self.update_task_status(task_id, target_name=target_name, status="running", message=f"正在执行 {deploy_mode} 部署...")
            
            if deploy_mode == "docker_compose":
                # Docker Compose 部署
                stack_name = f"{context.get('app', {}).get('name', 'app')}-{target_name}"
                compose_content = docker_config.get("compose_content", "")
                
                if not compose_content:
                    return {
                        "success": False,
                        "message": "Docker Compose 模式需要提供 compose_content"
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
                            logger.info(f"第 {attempt + 1} 次尝试部署 Stack（等待 {wait_time} 秒后重试）...")
                            self.update_task_status(
                                task_id, 
                                target_name=target_name, 
                                status="running", 
                                message=f"Stack 部署失败，{wait_time}秒后重试（{attempt + 1}/{max_retries}）..."
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
                        if "connection reset" in error_msg or "connection aborted" in error_msg:
                            if attempt < max_retries - 1:
                                logger.warning(f"Stack 部署时连接被重置（尝试 {attempt + 1}/{max_retries}）: {e}")
                                continue  # 继续重试
                            else:
                                # 最后一次重试也失败
                                logger.error(f"Stack 部署失败（{max_retries}次重试后）: {e}")
                                result = {
                                    "success": False,
                                    "message": f"Stack 部署失败：连接被重置（已重试 {max_retries} 次），可能是 Portainer 服务器不稳定或网络问题"
                                }
                        else:
                            # 其他错误，不重试
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
                
                # 更新任务状态（统一格式）
                if result.get("success"):
                    logger.info(f"[Portainer] Stack 部署成功: task_id={task_id}, target={target_name}")
                    status_msg = result.get("message", "Stack 部署成功")
                    self.update_task_status(
                        task_id, 
                        target_name=target_name, 
                        status="completed", 
                        result=result,
                        message=f"[Portainer] {status_msg}"
                    )
                else:
                    logger.error(f"[Portainer] Stack 部署失败: task_id={task_id}, target={target_name}, error={result.get('message')}")
                    status_msg = result.get("message", "Stack 部署失败")
                    self.update_task_status(
                        task_id, 
                        target_name=target_name, 
                        status="failed", 
                        result=result,
                        message=f"[Portainer] {status_msg}"
                    )
                
                return result
            else:
                # Docker Run 部署
                container_name = docker_config.get("container_name", f"{context.get('app', {}).get('name', 'app')}-{target_name}")
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
                        command = re.sub(r'\\\s*\n\s*', ' ', command)
                        command = re.sub(r'\\\\\s*\n\s*', ' ', command)
                        command = re.sub(r'\s+', ' ', command).strip()
                        cmd_parts = shlex.split(command)
                        # 镜像通常是最后一个参数
                        image = cmd_parts[-1] if cmd_parts else ""
                
                if not image:
                    error_msg = "无法确定镜像名称"
                    logger.error(error_msg)
                    self.update_task_status(
                        task_id, 
                        target_name=target_name, 
                        status="failed", 
                        result={"success": False, "message": error_msg},
                        message=error_msg
                    )
                    error_result = {
                        "success": False,
                        "message": error_msg,
                        "host_type": "portainer",
                        "deploy_method": "portainer_api",
                        "host_name": target_name
                    }
                    self.update_task_status(
                        task_id, 
                        target_name=target_name, 
                        status="failed", 
                        result=error_result,
                        message=f"[Portainer] {error_msg}"
                    )
                    return error_result
                
                logger.info(f"[Portainer] 部署 Docker 容器: name={container_name}, image={image}")
                
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
                            logger.info(f"第 {attempt + 1} 次尝试部署（等待 {wait_time} 秒后重试）...")
                            self.update_task_status(
                                task_id, 
                                target_name=target_name, 
                                status="running", 
                                message=f"部署失败，{wait_time}秒后重试（{attempt + 1}/{max_retries}）..."
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
                            restart_policy=restart_policy
                        )
                        
                        logger.info(f"Docker Run 部署结果: {result}")
                        break  # 成功，退出重试循环
                        
                    except Exception as e:
                        last_error = str(e)
                        error_msg = last_error.lower()
                        
                        # 如果是连接重置错误，可以重试
                        if "connection reset" in error_msg or "connection aborted" in error_msg:
                            if attempt < max_retries - 1:
                                logger.warning(f"[Portainer] 部署时连接被重置（尝试 {attempt + 1}/{max_retries}）: {e}")
                                continue  # 继续重试
                            else:
                                # 最后一次重试也失败
                                logger.error(f"[Portainer] 部署失败（{max_retries}次重试后）: {e}")
                                result = {
                                    "success": False,
                                    "message": f"部署失败：连接被重置（已重试 {max_retries} 次），可能是 Portainer 服务器不稳定或网络问题",
                                    "host_type": "portainer",
                                    "deploy_method": "portainer_api",
                                    "host_name": target_name
                                }
                        else:
                            # 其他错误，不重试
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
            
            # 统一结果格式：添加主机类型和部署方法标识
            if result:
                result.setdefault("host_type", "portainer")
                result.setdefault("deploy_method", "portainer_api")
                result.setdefault("host_name", target_name)
            
            # 更新任务状态（统一格式）
            if result.get("success"):
                logger.info(f"[Portainer] 部署成功: task_id={task_id}, target={target_name}")
                status_msg = result.get("message", "部署成功")
                self.update_task_status(
                    task_id, 
                    target_name=target_name, 
                    status="completed", 
                    result=result,
                    message=f"[Portainer] {status_msg}"
                )
            else:
                logger.error(f"[Portainer] 部署失败: task_id={task_id}, target={target_name}, error={result.get('message')}")
                status_msg = result.get("message", "部署失败")
                self.update_task_status(
                    task_id, 
                    target_name=target_name, 
                    status="failed", 
                    result=result,
                    message=f"[Portainer] {status_msg}"
                )
            
            return result
        
        except Exception as e:
            import traceback
            error_msg = f"Portainer 部署失败: {str(e)}"
            logger.exception(f"Portainer 部署失败: task_id={task_id}, target={target_name}")
            traceback.print_exc()
            
            # 更新任务状态为失败
            self.update_task_status(
                task_id, 
                target_name=target_name, 
                status="failed", 
                result={"success": False, "message": error_msg},
                message=error_msg
            )
            
            return {
                "success": False,
                "message": error_msg
            }


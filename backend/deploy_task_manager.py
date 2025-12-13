# backend/deploy_task_manager.py
"""
部署任务管理器
管理部署任务的生命周期，通过 WebSocket 分发任务到 Agent，跟踪任务执行状态
"""
import os
import uuid
import yaml
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from backend.deploy_config_parser import DeployConfigParser
from backend.websocket_handler import connection_manager
from backend.agent_host_manager import AgentHostManager


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
        result: Optional[Dict[str, Any]] = None
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
        
        # 获取要执行的目标
        targets = config.get("targets", [])
        if target_names:
            targets = [t for t in targets if t.get("name") in target_names]
        
        # 更新任务状态为运行中
        self.update_task_status(task_id, status="running")
        
        # 执行每个目标
        results = {}
        for target in targets:
            target_name = target.get("name")
            mode = target.get("mode")
            
            # 更新目标状态为运行中
            self.update_task_status(task_id, target_name=target_name, status="running")
            
            try:
                if mode == "agent":
                    # Agent 模式：通过 WebSocket 发送任务
                    result = await self._execute_agent_target(
                        task_id,
                        target,
                        config,
                        context
                    )
                elif mode == "ssh":
                    # SSH 模式：暂不支持，返回错误
                    result = {
                        "success": False,
                        "message": "SSH 模式暂未实现"
                    }
                else:
                    result = {
                        "success": False,
                        "message": f"未知的模式: {mode}"
                    }
                
                results[target_name] = result
                
                # 更新目标状态
                self.update_task_status(
                    task_id,
                    target_name=target_name,
                    status="completed" if result.get("success") else "failed",
                    result=result
                )
            
            except Exception as e:
                error_result = {
                    "success": False,
                    "message": f"执行异常: {str(e)}"
                }
                results[target_name] = error_result
                self.update_task_status(
                    task_id,
                    target_name=target_name,
                    status="failed",
                    result=error_result
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
        
        # 检查 Agent 是否在线
        if agent_host.get("status") != "online":
            return {
                "success": False,
                "message": f"Agent 主机离线: {agent_name}"
            }
        
        # 渲染目标配置（统一处理：无论来源是表单还是YAML，都转换为统一的配置格式）
        rendered_target = self.parser.render_target_config(target, context)
        
        # 构建部署消息（推送给Agent的统一格式）
        # deploy_config 包含完整的docker配置，Agent会根据此配置执行部署
        deploy_message = {
            "type": "deploy",
            "task_id": task_id,
            "deploy_config": rendered_target.get("docker", {}),  # 统一的docker配置格式
            "context": context,  # 模板变量上下文
            "target_name": target.get("name")
        }
        
        # 发送部署任务到 Agent
        success = await connection_manager.send_message(host_id, deploy_message)
        
        if not success:
            return {
                "success": False,
                "message": f"无法发送任务到 Agent: {agent_name}"
            }
        
        return {
            "success": True,
            "message": f"任务已发送到 Agent: {agent_name}",
            "host_id": host_id
        }


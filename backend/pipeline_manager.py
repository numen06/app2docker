# backend/pipeline_manager.py
"""流水线管理器 - 用于管理预配置的 Git 构建流水线"""
import json
import os
import uuid
import hmac
import hashlib
import threading
from datetime import datetime
from typing import Optional, Dict, List

# 流水线配置文件
PIPELINES_FILE = "data/pipelines.json"


class PipelineManager:
    """流水线管理器"""
    
    def __init__(self):
        self.lock = threading.RLock()
        self.pipelines = {}
        self._load_pipelines()
    
    def _load_pipelines(self):
        """从文件加载流水线配置"""
        if not os.path.exists(PIPELINES_FILE):
            return
        
        try:
            with open(PIPELINES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.pipelines = data.get('pipelines', {})
                print(f"✅ 加载了 {len(self.pipelines)} 个流水线配置")
        except Exception as e:
            print(f"⚠️ 加载流水线配置失败: {e}")
            self.pipelines = {}
    
    def _save_pipelines(self):
        """保存流水线配置到文件"""
        try:
            os.makedirs(os.path.dirname(PIPELINES_FILE), exist_ok=True)
            with open(PIPELINES_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'pipelines': self.pipelines,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存流水线配置失败: {e}")
            raise
    
    def create_pipeline(
        self,
        name: str,
        git_url: str,
        branch: str = None,
        project_type: str = "jar",
        template: str = None,
        image_name: str = None,
        tag: str = "latest",
        push: bool = False,
        push_registry: str = None,
        template_params: dict = None,
        sub_path: str = None,
        use_project_dockerfile: bool = True,
        dockerfile_name: str = "Dockerfile",  # Dockerfile文件名，默认Dockerfile
        webhook_secret: str = None,
        enabled: bool = True,
        description: str = "",
        cron_expression: str = None,
        webhook_branch_filter: bool = False,
        webhook_use_push_branch: bool = True,
        branch_tag_mapping: dict = None,  # 分支到标签的映射，如 {"main": "latest", "dev": "dev"}
    ) -> str:
        """
        创建流水线配置
        
        Args:
            name: 流水线名称
            git_url: Git 仓库地址
            branch: 分支名称
            project_type: 项目类型
            template: 模板名称
            image_name: 镜像名称
            tag: 镜像标签
            push: 是否推送
            push_registry: 推送仓库
            template_params: 模板参数
            sub_path: 子路径
            use_project_dockerfile: 是否使用项目中的 Dockerfile
            dockerfile_name: Dockerfile文件名，默认Dockerfile
            webhook_secret: Webhook 密钥
            enabled: 是否启用
            description: 描述
            cron_expression: Cron 表达式（用于定时触发）
        
        Returns:
            pipeline_id: 流水线 ID
        """
        pipeline_id = str(uuid.uuid4())
        
        # 生成 Webhook Token（用于 URL）
        webhook_token = str(uuid.uuid4())
        
        # 如果没有提供 webhook_secret，生成一个
        if not webhook_secret:
            webhook_secret = str(uuid.uuid4())
        
        pipeline = {
            "pipeline_id": pipeline_id,
            "name": name,
            "description": description,
            "enabled": enabled,
            # Git 配置
            "git_url": git_url,
            "branch": branch,
            "sub_path": sub_path,
            # 构建配置
            "project_type": project_type,
            "template": template,
            "image_name": image_name,
            "tag": tag,
            "push": push,
            "push_registry": push_registry,
            "template_params": template_params or {},
            "use_project_dockerfile": use_project_dockerfile,
            "dockerfile_name": dockerfile_name,  # Dockerfile文件名
            # Webhook 配置
            "webhook_token": webhook_token,
            "webhook_secret": webhook_secret,
            "webhook_branch_filter": webhook_branch_filter,  # 是否启用分支过滤
            "webhook_use_push_branch": webhook_use_push_branch,  # 是否使用推送的分支构建
            "branch_tag_mapping": branch_tag_mapping or {},  # 分支到标签的映射
            # 定时触发配置
            "cron_expression": cron_expression,
            "next_run_time": None,  # 下次执行时间
            # 任务绑定
            "current_task_id": None,  # 当前正在执行的任务ID
            "task_history": [],  # 任务历史记录列表
            # 元数据
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_triggered_at": None,
            "trigger_count": 0,
        }
        
        with self.lock:
            self.pipelines[pipeline_id] = pipeline
            self._save_pipelines()
        
        return pipeline_id
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Dict]:
        """获取流水线配置"""
        with self.lock:
            return self.pipelines.get(pipeline_id)
    
    def get_pipeline_by_token(self, webhook_token: str) -> Optional[Dict]:
        """通过 Webhook Token 获取流水线配置"""
        with self.lock:
            for pipeline in self.pipelines.values():
                if pipeline.get("webhook_token") == webhook_token:
                    return pipeline
            return None
    
    def list_pipelines(self, enabled: bool = None) -> List[Dict]:
        """
        列出所有流水线配置
        
        Args:
            enabled: 过滤条件，仅返回启用/禁用的流水线
        
        Returns:
            流水线列表
        """
        with self.lock:
            pipelines = list(self.pipelines.values())
            
            # 过滤启用状态
            if enabled is not None:
                pipelines = [p for p in pipelines if p.get("enabled") == enabled]
            
            # 按创建时间倒序排列
            pipelines.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return pipelines
    
    def update_pipeline(
        self,
        pipeline_id: str,
        name: str = None,
        git_url: str = None,
        branch: str = None,
        project_type: str = None,
        template: str = None,
        image_name: str = None,
        tag: str = None,
        push: bool = None,
        push_registry: str = None,
        template_params: dict = None,
        sub_path: str = None,
        use_project_dockerfile: bool = None,
        dockerfile_name: str = None,
        webhook_secret: str = None,
        enabled: bool = None,
        description: str = None,
        cron_expression: str = None,
        webhook_branch_filter: bool = None,
        webhook_use_push_branch: bool = None,
        branch_tag_mapping: dict = None,
    ) -> bool:
        """
        更新流水线配置
        
        Returns:
            True 表示更新成功，False 表示流水线不存在
        """
        with self.lock:
            if pipeline_id not in self.pipelines:
                return False
            
            pipeline = self.pipelines[pipeline_id]
            
            # 更新字段
            if name is not None:
                pipeline["name"] = name
            if git_url is not None:
                pipeline["git_url"] = git_url
            if branch is not None:
                pipeline["branch"] = branch
            if project_type is not None:
                pipeline["project_type"] = project_type
            if template is not None:
                pipeline["template"] = template
            if image_name is not None:
                pipeline["image_name"] = image_name
            if tag is not None:
                pipeline["tag"] = tag
            if push is not None:
                pipeline["push"] = push
            if push_registry is not None:
                pipeline["push_registry"] = push_registry
            if template_params is not None:
                pipeline["template_params"] = template_params
            if sub_path is not None:
                pipeline["sub_path"] = sub_path
            if use_project_dockerfile is not None:
                pipeline["use_project_dockerfile"] = use_project_dockerfile
            if dockerfile_name is not None:
                pipeline["dockerfile_name"] = dockerfile_name
            if webhook_secret is not None:
                pipeline["webhook_secret"] = webhook_secret
            if enabled is not None:
                pipeline["enabled"] = enabled
            if description is not None:
                pipeline["description"] = description
            if cron_expression is not None:
                pipeline["cron_expression"] = cron_expression
            if webhook_branch_filter is not None:
                pipeline["webhook_branch_filter"] = webhook_branch_filter
            if webhook_use_push_branch is not None:
                pipeline["webhook_use_push_branch"] = webhook_use_push_branch
            if branch_tag_mapping is not None:
                pipeline["branch_tag_mapping"] = branch_tag_mapping
            
            # 更新时间
            pipeline["updated_at"] = datetime.now().isoformat()
            
            self._save_pipelines()
            return True
    
    def delete_pipeline(self, pipeline_id: str) -> bool:
        """
        删除流水线配置
        
        Returns:
            True 表示删除成功，False 表示流水线不存在
        """
        with self.lock:
            if pipeline_id not in self.pipelines:
                return False
            
            del self.pipelines[pipeline_id]
            self._save_pipelines()
            return True
    
    def record_trigger(
        self, 
        pipeline_id: str, 
        task_id: str = None,
        trigger_source: str = "unknown",
        trigger_info: dict = None
    ):
        """记录流水线触发
        
        Args:
            pipeline_id: 流水线 ID
            task_id: 任务 ID，如果提供则绑定到流水线
            trigger_source: 触发来源 ("webhook", "manual", "cron")
            trigger_info: 触发信息（如 webhook 的分支、提交信息等）
        """
        with self.lock:
            if pipeline_id in self.pipelines:
                pipeline = self.pipelines[pipeline_id]
                pipeline["last_triggered_at"] = datetime.now().isoformat()
                pipeline["trigger_count"] = pipeline.get("trigger_count", 0) + 1
                
                if task_id:
                    pipeline["current_task_id"] = task_id
                    
                    # 记录到任务历史
                    if "task_history" not in pipeline:
                        pipeline["task_history"] = []
                    
                    history_entry = {
                        "task_id": task_id,
                        "trigger_source": trigger_source,
                        "triggered_at": datetime.now().isoformat(),
                        "trigger_info": trigger_info or {},
                    }
                    pipeline["task_history"].append(history_entry)
                    
                    # 限制历史记录数量（保留最近100条）
                    if len(pipeline["task_history"]) > 100:
                        pipeline["task_history"] = pipeline["task_history"][-100:]
                
                self._save_pipelines()
    
    def get_pipeline_running_task(self, pipeline_id: str) -> Optional[str]:
        """获取流水线当前正在执行的任务ID
        
        Returns:
            任务ID，如果没有运行中的任务则返回 None
        """
        with self.lock:
            if pipeline_id in self.pipelines:
                return self.pipelines[pipeline_id].get("current_task_id")
            return None
    
    def unbind_task(self, pipeline_id: str):
        """解绑流水线的任务绑定
        
        Args:
            pipeline_id: 流水线 ID
        """
        with self.lock:
            if pipeline_id in self.pipelines:
                self.pipelines[pipeline_id]["current_task_id"] = None
                self._save_pipelines()
    
    def find_pipeline_by_task(self, task_id: str) -> Optional[str]:
        """根据任务ID查找绑定的流水线ID
        
        Args:
            task_id: 任务 ID
            
        Returns:
            流水线 ID，如果没有绑定则返回 None
        """
        with self.lock:
            for pipeline_id, pipeline in self.pipelines.items():
                if pipeline.get("current_task_id") == task_id:
                    return pipeline_id
            return None
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
        signature_header: str = "sha256"
    ) -> bool:
        """
        验证 Webhook 签名（支持 GitHub/GitLab/Gitee 等平台）
        
        Args:
            payload: 请求体（原始字节）
            signature: 签名字符串
            secret: 密钥
            signature_header: 签名算法（sha1 或 sha256）
        
        Returns:
            True 表示签名验证通过
        """
        try:
            # 支持不同的签名格式
            # GitHub: sha256=xxx
            # GitLab: xxx
            # Gitee: xxx
            
            if "=" in signature:
                # GitHub 格式: sha256=xxx
                algo, sig = signature.split("=", 1)
            else:
                # GitLab/Gitee 格式: xxx
                algo = signature_header
                sig = signature
            
            # 计算 HMAC
            if algo.lower() == "sha1":
                mac = hmac.new(secret.encode(), payload, hashlib.sha1)
            elif algo.lower() == "sha256":
                mac = hmac.new(secret.encode(), payload, hashlib.sha256)
            else:
                print(f"❌ 不支持的签名算法: {algo}")
                return False
            
            expected_sig = mac.hexdigest()
            
            # 常量时间比较，防止时序攻击
            result = hmac.compare_digest(expected_sig, sig)
            
            if not result:
                print(f"❌ 签名不匹配: expected={expected_sig[:8]}..., got={sig[:8]}..., algo={algo}")
            
            return result
        except Exception as e:
            print(f"❌ Webhook 签名验证异常: {e}")
            import traceback
            traceback.print_exc()
            return False

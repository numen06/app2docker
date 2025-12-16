# backend/models.py
"""数据库模型定义"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Pipeline(Base):
    """流水线表"""

    __tablename__ = "pipelines"

    pipeline_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    enabled = Column(Boolean, default=True)

    # Git 配置
    git_url = Column(String(512), nullable=False)
    branch = Column(String(255))
    sub_path = Column(String(512))

    # 构建配置
    project_type = Column(String(50), default="jar")
    template = Column(String(255))
    image_name = Column(String(255))
    tag = Column(String(255), default="latest")
    push = Column(Boolean, default=False)
    push_registry = Column(String(255))
    template_params = Column(JSON, default=dict)
    use_project_dockerfile = Column(Boolean, default=True)
    dockerfile_name = Column(String(255), default="Dockerfile")

    # Webhook 配置
    webhook_token = Column(String(36), unique=True, nullable=False)
    webhook_secret = Column(String(255))
    webhook_branch_filter = Column(Boolean, default=False)
    webhook_use_push_branch = Column(Boolean, default=True)
    webhook_allowed_branches = Column(JSON, default=list)  # 允许触发的分支列表
    branch_tag_mapping = Column(JSON, default=dict)

    # 多服务配置
    selected_services = Column(JSON, default=list)
    service_push_config = Column(JSON, default=dict)
    service_template_params = Column(JSON, default=dict)
    push_mode = Column(String(50), default="multi")
    resource_package_configs = Column(JSON, default=list)

    # 定时触发配置
    cron_expression = Column(String(255))
    next_run_time = Column(DateTime)

    # 构建后Webhook配置
    post_build_webhooks = Column(JSON, default=list)  # 构建完成后触发的webhook列表

    # 任务绑定
    current_task_id = Column(String(36), ForeignKey("tasks.task_id"), nullable=True)
    task_queue = Column(JSON, default=list)  # 保留向后兼容

    # 元数据
    source_id = Column(String(36))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_triggered_at = Column(DateTime)
    trigger_count = Column(Integer, default=0)

    # 关系
    current_task = relationship(
        "Task", foreign_keys=[current_task_id], post_update=True
    )

    __table_args__ = (
        Index("idx_pipeline_webhook_token", "webhook_token"),
        Index("idx_pipeline_enabled", "enabled"),
    )


class Task(Base):
    """任务表"""

    __tablename__ = "tasks"

    task_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(String(50), nullable=False)  # "build" 或 "build_from_source"
    image = Column(String(255))
    tag = Column(String(255))
    status = Column(
        String(50), default="pending"
    )  # pending, running, completed, failed, stopped
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime)  # 任务开始执行的时间（重试时会重置）
    completed_at = Column(DateTime)
    error = Column(Text)

    # 任务配置（JSON格式，保存完整配置）
    task_config = Column(JSON, default=dict)

    # 任务来源
    source = Column(String(50), default="手动构建")
    pipeline_id = Column(String(36), ForeignKey("pipelines.pipeline_id"), nullable=True)

    # 向后兼容字段（从 task_config 中提取）
    git_url = Column(String(512))
    branch = Column(String(255))
    project_type = Column(String(50))
    template = Column(String(255))
    should_push = Column(Boolean, default=False)
    sub_path = Column(String(512))
    use_project_dockerfile = Column(Boolean, default=True)
    dockerfile_name = Column(String(255), default="Dockerfile")
    trigger_source = Column(String(50), default="manual")

    # 关系
    pipeline = relationship("Pipeline", foreign_keys=[pipeline_id])

    __table_args__ = (
        Index("idx_task_status", "status"),
        Index("idx_task_pipeline", "pipeline_id"),
        Index("idx_task_created", "created_at"),
    )


class TaskLog(Base):
    """任务日志表"""

    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey("tasks.task_id"), nullable=False)
    log_message = Column(Text, nullable=False)
    log_time = Column(DateTime, default=datetime.now)

    # 关系
    task = relationship("Task", backref="logs")

    __table_args__ = (
        Index("idx_task_log_task", "task_id"),
        Index("idx_task_log_time", "log_time"),
    )


class GitSource(Base):
    """Git 数据源表"""

    __tablename__ = "git_sources"

    source_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    git_url = Column(String(512), nullable=False)
    branches = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    default_branch = Column(String(255))
    username = Column(String(255))
    password = Column(Text)  # 加密存储
    dockerfiles = Column(JSON, default=dict)  # Dockerfile 字典

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (Index("idx_git_source_url", "git_url"),)


class Host(Base):
    """主机表"""

    __tablename__ = "hosts"

    host_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=22)
    username = Column(String(255))
    password = Column(Text)  # 加密存储
    private_key = Column(Text)  # 加密存储
    key_password = Column(Text)  # 加密存储
    docker_enabled = Column(Boolean, default=False)
    docker_version = Column(String(255))
    description = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (Index("idx_host_name", "name"),)


class ResourcePackage(Base):
    """资源包表"""

    __tablename__ = "resource_packages"

    package_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    filename = Column(String(255), nullable=False)
    size = Column(Integer, default=0)
    extracted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (Index("idx_resource_package_name", "name"),)


class OperationLog(Base):
    """操作日志表"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_operation_log_user", "username"),
        Index("idx_operation_log_action", "action"),
        Index("idx_operation_log_time", "timestamp"),
    )


class ExportTask(Base):
    """导出任务表"""

    __tablename__ = "export_tasks"

    task_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(String(50), default="export")  # "export"
    image = Column(String(255))
    tag = Column(String(255), default="latest")
    compress = Column(String(50), default="none")  # none, gzip, zip
    registry = Column(String(255))
    use_local = Column(Boolean, default=False)  # 是否使用本地仓库
    status = Column(
        String(50), default="pending"
    )  # pending, running, completed, failed, stopped
    file_path = Column(String(512))
    file_size = Column(Integer)
    source = Column(String(50), default="手动导出")
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    error = Column(Text)

    __table_args__ = (
        Index("idx_export_task_status", "status"),
        Index("idx_export_task_created", "created_at"),
    )


class PipelineTaskHistory(Base):
    """流水线任务历史表"""

    __tablename__ = "pipeline_task_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.pipeline_id"), nullable=False
    )
    task_id = Column(String(36), ForeignKey("tasks.task_id"), nullable=False)
    trigger_source = Column(String(50), default="unknown")
    trigger_info = Column(JSON, default=dict)
    triggered_at = Column(DateTime, default=datetime.now)

    # 关系
    pipeline = relationship("Pipeline")
    task = relationship("Task")

    __table_args__ = (
        Index("idx_pipeline_history_pipeline", "pipeline_id"),
        Index("idx_pipeline_history_task", "task_id"),
        Index("idx_pipeline_history_time", "triggered_at"),
    )


class AgentHost(Base):
    """Agent主机表"""

    __tablename__ = "agent_hosts"

    host_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    host_type = Column(
        String(20), default="agent"
    )  # agent, portainer（Portainer 和 Portainer Agent 统一为 portainer）
    token = Column(
        String(64), unique=True, nullable=True
    )  # 用于WebSocket连接认证（Agent模式）
    # Portainer 相关字段（Portainer 和 Portainer Agent 都通过 Portainer API 控制）
    portainer_url = Column(String(512))  # Portainer API URL
    portainer_api_key = Column(Text)  # Portainer API Key（加密存储）
    portainer_endpoint_id = Column(Integer)  # Portainer Endpoint ID
    status = Column(String(20), default="offline")  # offline, online, connecting
    last_heartbeat = Column(DateTime)  # 最后心跳时间
    host_info = Column(
        JSON, default=dict
    )  # 主机信息（IP、操作系统、CPU、内存、磁盘等）
    docker_info = Column(JSON, default=dict)  # Docker信息（版本、容器数、镜像数等）
    description = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_agent_host_token", "token"),
        Index("idx_agent_host_status", "status"),
        Index("idx_agent_host_name", "name"),
        Index("idx_agent_host_type", "host_type"),
    )

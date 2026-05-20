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

    # 团队与分组
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)
    group_id = Column(String(36), ForeignKey("pipeline_groups.group_id"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)

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
        Index("idx_pipeline_team", "team_id"),
        Index("idx_pipeline_group", "group_id"),
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
    deploy_config_id = Column(String(36), ForeignKey("deploy_configs.config_id"), nullable=True)  # 关联到部署配置
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)

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
    deploy_config = relationship("DeployConfig", foreign_keys=[deploy_config_id])

    __table_args__ = (
        Index("idx_task_status", "status"),
        Index("idx_task_pipeline", "pipeline_id"),
        Index("idx_task_deploy_config", "deploy_config_id"),
        Index("idx_task_created", "created_at"),
        Index("idx_task_type_status", "task_type", "status"),
        Index("idx_task_type_deploy_config", "task_type", "deploy_config_id"),
        Index("idx_task_team", "team_id"),
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

    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_git_source_url", "git_url"),
        Index("idx_git_source_team", "team_id"),
    )


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

    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_host_name", "name"),
        Index("idx_host_team", "team_id"),
    )


class ResourcePackage(Base):
    """资源包表"""

    __tablename__ = "resource_packages"

    package_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    filename = Column(String(255), nullable=False)
    size = Column(Integer, default=0)
    extracted = Column(Boolean, default=False)

    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_resource_package_name", "name"),
        Index("idx_resource_package_team", "team_id"),
    )


class OperationLog(Base):
    """操作日志表"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(JSON, default=dict)
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_operation_log_user", "username"),
        Index("idx_operation_log_action", "action"),
        Index("idx_operation_log_time", "timestamp"),
        Index("idx_operation_log_team", "team_id"),
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
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime)
    error = Column(Text)

    __table_args__ = (
        Index("idx_export_task_status", "status"),
        Index("idx_export_task_created", "created_at"),
        Index("idx_export_task_team", "team_id"),
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
    )  # 用于WebSocket连接认证（Agent模式，存储Agent的唯一标识）
    agent_unique_id = Column(
        String(128), nullable=True
    )  # Agent唯一标识（基于Docker socket生成，重启后不变）
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

    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)
    group_id = Column(String(36), ForeignKey("host_groups.group_id"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_agent_host_token", "token"),
        Index("idx_agent_host_unique_id", "agent_unique_id"),
        Index("idx_agent_host_status", "status"),
        Index("idx_agent_host_name", "name"),
        Index("idx_agent_host_type", "host_type"),
        Index("idx_agent_host_team", "team_id"),
        Index("idx_agent_host_group", "group_id"),
    )


class AgentSecret(Base):
    """Agent密钥表"""

    __tablename__ = "agent_secrets"

    secret_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    secret_key = Column(String(64), unique=True, nullable=False)  # 密钥值
    name = Column(String(255))  # 密钥名称/描述
    enabled = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("idx_agent_secret_key", "secret_key"),
        Index("idx_agent_secret_enabled", "enabled"),
    )


class User(Base):
    """用户表"""

    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    roles = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )
    app_keys = relationship(
        "AppKey", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_user_username", "username"),)


class Role(Base):
    """角色表"""

    __tablename__ = "roles"

    role_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    users = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    permissions = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_role_name", "name"),)


class AppKey(Base):
    """用户 APP Key 表"""

    __tablename__ = "app_keys"

    key_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False)
    key_prefix = Column(String(16), nullable=False)
    enabled = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="app_keys")

    __table_args__ = (
        Index("idx_app_key_user", "user_id"),
        Index("idx_app_key_hash", "key_hash"),
        Index("idx_app_key_enabled", "enabled"),
    )


class Permission(Base):
    """权限表"""

    __tablename__ = "permissions"

    permission_id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), default="menu")  # menu, action
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    roles = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_permission_code", "code"),)


class UserRole(Base):
    """用户-角色关联表"""

    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.role_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")

    __table_args__ = (
        Index("idx_user_role_user", "user_id"),
        Index("idx_user_role_role", "role_id"),
        Index("idx_user_role_unique", "user_id", "role_id", unique=True),
    )


class RolePermission(Base):
    """角色-权限关联表"""

    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(String(36), ForeignKey("roles.role_id"), nullable=False)
    permission_id = Column(
        String(36), ForeignKey("permissions.permission_id"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

    __table_args__ = (
        Index("idx_role_permission_role", "role_id"),
        Index("idx_role_permission_permission", "permission_id"),
        Index("idx_role_permission_unique", "role_id", "permission_id", unique=True),
    )


class DeployConfig(Base):
    """部署配置表"""

    __tablename__ = "deploy_configs"

    config_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_name = Column(
        String(255), nullable=False, unique=True
    )  # 应用名称（唯一性约束）
    config_content = Column(Text, nullable=False)  # YAML 配置内容（原始格式）
    config_json = Column(JSON, default=dict)  # 解析后的配置结构（便于查询和修改）
    registry = Column(String(255), nullable=True)  # 镜像仓库地址
    tag = Column(String(255), nullable=True)  # 镜像标签
    webhook_token = Column(String(36), unique=True, nullable=True)  # Webhook token
    webhook_secret = Column(String(255), nullable=True)  # Webhook 密钥
    webhook_branch_strategy = Column(String(50), nullable=True)  # 分支策略
    webhook_allowed_branches = Column(JSON, nullable=True)  # 允许触发的分支列表
    execution_count = Column(Integer, default=0)  # 执行次数统计
    last_executed_at = Column(DateTime, nullable=True)  # 最后执行时间
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)  # 创建时间
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )  # 更新时间

    __table_args__ = (
        Index("idx_deploy_config_app_name", "app_name"),
        Index("idx_deploy_config_webhook_token", "webhook_token"),
        Index("idx_deploy_config_created", "created_at"),
        Index("idx_deploy_config_team", "team_id"),
    )


class SystemSetting(Base):
    """系统设置表（键值对）"""

    __tablename__ = "system_settings"

    setting_key = Column(String(100), primary_key=True)
    setting_value = Column(String(255), nullable=False)
    description = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Team(Base):
    """团队表"""

    __tablename__ = "teams"

    team_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    description = Column(Text, default="")
    avatar_url = Column(String(512), nullable=True)
    created_by = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    task_cleanup_days = Column(Integer, default=7)  # 任务自动清理保留天数

    members = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    invitations = relationship(
        "TeamInvitation",
        back_populates="team",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("idx_team_slug", "slug"),)


class TeamMember(Base):
    """团队成员"""

    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    role = Column(String(20), nullable=False, default="member")
    joined_at = Column(DateTime, default=datetime.now)

    team = relationship("Team", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        Index("idx_team_member_team", "team_id"),
        Index("idx_team_member_user", "user_id"),
        Index("uq_team_member_team_user", "team_id", "user_id", unique=True),
    )


class TeamInvitation(Base):
    """团队邀请"""

    __tablename__ = "team_invitations"

    invitation_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="member")
    token = Column(String(64), unique=True, nullable=False)
    invited_by = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    team = relationship("Team", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        Index("idx_team_invitation_team", "team_id"),
        Index("idx_team_invitation_token", "token"),
    )


class PipelineGroup(Base):
    """流水线分组"""

    __tablename__ = "pipeline_groups"

    group_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (Index("idx_pipeline_group_team", "team_id"),)


class HostGroup(Base):
    """主机分组"""

    __tablename__ = "host_groups"

    group_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("teams.team_id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (Index("idx_host_group_team", "team_id"),)


class PipelinePermission(Base):
    """流水线成员权限"""

    __tablename__ = "pipeline_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(
        String(36), ForeignKey("pipelines.pipeline_id"), nullable=False
    )
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    permission = Column(String(20), nullable=False, default="view")
    granted_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("uq_pipeline_perm_pipeline_user", "pipeline_id", "user_id", unique=True),
    )


class HostPermission(Base):
    """主机成员权限"""

    __tablename__ = "host_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    host_id = Column(String(36), ForeignKey("agent_hosts.host_id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    permission = Column(String(20), nullable=False, default="view")
    granted_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("uq_host_perm_host_user", "host_id", "user_id", unique=True),
    )


class DeployConfigPermission(Base):
    """部署配置成员权限"""

    __tablename__ = "deploy_config_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(
        String(36), ForeignKey("deploy_configs.config_id"), nullable=False
    )
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    permission = Column(String(20), nullable=False, default="view")
    granted_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("uq_deploy_config_perm_config_user", "config_id", "user_id", unique=True),
    )


class GitSourcePermission(Base):
    """数据源成员权限"""

    __tablename__ = "git_source_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String(36), ForeignKey("git_sources.source_id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    permission = Column(String(20), nullable=False, default="view")
    granted_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("uq_git_source_perm_source_user", "source_id", "user_id", unique=True),
    )


class PipelineGroupPermission(Base):
    """流水线分组成员权限"""

    __tablename__ = "pipeline_group_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(
        String(36), ForeignKey("pipeline_groups.group_id"), nullable=False
    )
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    permission = Column(String(20), nullable=False, default="view")
    granted_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("uq_pipeline_group_perm_group_user", "group_id", "user_id", unique=True),
    )


class HostGroupPermission(Base):
    """主机分组成员权限"""

    __tablename__ = "host_group_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(36), ForeignKey("host_groups.group_id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False)
    permission = Column(String(20), nullable=False, default="view")
    granted_by = Column(String(36), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("uq_host_group_perm_group_user", "group_id", "user_id", unique=True),
    )

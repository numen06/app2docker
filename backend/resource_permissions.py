# backend/resource_permissions.py
"""团队资源级权限（云效模式）"""
from __future__ import annotations

from typing import Any, Optional, Set

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import (
    AgentHost,
    DeployConfig,
    DeployConfigPermission,
    GitSource,
    GitSourcePermission,
    HostGroupPermission,
    HostPermission,
    Pipeline,
    PipelineGroupPermission,
    PipelinePermission,
    TeamMember,
)
from backend.team_permissions import get_team_member, require_team_member

PERMISSION_LEVELS = LEVELS = ("view", "run", "edit", "admin")
LEVEL_ORDER = {level: idx for idx, level in enumerate(PERMISSION_LEVELS)}

# 路由层 resource_type -> 内部类型
_TYPE_ALIASES = {
    "agent_host": "host",
    "host": "host",
    "pipeline": "pipeline",
    "deploy_config": "deploy_config",
    "git_source": "git_source",
}


def _canonical_type(resource_type: str) -> str:
    t = _TYPE_ALIASES.get(resource_type, resource_type)
    if t not in ("pipeline", "host", "deploy_config", "git_source"):
        raise HTTPException(status_code=400, detail=f"未知资源类型: {resource_type}")
    return t


def normalize_permission(level: str) -> str:
    level = (level or "view").strip().lower()
    if level not in LEVEL_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"permission 必须是: {', '.join(PERMISSION_LEVELS)}",
        )
    return level


def max_permission(a: Optional[str], b: Optional[str]) -> Optional[str]:
    if a is None:
        return b
    if b is None:
        return a
    return a if LEVEL_ORDER[a] >= LEVEL_ORDER[b] else b


def permission_satisfies(effective: Optional[str], min_level: str) -> bool:
    if effective is None:
        return False
    return LEVEL_ORDER[effective] >= LEVEL_ORDER[min_level]


def is_team_owner(db: Session, team_id: str, user_id: str) -> bool:
    member = get_team_member(db, team_id, user_id)
    return member is not None and member.role == "owner"


def list_accessible_team_ids(db: Session, user_id: str) -> Set[str]:
    rows = (
        db.query(TeamMember.team_id)
        .filter(TeamMember.user_id == user_id)
        .all()
    )
    return {r[0] for r in rows}


def require_team_member_for_resource(db: Session, user_id: str, team_id: str) -> None:
    require_team_member(db, team_id, user_id)


def _resource_row(
    db: Session, resource_type: str, resource_id: str
) -> Optional[Any]:
    rt = _canonical_type(resource_type)
    if rt == "pipeline":
        return (
            db.query(Pipeline)
            .filter(Pipeline.pipeline_id == resource_id)
            .first()
        )
    if rt == "host":
        return (
            db.query(AgentHost).filter(AgentHost.host_id == resource_id).first()
        )
    if rt == "deploy_config":
        return (
            db.query(DeployConfig)
            .filter(DeployConfig.config_id == resource_id)
            .first()
        )
    if rt == "git_source":
        return (
            db.query(GitSource)
            .filter(GitSource.source_id == resource_id)
            .first()
        )
    return None


def _resource_permission_level(
    db: Session, resource_type: str, resource_id: str, user_id: str
) -> Optional[str]:
    rt = _canonical_type(resource_type)
    if rt == "pipeline":
        row = (
            db.query(PipelinePermission.permission)
            .filter(
                PipelinePermission.pipeline_id == resource_id,
                PipelinePermission.user_id == user_id,
            )
            .first()
        )
        return row[0] if row else None
    if rt == "host":
        row = (
            db.query(HostPermission.permission)
            .filter(
                HostPermission.host_id == resource_id,
                HostPermission.user_id == user_id,
            )
            .first()
        )
        return row[0] if row else None
    if rt == "deploy_config":
        row = (
            db.query(DeployConfigPermission.permission)
            .filter(
                DeployConfigPermission.config_id == resource_id,
                DeployConfigPermission.user_id == user_id,
            )
            .first()
        )
        return row[0] if row else None
    if rt == "git_source":
        row = (
            db.query(GitSourcePermission.permission)
            .filter(
                GitSourcePermission.source_id == resource_id,
                GitSourcePermission.user_id == user_id,
            )
            .first()
        )
        return row[0] if row else None
    return None


def _group_permission_level(
    db: Session, resource_type: str, group_id: str, user_id: str
) -> Optional[str]:
    if not group_id:
        return None
    rt = _canonical_type(resource_type)
    if rt == "pipeline":
        row = (
            db.query(PipelineGroupPermission.permission)
            .filter(
                PipelineGroupPermission.group_id == group_id,
                PipelineGroupPermission.user_id == user_id,
            )
            .first()
        )
        return row[0] if row else None
    if rt == "host":
        row = (
            db.query(HostGroupPermission.permission)
            .filter(
                HostGroupPermission.group_id == group_id,
                HostGroupPermission.user_id == user_id,
            )
            .first()
        )
        return row[0] if row else None
    return None


def get_effective_permission(
    db: Session,
    user_id: str,
    resource_type: str,
    resource_id: str,
) -> Optional[str]:
    resource = _resource_row(db, resource_type, resource_id)
    if not resource:
        return None

    team_id = getattr(resource, "team_id", None)
    if team_id is None:
        return "admin"

    if is_team_owner(db, team_id, user_id):
        return "admin"

    rt = _canonical_type(resource_type)
    resource_perm = _resource_permission_level(db, rt, resource_id, user_id)
    group_id = getattr(resource, "group_id", None)
    group_perm = _group_permission_level(db, rt, group_id, user_id)
    return max_permission(resource_perm, group_perm)


def user_can_access_resource(
    db: Session, user_id: str, resource_type: str, resource: Any
) -> bool:
    """判断用户是否可访问资源（列表过滤）；resource 为 ORM 行或资源 ID"""
    if isinstance(resource, str):
        resource_id = resource
    else:
        rt = _canonical_type(resource_type)
        if rt == "pipeline":
            resource_id = resource.pipeline_id
        elif rt == "host":
            resource_id = resource.host_id
        elif rt == "deploy_config":
            resource_id = resource.config_id
        elif rt == "git_source":
            resource_id = resource.source_id
        else:
            return False
    return user_can_list_resource(db, user_id, resource_type, resource_id)


def can_view(
    db: Session, user_id: str, resource_type: str, resource_id: str
) -> bool:
    effective = get_effective_permission(db, user_id, resource_type, resource_id)
    return permission_satisfies(effective, "view")


def user_can_list_resource(
    db: Session, user_id: str, resource_type: str, resource_id: str
) -> bool:
    resource = _resource_row(db, resource_type, resource_id)
    if not resource:
        return False
    team_id = getattr(resource, "team_id", None)
    if team_id is None:
        return True
    if get_team_member(db, team_id, user_id):
        return True
    return get_effective_permission(db, user_id, resource_type, resource_id) is not None


def require_resource_permission(
    db: Session,
    user_id: str,
    resource_type: str,
    resource_id: str,
    min_level: str,
) -> str:
    """按资源 ID 校验权限"""
    resource = _resource_row(db, resource_type, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="资源不存在")
    return require_resource_permission_on_row(
        db, user_id, resource, resource_type, min_level
    )


def require_resource_permission_on_row(
    db: Session,
    user_id: str,
    resource: Any,
    resource_type: str,
    min_level: str,
) -> str:
    min_level = normalize_permission(min_level)
    team_id = getattr(resource, "team_id", None)
    if team_id is None:
        return "admin"

    resource_id = None
    rt = _canonical_type(resource_type)
    if rt == "pipeline":
        resource_id = resource.pipeline_id
    elif rt == "host":
        resource_id = resource.host_id
    elif rt == "deploy_config":
        resource_id = resource.config_id
    elif rt == "git_source":
        resource_id = resource.source_id

    effective = get_effective_permission(db, user_id, rt, resource_id)
    if not permission_satisfies(effective, min_level):
        raise HTTPException(
            status_code=403,
            detail=f"权限不足：需要 {min_level} 及以上权限",
        )
    return effective or min_level


def grant_resource_permission(
    db: Session,
    resource_type: str,
    resource_id: str,
    target_user_id: str,
    permission: str,
    granted_by: str,
) -> None:
    permission = normalize_permission(permission)
    rt = _canonical_type(resource_type)
    if rt == "pipeline":
        existing = (
            db.query(PipelinePermission)
            .filter(
                PipelinePermission.pipeline_id == resource_id,
                PipelinePermission.user_id == target_user_id,
            )
            .first()
        )
        if existing:
            existing.permission = permission
            existing.granted_by = granted_by
        else:
            db.add(
                PipelinePermission(
                    pipeline_id=resource_id,
                    user_id=target_user_id,
                    permission=permission,
                    granted_by=granted_by,
                )
            )
    elif rt == "host":
        existing = (
            db.query(HostPermission)
            .filter(
                HostPermission.host_id == resource_id,
                HostPermission.user_id == target_user_id,
            )
            .first()
        )
        if existing:
            existing.permission = permission
            existing.granted_by = granted_by
        else:
            db.add(
                HostPermission(
                    host_id=resource_id,
                    user_id=target_user_id,
                    permission=permission,
                    granted_by=granted_by,
                )
            )
    elif rt == "deploy_config":
        existing = (
            db.query(DeployConfigPermission)
            .filter(
                DeployConfigPermission.config_id == resource_id,
                DeployConfigPermission.user_id == target_user_id,
            )
            .first()
        )
        if existing:
            existing.permission = permission
            existing.granted_by = granted_by
        else:
            db.add(
                DeployConfigPermission(
                    config_id=resource_id,
                    user_id=target_user_id,
                    permission=permission,
                    granted_by=granted_by,
                )
            )
    elif rt == "git_source":
        existing = (
            db.query(GitSourcePermission)
            .filter(
                GitSourcePermission.source_id == resource_id,
                GitSourcePermission.user_id == target_user_id,
            )
            .first()
        )
        if existing:
            existing.permission = permission
            existing.granted_by = granted_by
        else:
            db.add(
                GitSourcePermission(
                    source_id=resource_id,
                    user_id=target_user_id,
                    permission=permission,
                    granted_by=granted_by,
                )
            )
    db.commit()


def revoke_resource_permission(
    db: Session,
    resource_type: str,
    resource_id: str,
    target_user_id: str,
) -> bool:
    rt = _canonical_type(resource_type)
    row = None
    if rt == "pipeline":
        row = (
            db.query(PipelinePermission)
            .filter(
                PipelinePermission.pipeline_id == resource_id,
                PipelinePermission.user_id == target_user_id,
            )
            .first()
        )
    elif rt == "host":
        row = (
            db.query(HostPermission)
            .filter(
                HostPermission.host_id == resource_id,
                HostPermission.user_id == target_user_id,
            )
            .first()
        )
    elif rt == "deploy_config":
        row = (
            db.query(DeployConfigPermission)
            .filter(
                DeployConfigPermission.config_id == resource_id,
                DeployConfigPermission.user_id == target_user_id,
            )
            .first()
        )
    elif rt == "git_source":
        row = (
            db.query(GitSourcePermission)
            .filter(
                GitSourcePermission.source_id == resource_id,
                GitSourcePermission.user_id == target_user_id,
            )
            .first()
        )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def grant_creator_admin(
    db: Session,
    resource_type: str,
    resource_id: str,
    user_id: str,
    granted_by: Optional[str] = None,
) -> None:
    """为创建者授予 admin（参数顺序与 route_definitions 调用一致）"""
    grant_resource_permission(
        db,
        resource_type,
        resource_id,
        user_id,
        "admin",
        granted_by or user_id,
    )

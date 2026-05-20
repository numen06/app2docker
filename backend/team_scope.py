# backend/team_scope.py
"""团队租户范围：解析 team_id、校验资源归属"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.auth import check_role
from backend.models import (
    DeployConfig,
    ExportTask,
    Host,
    Pipeline,
    ResourcePackage,
    Task,
    TeamMember,
)
from backend.team_permissions import get_user_id_by_username, require_team_member


def is_global_admin(username: str) -> bool:
    """系统级 admin 角色（用户/角色管理等全局接口，不受 team 限制）"""
    return check_role(username, "admin")


def resolve_team_scope(
    db: Session,
    user_id: str,
    team_id: Optional[str],
    *,
    required: bool = True,
) -> Optional[str]:
    """
    解析并校验当前请求的 team_id。
    业务接口默认必须带 team_id（租户隔离），超级管理员在业务接口上同样受 team 约束。
    """
    if not team_id:
        if required:
            raise HTTPException(status_code=400, detail="需要指定 team_id")
        return None
    require_team_member(db, team_id, user_id)
    return team_id


def resolve_team_scope_from_request(
    db: Session,
    username: str,
    team_id: Optional[str],
    *,
    required: bool = True,
) -> Optional[str]:
    user_id = get_user_id_by_username(db, username)
    return resolve_team_scope(db, user_id, team_id, required=required)


def resolve_team_scope_from_request_with_fallback(
    db: Session,
    username: str,
    team_id: Optional[str],
) -> str:
    """
    解析 team_id。未传时仅当用户只属于一个团队时自动选用，避免多团队时静默落到「第一个团队」导致列表看不到任务。
    """
    if team_id:
        resolved = resolve_team_scope_from_request(db, username, team_id)
        assert resolved
        return resolved

    user_id = get_user_id_by_username(db, username)
    members = (
        db.query(TeamMember)
        .filter(TeamMember.user_id == user_id)
        .order_by(TeamMember.joined_at.asc())
        .all()
    )
    if len(members) == 1 and members[0].team_id:
        require_team_member(db, members[0].team_id, user_id)
        return members[0].team_id
    if len(members) > 1:
        raise HTTPException(
            status_code=400,
            detail="需要指定 team_id（请先在顶部选择当前团队）",
        )

    raise HTTPException(status_code=400, detail="需要指定 team_id")


def get_effective_team_id_for_task(db: Session, task: Task) -> Optional[str]:
    if getattr(task, "team_id", None):
        return task.team_id
    if task.pipeline_id:
        p = db.query(Pipeline).filter(Pipeline.pipeline_id == task.pipeline_id).first()
        if p and p.team_id:
            return p.team_id
    if task.deploy_config_id:
        c = (
            db.query(DeployConfig)
            .filter(DeployConfig.config_id == task.deploy_config_id)
            .first()
        )
        if c and c.team_id:
            return c.team_id
    cfg = task.task_config or {}
    if isinstance(cfg, dict) and cfg.get("team_id"):
        return cfg.get("team_id")
    return None


def task_belongs_to_team(db: Session, task: Task, team_id: str) -> bool:
    effective = get_effective_team_id_for_task(db, task)
    if effective is None:
        return False
    return effective == team_id


def require_task_in_team(db: Session, user_id: str, task_id: str, team_id: str) -> Task:
    resolve_team_scope(db, user_id, team_id)
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task_belongs_to_team(db, task, team_id):
        raise HTTPException(status_code=403, detail="无权访问该团队的任务")
    return task


def require_export_task_in_team(
    db: Session, user_id: str, task_id: str, team_id: str
) -> ExportTask:
    resolve_team_scope(db, user_id, team_id)
    task = db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if getattr(task, "team_id", None) and task.team_id != team_id:
        raise HTTPException(status_code=403, detail="无权访问该团队的导出任务")
    if task.team_id is None:
        raise HTTPException(status_code=403, detail="无权访问该团队的导出任务")
    return task


def require_host_in_team(db: Session, user_id: str, host_id: str, team_id: str) -> Host:
    resolve_team_scope(db, user_id, team_id)
    host = db.query(Host).filter(Host.host_id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    if getattr(host, "team_id", None) != team_id:
        raise HTTPException(status_code=403, detail="无权访问该团队的主机")
    return host


def require_resource_package_in_team(
    db: Session, user_id: str, package_id: str, team_id: str
) -> ResourcePackage:
    resolve_team_scope(db, user_id, team_id)
    pkg = (
        db.query(ResourcePackage)
        .filter(ResourcePackage.package_id == package_id)
        .first()
    )
    if not pkg:
        raise HTTPException(status_code=404, detail="资源包不存在")
    if getattr(pkg, "team_id", None) != team_id:
        raise HTTPException(status_code=403, detail="无权访问该团队的资源包")
    return pkg


def infer_team_id_for_new_task(
    db: Session,
    *,
    team_id: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    deploy_config_id: Optional[str] = None,
    task_config: Optional[dict] = None,
) -> Optional[str]:
    if team_id:
        return team_id
    if pipeline_id:
        p = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
        if p and p.team_id:
            return p.team_id
    if deploy_config_id:
        c = (
            db.query(DeployConfig)
            .filter(DeployConfig.config_id == deploy_config_id)
            .first()
        )
        if c and c.team_id:
            return c.team_id
    if task_config and isinstance(task_config, dict) and task_config.get("team_id"):
        return task_config.get("team_id")
    return None

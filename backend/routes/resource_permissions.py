# backend/routes/resource_permissions.py
"""资源成员权限与分组 API"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    User,
    Pipeline,
    PipelineGroup,
    PipelineGroupPermission,
    PipelinePermission,
    AgentHost,
    HostGroup,
    HostGroupPermission,
    HostPermission,
    DeployConfig,
    DeployConfigPermission,
    GitSource,
    GitSourcePermission,
    TeamMember,
)
from backend.route_definitions import require_auth
from backend.resource_permissions import (
    PERMISSION_LEVELS,
    get_effective_permission,
    grant_resource_permission,
    normalize_permission,
    require_resource_permission,
    require_team_member_for_resource,
    revoke_resource_permission,
)
from backend.team_permissions import get_user_id_by_username

router = APIRouter(tags=["resource-permissions"])


class SetPermissionBody(BaseModel):
    permission: str = Field(..., description="admin/edit/run/view")


class ResourceMemberOut(BaseModel):
    user_id: str
    username: str
    email: str | None
    permission: str
    granted_by: str | None
    created_at: datetime | None


class MyPermissionOut(BaseModel):
    permission: str | None
    effective: bool


class GroupCreate(BaseModel):
    team_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class GroupOut(BaseModel):
    group_id: str
    team_id: str
    name: str
    description: str
    created_at: datetime | None

    class Config:
        from_attributes = True


def _perm_rows_to_members(db: Session, rows) -> List[ResourceMemberOut]:
    result = []
    for row in rows:
        user = db.query(User).filter(User.user_id == row.user_id).first()
        result.append(
            ResourceMemberOut(
                user_id=row.user_id,
                username=user.username if user else row.user_id,
                email=user.email if user else None,
                permission=row.permission,
                granted_by=row.granted_by,
                created_at=row.created_at,
            )
        )
    return result


def _ensure_target_team_member(db: Session, team_id: str, target_user_id: str) -> None:
    if not (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == target_user_id)
        .first()
    ):
        raise HTTPException(status_code=400, detail="目标用户不是团队成员")


# --- Pipeline members ---


@router.get("/pipelines/{pipeline_id}/members", response_model=List[ResourceMemberOut])
def list_pipeline_members(
    pipeline_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "pipeline", pipeline_id, "admin")
    rows = (
        db.query(PipelinePermission)
        .filter(PipelinePermission.pipeline_id == pipeline_id)
        .all()
    )
    return _perm_rows_to_members(db, rows)


@router.get("/pipelines/{pipeline_id}/my-permission", response_model=MyPermissionOut)
def my_pipeline_permission(
    pipeline_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    perm = get_effective_permission(db, user_id, "pipeline", pipeline_id)
    return MyPermissionOut(permission=perm, effective=perm is not None)


@router.put("/pipelines/{pipeline_id}/members/{target_user_id}")
def set_pipeline_member_permission(
    pipeline_id: str,
    target_user_id: str,
    body: SetPermissionBody,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "pipeline", pipeline_id, "admin")
    pipeline = db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="流水线不存在")
    if pipeline.team_id:
        _ensure_target_team_member(db, pipeline.team_id, target_user_id)
    grant_resource_permission(
        db,
        "pipeline",
        pipeline_id,
        target_user_id,
        normalize_permission(body.permission),
        user_id,
    )
    return {"message": "权限已更新"}


@router.delete("/pipelines/{pipeline_id}/members/{target_user_id}", status_code=204)
def delete_pipeline_member_permission(
    pipeline_id: str,
    target_user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "pipeline", pipeline_id, "admin")
    if not revoke_resource_permission(db, "pipeline", pipeline_id, target_user_id):
        raise HTTPException(status_code=404, detail="成员权限不存在")
    return None


# --- Agent host members (API path: /hosts) ---


@router.get("/hosts/{host_id}/members", response_model=List[ResourceMemberOut])
def list_host_members(
    host_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "agent_host", host_id, "admin")
    rows = db.query(HostPermission).filter(HostPermission.host_id == host_id).all()
    return _perm_rows_to_members(db, rows)


@router.get("/hosts/{host_id}/my-permission", response_model=MyPermissionOut)
def my_host_permission(
    host_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    perm = get_effective_permission(db, user_id, "agent_host", host_id)
    return MyPermissionOut(permission=perm, effective=perm is not None)


@router.put("/hosts/{host_id}/members/{target_user_id}")
def set_host_member_permission(
    host_id: str,
    target_user_id: str,
    body: SetPermissionBody,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "agent_host", host_id, "admin")
    host = db.query(AgentHost).filter(AgentHost.host_id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    if host.team_id:
        _ensure_target_team_member(db, host.team_id, target_user_id)
    grant_resource_permission(
        db,
        "agent_host",
        host_id,
        target_user_id,
        normalize_permission(body.permission),
        user_id,
    )
    return {"message": "权限已更新"}


@router.delete("/hosts/{host_id}/members/{target_user_id}", status_code=204)
def delete_host_member_permission(
    host_id: str,
    target_user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "agent_host", host_id, "admin")
    if not revoke_resource_permission(db, "agent_host", host_id, target_user_id):
        raise HTTPException(status_code=404, detail="成员权限不存在")
    return None


# --- Deploy config members ---


@router.get(
    "/deploy-configs/{config_id}/members", response_model=List[ResourceMemberOut]
)
def list_deploy_config_members(
    config_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "deploy_config", config_id, "admin")
    rows = (
        db.query(DeployConfigPermission)
        .filter(DeployConfigPermission.config_id == config_id)
        .all()
    )
    return _perm_rows_to_members(db, rows)


@router.get("/deploy-configs/{config_id}/my-permission", response_model=MyPermissionOut)
def my_deploy_config_permission(
    config_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    perm = get_effective_permission(db, user_id, "deploy_config", config_id)
    return MyPermissionOut(permission=perm, effective=perm is not None)


@router.put("/deploy-configs/{config_id}/members/{target_user_id}")
def set_deploy_config_member_permission(
    config_id: str,
    target_user_id: str,
    body: SetPermissionBody,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "deploy_config", config_id, "admin")
    config = (
        db.query(DeployConfig).filter(DeployConfig.config_id == config_id).first()
    )
    if not config:
        raise HTTPException(status_code=404, detail="部署配置不存在")
    if config.team_id:
        _ensure_target_team_member(db, config.team_id, target_user_id)
    grant_resource_permission(
        db,
        "deploy_config",
        config_id,
        target_user_id,
        normalize_permission(body.permission),
        user_id,
    )
    return {"message": "权限已更新"}


@router.delete("/deploy-configs/{config_id}/members/{target_user_id}", status_code=204)
def delete_deploy_config_member_permission(
    config_id: str,
    target_user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "deploy_config", config_id, "admin")
    if not revoke_resource_permission(db, "deploy_config", config_id, target_user_id):
        raise HTTPException(status_code=404, detail="成员权限不存在")
    return None


# --- Git source members ---


@router.get("/git-sources/{source_id}/members", response_model=List[ResourceMemberOut])
def list_git_source_members(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "git_source", source_id, "admin")
    rows = (
        db.query(GitSourcePermission)
        .filter(GitSourcePermission.source_id == source_id)
        .all()
    )
    return _perm_rows_to_members(db, rows)


@router.get("/git-sources/{source_id}/my-permission", response_model=MyPermissionOut)
def my_git_source_permission(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    perm = get_effective_permission(db, user_id, "git_source", source_id)
    return MyPermissionOut(permission=perm, effective=perm is not None)


@router.put("/git-sources/{source_id}/members/{target_user_id}")
def set_git_source_member_permission(
    source_id: str,
    target_user_id: str,
    body: SetPermissionBody,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "git_source", source_id, "admin")
    source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    if source.team_id:
        _ensure_target_team_member(db, source.team_id, target_user_id)
    grant_resource_permission(
        db,
        "git_source",
        source_id,
        target_user_id,
        normalize_permission(body.permission),
        user_id,
    )
    return {"message": "权限已更新"}


@router.delete("/git-sources/{source_id}/members/{target_user_id}", status_code=204)
def delete_git_source_member_permission(
    source_id: str,
    target_user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_resource_permission(db, user_id, "git_source", source_id, "admin")
    if not revoke_resource_permission(db, "git_source", source_id, target_user_id):
        raise HTTPException(status_code=404, detail="成员权限不存在")
    return None


# --- Pipeline groups ---


@router.get("/pipeline-groups", response_model=List[GroupOut])
def list_pipeline_groups(
    request: Request,
    team_id: str = Query(...),
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_member_for_resource(db, user_id, team_id)
    groups = (
        db.query(PipelineGroup)
        .filter(PipelineGroup.team_id == team_id)
        .order_by(PipelineGroup.created_at.desc())
        .all()
    )
    return groups


@router.post("/pipeline-groups", response_model=GroupOut)
def create_pipeline_group(
    body: GroupCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_member_for_resource(db, user_id, body.team_id)
    group = PipelineGroup(
        group_id=str(uuid.uuid4()),
        team_id=body.team_id,
        name=body.name,
        description=body.description or "",
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get(
    "/pipeline-groups/{group_id}/members", response_model=List[ResourceMemberOut]
)
def list_pipeline_group_members(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    group = db.query(PipelineGroup).filter(PipelineGroup.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    require_team_member_for_resource(db, user_id, group.team_id)
    rows = (
        db.query(PipelineGroupPermission)
        .filter(PipelineGroupPermission.group_id == group_id)
        .all()
    )
    return _perm_rows_to_members(db, rows)


@router.put("/pipeline-groups/{group_id}/members/{target_user_id}")
def set_pipeline_group_member_permission(
    group_id: str,
    target_user_id: str,
    body: SetPermissionBody,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    group = db.query(PipelineGroup).filter(PipelineGroup.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    require_team_member_for_resource(db, user_id, group.team_id)
    _ensure_target_team_member(db, group.team_id, target_user_id)
    perm = normalize_permission(body.permission)
    existing = (
        db.query(PipelineGroupPermission)
        .filter(
            PipelineGroupPermission.group_id == group_id,
            PipelineGroupPermission.user_id == target_user_id,
        )
        .first()
    )
    if existing:
        existing.permission = perm
        existing.granted_by = user_id
    else:
        db.add(
            PipelineGroupPermission(
                group_id=group_id,
                user_id=target_user_id,
                permission=perm,
                granted_by=user_id,
            )
        )
    db.commit()
    return {"message": "分组权限已更新"}


@router.delete("/pipeline-groups/{group_id}/members/{target_user_id}", status_code=204)
def delete_pipeline_group_member_permission(
    group_id: str,
    target_user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    group = db.query(PipelineGroup).filter(PipelineGroup.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    require_team_member_for_resource(db, user_id, group.team_id)
    row = (
        db.query(PipelineGroupPermission)
        .filter(
            PipelineGroupPermission.group_id == group_id,
            PipelineGroupPermission.user_id == target_user_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="成员权限不存在")
    db.delete(row)
    db.commit()
    return None


# --- Host groups ---


@router.get("/host-groups", response_model=List[GroupOut])
def list_host_groups(
    request: Request,
    team_id: str = Query(...),
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_member_for_resource(db, user_id, team_id)
    return (
        db.query(HostGroup)
        .filter(HostGroup.team_id == team_id)
        .order_by(HostGroup.created_at.desc())
        .all()
    )


@router.post("/host-groups", response_model=GroupOut)
def create_host_group(
    body: GroupCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_member_for_resource(db, user_id, body.team_id)
    group = HostGroup(
        group_id=str(uuid.uuid4()),
        team_id=body.team_id,
        name=body.name,
        description=body.description or "",
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/host-groups/{group_id}/members", response_model=List[ResourceMemberOut])
def list_host_group_members(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    group = db.query(HostGroup).filter(HostGroup.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    require_team_member_for_resource(db, user_id, group.team_id)
    rows = (
        db.query(HostGroupPermission)
        .filter(HostGroupPermission.group_id == group_id)
        .all()
    )
    return _perm_rows_to_members(db, rows)


@router.put("/host-groups/{group_id}/members/{target_user_id}")
def set_host_group_member_permission(
    group_id: str,
    target_user_id: str,
    body: SetPermissionBody,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    group = db.query(HostGroup).filter(HostGroup.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    require_team_member_for_resource(db, user_id, group.team_id)
    _ensure_target_team_member(db, group.team_id, target_user_id)
    perm = normalize_permission(body.permission)
    existing = (
        db.query(HostGroupPermission)
        .filter(
            HostGroupPermission.group_id == group_id,
            HostGroupPermission.user_id == target_user_id,
        )
        .first()
    )
    if existing:
        existing.permission = perm
        existing.granted_by = user_id
    else:
        db.add(
            HostGroupPermission(
                group_id=group_id,
                user_id=target_user_id,
                permission=perm,
                granted_by=user_id,
            )
        )
    db.commit()
    return {"message": "分组权限已更新"}


# --- /agent-hosts 路径别名（与 /hosts 行为一致） ---


@router.get(
    "/agent-hosts/{host_id}/members", response_model=List[ResourceMemberOut]
)
def list_agent_host_members_alias(
    host_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    return list_host_members(host_id, request, db)


@router.get("/agent-hosts/{host_id}/my-permission", response_model=MyPermissionOut)
def my_agent_host_permission_alias(
    host_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    return my_host_permission(host_id, request, db)


@router.put("/agent-hosts/{host_id}/members/{target_user_id}")
def set_agent_host_member_permission_alias(
    host_id: str,
    target_user_id: str,
    body: SetPermissionBody,
    request: Request,
    db: Session = Depends(get_db),
):
    return set_host_member_permission(host_id, target_user_id, body, request, db)


@router.delete("/agent-hosts/{host_id}/members/{target_user_id}", status_code=204)
def delete_agent_host_member_permission_alias(
    host_id: str,
    target_user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    return delete_host_member_permission(host_id, target_user_id, request, db)

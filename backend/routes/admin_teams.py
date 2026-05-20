# backend/routes/admin_teams.py
"""超级管理员：全站团队 CRUD"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth import check_role
from backend.database import DEFAULT_TEAM_NAME, get_db
from backend.models import Team, TeamMember, User
from backend.route_definitions import require_auth
from backend.team_deletion import delete_team_cascade
from backend.team_permissions import get_user_id_by_username
from backend.team_utils import ensure_unique_slug, slugify_name, team_to_dict

router = APIRouter(prefix="/admin/teams", tags=["admin-teams"])


def _require_global_admin(request: Request, db: Session) -> str:
    username = require_auth(request)
    if not check_role(username, "admin"):
        raise HTTPException(status_code=403, detail="权限不足：需要管理员权限")
    return get_user_id_by_username(db, username)


def _owner_username(db: Session, team_id: str) -> Optional[str]:
    row = (
        db.query(User.username)
        .join(TeamMember, TeamMember.user_id == User.user_id)
        .filter(TeamMember.team_id == team_id, TeamMember.role == "owner")
        .first()
    )
    return row[0] if row else None


def _username_by_id(db: Session, user_id: str) -> Optional[str]:
    row = db.query(User.username).filter(User.user_id == user_id).first()
    return row[0] if row else None


def _team_admin_item(db: Session, team: Team) -> dict:
    member_count = (
        db.query(func.count(TeamMember.id))
        .filter(TeamMember.team_id == team.team_id)
        .scalar()
        or 0
    )
    item = team_to_dict(team)
    item["member_count"] = int(member_count)
    item["owner_username"] = _owner_username(db, team.team_id)
    item["created_by_username"] = _username_by_id(db, team.created_by)
    return item


class AdminTeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    owner_user_id: str = Field(..., min_length=1)
    task_cleanup_days: int = Field(default=7, ge=1, le=365)


class AdminTeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    task_cleanup_days: Optional[int] = Field(None, ge=1, le=365)


@router.get("")
def list_teams(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    _require_global_admin(request, db)
    query = db.query(Team)
    total = query.count()
    offset = (page - 1) * page_size
    teams = (
        query.order_by(Team.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "teams": [_team_admin_item(db, t) for t in teams],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("")
def create_team(
    body: AdminTeamCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    admin_user_id = _require_global_admin(request, db)
    name = body.name.strip()
    if name == DEFAULT_TEAM_NAME:
        raise HTTPException(
            status_code=400,
            detail=f"团队名称「{DEFAULT_TEAM_NAME}」为系统保留，请使用其他名称",
        )
    owner = db.query(User).filter(User.user_id == body.owner_user_id).first()
    if not owner:
        raise HTTPException(status_code=400, detail="指定的所有者用户不存在")
    slug = ensure_unique_slug(db, slugify_name(name))
    team = Team(
        team_id=str(uuid.uuid4()),
        name=name,
        slug=slug,
        description=body.description or "",
        created_by=admin_user_id,
        task_cleanup_days=body.task_cleanup_days,
    )
    db.add(team)
    db.flush()
    db.add(
        TeamMember(
            team_id=team.team_id,
            user_id=body.owner_user_id,
            role="owner",
        )
    )
    db.commit()
    db.refresh(team)
    return _team_admin_item(db, team)


@router.get("/{team_id}")
def get_team(
    team_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_global_admin(request, db)
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    return _team_admin_item(db, team)


@router.put("/{team_id}")
def update_team(
    team_id: str,
    body: AdminTeamUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_global_admin(request, db)
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    if body.name is not None:
        new_name = body.name.strip()
        if new_name == DEFAULT_TEAM_NAME and team.name != DEFAULT_TEAM_NAME:
            raise HTTPException(
                status_code=400,
                detail=f"不能使用系统保留名称「{DEFAULT_TEAM_NAME}」",
            )
        team.name = new_name
        team.slug = ensure_unique_slug(
            db, slugify_name(team.name), exclude_team_id=team.team_id
        )
    if body.description is not None:
        team.description = body.description
    if body.task_cleanup_days is not None:
        team.task_cleanup_days = body.task_cleanup_days
    team.updated_at = datetime.now()
    db.commit()
    db.refresh(team)
    return _team_admin_item(db, team)


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_global_admin(request, db)
    delete_team_cascade(db, team_id)
    return None

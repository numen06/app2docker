# backend/routes/teams.py
"""团队管理 API"""
from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Team, TeamInvitation, TeamMember, User
from backend.route_definitions import require_auth
from backend.team_permissions import (
    get_team_member,
    get_user_id_by_username,
    menu_permissions_for_team_role,
    require_team_admin,
    require_team_member,
    require_team_owner,
)

router = APIRouter(prefix="/teams", tags=["teams"])

TEAM_ROLES = frozenset({"owner", "admin", "member"})


def _slugify_name(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    s = s.strip("-")
    return s or "team"


def _ensure_unique_slug(
    db: Session, base_slug: str, exclude_team_id: str | None = None
) -> str:
    slug = base_slug
    while True:
        q = db.query(Team).filter(Team.slug == slug)
        if exclude_team_id:
            q = q.filter(Team.team_id != exclude_team_id)
        if q.first() is None:
            return slug
        slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"


def _normalize_role(role: str) -> str:
    r = role.strip().lower()
    if r not in TEAM_ROLES:
        raise HTTPException(
            status_code=400, detail="role 必须是 owner、admin 或 member"
        )
    return r


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    avatar_url: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    avatar_url: str | None = None


class TeamOut(BaseModel):
    team_id: str
    name: str
    slug: str
    description: str
    avatar_url: str | None
    created_by: str
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class TeamMembershipOut(BaseModel):
    team: TeamOut
    role: str


class TeamMemberOut(BaseModel):
    user_id: str
    username: str
    email: str | None
    role: str
    joined_at: datetime | None


class InviteRequest(BaseModel):
    email: str | None = None
    role: str = "member"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        if "@" not in s or "." not in s.split("@")[-1]:
            raise ValueError("无效的邮箱格式")
        return s


class MemberRoleUpdate(BaseModel):
    role: str


class InviteCreatedOut(BaseModel):
    invitation_id: str
    token: str
    email: str | None = None
    role: str
    expires_at: datetime


class MenuPermissionsOut(BaseModel):
    team_id: str
    role: str
    permissions: List[str]
    can_manage_team: bool = False
    can_assign_admin: bool = False
    can_dissolve_team: bool = False


class TeamSettingsOut(BaseModel):
    task_cleanup_days: int = Field(default=7, ge=1, le=365)


class TeamSettingsUpdate(BaseModel):
    task_cleanup_days: int = Field(..., ge=1, le=365)


def _team_to_out(t: Team) -> TeamOut:
    return TeamOut(
        team_id=t.team_id,
        name=t.name,
        slug=t.slug,
        description=t.description or "",
        avatar_url=t.avatar_url,
        created_by=t.created_by,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get("/me", response_model=List[TeamMembershipOut])
def list_my_teams(request: Request, db: Session = Depends(get_db)):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    rows = (
        db.query(TeamMember, Team)
        .join(Team, TeamMember.team_id == Team.team_id)
        .filter(TeamMember.user_id == user_id)
        .all()
    )
    return [
        TeamMembershipOut(team=_team_to_out(team), role=member.role)
        for member, team in rows
    ]


@router.post(
    "/invitations/{token}/accept",
    response_model=TeamMembershipOut,
)
def accept_invitation(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    inv = (
        db.query(TeamInvitation)
        .filter(
            TeamInvitation.token == token,
            TeamInvitation.accepted_at.is_(None),
        )
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="邀请不存在或已失效")
    if inv.expires_at and inv.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="邀请已过期")
    inv_email = (inv.email or "").strip()
    if inv_email:
        if not (user.email and user.email.strip()):
            raise HTTPException(
                status_code=400,
                detail="请先在个人资料中设置邮箱后再接受邀请",
            )
        if user.email.strip().casefold() != inv_email.casefold():
            raise HTTPException(status_code=403, detail="当前登录用户邮箱与邀请不匹配")
    team = db.query(Team).filter(Team.team_id == inv.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    existing = get_team_member(db, inv.team_id, user_id)
    if existing:
        inv.accepted_at = datetime.now()
        db.commit()
        return TeamMembershipOut(team=_team_to_out(team), role=existing.role)
    role = _normalize_role(inv.role)
    member = TeamMember(
        team_id=inv.team_id,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    inv.accepted_at = datetime.now()
    db.commit()
    db.refresh(member)
    return TeamMembershipOut(team=_team_to_out(team), role=member.role)


@router.post("", response_model=TeamOut)
def create_team(
    body: TeamCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    name = body.name.strip()
    if name == "默认团队":
        base = "default"
    else:
        base = _slugify_name(name)
    slug = _ensure_unique_slug(db, base)
    team = Team(
        team_id=str(uuid.uuid4()),
        name=name,
        slug=slug,
        description=body.description or "",
        avatar_url=body.avatar_url,
        created_by=user_id,
    )
    db.add(team)
    db.flush()
    db.add(
        TeamMember(
            team_id=team.team_id,
            user_id=user_id,
            role="owner",
        )
    )
    db.commit()
    db.refresh(team)
    return _team_to_out(team)


@router.get("/{team_id}/menu-permissions", response_model=MenuPermissionsOut)
def get_team_menu_permissions(
    team_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """根据当前用户在团队中的角色返回菜单权限。"""
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    member = require_team_member(db, team_id, user_id)
    perms = menu_permissions_for_team_role(member.role)
    r = member.role
    return MenuPermissionsOut(
        team_id=team_id,
        role=r,
        permissions=perms,
        can_manage_team=r in ("owner", "admin"),
        can_assign_admin=r == "owner",
        can_dissolve_team=r == "owner",
    )


@router.get("/{team_id}", response_model=TeamOut)
def get_team(
    team_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_member(db, team_id, user_id)
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    return _team_to_out(team)


@router.patch("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: str,
    body: TeamUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_admin(db, team_id, user_id)
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    if body.name is not None:
        team.name = body.name.strip()
        team.slug = _ensure_unique_slug(
            db, _slugify_name(team.name), exclude_team_id=team.team_id
        )
    if body.description is not None:
        team.description = body.description
    if body.avatar_url is not None:
        team.avatar_url = body.avatar_url
    db.commit()
    db.refresh(team)
    return _team_to_out(team)


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_owner(db, team_id, user_id)
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    db.delete(team)
    db.commit()
    return None


@router.post("/{team_id}/invite", response_model=InviteCreatedOut)
def invite_member(
    team_id: str,
    body: InviteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    actor = require_team_admin(db, team_id, user_id)
    invite_role = _normalize_role(body.role)
    if invite_role == "owner" and actor.role != "owner":
        raise HTTPException(status_code=403, detail="仅所有者可邀请所有者角色")
    if invite_role == "admin" and actor.role != "owner":
        raise HTTPException(status_code=403, detail="仅所有者可邀请管理员")
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    token = secrets.token_urlsafe(32)
    invite_email = (body.email or "").strip() if body.email else ""
    inv = TeamInvitation(
        invitation_id=str(uuid.uuid4()),
        team_id=team_id,
        email=invite_email,
        role=invite_role,
        token=token,
        invited_by=user_id,
        expires_at=datetime.now() + timedelta(days=7),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return InviteCreatedOut(
        invitation_id=inv.invitation_id,
        token=inv.token,
        email=inv.email or None,
        role=inv.role,
        expires_at=inv.expires_at,
    )


@router.get("/{team_id}/members", response_model=List[TeamMemberOut])
def list_members(
    team_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_member(db, team_id, user_id)
    rows = (
        db.query(TeamMember, User)
        .join(User, TeamMember.user_id == User.user_id)
        .filter(TeamMember.team_id == team_id)
        .all()
    )
    return [
        TeamMemberOut(
            user_id=u.user_id,
            username=u.username,
            email=u.email,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m, u in rows
    ]


@router.patch("/{team_id}/members/{target_user_id}", response_model=TeamMemberOut)
def patch_member_role(
    team_id: str,
    target_user_id: str,
    body: MemberRoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    actor = require_team_admin(db, team_id, user_id)
    new_role = _normalize_role(body.role)
    target = get_team_member(db, team_id, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="成员不存在")
    if new_role == "admin" and actor.role != "owner":
        raise HTTPException(status_code=403, detail="仅所有者可任命管理员")
    if target.role == "admin" and new_role != "admin" and actor.role != "owner":
        raise HTTPException(status_code=403, detail="仅所有者可变更管理员角色")
    if target.role == "owner" and new_role != "owner" and actor.role != "owner":
        raise HTTPException(status_code=403, detail="仅所有者可变更所有者角色")
    if new_role == "owner":
        if actor.role != "owner":
            raise HTTPException(status_code=403, detail="仅所有者可转让所有者")
        current_owner = (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team_id, TeamMember.role == "owner")
            .first()
        )
        if current_owner and current_owner.user_id != target_user_id:
            current_owner.role = "admin"
        target.role = "owner"
        team = db.query(Team).filter(Team.team_id == team_id).first()
        if team:
            team.created_by = target_user_id
    else:
        if target.role == "owner" and new_role != "owner":
            others = (
                db.query(TeamMember)
                .filter(
                    TeamMember.team_id == team_id,
                    TeamMember.user_id != target_user_id,
                    TeamMember.role == "owner",
                )
                .count()
            )
            if others == 0:
                raise HTTPException(
                    status_code=400, detail="团队至少保留一位所有者"
                )
        target.role = new_role
    db.commit()
    db.refresh(target)
    u = db.query(User).filter(User.user_id == target_user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    return TeamMemberOut(
        user_id=u.user_id,
        username=u.username,
        email=u.email,
        role=target.role,
        joined_at=target.joined_at,
    )


@router.delete("/{team_id}/members/{target_user_id}", status_code=204)
def remove_member(
    team_id: str,
    target_user_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    actor = require_team_admin(db, team_id, user_id)
    target = get_team_member(db, team_id, target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="成员不存在")
    if target.role == "owner":
        raise HTTPException(status_code=400, detail="不能移除团队所有者")
    if target.role == "admin" and actor.role != "owner":
        raise HTTPException(status_code=403, detail="仅所有者可移除管理员")
    db.delete(target)
    db.commit()
    return None


@router.get("/{team_id}/settings", response_model=TeamSettingsOut)
def get_team_settings(
    team_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_member(db, team_id, user_id)
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    days = team.task_cleanup_days if team.task_cleanup_days is not None else 7
    return TeamSettingsOut(task_cleanup_days=max(1, int(days)))


@router.put("/{team_id}/settings", response_model=TeamSettingsOut)
def update_team_settings(
    team_id: str,
    body: TeamSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    username = require_auth(request)
    user_id = get_user_id_by_username(db, username)
    require_team_admin(db, team_id, user_id)
    team = db.query(Team).filter(Team.team_id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")
    team.task_cleanup_days = body.task_cleanup_days
    team.updated_at = datetime.now()
    db.commit()
    db.refresh(team)
    return TeamSettingsOut(task_cleanup_days=team.task_cleanup_days)

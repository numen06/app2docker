# backend/team_permissions.py
"""团队权限与成员校验"""
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.models import User, TeamMember
from backend.permissions import ALL_MENU_PERMISSIONS

# 团队成员可见的菜单（普通成员）
TEAM_MEMBER_MENU_PERMISSIONS = [
    "menu.dashboard",
    "menu.pipeline",
    "menu.host",
]

# Owner / Admin 在团队内可用的全部业务菜单（不含全局系统管理 menu.users）
TEAM_ADMIN_MENU_PERMISSIONS = list(ALL_MENU_PERMISSIONS)


def get_user_id_by_username(db: Session, username: str) -> str:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user.user_id


def get_team_member(
    db: Session, team_id: str, user_id: str
) -> TeamMember | None:
    return (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        .first()
    )


def require_team_member(db: Session, team_id: str, user_id: str) -> TeamMember:
    member = get_team_member(db, team_id, user_id)
    if not member:
        raise HTTPException(status_code=403, detail="无权访问该团队")
    return member


def require_team_admin(db: Session, team_id: str, user_id: str) -> TeamMember:
    member = require_team_member(db, team_id, user_id)
    if member.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="需要团队管理员权限")
    return member


def require_team_owner(db: Session, team_id: str, user_id: str) -> TeamMember:
    member = require_team_member(db, team_id, user_id)
    if member.role != "owner":
        raise HTTPException(status_code=403, detail="需要团队所有者权限")
    return member


def menu_permissions_for_team_role(role: str) -> list[str]:
    """根据团队角色返回菜单权限代码列表。"""
    r = (role or "").strip().lower()
    if r in ("owner", "admin"):
        return list(TEAM_ADMIN_MENU_PERMISSIONS)
    return list(TEAM_MEMBER_MENU_PERMISSIONS)

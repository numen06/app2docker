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
    """团队角色默认菜单（仅当用户无系统角色 menu.* 时回退）。"""
    r = (role or "").strip().lower()
    if r in ("owner", "admin"):
        return list(TEAM_ADMIN_MENU_PERMISSIONS)
    return list(TEAM_MEMBER_MENU_PERMISSIONS)


def effective_menu_permissions_for_team_user(username: str, team_role: str) -> list[str]:
    """
    团队上下文侧栏菜单：以系统角色（角色管理）配置的 menu.* 为准；
    团队角色不硬编码裁剪 member 菜单。menu.users 仅当全局角色已授予时保留。
    """
    from backend.auth import get_user_permissions

    global_perms = get_user_permissions(username)
    menu_codes = {p for p in global_perms if p.startswith("menu.")}
    if "menu.users" not in global_perms:
        menu_codes.discard("menu.users")
    if not menu_codes:
        menu_codes = set(menu_permissions_for_team_role(team_role))
    return sorted(menu_codes)

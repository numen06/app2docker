# backend/registry_manager.py
"""团队级镜像仓库管理（数据库）"""
from __future__ import annotations

import base64
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.crypto_utils import decrypt_password, encrypt_password
from backend.database import get_db_session
from backend.models import DockerRegistry
from backend.resource_permissions import (
    get_effective_permission,
    grant_creator_admin,
    require_resource_permission,
    user_can_access_resource,
)


def _decrypt_stored_password(password: str) -> str:
    if not password:
        return ""
    try:
        return decrypt_password(password)
    except (ValueError, Exception):
        return password


def _registry_to_safe_dict(row: DockerRegistry, include_password: bool = False) -> Dict[str, Any]:
    data = {
        "registry_id": row.registry_id,
        "team_id": row.team_id,
        "created_by": row.created_by,
        "name": row.name,
        "registry": row.registry,
        "registry_prefix": row.registry_prefix or "",
        "username": row.username or "",
        "active": bool(row.active),
        "has_password": bool(row.password),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_password:
        data["password"] = _decrypt_stored_password(row.password or "")
    return data


def list_registries_for_user(
    user_id: str,
    team_id: str,
    query: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    db = get_db_session()
    try:
        q = db.query(DockerRegistry).filter(DockerRegistry.team_id == team_id)
        rows = q.order_by(DockerRegistry.created_at.desc()).all()
        result = []
        for row in rows:
            if not user_can_access_resource(db, user_id, "registry", row):
                continue
            item = _registry_to_safe_dict(row)
            item["my_permission"] = get_effective_permission(
                db, user_id, "registry", row.registry_id
            )
            if query:
                ql = query.lower().strip()
                if (
                    ql not in (item.get("name") or "").lower()
                    and ql not in (item.get("registry") or "").lower()
                    and ql not in (item.get("registry_prefix") or "").lower()
                ):
                    continue
            result.append(item)
            if len(result) >= limit:
                break
        return result
    finally:
        db.close()


def get_registry_row(registry_id: str) -> Optional[DockerRegistry]:
    db = get_db_session()
    try:
        return (
            db.query(DockerRegistry)
            .filter(DockerRegistry.registry_id == registry_id)
            .first()
        )
    finally:
        db.close()


def get_registry_by_id(registry_id: str, user_id: str, min_level: str = "view") -> Dict[str, Any]:
    db = get_db_session()
    try:
        require_resource_permission(db, user_id, "registry", registry_id, min_level)
        row = (
            db.query(DockerRegistry)
            .filter(DockerRegistry.registry_id == registry_id)
            .first()
        )
        if not row:
            raise ValueError("镜像仓库不存在")
        return _registry_to_safe_dict(row)
    finally:
        db.close()


def resolve_registry(
    key: str,
    team_id: Optional[str] = None,
) -> Optional[DockerRegistry]:
    """按 registry_id 或 name 解析仓库"""
    if not key:
        return None
    db = get_db_session()
    try:
        row = (
            db.query(DockerRegistry)
            .filter(DockerRegistry.registry_id == key)
            .first()
        )
        if row:
            return row
        q = db.query(DockerRegistry).filter(DockerRegistry.name == key)
        if team_id:
            q = q.filter(DockerRegistry.team_id == team_id)
        return q.first()
    finally:
        db.close()


def get_active_registry_for_team(
    team_id: str,
    user_id: Optional[str] = None,
    include_password: bool = True,
) -> Optional[Dict[str, Any]]:
    db = get_db_session()
    try:
        rows = (
            db.query(DockerRegistry)
            .filter(DockerRegistry.team_id == team_id)
            .order_by(DockerRegistry.created_at.asc())
            .all()
        )
        active_row = None
        for row in rows:
            if user_id and not user_can_access_resource(db, user_id, "registry", row):
                continue
            if row.active:
                active_row = row
                break
        if not active_row:
            for row in rows:
                if user_id and not user_can_access_resource(db, user_id, "registry", row):
                    continue
                active_row = row
                break
        if not active_row:
            return None
        return _registry_to_safe_dict(active_row, include_password=include_password)
    finally:
        db.close()


def get_registry_by_name_for_team(
    name: str,
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
    include_password: bool = True,
) -> Optional[Dict[str, Any]]:
    row = resolve_registry(name, team_id=team_id)
    if not row:
        return None
    if user_id:
        db = get_db_session()
        try:
            if not user_can_access_resource(db, user_id, "registry", row):
                return None
            if not get_effective_permission(db, user_id, "registry", row.registry_id):
                return None
        finally:
            db.close()
    return _registry_to_safe_dict(row, include_password=include_password)


def create_registry(
    *,
    team_id: str,
    created_by: str,
    name: str,
    registry: str,
    registry_prefix: str = "",
    username: str = "",
    password: str = "",
    active: bool = False,
) -> Dict[str, Any]:
    db = get_db_session()
    try:
        registry_id = str(uuid.uuid4())
        enc_password = encrypt_password(password) if password else ""
        if active:
            db.query(DockerRegistry).filter(
                DockerRegistry.team_id == team_id, DockerRegistry.active == True
            ).update({"active": False})
        row = DockerRegistry(
            registry_id=registry_id,
            team_id=team_id,
            created_by=created_by,
            name=name,
            registry=registry,
            registry_prefix=registry_prefix or "",
            username=username or "",
            password=enc_password,
            active=active,
        )
        db.add(row)
        db.commit()
        grant_creator_admin(db, "registry", registry_id, created_by)
        return _registry_to_safe_dict(row)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_registry(
    registry_id: str,
    user_id: str,
    *,
    name: Optional[str] = None,
    registry: Optional[str] = None,
    registry_prefix: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    password_unchanged: bool = False,
    active: Optional[bool] = None,
) -> Dict[str, Any]:
    db = get_db_session()
    try:
        require_resource_permission(db, user_id, "registry", registry_id, "edit")
        row = (
            db.query(DockerRegistry)
            .filter(DockerRegistry.registry_id == registry_id)
            .first()
        )
        if not row:
            raise ValueError("镜像仓库不存在")
        if name is not None:
            row.name = name
        if registry is not None:
            row.registry = registry
        if registry_prefix is not None:
            row.registry_prefix = registry_prefix
        if username is not None:
            row.username = username
        if password is not None and not password_unchanged:
            row.password = encrypt_password(password) if password else ""
        if active is not None:
            if active:
                db.query(DockerRegistry).filter(
                    DockerRegistry.team_id == row.team_id,
                    DockerRegistry.active == True,
                    DockerRegistry.registry_id != registry_id,
                ).update({"active": False})
            row.active = active
        row.updated_at = datetime.now()
        db.commit()
        return _registry_to_safe_dict(row)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_registry(registry_id: str, user_id: str) -> bool:
    db = get_db_session()
    try:
        require_resource_permission(db, user_id, "registry", registry_id, "admin")
        row = (
            db.query(DockerRegistry)
            .filter(DockerRegistry.registry_id == registry_id)
            .first()
        )
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_registry_password_for_row(row: DockerRegistry) -> Optional[str]:
    pwd = _decrypt_stored_password(row.password or "")
    return pwd or None


def scope_from_task_like(
    team_id: Optional[str] = None,
    user_id: Optional[str] = None,
    task_config: Optional[dict] = None,
) -> tuple[Optional[str], Optional[str]]:
    """从任务/配置对象提取团队与用户范围"""
    tid = team_id
    uid = user_id
    if task_config and isinstance(task_config, dict):
        tid = tid or task_config.get("team_id")
        uid = uid or task_config.get("created_by") or task_config.get("user_id")
    return tid, uid


def db_has_registries() -> bool:
    db = get_db_session()
    try:
        return db.query(DockerRegistry).count() > 0
    finally:
        db.close()


def _password_plain_from_config_entry(reg: Dict[str, Any]) -> str:
    """从 config 条目解析明文密码（兼容加密 / base64 / 明文）"""
    password = reg.get("password") or ""
    if not password:
        return ""
    try:
        return decrypt_password(password)
    except (ValueError, Exception):
        try:
            decoded = base64.b64decode(password.encode("utf-8"))
            return decoded.decode("utf-8")
        except Exception:
            return password


def _config_registry_entries() -> List[Dict[str, Any]]:
    from backend.config import load_config

    config = load_config()
    registries = config.get("docker", {}).get("registries", [])
    if not isinstance(registries, list):
        return []
    return [r for r in registries if isinstance(r, dict)]


def ensure_team_registries_from_config(
    team_id: str,
    created_by: str,
) -> int:
    """
    当团队下 docker_registries 为空时，将 config 中的 registries 幂等写入数据库。
    返回本次新写入条数。
    """
    if not team_id or not created_by:
        return 0

    db = get_db_session()
    try:
        existing = (
            db.query(DockerRegistry)
            .filter(DockerRegistry.team_id == team_id)
            .count()
        )
        if existing > 0:
            return 0
    finally:
        db.close()

    entries = _config_registry_entries()
    if not entries:
        return 0

    migrated = 0
    for reg in entries:
        name = (reg.get("name") or "Registry").strip()
        if not name:
            continue
        try:
            create_registry(
                team_id=team_id,
                created_by=created_by,
                name=name,
                registry=reg.get("registry") or "docker.io",
                registry_prefix=reg.get("registry_prefix") or "",
                username=reg.get("username") or "",
                password=_password_plain_from_config_entry(reg),
                active=bool(reg.get("active", False)),
            )
            migrated += 1
        except Exception as e:
            print(f"⚠️ 迁移镜像仓库到团队 {team_id} 失败 ({name}): {e}")
    if migrated:
        print(f"✅ 已从 config 为团队 {team_id} 迁移 {migrated} 条镜像仓库")
    return migrated

# backend/template_manager.py
"""团队级用户模板元数据与权限"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.database import get_db_session
from backend.handlers import USER_TEMPLATES_DIR, get_all_templates
from backend.models import TemplateRecord
from backend.resource_permissions import (
    get_effective_permission,
    grant_creator_admin,
    require_resource_permission,
    user_can_access_resource,
)


def _builtin_template_items() -> List[Dict[str, Any]]:
    templates = get_all_templates()
    items = []
    for name, info in templates.items():
        if info.get("type") != "builtin":
            continue
        try:
            stat = os.stat(info["path"])
            items.append(
                {
                    "template_id": None,
                    "name": name,
                    "filename": os.path.basename(info["path"]),
                    "size": stat.st_size,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": "builtin",
                    "project_type": info.get("project_type", "jar"),
                    "editable": False,
                    "my_permission": "view",
                }
            )
        except OSError:
            continue
    return items


def list_templates_for_user(
    user_id: str,
    team_id: str,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    items = _builtin_template_items()
    db = get_db_session()
    try:
        rows = (
            db.query(TemplateRecord)
            .filter(TemplateRecord.team_id == team_id)
            .order_by(TemplateRecord.updated_at.desc())
            .all()
        )
        for row in rows:
            if not user_can_access_resource(db, user_id, "template", row):
                continue
            if not os.path.exists(row.file_path):
                continue
            try:
                stat = os.stat(row.file_path)
                item = {
                    "template_id": row.template_id,
                    "name": row.name,
                    "filename": os.path.basename(row.file_path),
                    "size": stat.st_size,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "type": row.template_type,
                    "project_type": row.project_type,
                    "editable": row.template_type == "user",
                    "my_permission": get_effective_permission(
                        db, user_id, "template", row.template_id
                    ),
                }
                if query:
                    ql = query.lower().strip()
                    if (
                        ql not in item["name"].lower()
                        and ql not in item.get("project_type", "").lower()
                    ):
                        continue
                items.append(item)
            except OSError:
                continue
    finally:
        db.close()
    return items


def get_template_record_by_name(team_id: str, name: str) -> Optional[TemplateRecord]:
    db = get_db_session()
    try:
        return (
            db.query(TemplateRecord)
            .filter(TemplateRecord.team_id == team_id, TemplateRecord.name == name)
            .first()
        )
    finally:
        db.close()


def get_template_record(template_id: str) -> Optional[TemplateRecord]:
    db = get_db_session()
    try:
        return (
            db.query(TemplateRecord)
            .filter(TemplateRecord.template_id == template_id)
            .first()
        )
    finally:
        db.close()


def create_template_record(
    *,
    team_id: str,
    created_by: str,
    name: str,
    project_type: str,
    file_path: str,
) -> TemplateRecord:
    db = get_db_session()
    try:
        template_id = str(uuid.uuid4())
        row = TemplateRecord(
            template_id=template_id,
            team_id=team_id,
            created_by=created_by,
            name=name,
            project_type=project_type,
            file_path=file_path,
            template_type="user",
        )
        db.add(row)
        db.commit()
        grant_creator_admin(db, "template", template_id, created_by)
        return row
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_template_record(
    template_id: str,
    user_id: str,
    *,
    name: Optional[str] = None,
    project_type: Optional[str] = None,
    file_path: Optional[str] = None,
) -> TemplateRecord:
    db = get_db_session()
    try:
        require_resource_permission(db, user_id, "template", template_id, "edit")
        row = (
            db.query(TemplateRecord)
            .filter(TemplateRecord.template_id == template_id)
            .first()
        )
        if not row:
            raise ValueError("模板不存在")
        if name is not None:
            row.name = name
        if project_type is not None:
            row.project_type = project_type
        if file_path is not None:
            row.file_path = file_path
        row.updated_at = datetime.now()
        db.commit()
        return row
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_template_record(template_id: str, user_id: str) -> Optional[TemplateRecord]:
    db = get_db_session()
    try:
        require_resource_permission(db, user_id, "template", template_id, "admin")
        row = (
            db.query(TemplateRecord)
            .filter(TemplateRecord.template_id == template_id)
            .first()
        )
        if not row:
            return None
        db.delete(row)
        db.commit()
        return row
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def user_can_read_template_by_name(
    user_id: str, team_id: str, name: str
) -> bool:
    templates = get_all_templates()
    if name in templates and templates[name].get("type") == "builtin":
        return True
    row = get_template_record_by_name(team_id, name)
    if not row:
        return False
    db = get_db_session()
    try:
        perm = get_effective_permission(db, user_id, "template", row.template_id)
        return perm is not None
    finally:
        db.close()

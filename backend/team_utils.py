# backend/team_utils.py
"""团队 slug 与序列化工具"""
from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from backend.models import Team


def slugify_name(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s)
    s = s.strip("-")
    return s or "team"


def ensure_unique_slug(
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


def team_to_dict(t: Team) -> dict:
    return {
        "team_id": t.team_id,
        "name": t.name,
        "slug": t.slug,
        "description": t.description or "",
        "avatar_url": t.avatar_url,
        "created_by": t.created_by,
        "task_cleanup_days": (
            max(1, int(t.task_cleanup_days)) if t.task_cleanup_days is not None else 7
        ),
        "max_concurrent_tasks": (
            min(10, max(1, int(t.max_concurrent_tasks)))
            if t.max_concurrent_tasks is not None
            else 10
        ),
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }

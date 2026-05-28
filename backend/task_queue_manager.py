import threading
from datetime import datetime

from backend.database import get_db_session
from backend.models import ExportTask, MigrationTask, SystemSetting, Task, Team


class GlobalTaskQueueManager:
    """全局任务并发控制器（跨构建/部署/导出）。"""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._lock = threading.Lock()
        return cls._instance

    def _get_or_create_setting(self, db, key: str, default: str, description: str = ""):
        setting = (
            db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        )
        if setting:
            return setting
        setting = SystemSetting(
            setting_key=key, setting_value=default, description=description
        )
        db.add(setting)
        db.commit()
        return setting

    def ensure_defaults(self):
        db = get_db_session()
        try:
            self._get_or_create_setting(
                db,
                "max_concurrent_tasks",
                "10",
                "系统默认最大并发任务数（运行中）",
            )
        finally:
            db.close()

    def get_max_concurrent(self, team_id: str | None = None) -> int:
        db = get_db_session()
        try:
            if team_id:
                team = db.query(Team).filter(Team.team_id == team_id).first()
                if team and team.max_concurrent_tasks is not None:
                    return min(10, max(1, int(team.max_concurrent_tasks)))
                return 10
            setting = self._get_or_create_setting(
                db, "max_concurrent_tasks", "10", "系统默认最大并发任务数（运行中）"
            )
            try:
                value = int(setting.setting_value)
            except (TypeError, ValueError):
                value = 10
            return min(10, max(1, value))
        finally:
            db.close()

    def set_max_concurrent(self, value: int, team_id: str | None = None) -> int:
        safe_value = min(10, max(1, int(value)))
        db = get_db_session()
        try:
            if team_id:
                team = db.query(Team).filter(Team.team_id == team_id).first()
                if not team:
                    return safe_value
                team.max_concurrent_tasks = safe_value
                team.updated_at = datetime.now()
                db.commit()
                return safe_value
            setting = self._get_or_create_setting(
                db, "max_concurrent_tasks", str(safe_value)
            )
            setting.setting_value = str(safe_value)
            setting.updated_at = datetime.now()
            db.commit()
            return safe_value
        finally:
            db.close()

    def get_running_count(self, team_id: str | None = None) -> int:
        db = get_db_session()
        try:
            task_q = db.query(Task).filter(Task.status == "running")
            export_q = db.query(ExportTask).filter(ExportTask.status == "running")
            migration_q = db.query(MigrationTask).filter(
                MigrationTask.status == "running"
            )
            if team_id:
                task_q = task_q.filter(Task.team_id == team_id)
                export_q = export_q.filter(ExportTask.team_id == team_id)
                migration_q = migration_q.filter(MigrationTask.team_id == team_id)
            return task_q.count() + export_q.count() + migration_q.count()
        finally:
            db.close()

    def get_pending_count(self, team_id: str | None = None) -> int:
        db = get_db_session()
        try:
            task_q = (
                db.query(Task)
                .filter(Task.status == "pending")
                .filter(Task.task_type.in_(["build", "build_from_source", "deploy"]))
            )
            export_q = db.query(ExportTask).filter(ExportTask.status == "pending")
            migration_q = db.query(MigrationTask).filter(
                MigrationTask.status == "pending"
            )
            if team_id:
                task_q = task_q.filter(Task.team_id == team_id)
                export_q = export_q.filter(ExportTask.team_id == team_id)
                migration_q = migration_q.filter(MigrationTask.team_id == team_id)
            return task_q.count() + export_q.count() + migration_q.count()
        finally:
            db.close()

    def start_if_slot_available(self, starter, team_id: str | None = None) -> bool:
        """如果团队并发槽位可用则执行 starter（内部加锁，防止并发抢占）。"""
        with self._lock:
            if self.get_running_count(team_id) >= self.get_max_concurrent(team_id):
                return False
            starter()
            return True

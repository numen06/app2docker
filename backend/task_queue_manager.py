import threading
from datetime import datetime

from backend.database import get_db_session
from backend.models import ExportTask, SystemSetting, Task


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
                "15",
                "系统全局最大并发任务数（运行中）",
            )
        finally:
            db.close()

    def get_max_concurrent(self) -> int:
        db = get_db_session()
        try:
            setting = self._get_or_create_setting(
                db, "max_concurrent_tasks", "15", "系统全局最大并发任务数（运行中）"
            )
            try:
                value = int(setting.setting_value)
            except (TypeError, ValueError):
                value = 15
            return max(1, value)
        finally:
            db.close()

    def set_max_concurrent(self, value: int) -> int:
        safe_value = max(1, int(value))
        db = get_db_session()
        try:
            setting = self._get_or_create_setting(
                db, "max_concurrent_tasks", str(safe_value)
            )
            setting.setting_value = str(safe_value)
            setting.updated_at = datetime.now()
            db.commit()
            return safe_value
        finally:
            db.close()

    def get_running_count(self) -> int:
        db = get_db_session()
        try:
            running_tasks = db.query(Task).filter(Task.status == "running").count()
            running_exports = (
                db.query(ExportTask).filter(ExportTask.status == "running").count()
            )
            return running_tasks + running_exports
        finally:
            db.close()

    def get_pending_count(self) -> int:
        db = get_db_session()
        try:
            pending_tasks = (
                db.query(Task)
                .filter(Task.status == "pending")
                .filter(Task.task_type.in_(["build_from_source", "deploy"]))
                .count()
            )
            pending_exports = (
                db.query(ExportTask).filter(ExportTask.status == "pending").count()
            )
            return pending_tasks + pending_exports
        finally:
            db.close()

    def start_if_slot_available(self, starter) -> bool:
        """如果有并发槽位则执行 starter（内部加锁，防止并发抢占）。"""
        with self._lock:
            if self.get_running_count() >= self.get_max_concurrent():
                return False
            starter()
            return True

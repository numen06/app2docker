# backend/dashboard_cache.py
"""仪表盘统计缓存管理模块"""
import threading
import time
from typing import Dict, Optional

_GLOBAL_CACHE_KEY = "__global__"


class DashboardCacheManager:
    """仪表盘统计缓存管理器"""

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = threading.Lock()
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化缓存管理器"""
        self._caches: Dict[str, Dict] = {}
        self._cache_times: Dict[str, float] = {}
        self._cache_duration = 60  # 60秒缓存有效期
        self._refreshing_keys: set = set()
        self._refresh_lock = threading.Lock()

    def _cache_key(self, team_id: Optional[str]) -> str:
        return team_id if team_id else _GLOBAL_CACHE_KEY

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._caches or cache_key not in self._cache_times:
            return False
        elapsed = time.time() - self._cache_times[cache_key]
        return elapsed < self._cache_duration

    def get_stats(
        self, team_id: Optional[str] = None, force_refresh: bool = False
    ) -> Dict:
        """
        获取仪表盘统计数据（带缓存）

        Args:
            team_id: 团队 ID；为空时统计全站
            force_refresh: 是否强制刷新缓存

        Returns:
            统计数据字典
        """
        cache_key = self._cache_key(team_id)

        with self._lock:
            if not force_refresh and self._is_cache_valid(cache_key):
                return self._caches[cache_key].copy()

            with self._refresh_lock:
                if cache_key in self._refreshing_keys and not force_refresh:
                    if cache_key in self._caches:
                        return self._caches[cache_key].copy()

                self._refreshing_keys.add(cache_key)
                try:
                    stats = self._calculate_stats(team_id=team_id)
                    self._caches[cache_key] = stats
                    self._cache_times[cache_key] = time.time()
                finally:
                    self._refreshing_keys.discard(cache_key)

            return self._caches[cache_key].copy()

    def _team_task_filter(self, db, team_id: str):
        """构建团队任务查询过滤条件"""
        from sqlalchemy import or_
        from backend.models import Task, Pipeline, DeployConfig

        pipeline_ids = db.query(Pipeline.pipeline_id).filter(
            Pipeline.team_id == team_id
        )
        deploy_ids = db.query(DeployConfig.config_id).filter(
            DeployConfig.team_id == team_id
        )
        return or_(
            Task.pipeline_id.in_(pipeline_ids),
            Task.deploy_config_id.in_(deploy_ids),
        )

    def _calculate_stats(self, team_id: Optional[str] = None) -> Dict:
        """计算仪表盘统计数据"""
        from backend.database import get_db_session
        from backend.models import (
            Task,
            Pipeline,
            GitSource,
            Host,
            AgentHost,
            ResourcePackage,
            ExportTask,
        )

        stats = {
            "totalTasks": 0,
            "runningTasks": 0,
            "completedTasks": 0,
            "pipelines": 0,
            "enabledPipelines": 0,
            "disabledPipelines": 0,
            "datasources": 0,
            "registries": 0,
            "templates": 0,
            "resourcePackages": 0,
            "hosts": 0,
            "buildStorage": 0,
            "exportStorage": 0,
            "totalStorage": 0,
        }
        build_stats = {"total_size_mb": 0, "dir_count": 0}
        export_stats = {"total_size_mb": 0, "file_count": 0}

        db = get_db_session()
        try:
            try:
                if team_id:
                    task_filter = self._team_task_filter(db, team_id)
                    stats["totalTasks"] = db.query(Task).filter(task_filter).count()
                    stats["runningTasks"] = (
                        db.query(Task)
                        .filter(task_filter, Task.status == "running")
                        .count()
                    )
                    stats["completedTasks"] = (
                        db.query(Task)
                        .filter(task_filter, Task.status == "completed")
                        .count()
                    )
                else:
                    stats["totalTasks"] = (
                        db.query(Task).count() + db.query(ExportTask).count()
                    )
                    stats["runningTasks"] = (
                        db.query(Task).filter(Task.status == "running").count()
                        + db.query(ExportTask)
                        .filter(ExportTask.status == "running")
                        .count()
                    )
                    stats["completedTasks"] = (
                        db.query(Task).filter(Task.status == "completed").count()
                        + db.query(ExportTask)
                        .filter(ExportTask.status == "completed")
                        .count()
                    )
            except Exception as e:
                print(f"⚠️ 获取任务统计失败: {e}")
                import traceback

                traceback.print_exc()

            try:
                pipeline_q = db.query(Pipeline)
                if team_id:
                    pipeline_q = pipeline_q.filter(Pipeline.team_id == team_id)
                stats["pipelines"] = pipeline_q.count()
                stats["enabledPipelines"] = pipeline_q.filter(
                    Pipeline.enabled == True
                ).count()
                stats["disabledPipelines"] = stats["pipelines"] - stats["enabledPipelines"]
            except Exception as e:
                print(f"⚠️ 获取流水线统计失败: {e}")

            try:
                ds_q = db.query(GitSource)
                if team_id:
                    ds_q = ds_q.filter(GitSource.team_id == team_id)
                stats["datasources"] = ds_q.count()
            except Exception as e:
                print(f"⚠️ 获取数据源统计失败: {e}")

            try:
                if team_id:
                    stats["hosts"] = (
                        db.query(AgentHost)
                        .filter(AgentHost.team_id == team_id)
                        .count()
                    )
                else:
                    stats["hosts"] = (
                        db.query(Host).count() + db.query(AgentHost).count()
                    )
            except Exception as e:
                print(f"⚠️ 获取主机统计失败: {e}")

            try:
                stats["resourcePackages"] = db.query(ResourcePackage).count()
            except Exception as e:
                print(f"⚠️ 获取资源包统计失败: {e}")
        finally:
            db.close()

        try:
            from backend.config import get_all_registries

            registries = get_all_registries()
            stats["registries"] = len(registries)
        except Exception as e:
            print(f"⚠️ 获取仓库统计失败: {e}")

        try:
            from backend.config import get_all_templates

            templates = get_all_templates()
            stats["templates"] = len(templates)
        except Exception as e:
            print(f"⚠️ 获取模板统计失败: {e}")

        try:
            from backend.stats_cache import StatsCacheManager
            from backend.handlers import BUILD_DIR, EXPORT_DIR

            build_cache_manager = StatsCacheManager(BUILD_DIR)
            build_stats_data = build_cache_manager.get_build_dir_stats()
            build_storage_mb = build_stats_data.get("total_size_mb", 0)
            build_stats["total_size_mb"] = build_storage_mb
            build_stats["dir_count"] = build_stats_data.get("dir_count", 0)

            export_cache_manager = StatsCacheManager(EXPORT_DIR)
            export_stats_data = export_cache_manager.get_export_dir_stats()
            export_storage_mb = export_stats_data.get("total_size_mb", 0)
            export_stats["total_size_mb"] = export_storage_mb
            export_stats["file_count"] = export_stats_data.get("file_count", 0)

            stats["buildStorage"] = build_storage_mb * 1024 * 1024
            stats["exportStorage"] = export_storage_mb * 1024 * 1024
            stats["totalStorage"] = stats["buildStorage"] + stats["exportStorage"]
        except Exception as e:
            print(f"⚠️ 获取存储统计失败: {e}")
            import traceback

            traceback.print_exc()

        return {
            "success": True,
            "stats": stats,
            "buildStats": build_stats,
            "exportStats": export_stats,
        }

    def clear_cache(self, team_id: Optional[str] = None):
        """清空缓存；team_id 为空时清空全部"""
        with self._lock:
            if team_id is None:
                self._caches.clear()
                self._cache_times.clear()
            else:
                cache_key = self._cache_key(team_id)
                self._caches.pop(cache_key, None)
                self._cache_times.pop(cache_key, None)


dashboard_cache = DashboardCacheManager()

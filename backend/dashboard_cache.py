# backend/dashboard_cache.py
"""仪表盘统计缓存管理模块"""
import threading
import time
from typing import Dict, Optional
from datetime import datetime


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
        self._cache: Optional[Dict] = None
        self._cache_time: Optional[float] = None
        self._cache_duration = 60  # 60秒缓存有效期
        self._refreshing = False
        self._refresh_lock = threading.Lock()

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self._cache is None or self._cache_time is None:
            return False
        elapsed = time.time() - self._cache_time
        return elapsed < self._cache_duration

    def get_stats(self, force_refresh: bool = False) -> Dict:
        """
        获取仪表盘统计数据（带缓存）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            统计数据字典
        """
        with self._lock:
            # 如果缓存有效且不强制刷新，直接返回
            if not force_refresh and self._is_cache_valid():
                return self._cache.copy()

            # 防止并发刷新
            with self._refresh_lock:
                if self._refreshing and not force_refresh:
                    # 如果正在刷新且不是强制刷新，返回旧缓存
                    if self._cache:
                        return self._cache.copy()

                self._refreshing = True
                try:
                    # 计算统计数据
                    stats = self._calculate_stats()
                    self._cache = stats
                    self._cache_time = time.time()
                finally:
                    self._refreshing = False

            return self._cache.copy()

    def _calculate_stats(self) -> Dict:
        """计算仪表盘统计数据"""
        from backend.database import get_db_session
        from backend.models import (
            Task, Pipeline, GitSource, Host, ResourcePackage, ExportTask,
        )

        # 初始化默认值
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

        # 使用数据库 count 查询统计，避免加载全部数据（性能更好且无截断问题）
        db = get_db_session()
        try:
            # 获取任务统计
            try:
                stats["totalTasks"] = db.query(Task).count() + db.query(ExportTask).count()
                stats["runningTasks"] = (
                    db.query(Task).filter(Task.status == "running").count()
                    + db.query(ExportTask).filter(ExportTask.status == "running").count()
                )
                stats["completedTasks"] = (
                    db.query(Task).filter(Task.status == "completed").count()
                    + db.query(ExportTask).filter(ExportTask.status == "completed").count()
                )
            except Exception as e:
                print(f"⚠️ 获取任务统计失败: {e}")
                import traceback
                traceback.print_exc()

            # 获取流水线统计
            try:
                stats["pipelines"] = db.query(Pipeline).count()
                stats["enabledPipelines"] = db.query(Pipeline).filter(Pipeline.enabled == True).count()
                stats["disabledPipelines"] = stats["pipelines"] - stats["enabledPipelines"]
            except Exception as e:
                print(f"⚠️ 获取流水线统计失败: {e}")

            # 获取数据源统计（直接 count 查询，避免 list_sources 的 50 条截断）
            try:
                stats["datasources"] = db.query(GitSource).count()
            except Exception as e:
                print(f"⚠️ 获取数据源统计失败: {e}")

            # 获取主机统计
            try:
                stats["hosts"] = db.query(Host).count()
            except Exception as e:
                print(f"⚠️ 获取主机统计失败: {e}")

            # 获取资源包统计（直接 count 查询，避免 list_packages 中的文件存在性检查开销）
            try:
                stats["resourcePackages"] = db.query(ResourcePackage).count()
            except Exception as e:
                print(f"⚠️ 获取资源包统计失败: {e}")
        finally:
            db.close()

        # 获取仓库统计（配置文件数据，保持原有方式）
        try:
            from backend.config import get_all_registries

            registries = get_all_registries()
            stats["registries"] = len(registries)
        except Exception as e:
            print(f"⚠️ 获取仓库统计失败: {e}")

        # 获取模板统计（配置文件数据，保持原有方式）
        try:
            from backend.config import get_all_templates

            templates = get_all_templates()
            stats["templates"] = len(templates)
        except Exception as e:
            print(f"⚠️ 获取模板统计失败: {e}")

        # 获取存储统计
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

            # 转换为字节
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

    def clear_cache(self):
        """清空缓存"""
        with self._lock:
            self._cache = None
            self._cache_time = None


# 全局缓存实例
dashboard_cache = DashboardCacheManager()

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

        # 获取任务统计（单独处理，避免影响其他统计）
        try:
            from backend.handlers import BuildTaskManager, ExportTaskManager

            build_manager = BuildTaskManager()
            export_manager = ExportTaskManager()

            # 获取构建任务和导出任务
            build_tasks = build_manager.list_tasks()
            export_tasks = export_manager.list_tasks()
            all_tasks = build_tasks + export_tasks

            stats["totalTasks"] = len(all_tasks)
            stats["runningTasks"] = len(
                [t for t in all_tasks if t.get("status") == "running"]
            )
            stats["completedTasks"] = len(
                [t for t in all_tasks if t.get("status") == "completed"]
            )
        except Exception as e:
            print(f"⚠️ 获取任务统计失败: {e}")
            import traceback

            traceback.print_exc()

        # 获取流水线统计
        try:
            from backend.pipeline_manager import PipelineManager

            pipeline_manager = PipelineManager()
            pipelines = pipeline_manager.list_pipelines()
            stats["pipelines"] = len(pipelines)
            stats["enabledPipelines"] = len(
                [p for p in pipelines if p.get("enabled", False)]
            )
            stats["disabledPipelines"] = stats["pipelines"] - stats["enabledPipelines"]
        except Exception as e:
            print(f"⚠️ 获取流水线统计失败: {e}")

        # 获取数据源统计
        try:
            from backend.git_source_manager import GitSourceManager

            git_source_manager = GitSourceManager()
            datasources = git_source_manager.list_sources()
            stats["datasources"] = len(datasources)
        except Exception as e:
            print(f"⚠️ 获取数据源统计失败: {e}")

        # 获取仓库统计
        try:
            from backend.config import get_all_registries

            registries = get_all_registries()
            stats["registries"] = len(registries)
        except Exception as e:
            print(f"⚠️ 获取仓库统计失败: {e}")

        # 获取模板统计
        try:
            from backend.config import get_all_templates

            templates = get_all_templates()
            stats["templates"] = len(templates)
        except Exception as e:
            print(f"⚠️ 获取模板统计失败: {e}")

        # 获取资源包统计
        try:
            from backend.resource_package_manager import ResourcePackageManager

            resource_package_manager = ResourcePackageManager()
            resource_packages = resource_package_manager.list_packages()
            stats["resourcePackages"] = len(resource_packages)
        except Exception as e:
            print(f"⚠️ 获取资源包统计失败: {e}")

        # 获取主机统计
        try:
            from backend.host_manager import HostManager

            host_manager = HostManager()
            hosts = host_manager.list_hosts()
            stats["hosts"] = len(hosts)
        except Exception as e:
            print(f"⚠️ 获取主机统计失败: {e}")

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

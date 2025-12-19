# backend/stats_cache.py
"""目录统计缓存管理模块"""
import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from pathlib import Path


class StatsCacheManager:
    """目录统计缓存管理器"""

    def __init__(self, base_dir: str, cache_filename: str = ".stats.json"):
        """
        初始化缓存管理器

        Args:
            base_dir: 要统计的目录路径
            cache_filename: 缓存文件名，默认为 .stats.json
        """
        self.base_dir = base_dir
        self.cache_file = os.path.join(base_dir, cache_filename)
        self.lock = threading.Lock()

        # 内存缓存：快速返回结果，避免频繁扫描
        self._memory_cache: Optional[Dict] = None
        self._memory_cache_time: Optional[float] = None
        self._memory_cache_duration = 300  # 5分钟内存缓存有效期（秒）

        # 后台扫描防抖：避免短时间内多次触发扫描
        self._last_scan_time: Optional[float] = None
        self._scan_debounce_interval = 60  # 60秒内最多触发一次后台扫描
        self._scanning = False

    def _load_cache(self) -> Dict:
        """加载缓存文件"""
        if not os.path.exists(self.cache_file):
            return {
                "cache_time": None,
                "total_size": 0,
                "total_size_mb": 0,
                "dir_count": 0,
                "file_count": 0,
                "items": {},
            }

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
                # 兼容旧格式
                if "items" not in cache:
                    cache["items"] = {}
                return cache
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ 加载缓存文件失败 ({self.cache_file}): {e}，将重新扫描")
            return {
                "cache_time": None,
                "total_size": 0,
                "total_size_mb": 0,
                "dir_count": 0,
                "file_count": 0,
                "items": {},
            }

    def _save_cache(self, cache: Dict):
        """保存缓存文件"""
        try:
            # 确保目录存在
            os.makedirs(self.base_dir, exist_ok=True)

            # 更新缓存时间
            cache["cache_time"] = datetime.now().isoformat()

            # 写入文件（使用临时文件确保原子性）
            temp_file = self.cache_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)

            # 原子替换
            if os.path.exists(self.cache_file):
                os.replace(temp_file, self.cache_file)
            else:
                os.rename(temp_file, self.cache_file)
        except Exception as e:
            print(f"⚠️ 保存缓存文件失败 ({self.cache_file}): {e}")
            # 清理临时文件
            temp_file = self.cache_file + ".tmp"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def _get_dir_mtime(self, dir_path: str, quick_check: bool = True) -> float:
        """
        获取目录的修改时间

        Args:
            dir_path: 目录路径
            quick_check: 如果为True，只检查目录本身的修改时间（快速模式）
                        如果为False，遍历整个目录树获取最新修改时间（完整模式）

        Returns:
            目录修改时间戳
        """
        if not os.path.exists(dir_path):
            return 0

        # 快速模式：只检查目录本身的修改时间，避免遍历整个目录树
        if quick_check:
            try:
                return os.path.getmtime(dir_path)
            except Exception as e:
                print(f"⚠️ 获取目录修改时间失败 ({dir_path}): {e}")
                return 0

        # 完整模式：遍历目录树获取最新修改时间（仅在必要时使用）
        max_mtime = os.path.getmtime(dir_path)
        try:
            for root, dirs, files in os.walk(dir_path):
                for d in dirs:
                    d_path = os.path.join(root, d)
                    try:
                        max_mtime = max(max_mtime, os.path.getmtime(d_path))
                    except:
                        pass
                for f in files:
                    f_path = os.path.join(root, f)
                    try:
                        max_mtime = max(max_mtime, os.path.getmtime(f_path))
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ 获取目录修改时间失败 ({dir_path}): {e}")

        return max_mtime

    def _is_memory_cache_valid(self) -> bool:
        """检查内存缓存是否有效"""
        if self._memory_cache is None or self._memory_cache_time is None:
            return False
        elapsed = time.time() - self._memory_cache_time
        return elapsed < self._memory_cache_duration

    def _calculate_dir_size(self, dir_path: str) -> Tuple[int, int]:
        """
        计算目录大小和文件数量

        Returns:
            (total_size, file_count)
        """
        total_size = 0
        file_count = 0

        try:
            for root, dirs, files in os.walk(dir_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        file_count += 1
                    except Exception as e:
                        print(f"⚠️ 计算文件大小失败 ({file_path}): {e}")
        except Exception as e:
            print(f"⚠️ 遍历目录失败 ({dir_path}): {e}")

        return total_size, file_count

    def get_build_dir_stats(self, force_refresh: bool = False) -> Dict:
        """
        获取构建目录统计信息（带缓存）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            {
                "success": True,
                "total_size_mb": float,
                "dir_count": int,
                "exists": bool
            }
        """
        with self.lock:
            if not os.path.exists(self.base_dir):
                result = {
                    "success": True,
                    "total_size_mb": 0,
                    "dir_count": 0,
                    "exists": False,
                }
                self._memory_cache = result
                self._memory_cache_time = time.time()
                return result

            # 检查内存缓存：如果缓存有效且不强制刷新，直接返回
            if not force_refresh and self._is_memory_cache_valid():
                return self._memory_cache.copy()

            cache = self._load_cache()
            cache_time = None
            if cache["cache_time"]:
                try:
                    cache_time = datetime.fromisoformat(cache["cache_time"]).timestamp()
                except:
                    cache_time = None

            total_size = 0
            dir_count = 0
            items = cache.get("items", {})
            updated_items = {}
            has_changes = False

            # 遍历构建目录
            current_items = set()
            for item in os.listdir(self.base_dir):
                item_path = os.path.join(self.base_dir, item)
                if not os.path.isdir(item_path):
                    continue

                # 跳过 tasks 目录和缓存文件
                if item == "tasks" or item.startswith(".stats"):
                    continue

                current_items.add(item)

                try:
                    # 快速检查：只获取目录本身的修改时间（不遍历整个目录树）
                    dir_mtime = self._get_dir_mtime(item_path, quick_check=True)

                    # 检查是否需要重新计算
                    item_cache = items.get(item)
                    need_rescan = True

                    if item_cache and cache_time:
                        cached_mtime = item_cache.get("mtime", 0)
                        # 如果目录修改时间没有变化，使用缓存
                        if dir_mtime <= cached_mtime:
                            # 使用缓存
                            item_size = item_cache.get("size", 0)
                            total_size += item_size
                            dir_count += 1
                            updated_items[item] = item_cache.copy()
                            need_rescan = False

                    if need_rescan:
                        # 目录有变化，需要重新计算
                        has_changes = True
                        # 重新计算时使用完整模式获取修改时间
                        dir_mtime = self._get_dir_mtime(item_path, quick_check=False)
                        item_size, _ = self._calculate_dir_size(item_path)
                        total_size += item_size
                        dir_count += 1
                        updated_items[item] = {
                            "size": item_size,
                            "mtime": dir_mtime,
                            "file_count": 0,  # 构建目录不统计文件数
                        }

                except Exception as e:
                    print(f"⚠️ 计算目录大小失败 ({item_path}): {e}")

            # 检查是否有目录被删除
            cached_items = set(items.keys())
            if current_items != cached_items:
                has_changes = True

            # 只有在有变化时才更新缓存文件
            if has_changes or force_refresh:
                cache["items"] = updated_items
                cache["total_size"] = total_size
                cache["total_size_mb"] = round(total_size / 1024 / 1024, 2)
                cache["dir_count"] = dir_count
                self._save_cache(cache)
            else:
                # 没有变化，使用缓存中的值
                total_size = cache.get("total_size", 0)
                dir_count = cache.get("dir_count", 0)

            result = {
                "success": True,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "dir_count": dir_count,
                "exists": True,
            }

            # 更新内存缓存
            self._memory_cache = result
            self._memory_cache_time = time.time()

            return result

    def get_export_dir_stats(self, force_refresh: bool = False) -> Dict:
        """
        获取导出目录统计信息（带缓存）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            {
                "success": True,
                "total_size_mb": float,
                "file_count": int,
                "exists": bool
            }
        """
        with self.lock:
            if not os.path.exists(self.base_dir):
                result = {
                    "success": True,
                    "total_size_mb": 0,
                    "file_count": 0,
                    "exists": False,
                }
                self._memory_cache = result
                self._memory_cache_time = time.time()
                return result

            # 检查内存缓存：如果缓存有效且不强制刷新，直接返回
            if not force_refresh and self._is_memory_cache_valid():
                return self._memory_cache.copy()

            cache = self._load_cache()
            cache_time = None
            if cache["cache_time"]:
                try:
                    cache_time = datetime.fromisoformat(cache["cache_time"]).timestamp()
                except:
                    cache_time = None

            total_size = 0
            file_count = 0
            items = cache.get("items", {})
            updated_items = {}
            has_changes = False

            # 遍历导出目录（包括所有子目录）
            current_files = set()
            for root, dirs, files in os.walk(self.base_dir):
                # 跳过缓存文件目录
                if ".stats" in root:
                    continue

                for filename in files:
                    # 跳过 tasks.json 元数据文件和缓存文件
                    if filename == "tasks.json" or filename.startswith(".stats"):
                        continue

                    file_path = os.path.join(root, filename)
                    try:
                        # 获取文件修改时间
                        file_mtime = os.path.getmtime(file_path)

                        # 使用相对路径作为 key
                        rel_path = os.path.relpath(file_path, self.base_dir)
                        current_files.add(rel_path)

                        # 检查是否需要重新计算
                        item_cache = items.get(rel_path)
                        need_rescan = True

                        if item_cache and cache_time:
                            cached_mtime = item_cache.get("mtime", 0)
                            if file_mtime <= cached_mtime:
                                # 使用缓存
                                file_size = item_cache.get("size", 0)
                                total_size += file_size
                                file_count += 1
                                updated_items[rel_path] = item_cache.copy()
                                need_rescan = False

                        if need_rescan:
                            # 文件有变化，需要重新计算
                            has_changes = True
                            file_size = os.path.getsize(file_path)
                            total_size += file_size
                            file_count += 1
                            updated_items[rel_path] = {
                                "size": file_size,
                                "mtime": file_mtime,
                                "file_count": 1,
                            }

                    except Exception as e:
                        print(f"⚠️ 计算文件大小失败 ({file_path}): {e}")

            # 检查是否有文件被删除
            cached_files = set(items.keys())
            if current_files != cached_files:
                has_changes = True

            # 只有在有变化时才更新缓存文件
            if has_changes or force_refresh:
                cache["items"] = updated_items
                cache["total_size"] = total_size
                cache["total_size_mb"] = round(total_size / 1024 / 1024, 2)
                cache["file_count"] = file_count
                self._save_cache(cache)
            else:
                # 没有变化，使用缓存中的值
                total_size = cache.get("total_size", 0)
                file_count = cache.get("file_count", 0)

            result = {
                "success": True,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "file_count": file_count,
                "exists": True,
            }

            # 更新内存缓存
            self._memory_cache = result
            self._memory_cache_time = time.time()

            return result

    def update_cache_async(self, stats_type: str = "build"):
        """
        异步更新缓存（在后台线程中执行，带防抖机制）

        Args:
            stats_type: 统计类型，"build" 或 "export"
        """
        current_time = time.time()

        # 防抖检查：如果距离上次扫描时间太短，跳过本次扫描
        if self._last_scan_time is not None:
            elapsed = current_time - self._last_scan_time
            if elapsed < self._scan_debounce_interval:
                # 距离上次扫描时间太短，跳过
                return

        # 如果正在扫描，跳过
        if self._scanning:
            return

        self._last_scan_time = current_time
        self._scanning = True

        def _update():
            try:
                if stats_type == "build":
                    self.get_build_dir_stats(force_refresh=True)
                elif stats_type == "export":
                    self.get_export_dir_stats(force_refresh=True)
            except Exception as e:
                print(f"⚠️ 异步更新统计缓存失败: {e}")
            finally:
                self._scanning = False

        thread = threading.Thread(target=_update, daemon=True)
        thread.start()

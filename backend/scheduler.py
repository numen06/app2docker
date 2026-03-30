# backend/scheduler.py
"""流水线定时调度器"""
import threading
import time
from datetime import datetime, timedelta
from typing import Optional
from croniter import croniter
from backend.pipeline_manager import PipelineManager
from backend.handlers import BuildManager


class PipelineScheduler:
    """流水线定时调度器"""
    
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.pipeline_manager = PipelineManager()
        self.build_manager = None  # 延迟初始化
    
    def start(self):
        """启动调度器"""
        if self.running:
            print("⚠️ 调度器已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("✅ 流水线调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("✅ 流水线调度器已停止")
    
    def _run(self):
        """调度器主循环"""
        last_agent_check = 0
        agent_check_interval = 60  # 每60秒检查一次Agent主机
        last_portainer_check = 0
        portainer_check_interval = 120  # 每120秒检查一次Portainer主机（使用较长的间隔，避免频繁检测）
        last_docker_refresh = 0
        docker_refresh_interval = 1800  # 每30分钟刷新一次Docker信息缓存
        
        while self.running:
            try:
                self._check_pipelines()
                
                current_time = time.time()
                
                # 定期检查Agent主机离线状态
                if current_time - last_agent_check >= agent_check_interval:
                    self._check_agent_hosts()
                    last_agent_check = current_time
                
                # 定期检查Portainer主机状态
                if current_time - last_portainer_check >= portainer_check_interval:
                    self._check_portainer_hosts()
                    last_portainer_check = current_time
                
                # 定期刷新Docker信息缓存
                if current_time - last_docker_refresh >= docker_refresh_interval:
                    self._refresh_docker_info()
                    last_docker_refresh = current_time
            except Exception as e:
                print(f"❌ 调度器执行出错: {e}")
                import traceback
                traceback.print_exc()
            
            # 每分钟检查一次
            time.sleep(60)
    
    def _check_pipelines(self):
        """检查并执行到期的流水线"""
        now = datetime.now()
        
        # 获取所有启用的流水线
        pipelines = self.pipeline_manager.list_pipelines(enabled=True)
        
        for pipeline in pipelines:
            cron_expr = pipeline.get("cron_expression")
            if not cron_expr:
                continue
            
            pipeline_id = pipeline.get("pipeline_id")
            
            try:
                # 验证 cron 表达式
                if not croniter.is_valid(cron_expr):
                    print(f"⚠️ 流水线 {pipeline_id} 的 cron 表达式无效: {cron_expr}")
                    continue
                
                # 计算下次执行时间
                next_run = pipeline.get("next_run_time")
                
                if next_run is None:
                    # 首次运行，计算下次执行时间（基于上一分钟，确保错过的时间点也能触发）
                    cron = croniter(cron_expr, now - timedelta(minutes=1))
                    next_run_time = cron.get_next(datetime)
                    self._update_next_run_time(pipeline_id, next_run_time)
                    print(f"📅 流水线 {pipeline['name']} 下次执行时间: {next_run_time}")
                    # 如果下次执行时间已过或即将到达（1分钟内），立即触发
                    if now >= next_run_time - timedelta(minutes=1):
                        print(f"🚀 首次触发定时流水线: {pipeline['name']}")
                        self._trigger_pipeline(pipeline)
                        cron = croniter(cron_expr, now)
                        next_run_time = cron.get_next(datetime)
                        self._update_next_run_time(pipeline_id, next_run_time)
                        print(f"📅 流水线 {pipeline['name']} 新的下次执行时间: {next_run_time}")
                    continue
                
                # 解析下次执行时间
                next_run_dt = datetime.fromisoformat(next_run)
                
                # 检查是否到期
                if now >= next_run_dt:
                    print(f"🚀 触发定时流水线: {pipeline['name']}")
                    self._trigger_pipeline(pipeline)
                    
                    # 计算新的下次执行时间
                    cron = croniter(cron_expr, now)
                    next_run_time = cron.get_next(datetime)
                    self._update_next_run_time(pipeline_id, next_run_time)
                    print(f"📅 流水线 {pipeline['name']} 新的下次执行时间: {next_run_time}")
            
            except Exception as e:
                print(f"❌ 处理流水线 {pipeline_id} 时出错: {e}")
                import traceback
                traceback.print_exc()
    
    def _update_next_run_time(self, pipeline_id: str, next_run_time: datetime):
        """更新流水线的下次执行时间"""
        try:
            pipeline = self.pipeline_manager.get_pipeline(pipeline_id)
            if pipeline:
                pipeline["next_run_time"] = next_run_time.isoformat()
                # 直接保存
                self.pipeline_manager._save_pipelines()
        except Exception as e:
            print(f"❌ 更新下次执行时间失败: {e}")
    
    def _trigger_pipeline(self, pipeline: dict):
        """触发流水线构建"""
        try:
            pipeline_id = pipeline.get("pipeline_id")
            pipeline_name = pipeline.get("name", "unknown")
            
            # 从流水线配置生成任务配置JSON
            from backend.handlers import pipeline_to_task_config
            task_config = pipeline_to_task_config(pipeline, trigger_source="cron")
            
            # 检查防抖和相同信息（3秒内相同信息要屏蔽）
            is_same_trigger = self.pipeline_manager.check_same_trigger_info(
                pipeline_id, task_config, debounce_seconds=3
            )
            if is_same_trigger:
                # 3秒内相同信息，屏蔽
                print(
                    f"🚫 流水线 {pipeline_name} 触发被屏蔽（3秒内相同信息）"
                )
                return
            
            # 检查是否有正在运行的任务
            current_task_id = self.pipeline_manager.get_pipeline_running_task(pipeline_id)
            if current_task_id:
                # 检查任务是否真的在运行
                if self.build_manager is None:
                    self.build_manager = BuildManager()
                
                task = self.build_manager.task_manager.get_task(current_task_id)
                if task and task.get("status") in ["pending", "running"]:
                    # 有任务正在运行，立即创建新任务（状态为 pending，等待执行）
                    task_id = self.build_manager._trigger_task_from_config(task_config)
                    # 更新最后一次触发的配置信息
                    self.pipeline_manager.update_last_trigger_config(pipeline_id, task_config)
                    queue_length = self.pipeline_manager.get_queue_length(pipeline_id)
                    print(f"⚠️ 流水线 {pipeline_name} 已有正在执行的任务 {current_task_id[:8]}，已创建新任务（pending），队列长度: {queue_length}")
                    return
                else:
                    # 任务已完成或不存在，解绑
                    self.pipeline_manager.unbind_task(pipeline_id)
            
            # 延迟导入避免循环依赖
            if self.build_manager is None:
                self.build_manager = BuildManager()
            
            # 没有运行中的任务，立即启动构建任务
            task_id = self.build_manager._trigger_task_from_config(task_config)
            # 更新最后一次触发的配置信息
            self.pipeline_manager.update_last_trigger_config(pipeline_id, task_config)
            
            print(f"✅ 定时触发流水线: {pipeline_name}, 任务ID: {task_id[:8]}")
            
            # 记录触发并绑定任务（定时触发）
            self.pipeline_manager.record_trigger(
                pipeline_id, 
                task_id,
                trigger_source="cron",
                trigger_info={
                    "cron_expression": pipeline.get("cron_expression"),
                    "branch": pipeline.get("branch"),
                }
            )
            
        except Exception as e:
            pipeline_name = pipeline.get("name", "unknown")
            print(f"❌ 触发流水线 {pipeline_name} 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _check_agent_hosts(self):
        """检查并更新离线Agent主机"""
        try:
            from backend.agent_host_manager import AgentHostManager
            manager = AgentHostManager()
            manager.check_offline_hosts(timeout_seconds=60)
        except Exception as e:
            print(f"⚠️ 检查Agent主机状态失败: {e}")
    
    def _check_portainer_hosts(self):
        """检查Portainer主机状态"""
        try:
            from backend.agent_host_manager import AgentHostManager
            manager = AgentHostManager()
            manager.check_portainer_hosts_status()
        except Exception as e:
            print(f"⚠️ 检查Portainer主机失败: {e}")
    
    def _refresh_docker_info(self):
        """刷新Docker信息缓存"""
        try:
            from backend.docker_info_cache import docker_info_cache
            docker_info_cache.refresh_cache()
            print("✅ Docker信息缓存已刷新（后台任务）")
        except Exception as e:
            print(f"⚠️ 刷新Docker信息缓存失败: {e}")


# 全局调度器实例
_scheduler: Optional[PipelineScheduler] = None


def get_scheduler() -> PipelineScheduler:
    """获取调度器实例（单例）"""
    global _scheduler
    if _scheduler is None:
        _scheduler = PipelineScheduler()
    return _scheduler


def start_scheduler():
    """启动调度器"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """停止调度器"""
    scheduler = get_scheduler()
    scheduler.stop()

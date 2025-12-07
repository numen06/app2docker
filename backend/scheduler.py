# backend/scheduler.py
"""流水线定时调度器"""
import threading
import time
from datetime import datetime
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
        while self.running:
            try:
                self._check_pipelines()
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
                    # 首次运行，计算下次执行时间
                    cron = croniter(cron_expr, now)
                    next_run_time = cron.get_next(datetime)
                    self._update_next_run_time(pipeline_id, next_run_time)
                    print(f"📅 流水线 {pipeline['name']} 下次执行时间: {next_run_time}")
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
            # 延迟导入避免循环依赖
            if self.build_manager is None:
                self.build_manager = BuildManager()
            
            # 提取构建参数
            git_url = pipeline.get("git_url")
            branch = pipeline.get("branch") or "main"
            project_type = pipeline.get("project_type", "jar")
            template = pipeline.get("template")
            image_name = pipeline.get("image_name", "my-app")
            tag = pipeline.get("tag", "latest")
            push = pipeline.get("push", False)
            push_registry = pipeline.get("push_registry")
            template_params = pipeline.get("template_params", {})
            sub_path = pipeline.get("sub_path")
            use_project_dockerfile = pipeline.get("use_project_dockerfile", True)
            
            # 启动构建任务
            task_id = self.build_manager.start_build_from_source(
                git_url=git_url,
                branch=branch,
                project_type=project_type,
                template=template,
                image_name=image_name,
                tag=tag,
                push=push,
                push_registry=push_registry,
                template_params=template_params,
                sub_path=sub_path,
                use_project_dockerfile=use_project_dockerfile,
                username="scheduler"  # 系统用户
            )
            
            # 记录触发
            self.pipeline_manager.record_trigger(pipeline.get("pipeline_id"))
            
            print(f"✅ 定时流水线 {pipeline['name']} 已触发，任务ID: {task_id}")
        
        except Exception as e:
            print(f"❌ 触发流水线失败: {e}")
            import traceback
            traceback.print_exc()


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

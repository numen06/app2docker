# backend/pipeline_manager.py
"""流水线管理器 - 用于管理预配置的 Git 构建流水线（基于数据库）"""
import json
import uuid
import hmac
import hashlib
import threading
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from backend.database import get_db_session, init_db
from backend.models import Pipeline, PipelineTaskHistory

# 确保数据库已初始化
try:
    init_db()
except:
    pass


class PipelineManager:
    """流水线管理器（基于数据库）"""

    def __init__(self):
        self.lock = threading.RLock()

    def _safe_get_json_field(self, pipeline, field_name, default_value):
        """安全地获取 JSON 字段，如果解码失败返回默认值"""
        try:
            value = getattr(pipeline, field_name, None)
            if value is None:
                return default_value
            # 如果已经是字典或列表，直接返回
            if isinstance(value, (dict, list)):
                return value
            # 如果是字符串，尝试解析（虽然 SQLAlchemy 应该已经解析了）
            if isinstance(value, str):
                import json

                return json.loads(value) if value else default_value
            return value
        except Exception as e:
            print(f"⚠️ 获取字段 {field_name} 失败: {e}")
            return default_value

    def _to_dict(self, pipeline: Pipeline) -> Dict:
        """将数据库模型转换为字典"""
        if not pipeline:
            return None

        try:
            return {
                "pipeline_id": pipeline.pipeline_id,
                "name": pipeline.name,
                "description": pipeline.description,
                "enabled": pipeline.enabled,
                "git_url": pipeline.git_url,
                "branch": pipeline.branch,
                "sub_path": pipeline.sub_path,
                "project_type": pipeline.project_type,
                "template": pipeline.template,
                "image_name": pipeline.image_name,
                "tag": pipeline.tag,
                "push": pipeline.push,
                "push_registry": pipeline.push_registry,
                "template_params": self._safe_get_json_field(
                    pipeline, "template_params", {}
                ),
                "use_project_dockerfile": pipeline.use_project_dockerfile,
                "dockerfile_name": pipeline.dockerfile_name,
                "webhook_token": pipeline.webhook_token,
                "webhook_secret": pipeline.webhook_secret,
                "webhook_branch_filter": pipeline.webhook_branch_filter,
                "webhook_use_push_branch": pipeline.webhook_use_push_branch,
                "webhook_allowed_branches": self._safe_get_json_field(
                    pipeline, "webhook_allowed_branches", []
                ),
                "branch_tag_mapping": self._safe_get_json_field(
                    pipeline, "branch_tag_mapping", {}
                ),
                "source_id": pipeline.source_id,
                "selected_services": self._safe_get_json_field(
                    pipeline, "selected_services", []
                ),
                "service_push_config": self._safe_get_json_field(
                    pipeline, "service_push_config", {}
                ),
                "service_template_params": self._safe_get_json_field(
                    pipeline, "service_template_params", {}
                ),
                "push_mode": pipeline.push_mode,
                "resource_package_configs": self._safe_get_json_field(
                    pipeline, "resource_package_configs", []
                ),
                "cron_expression": pipeline.cron_expression,
                "next_run_time": (
                    pipeline.next_run_time.isoformat()
                    if pipeline.next_run_time
                    else None
                ),
                "current_task_id": pipeline.current_task_id,
                "task_queue": self._safe_get_json_field(pipeline, "task_queue", []),
                "created_at": (
                    pipeline.created_at.isoformat() if pipeline.created_at else None
                ),
                "updated_at": (
                    pipeline.updated_at.isoformat() if pipeline.updated_at else None
                ),
                "last_triggered_at": (
                    pipeline.last_triggered_at.isoformat()
                    if pipeline.last_triggered_at
                    else None
                ),
                "trigger_count": pipeline.trigger_count,
            }
        except Exception as e:
            print(
                f"⚠️ 转换流水线 {pipeline.pipeline_id if pipeline else 'None'} 为字典失败: {e}"
            )
            import traceback

            traceback.print_exc()
            # 返回基本信息，避免完全失败
            return {
                "pipeline_id": getattr(pipeline, "pipeline_id", None),
                "name": getattr(pipeline, "name", "Unknown"),
                "enabled": getattr(pipeline, "enabled", False),
                "error": f"转换失败: {str(e)}",
            }

    def create_pipeline(
        self,
        name: str,
        git_url: str,
        branch: str = None,
        project_type: str = "jar",
        template: str = None,
        image_name: str = None,
        tag: str = "latest",
        push: bool = False,
        push_registry: str = None,
        template_params: dict = None,
        sub_path: str = None,
        use_project_dockerfile: bool = True,
        dockerfile_name: str = "Dockerfile",
        webhook_secret: str = None,
        webhook_token: str = None,
        enabled: bool = True,
        description: str = "",
        cron_expression: str = None,
        webhook_branch_filter: bool = False,
        webhook_use_push_branch: bool = True,
        webhook_allowed_branches: list = None,
        branch_tag_mapping: dict = None,
        source_id: str = None,
        selected_services: list = None,
        service_push_config: dict = None,
        service_template_params: dict = None,
        push_mode: str = "multi",
        resource_package_configs: list = None,
    ) -> str:
        """创建流水线配置"""
        pipeline_id = str(uuid.uuid4())

        # 生成 Webhook Token
        if not webhook_token:
            webhook_token = str(uuid.uuid4())

        # 检查 token 是否已被使用
        db = get_db_session()
        try:
            existing = (
                db.query(Pipeline)
                .filter(Pipeline.webhook_token == webhook_token)
                .first()
            )
            if existing:
                raise ValueError(f"Webhook Token '{webhook_token}' 已被其他流水线使用")

            # 如果没有提供 webhook_secret，生成一个
            if not webhook_secret:
                webhook_secret = str(uuid.uuid4())

            pipeline = Pipeline(
                pipeline_id=pipeline_id,
                name=name,
                description=description,
                enabled=enabled,
                git_url=git_url,
                branch=branch,
                sub_path=sub_path,
                project_type=project_type,
                template=template,
                image_name=image_name,
                tag=tag,
                push=push,
                push_registry=push_registry,
                template_params=template_params or {},
                use_project_dockerfile=use_project_dockerfile,
                dockerfile_name=dockerfile_name,
                webhook_token=webhook_token,
                webhook_secret=webhook_secret,
                webhook_branch_filter=webhook_branch_filter,
                webhook_use_push_branch=webhook_use_push_branch,
                webhook_allowed_branches=webhook_allowed_branches or [],
                branch_tag_mapping=branch_tag_mapping or {},
                source_id=source_id,
                selected_services=selected_services or [],
                service_push_config=service_push_config or {},
                service_template_params=service_template_params or {},
                push_mode=push_mode or "multi",
                resource_package_configs=resource_package_configs or [],
                cron_expression=cron_expression,
                task_queue=[],
            )

            db.add(pipeline)
            db.commit()
            return pipeline_id
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict]:
        """获取流水线配置"""
        # 使用原始 SQL 查询来避免 JSON 解码问题（与 list_pipelines 保持一致）
        import sqlite3
        from backend.database import DB_FILE

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # 先尝试参数化查询
            cursor.execute(
                "SELECT * FROM pipelines WHERE pipeline_id = ?", (pipeline_id,)
            )
            row = cursor.fetchone()

            # 如果没找到，尝试获取所有流水线并在内存中匹配（处理可能的编码问题）
            if not row:
                cursor.execute("SELECT * FROM pipelines")
                all_rows = cursor.fetchall()
                for r in all_rows:
                    if r["pipeline_id"] == pipeline_id:
                        row = r
                        break

            if not row:
                return None

            # 手动构建字典，安全处理 JSON 字段（与 list_pipelines 逻辑一致）
            pipeline_dict = {
                "pipeline_id": row["pipeline_id"],
                "name": row["name"],
                "description": row["description"] or "",
                "enabled": bool(row["enabled"]),
                "git_url": row["git_url"],
                "branch": row["branch"],
                "sub_path": row["sub_path"],
                "project_type": row["project_type"],
                "template": row["template"],
                "image_name": row["image_name"],
                "tag": row["tag"],
                "push": bool(row["push"]),
                "push_registry": row["push_registry"],
                "template_params": self._safe_parse_json(row["template_params"], {}),
                "use_project_dockerfile": bool(row["use_project_dockerfile"]),
                "dockerfile_name": row["dockerfile_name"],
                "webhook_token": row["webhook_token"],
                "webhook_secret": row["webhook_secret"],
                "webhook_branch_filter": bool(row["webhook_branch_filter"]),
                "webhook_use_push_branch": bool(row["webhook_use_push_branch"]),
                "webhook_allowed_branches": self._safe_parse_json(
                    (
                        row["webhook_allowed_branches"]
                        if "webhook_allowed_branches" in row.keys()
                        else None
                    ),
                    [],
                ),
                "branch_tag_mapping": self._safe_parse_json(
                    row["branch_tag_mapping"], {}
                ),
                "source_id": row["source_id"],
                "selected_services": self._safe_parse_json(
                    row["selected_services"], []
                ),
                "service_push_config": self._safe_parse_json(
                    row["service_push_config"], {}
                ),
                "service_template_params": self._safe_parse_json(
                    row["service_template_params"], {}
                ),
                "push_mode": row["push_mode"],
                "resource_package_configs": self._safe_parse_json(
                    row["resource_package_configs"], []
                ),
                "cron_expression": row["cron_expression"],
                "next_run_time": row["next_run_time"],
                "current_task_id": row["current_task_id"],
                "task_queue": self._safe_parse_json(row["task_queue"], []),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "last_triggered_at": row["last_triggered_at"],
                "trigger_count": row["trigger_count"] or 0,
            }

            # 格式化日期时间
            from datetime import datetime

            for date_field in [
                "created_at",
                "updated_at",
                "last_triggered_at",
                "next_run_time",
            ]:
                if pipeline_dict[date_field]:
                    if isinstance(pipeline_dict[date_field], datetime):
                        pipeline_dict[date_field] = pipeline_dict[
                            date_field
                        ].isoformat()

            return pipeline_dict
        finally:
            conn.close()

    def get_pipeline_by_token(self, webhook_token: str) -> Optional[Dict]:
        """通过 Webhook Token 获取流水线配置"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline)
                .filter(Pipeline.webhook_token == webhook_token)
                .first()
            )
            return self._to_dict(pipeline)
        finally:
            db.close()

    def list_pipelines(self, enabled: bool = None) -> List[Dict]:
        """列出所有流水线配置"""
        db = get_db_session()
        try:
            # 使用原始 SQL 查询来避免 SQLAlchemy 的 JSON 自动解码问题
            import sqlite3
            from backend.database import DB_FILE

            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            try:
                if enabled is not None:
                    cursor.execute(
                        "SELECT * FROM pipelines WHERE enabled = ? ORDER BY created_at DESC",
                        (enabled,),
                    )
                else:
                    cursor.execute("SELECT * FROM pipelines ORDER BY created_at DESC")

                rows = cursor.fetchall()
                result = []

                for row in rows:
                    try:
                        # 手动构建字典，安全处理 JSON 字段
                        pipeline_dict = {
                            "pipeline_id": row["pipeline_id"],
                            "name": row["name"],
                            "description": row["description"] or "",
                            "enabled": bool(row["enabled"]),
                            "git_url": row["git_url"],
                            "branch": row["branch"],
                            "sub_path": row["sub_path"],
                            "project_type": row["project_type"],
                            "template": row["template"],
                            "image_name": row["image_name"],
                            "tag": row["tag"],
                            "push": bool(row["push"]),
                            "push_registry": row["push_registry"],
                            "template_params": self._safe_parse_json(
                                row["template_params"], {}
                            ),
                            "use_project_dockerfile": bool(
                                row["use_project_dockerfile"]
                            ),
                            "dockerfile_name": row["dockerfile_name"],
                            "webhook_token": row["webhook_token"],
                            "webhook_secret": row["webhook_secret"],
                            "webhook_branch_filter": bool(row["webhook_branch_filter"]),
                            "webhook_use_push_branch": bool(
                                row["webhook_use_push_branch"]
                            ),
                            "webhook_allowed_branches": self._safe_parse_json(
                                (
                                    row["webhook_allowed_branches"]
                                    if "webhook_allowed_branches" in row.keys()
                                    else None
                                ),
                                [],
                            ),
                            "branch_tag_mapping": self._safe_parse_json(
                                row["branch_tag_mapping"], {}
                            ),
                            "source_id": row["source_id"],
                            "selected_services": self._safe_parse_json(
                                row["selected_services"], []
                            ),
                            "service_push_config": self._safe_parse_json(
                                row["service_push_config"], {}
                            ),
                            "service_template_params": self._safe_parse_json(
                                row["service_template_params"], {}
                            ),
                            "push_mode": row["push_mode"],
                            "resource_package_configs": self._safe_parse_json(
                                row["resource_package_configs"], []
                            ),
                            "cron_expression": row["cron_expression"],
                            "next_run_time": row["next_run_time"],
                            "current_task_id": row["current_task_id"],
                            "task_queue": self._safe_parse_json(row["task_queue"], []),
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                            "last_triggered_at": row["last_triggered_at"],
                            "trigger_count": row["trigger_count"] or 0,
                        }

                        # 格式化日期时间（SQLite 返回的是字符串，需要转换为 ISO 格式）
                        from datetime import datetime

                        for date_field in [
                            "created_at",
                            "updated_at",
                            "last_triggered_at",
                            "next_run_time",
                        ]:
                            if pipeline_dict[date_field]:
                                # 如果已经是字符串格式，直接使用；否则转换为 ISO 格式
                                if isinstance(pipeline_dict[date_field], datetime):
                                    pipeline_dict[date_field] = pipeline_dict[
                                        date_field
                                    ].isoformat()
                                elif isinstance(pipeline_dict[date_field], str):
                                    # 已经是字符串，保持原样
                                    pass

                        result.append(pipeline_dict)
                    except Exception as e:
                        pipeline_id = (
                            row["pipeline_id"]
                            if "pipeline_id" in row.keys()
                            else "Unknown"
                        )
                        print(f"⚠️ 跳过流水线 {pipeline_id}: {e}")
                        import traceback

                        traceback.print_exc()

                return result
            finally:
                conn.close()
        finally:
            db.close()

    def _safe_parse_json(self, value, default):
        """安全地解析 JSON 值"""
        if value is None or value == "":
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            import json

            return json.loads(value) if value else default
        except (json.JSONDecodeError, TypeError):
            return default

    def update_pipeline(
        self,
        pipeline_id: str,
        name: str = None,
        git_url: str = None,
        branch: str = None,
        project_type: str = None,
        template: str = None,
        image_name: str = None,
        tag: str = None,
        push: bool = None,
        push_registry: str = None,
        template_params: dict = None,
        sub_path: str = None,
        use_project_dockerfile: bool = None,
        dockerfile_name: str = None,
        webhook_secret: str = None,
        webhook_token: str = None,
        enabled: bool = None,
        description: str = None,
        cron_expression: str = None,
        webhook_branch_filter: bool = None,
        webhook_use_push_branch: bool = None,
        webhook_allowed_branches: list = None,
        branch_tag_mapping: dict = None,
        source_id: str = None,
        selected_services: list = None,
        service_push_config: dict = None,
        service_template_params: dict = None,
        push_mode: str = None,
        resource_package_configs: list = None,
    ) -> bool:
        """更新流水线配置"""
        db = get_db_session()
        try:
            # 先刷新 session，确保获取最新的数据
            db.expire_all()
            
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            if not pipeline:
                return False

            # 刷新对象，确保与数据库同步
            db.refresh(pipeline)

            # 更新字段
            if name is not None:
                pipeline.name = name
            if git_url is not None:
                pipeline.git_url = git_url
            if branch is not None:
                pipeline.branch = branch
            if project_type is not None:
                pipeline.project_type = project_type
            if template is not None:
                pipeline.template = template
            if image_name is not None:
                pipeline.image_name = image_name
            if tag is not None:
                pipeline.tag = tag
            if push is not None:
                pipeline.push = push
            if push_registry is not None:
                pipeline.push_registry = push_registry
            if template_params is not None:
                pipeline.template_params = template_params
            if sub_path is not None:
                pipeline.sub_path = sub_path
            if use_project_dockerfile is not None:
                pipeline.use_project_dockerfile = use_project_dockerfile
            if dockerfile_name is not None:
                pipeline.dockerfile_name = dockerfile_name
            if webhook_secret is not None:
                pipeline.webhook_secret = webhook_secret
            if webhook_token is not None:
                # 检查 token 是否已被其他流水线使用
                existing = (
                    db.query(Pipeline)
                    .filter(
                        Pipeline.webhook_token == webhook_token,
                        Pipeline.pipeline_id != pipeline_id,
                    )
                    .first()
                )
                if existing:
                    raise ValueError(
                        f"Webhook Token '{webhook_token}' 已被其他流水线使用"
                    )
                pipeline.webhook_token = webhook_token
            if enabled is not None:
                pipeline.enabled = enabled
            if description is not None:
                pipeline.description = description
            if cron_expression is not None:
                pipeline.cron_expression = cron_expression
            if webhook_branch_filter is not None:
                pipeline.webhook_branch_filter = webhook_branch_filter
            if webhook_use_push_branch is not None:
                pipeline.webhook_use_push_branch = webhook_use_push_branch
            if webhook_allowed_branches is not None:
                pipeline.webhook_allowed_branches = webhook_allowed_branches
            if branch_tag_mapping is not None:
                pipeline.branch_tag_mapping = branch_tag_mapping
            if source_id is not None:
                pipeline.source_id = source_id
            if selected_services is not None:
                pipeline.selected_services = selected_services
            if service_push_config is not None:
                pipeline.service_push_config = service_push_config
            if service_template_params is not None:
                pipeline.service_template_params = service_template_params
            if push_mode is not None:
                pipeline.push_mode = push_mode
            if resource_package_configs is not None:
                pipeline.resource_package_configs = resource_package_configs

            pipeline.updated_at = datetime.now()

            # 提交更改
            try:
                db.flush()  # 先 flush，检查是否有错误
                db.commit()
            except Exception as commit_error:
                # 如果 commit 失败，记录错误并回滚
                db.rollback()
                error_msg = str(commit_error)
                print(f"⚠️ 数据库提交失败: {error_msg}")
                print(f"⚠️ 流水线ID: {pipeline_id}")
                # 如果是更新行数不匹配的错误，可能是对象已被删除或并发修改
                if (
                    "expected to update" in error_msg.lower()
                    and "0 were matched" in error_msg.lower()
                ):
                    print(f"⚠️ 流水线可能在更新过程中被删除或并发修改: {pipeline_id}")
                    # 重新查询确认流水线是否还存在
                    db.expire_all()  # 清除缓存
                    check_pipeline = (
                        db.query(Pipeline)
                        .filter(Pipeline.pipeline_id == pipeline_id)
                        .first()
                    )
                    if not check_pipeline:
                        print(f"⚠️ 确认：流水线已被删除: {pipeline_id}")
                        return False
                    else:
                        print(
                            f"⚠️ 确认：流水线仍然存在，可能是并发修改导致: {pipeline_id}"
                        )
                        # 尝试重新更新：重新获取对象并更新
                        try:
                            db.refresh(check_pipeline)
                            # 使用字典收集需要更新的字段，然后批量应用
                            updates = {}
                            if name is not None:
                                updates['name'] = name
                            if git_url is not None:
                                updates['git_url'] = git_url
                            if branch is not None:
                                updates['branch'] = branch
                            if project_type is not None:
                                updates['project_type'] = project_type
                            if template is not None:
                                updates['template'] = template
                            if image_name is not None:
                                updates['image_name'] = image_name
                            if tag is not None:
                                updates['tag'] = tag
                            if push is not None:
                                updates['push'] = push
                            if push_registry is not None:
                                updates['push_registry'] = push_registry
                            if template_params is not None:
                                updates['template_params'] = template_params
                            if sub_path is not None:
                                updates['sub_path'] = sub_path
                            if use_project_dockerfile is not None:
                                updates['use_project_dockerfile'] = use_project_dockerfile
                            if dockerfile_name is not None:
                                updates['dockerfile_name'] = dockerfile_name
                            if webhook_secret is not None:
                                updates['webhook_secret'] = webhook_secret
                            if webhook_token is not None:
                                # 检查 token 是否已被其他流水线使用
                                existing = (
                                    db.query(Pipeline)
                                    .filter(
                                        Pipeline.webhook_token == webhook_token,
                                        Pipeline.pipeline_id != pipeline_id,
                                    )
                                    .first()
                                )
                                if existing:
                                    raise ValueError(
                                        f"Webhook Token '{webhook_token}' 已被其他流水线使用"
                                    )
                                updates['webhook_token'] = webhook_token
                            if enabled is not None:
                                updates['enabled'] = enabled
                            if description is not None:
                                updates['description'] = description
                            if cron_expression is not None:
                                updates['cron_expression'] = cron_expression
                            if webhook_branch_filter is not None:
                                updates['webhook_branch_filter'] = webhook_branch_filter
                            if webhook_use_push_branch is not None:
                                updates['webhook_use_push_branch'] = webhook_use_push_branch
                            if webhook_allowed_branches is not None:
                                updates['webhook_allowed_branches'] = webhook_allowed_branches
                            if branch_tag_mapping is not None:
                                updates['branch_tag_mapping'] = branch_tag_mapping
                            if source_id is not None:
                                updates['source_id'] = source_id
                            if selected_services is not None:
                                updates['selected_services'] = selected_services
                            if service_push_config is not None:
                                updates['service_push_config'] = service_push_config
                            if service_template_params is not None:
                                updates['service_template_params'] = service_template_params
                            if push_mode is not None:
                                updates['push_mode'] = push_mode
                            if resource_package_configs is not None:
                                updates['resource_package_configs'] = resource_package_configs
                            
                            # 批量应用更新
                            for key, value in updates.items():
                                setattr(check_pipeline, key, value)
                            
                            check_pipeline.updated_at = datetime.now()
                            db.commit()
                            print(f"✅ 重试更新成功: {pipeline_id}")
                            return True
                        except Exception as retry_error:
                            db.rollback()
                            print(f"⚠️ 重试更新也失败: {retry_error}")
                            raise ValueError(f"流水线更新失败，可能是并发修改: {error_msg}")
                raise

            return True
        except Exception as e:
            db.rollback()
            # 如果是字段不存在的错误，尝试迁移数据库
            if (
                "no such column" in str(e).lower()
                or "webhook_allowed_branches" in str(e).lower()
            ):
                try:
                    from backend.database import migrate_add_webhook_allowed_branches

                    migrate_add_webhook_allowed_branches()
                    # 重试更新
                    db.commit()
                    return True
                except Exception as migrate_error:
                    print(f"⚠️ 数据库迁移失败: {migrate_error}")
                    raise ValueError(f"数据库字段缺失，请重启应用以自动迁移: {str(e)}")
            raise
        finally:
            db.close()

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """删除流水线配置"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            if not pipeline:
                return False

            db.delete(pipeline)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def record_trigger(
        self,
        pipeline_id: str,
        task_id: str = None,
        trigger_source: str = "unknown",
        trigger_info: dict = None,
    ):
        """记录流水线触发"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            if not pipeline:
                return

            pipeline.last_triggered_at = datetime.now()
            pipeline.trigger_count = (pipeline.trigger_count or 0) + 1

            if task_id:
                pipeline.current_task_id = task_id

                # 记录到任务历史表
                history = PipelineTaskHistory(
                    pipeline_id=pipeline_id,
                    task_id=task_id,
                    trigger_source=trigger_source,
                    trigger_info=trigger_info or {},
                )
                db.add(history)
                # 立即刷新，确保对象已持久化
                db.flush()

            # 提交主操作
            db.commit()

        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

        # 限制历史记录数量（保留最近100条）- 使用单独的数据库会话
        if task_id:
            self._cleanup_old_history(pipeline_id)

    def _cleanup_old_history(self, pipeline_id: str):
        """清理旧的历史记录（保留最近100条）"""
        db = get_db_session()
        try:
            history_count = (
                db.query(PipelineTaskHistory)
                .filter(PipelineTaskHistory.pipeline_id == pipeline_id)
                .count()
            )
            if history_count > 100:
                # 查询需要删除的最旧记录
                oldest_records = (
                    db.query(PipelineTaskHistory)
                    .filter(PipelineTaskHistory.pipeline_id == pipeline_id)
                    .order_by(PipelineTaskHistory.triggered_at.asc())
                    .limit(history_count - 100)
                    .all()
                )
                # 删除最旧的记录
                for record in oldest_records:
                    db.delete(record)
                db.commit()
        except Exception as cleanup_error:
            # 清理失败不影响主流程
            print(f"⚠️ 清理历史记录失败: {cleanup_error}")
            try:
                db.rollback()
            except:
                pass
        finally:
            db.close()

    def get_pipeline_running_task(self, pipeline_id: str) -> Optional[str]:
        """获取流水线当前正在执行的任务ID"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            return pipeline.current_task_id if pipeline else None
        finally:
            db.close()

    def unbind_task(self, pipeline_id: str):
        """解绑流水线的任务绑定"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            if pipeline:
                pipeline.current_task_id = None
                db.commit()
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def add_task_to_queue(self, pipeline_id: str, task_config: dict) -> str:
        """将任务添加到队列"""
        queue_id = str(uuid.uuid4())
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            if not pipeline:
                raise ValueError(f"流水线不存在: {pipeline_id}")

            queue = pipeline.task_queue or []
            queue.append(
                {
                    "queue_id": queue_id,
                    "task_config": task_config,
                    "created_at": datetime.now().isoformat(),
                }
            )
            pipeline.task_queue = queue
            pipeline.last_triggered_at = datetime.now()
            db.commit()
            return queue_id
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def get_queue_length(self, pipeline_id: str) -> int:
        """获取队列长度（从实际任务列表中统计）"""
        try:
            from backend.handlers import BuildManager

            build_manager = BuildManager()
            pending_tasks = build_manager.task_manager.list_tasks(status="pending")

            current_task_id = self.get_pipeline_running_task(pipeline_id)

            queue_count = 0
            for task in pending_tasks:
                task_config = task.get("task_config", {})
                task_pipeline_id = task_config.get("pipeline_id")
                task_id = task.get("task_id")

                if task_pipeline_id == pipeline_id and task_id != current_task_id:
                    queue_count += 1

            return queue_count
        except Exception as e:
            print(f"⚠️ 获取队列长度失败: {e}")
            import traceback

            traceback.print_exc()
            # 回退到使用字段的方式
            db = get_db_session()
            try:
                pipeline = (
                    db.query(Pipeline)
                    .filter(Pipeline.pipeline_id == pipeline_id)
                    .first()
                )
                return len(pipeline.task_queue or []) if pipeline else 0
            finally:
                db.close()

    def get_next_queued_task(self, pipeline_id: str) -> Optional[dict]:
        """获取队列中的下一个任务配置"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            if pipeline and pipeline.task_queue:
                return pipeline.task_queue[0]
            return None
        finally:
            db.close()

    def remove_queued_task(self, pipeline_id: str, queue_id: str = None):
        """从队列中移除任务"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            if not pipeline or not pipeline.task_queue:
                return

            queue = pipeline.task_queue
            if queue_id:
                pipeline.task_queue = [
                    q for q in queue if q.get("queue_id") != queue_id
                ]
            else:
                pipeline.task_queue = queue[1:] if len(queue) > 1 else []

            db.commit()
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def find_pipeline_by_task(self, task_id: str) -> Optional[str]:
        """根据任务ID查找绑定的流水线ID"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.current_task_id == task_id).first()
            )
            return pipeline.pipeline_id if pipeline else None
        finally:
            db.close()

    def check_debounce(self, pipeline_id: str, debounce_seconds: int = 5) -> bool:
        """检查是否在防抖时间内"""
        db = get_db_session()
        try:
            pipeline = (
                db.query(Pipeline).filter(Pipeline.pipeline_id == pipeline_id).first()
            )
            if not pipeline or not pipeline.last_triggered_at:
                return False

            elapsed = (datetime.now() - pipeline.last_triggered_at).total_seconds()
            return elapsed < debounce_seconds
        finally:
            db.close()

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str,
        signature_header: str = "sha256",
    ) -> bool:
        """验证 Webhook 签名"""
        try:
            if "=" in signature:
                algo, sig = signature.split("=", 1)
            else:
                algo = signature_header
                sig = signature

            if algo.lower() == "sha1":
                mac = hmac.new(secret.encode(), payload, hashlib.sha1)
            elif algo.lower() == "sha256":
                mac = hmac.new(secret.encode(), payload, hashlib.sha256)
            else:
                print(f"❌ 不支持的签名算法: {algo}")
                return False

            expected_sig = mac.hexdigest()
            result = hmac.compare_digest(expected_sig, sig)

            if not result:
                print(
                    f"❌ 签名不匹配: expected={expected_sig[:8]}..., got={sig[:8]}..., algo={algo}"
                )

            return result
        except Exception as e:
            print(f"❌ Webhook 签名验证异常: {e}")
            import traceback

            traceback.print_exc()
            return False

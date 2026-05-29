# backend/migration_manager.py
"""镜像迁移任务管理：跨仓库 pull + tag + push，支持手动与 Cron 定时。"""
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from croniter import croniter

from backend.handlers import (
    DOCKER_AVAILABLE,
    GlobalTaskQueueManager,
    _process_global_queued_tasks,
    docker_builder,
    init_docker_builder,
)


def _parse_image_ref(image_ref: str) -> Tuple[str, str]:
    """解析完整镜像引用为 repository 与 tag。"""
    ref = (image_ref or "").strip()
    if ref.startswith("https://"):
        ref = ref[8:]
    elif ref.startswith("http://"):
        ref = ref[7:]
    if not ref:
        raise ValueError("镜像名称不能为空")
    if " " in ref:
        raise ValueError("镜像名称不能包含空格")
    if ":" in ref:
        repo, tag = ref.rsplit(":", 1)
        if not repo:
            raise ValueError("镜像名称格式无效")
        return repo, tag or "latest"
    return ref, "latest"


def _normalize_registry_credentials(
    username: str, password: str
) -> Tuple[str, str]:
    """仅当用户名与密码均非空时视为有效凭证（公开仓库勿带空/错误密码）。"""
    u = (username or "").strip()
    p = (password or "").strip()
    if u and p:
        return u, p
    return "", ""


def _build_auth_config(
    registry_host: str, username: str, password: str
) -> Optional[Dict[str, str]]:
    username, password = _normalize_registry_credentials(username, password)
    if not username or not password:
        return None
    host = (registry_host or "").strip()
    auth: Dict[str, str] = {"username": username, "password": password}
    if host and host != "docker.io":
        auth["serveraddress"] = host
    else:
        auth["serveraddress"] = "https://index.docker.io/v1/"
    return auth


def _login_registry(
    registry_host: str, username: str, password: str, label: str = ""
) -> None:
    username, password = _normalize_registry_credentials(username, password)
    if not username or not password:
        return
    if not hasattr(docker_builder, "client") or not docker_builder.client:
        return
    host = (registry_host or "").strip()
    login_registry = host if host and host != "docker.io" else None
    docker_builder.client.login(
        username=username,
        password=password,
        registry=login_registry,
    )


def _consume_stream(stream, check_stop=None) -> None:
    for chunk in stream:
        if check_stop and check_stop():
            raise RuntimeError("任务已停止")
        if isinstance(chunk, dict) and chunk.get("error"):
            raise RuntimeError(chunk["error"])


def _tag_image(src_full: str, tgt_repo: str, tgt_tag: str) -> None:
    """为镜像打目标标签（使用 Docker API，兼容 Image 对象与低层 client）。"""
    if not docker_builder or not docker_builder.is_available():
        raise RuntimeError("Docker 不可用，无法打标签")

    client = getattr(docker_builder, "client", None)
    if client and hasattr(client, "api"):
        docker_builder.get_image(src_full)
        client.api.tag(src_full, tgt_repo, tag=tgt_tag)
        return

    image = docker_builder.get_image(src_full)
    if hasattr(image, "tag"):
        image.tag(tgt_repo, tag=tgt_tag)
        return

    raise RuntimeError("Docker 客户端不可用，无法打标签")


def _registry_api_base(registry_host: str) -> str:
    host = (registry_host or "docker.io").strip().rstrip("/")
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    if host in ("docker.io", "index.docker.io"):
        return "https://registry-1.docker.io"
    return f"https://{host}"


def _split_repository_for_manifest(repository: str, configured_registry: str) -> Tuple[str, str]:
    """将 pull 用的 repository 拆为 registry 主机与 v2 API 镜像名。"""
    parts = (repository or "").split("/")
    if not parts:
        return (configured_registry or "docker.io").strip(), ""
    first = parts[0]
    if len(parts) >= 2 and ("." in first or ":" in first or first == "localhost"):
        host = first
        name = "/".join(parts[1:])
    else:
        host = (configured_registry or "docker.io").strip()
        name = repository
    if name and host in ("docker.io", "index.docker.io") and "/" not in name:
        name = f"library/{name}"
    return host, name


def _apply_basic_auth(req, username: str, password: str) -> None:
    import base64

    if username and password:
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode(
            "ascii"
        )
        req.add_header("Authorization", f"Basic {token}")


def _manifest_accept_header(req) -> None:
    req.add_header(
        "Accept",
        "application/vnd.docker.distribution.manifest.v2+json, "
        "application/vnd.docker.distribution.manifest.list.v2+json",
    )


def _parse_bearer_challenge(www_authenticate: str) -> Optional[Dict[str, str]]:
    """解析 Registry v2 的 Bearer 挑战（公开仓库也会先返回 401 + 此头，并非密码错误）。"""
    import re

    if not www_authenticate:
        return None
    text = www_authenticate
    if isinstance(text, (list, tuple)):
        text = ", ".join(str(x) for x in text)
    for part in re.split(r"(?i)(?<=\s),?\s*(?=Bearer\s)", text):
        if "bearer" not in part.lower():
            continue
        params: Dict[str, str] = {}
        for key in ("realm", "service", "scope"):
            m = re.search(rf'{key}="([^"]*)"', part, re.I)
            if m:
                params[key] = m.group(1)
        if params.get("realm"):
            return params
    return None


def _fetch_registry_bearer_token(
    challenge: Dict[str, str],
    username: str,
    password: str,
    image_name: str = "",
    registry_host: str = "",
    timeout: int = 20,
) -> str:
    import json
    import urllib.parse
    import urllib.request

    realm = (challenge.get("realm") or "").strip()
    if not realm:
        raise ValueError("仓库未提供 token 地址")

    params: Dict[str, str] = {}
    service = (challenge.get("service") or registry_host or "").strip()
    scope = (challenge.get("scope") or "").strip()
    if service:
        params["service"] = service
    if scope:
        params["scope"] = scope
    elif image_name:
        params["scope"] = f"repository:{image_name}:pull"

    url = realm
    if params:
        url = f"{realm}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(url, method="GET")
    user, pwd = _normalize_registry_credentials(username, password)
    if user and pwd:
        _apply_basic_auth(req, user, pwd)

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    token = data.get("token") or data.get("access_token")
    if not token:
        raise ValueError("仓库 token 响应无效")
    return str(token)


def _manifest_http_once(
    manifest_url: str,
    method: str,
    *,
    basic_user: str = "",
    basic_pass: str = "",
    bearer_token: str = "",
    timeout: int = 20,
):
    import urllib.request

    req = urllib.request.Request(manifest_url, method=method)
    _manifest_accept_header(req)
    if bearer_token:
        req.add_header("Authorization", f"Bearer {bearer_token}")
    elif basic_user and basic_pass:
        _apply_basic_auth(req, basic_user, basic_pass)
    return urllib.request.urlopen(req, timeout=timeout)


def _open_manifest_request(
    manifest_url: str,
    method: str,
    username: str,
    password: str,
    image_name: str = "",
    registry_host: str = "",
    timeout: int = 20,
):
    """
    请求 manifest。Docker Registry v2 会先 401 并要求 Bearer token（公开源亦然）；
    携带错误 Basic 认证时会在有凭证时回退为匿名再走 token 流程。
    """
    import urllib.error

    user, pwd = _normalize_registry_credentials(username, password)
    use_basic_attempts = [True, False] if user and pwd else [False]
    last_error: Optional[urllib.error.HTTPError] = None

    for use_basic in use_basic_attempts:
        try:
            return _manifest_http_once(
                manifest_url,
                method,
                basic_user=user if use_basic else "",
                basic_pass=pwd if use_basic else "",
                timeout=timeout,
            )
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code != 401:
                raise
            challenge = _parse_bearer_challenge(
                e.headers.get("WWW-Authenticate", "")
            )
            if challenge:
                try:
                    token = _fetch_registry_bearer_token(
                        challenge,
                        user,
                        pwd,
                        image_name=image_name,
                        registry_host=registry_host,
                        timeout=timeout,
                    )
                    return _manifest_http_once(
                        manifest_url,
                        method,
                        bearer_token=token,
                        timeout=timeout,
                    )
                except urllib.error.HTTPError as bearer_err:
                    last_error = bearer_err
                    if bearer_err.code != 401:
                        raise
                except Exception:
                    pass
            continue

    if last_error:
        raise last_error
    raise RuntimeError("无法请求镜像 manifest")


def test_source_image_availability(
    source_image: str,
    source_registry_name: str,
    team_id: Optional[str],
    user_id: Optional[str],
) -> Dict[str, Any]:
    """
    检测源镜像在远程仓库是否存在（Registry v2 manifest），非仅测试仓库连通性。
    """
    import urllib.error
    from urllib.parse import quote

    full_ref = (source_image or "").strip()
    if not full_ref:
        return {"success": False, "message": "请先填写源镜像路径与标签"}
    if not (source_registry_name or "").strip():
        return {"success": False, "message": "请先选择源镜像仓库"}

    try:
        repo, tag = _parse_image_ref(full_ref)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    cfg = _load_team_registry_config(source_registry_name, team_id, user_id)
    reg_host, image_name = _split_repository_for_manifest(repo, cfg.get("registry") or "")
    if not image_name:
        return {"success": False, "message": "镜像名称无效"}

    username = cfg.get("username") or ""
    password = cfg.get("password") or ""
    base = _registry_api_base(reg_host)
    manifest_url = (
        f"{base}/v2/{quote(image_name, safe='')}/manifests/{quote(tag, safe='')}"
    )

    try:
        with _open_manifest_request(
            manifest_url,
            "HEAD",
            username,
            password,
            image_name=image_name,
            registry_host=reg_host,
        ) as resp:
            if resp.status in (200, 201):
                return {
                    "success": True,
                    "message": f"源镜像存在：{full_ref}",
                    "details": f"HTTP {resp.status} {manifest_url}",
                }
            return {
                "success": False,
                "message": f"仓库返回异常: HTTP {resp.status}",
                "details": manifest_url,
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {
                "success": False,
                "message": f"源镜像不存在：{full_ref}",
                "details": manifest_url,
                "suggestions": [
                    "请检查镜像路径与标签是否正确",
                    "确认该镜像已推送到源仓库",
                ],
            }
        if e.code == 401:
            u, p = _normalize_registry_credentials(username, password)
            if u and p:
                msg = "无法访问该镜像：账号或密码无效"
                suggestions = [
                    "请检查源仓库配置中的用户名与密码",
                    "公开镜像源请清空用户名和密码",
                ]
            else:
                msg = "无法访问该镜像：仓库拒绝拉取或镜像不存在"
                suggestions = [
                    "请检查镜像路径、标签与仓库前缀是否正确",
                    "私有镜像请在源仓库中配置有效的 pull 账号",
                ]
            return {
                "success": False,
                "message": msg,
                "details": manifest_url,
                "suggestions": suggestions,
            }
        if e.code == 403:
            return {
                "success": False,
                "message": "无法访问该镜像：无权限",
                "details": manifest_url,
            }
        # 部分仓库不支持 HEAD，尝试 GET
        if e.code == 405:
            return _test_source_image_manifest_get(
                manifest_url,
                full_ref,
                username,
                password,
                image_name=image_name,
                registry_host=reg_host,
            )
        return {
            "success": False,
            "message": f"检测失败: HTTP {e.code}",
            "details": str(e) or manifest_url,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"无法检测源镜像: {e}",
            "details": manifest_url,
            "suggestions": [
                "请检查源仓库地址与网络",
                "确认镜像路径、标签与仓库前缀配置一致",
            ],
        }


def _test_source_image_manifest_get(
    manifest_url: str,
    full_ref: str,
    username: str,
    password: str,
    image_name: str = "",
    registry_host: str = "",
) -> Dict[str, Any]:
    import urllib.error

    try:
        with _open_manifest_request(
            manifest_url,
            "GET",
            username,
            password,
            image_name=image_name,
            registry_host=reg_host,
        ) as resp:
            if 200 <= resp.status < 300:
                return {
                    "success": True,
                    "message": f"源镜像存在：{full_ref}",
                    "details": f"HTTP {resp.status}",
                }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {
                "success": False,
                "message": f"源镜像不存在：{full_ref}",
                "details": manifest_url,
            }
    except Exception as e:
        return {"success": False, "message": f"无法检测源镜像: {e}"}
    return {"success": False, "message": f"源镜像不存在：{full_ref}"}


def _load_team_registry_config(
    registry_name: str,
    team_id: Optional[str],
    user_id: Optional[str],
) -> Dict[str, str]:
    """从团队已配置仓库读取地址与凭证。"""
    name = (registry_name or "").strip()
    if not name:
        raise ValueError("请选择镜像仓库")
    from backend.config import get_registry_by_name

    cfg = get_registry_by_name(name, team_id=team_id, user_id=user_id)
    if not cfg:
        raise ValueError(f"仓库「{name}」不存在或无权访问")
    u, p = _normalize_registry_credentials(
        cfg.get("username") or "", cfg.get("password") or ""
    )
    return {
        "registry": (cfg.get("registry") or "").strip(),
        "username": u,
        "password": p,
    }


class MigrationTaskManager:
    """镜像迁移任务管理器（单例）"""

    _instance_lock = threading.Lock()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        from backend.database import init_db

        try:
            init_db()
        except Exception:
            pass
        self.lock = threading.Lock()
        self._running_threads: Dict[str, threading.Thread] = {}

    def _to_dict(self, task) -> dict:
        if not task:
            return {}
        return {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "source_registry": task.source_registry or "",
            "source_registry_name": task.source_registry_name or "",
            "source_username": task.source_username or "",
            "source_has_password": bool(task.source_password),
            "source_image": task.source_image or "",
            "target_registry": task.target_registry or "",
            "target_registry_name": task.target_registry_name or "",
            "target_username": task.target_username or "",
            "target_has_password": bool(task.target_password),
            "target_image": task.target_image or "",
            "status": task.status,
            "schedule_cron": task.schedule_cron or "",
            "schedule_enabled": bool(task.schedule_enabled),
            "next_run_time": (
                task.next_run_time.isoformat() if task.next_run_time else None
            ),
            "run_count": task.run_count or 0,
            "last_run_at": (
                task.last_run_at.isoformat() if task.last_run_at else None
            ),
            "last_run_status": task.last_run_status or "",
            "error": task.error or "",
            "team_id": getattr(task, "team_id", None),
            "created_by": getattr(task, "created_by", None),
            "created_at": (
                task.created_at.isoformat() if task.created_at else None
            ),
            "updated_at": (
                task.updated_at.isoformat() if task.updated_at else None
            ),
        }

    def list_tasks(
        self, team_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[dict]:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            q = db.query(MigrationTask)
            if team_id:
                q = q.filter(MigrationTask.team_id == team_id)
            if status:
                q = q.filter(MigrationTask.status == status)
            rows = q.order_by(MigrationTask.created_at.desc()).all()
            return [self._to_dict(r) for r in rows]
        finally:
            db.close()

    def get_task(self, task_id: str) -> Optional[dict]:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            row = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            return self._to_dict(row) if row else None
        finally:
            db.close()

    def create_task(
        self,
        task_name: str,
        source_image: str,
        target_image: str,
        source_registry: str = "",
        source_registry_name: str = "",
        source_username: str = "",
        source_password: str = "",
        target_registry: str = "",
        target_registry_name: str = "",
        target_username: str = "",
        target_password: str = "",
        schedule_cron: str = "",
        schedule_enabled: bool = False,
        team_id: Optional[str] = None,
        created_by: Optional[str] = None,
        execute_now: bool = False,
    ) -> str:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        _parse_image_ref(source_image)
        _parse_image_ref(target_image)

        if not (source_registry_name or "").strip():
            raise ValueError("请选择源镜像仓库")
        if not (target_registry_name or "").strip():
            raise ValueError("请选择目标镜像仓库")

        src_cfg = _load_team_registry_config(
            source_registry_name, team_id, created_by
        )
        tgt_cfg = _load_team_registry_config(
            target_registry_name, team_id, created_by
        )
        source_registry = src_cfg["registry"]
        target_registry = tgt_cfg["registry"]
        # 凭证不写入任务表，执行时从团队仓库配置读取
        source_username = ""
        source_password = ""
        target_username = ""
        target_password = ""

        if schedule_enabled and schedule_cron:
            if not croniter.is_valid(schedule_cron):
                raise ValueError(f"无效的 Cron 表达式: {schedule_cron}")

        task_id = str(uuid.uuid4())
        now = datetime.now()
        next_run = None
        if schedule_enabled and schedule_cron:
            cron = croniter(schedule_cron, now - timedelta(minutes=1))
            next_run = cron.get_next(datetime)

        db = get_db_session()
        try:
            obj = MigrationTask(
                task_id=task_id,
                task_name=task_name or source_image,
                source_registry=source_registry or "",
                source_registry_name=source_registry_name or "",
                source_username=source_username or "",
                source_password=source_password or "",
                source_image=source_image.strip(),
                target_registry=target_registry or "",
                target_registry_name=target_registry_name or "",
                target_username=target_username or "",
                target_password=target_password or "",
                target_image=target_image.strip(),
                status="idle",
                schedule_cron=schedule_cron or "",
                schedule_enabled=bool(schedule_enabled),
                next_run_time=next_run,
                team_id=team_id,
                created_by=created_by,
                created_at=now,
                updated_at=now,
            )
            db.add(obj)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        if execute_now:
            self.execute_task(task_id, trigger_source="manual")
        return task_id

    def update_task(self, task_id: str, **fields) -> bool:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        allowed = {
            "task_name",
            "source_registry",
            "source_registry_name",
            "source_username",
            "source_password",
            "source_image",
            "target_registry",
            "target_registry_name",
            "target_username",
            "target_password",
            "target_image",
            "schedule_cron",
            "schedule_enabled",
        }

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if not task:
                return False
            if task.status == "running":
                raise ValueError("任务运行中，无法编辑")

            for key, value in fields.items():
                if key not in allowed:
                    continue
                if key.endswith("_password") or key.endswith("_username"):
                    continue
                setattr(task, key, value)

            team_id = getattr(task, "team_id", None)
            user_id = getattr(task, "created_by", None)
            if fields.get("source_registry_name"):
                src_cfg = _load_team_registry_config(
                    fields["source_registry_name"], team_id, user_id
                )
                task.source_registry = src_cfg["registry"]
                task.source_username = ""
                task.source_password = ""
            if fields.get("target_registry_name"):
                tgt_cfg = _load_team_registry_config(
                    fields["target_registry_name"], team_id, user_id
                )
                task.target_registry = tgt_cfg["registry"]
                task.target_username = ""
                task.target_password = ""

            if "source_image" in fields and fields["source_image"]:
                _parse_image_ref(fields["source_image"])
            if "target_image" in fields and fields["target_image"]:
                _parse_image_ref(fields["target_image"])

            cron_expr = task.schedule_cron or ""
            enabled = bool(task.schedule_enabled)
            if enabled and cron_expr:
                if not croniter.is_valid(cron_expr):
                    raise ValueError(f"无效的 Cron 表达式: {cron_expr}")
                cron = croniter(cron_expr, datetime.now() - timedelta(minutes=1))
                task.next_run_time = cron.get_next(datetime)
            elif not enabled:
                task.next_run_time = None

            task.updated_at = datetime.now()
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def toggle_schedule(self, task_id: str, enabled: Optional[bool] = None) -> bool:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if not task:
                return False
            if enabled is None:
                task.schedule_enabled = not task.schedule_enabled
            else:
                task.schedule_enabled = bool(enabled)

            if task.schedule_enabled:
                if not (task.schedule_cron or "").strip():
                    raise ValueError("请先配置 Cron 表达式")
                if not croniter.is_valid(task.schedule_cron):
                    raise ValueError(f"无效的 Cron 表达式: {task.schedule_cron}")
                cron = croniter(
                    task.schedule_cron, datetime.now() - timedelta(minutes=1)
                )
                task.next_run_time = cron.get_next(datetime)
            else:
                task.next_run_time = None

            task.updated_at = datetime.now()
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_task(self, task_id: str) -> bool:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if not task:
                return False
            if task.status == "running":
                return False
            db.delete(task)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def stop_task(self, task_id: str) -> bool:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if not task:
                return False
            if task.status not in ("running", "pending"):
                return False
            was_running = task.status == "running"
            task.status = "stopped"
            task.error = "任务已停止"
            task.updated_at = datetime.now()
            db.commit()
            if was_running:
                _process_global_queued_tasks()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def execute_task(
        self, task_id: str, trigger_source: str = "manual"
    ) -> bool:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if not task:
                return False
            if task.status in ("running", "pending"):
                return False
            task.status = "pending"
            task.error = ""
            task.updated_at = datetime.now()
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        _process_global_queued_tasks()
        return True

    def start_pending_task(self, task_id: str) -> bool:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if not task or task.status != "pending":
                return False
            task.status = "running"
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        thread = threading.Thread(
            target=self._run_migration,
            args=(task_id,),
            daemon=True,
        )
        self._running_threads[task_id] = thread
        thread.start()
        return True

    def _is_stopped(self, task_id: str) -> bool:
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            return not task or task.status == "stopped"
        finally:
            db.close()

    def _finish_run(
        self,
        task_id: str,
        success: bool,
        error: str = "",
        trigger_source: str = "manual",
    ):
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if not task:
                return

            if task.status == "stopped":
                return

            now = datetime.now()
            task.run_count = (task.run_count or 0) + 1
            task.last_run_at = now
            task.last_run_status = "completed" if success else "failed"
            task.status = "idle" if success else "failed"
            task.error = error or ""
            task.updated_at = now

            if task.schedule_enabled and task.schedule_cron:
                try:
                    cron = croniter(task.schedule_cron, now)
                    task.next_run_time = cron.get_next(datetime)
                except Exception:
                    pass
            elif not task.schedule_enabled:
                task.next_run_time = None

            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
            self._running_threads.pop(task_id, None)
            _process_global_queued_tasks()

    def _resolve_registry_auth(
        self,
        registry_name: str,
        registry_host: str,
        username: str,
        password: str,
        team_id: Optional[str],
        user_id: Optional[str],
    ) -> Tuple[str, str, str]:
        """优先从团队已配置仓库读取凭证。"""
        name = (registry_name or "").strip()
        if name:
            try:
                cfg = _load_team_registry_config(name, team_id, user_id)
                u, p = _normalize_registry_credentials(
                    cfg.get("username") or "", cfg.get("password") or ""
                )
                return (
                    u,
                    p,
                    cfg.get("registry") or registry_host or "",
                )
            except Exception as e:
                print(f"⚠️ 解析仓库配置失败: {e}")
        return username or "", password or "", registry_host or ""

    def _run_migration(self, task_id: str):
        from backend.database import get_db_session
        from backend.models import MigrationTask

        print(f"🔄 [镜像迁移] 开始: {task_id[:8]}")

        if not DOCKER_AVAILABLE:
            try:
                init_docker_builder()
            except Exception:
                pass
        if not DOCKER_AVAILABLE:
            self._finish_run(
                task_id, False, error="Docker 服务不可用，无法执行镜像迁移"
            )
            return

        conn_info = ""
        try:
            conn_info = docker_builder.get_connection_info() or ""
        except Exception:
            pass
        if "模拟" in conn_info or not getattr(docker_builder, "client", None):
            self._finish_run(
                task_id,
                False,
                error="Docker 服务不可用或未连接，无法执行镜像迁移（请确认本机 Docker 已启动）",
            )
            return

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if not task or task.status == "stopped":
                return

            source_image = task.source_image
            target_image = task.target_image
            src_repo, src_tag = _parse_image_ref(source_image)
            tgt_repo, tgt_tag = _parse_image_ref(target_image)
            src_full = f"{src_repo}:{src_tag}"
            tgt_full = f"{tgt_repo}:{tgt_tag}"

            team_id = getattr(task, "team_id", None)
            user_id = getattr(task, "created_by", None)
            src_user, src_pass, src_host = self._resolve_registry_auth(
                task.source_registry_name,
                task.source_registry,
                task.source_username,
                task.source_password,
                team_id,
                user_id,
            )
            tgt_user, tgt_pass, tgt_host = self._resolve_registry_auth(
                task.target_registry_name,
                task.target_registry,
                task.target_username,
                task.target_password,
                team_id,
                user_id,
            )
            src_auth = _build_auth_config(src_host, src_user, src_pass)
            tgt_auth = _build_auth_config(tgt_host, tgt_user, tgt_pass)

            check = lambda: self._is_stopped(task_id)

            print(f"📥 [镜像迁移] 拉取: {src_full}")
            _login_registry(src_host, src_user, src_pass, "source")
            pull_stream = docker_builder.pull_image(src_repo, src_tag, src_auth)
            _consume_stream(pull_stream, check_stop=check)

            if check():
                return

            print(f"🏷️ [镜像迁移] 打标签: {src_full} -> {tgt_full}")
            _tag_image(src_full, tgt_repo, tgt_tag)

            if check():
                return

            print(f"📤 [镜像迁移] 推送: {tgt_full}")
            _login_registry(tgt_host, tgt_user, tgt_pass, "target")
            push_stream = docker_builder.push_image(tgt_repo, tgt_tag, tgt_auth)
            _consume_stream(push_stream, check_stop=check)

            print(f"✅ [镜像迁移] 完成: {task_id[:8]}")
            self._finish_run(task_id, True)
        except Exception as e:
            import traceback

            err = str(e)
            print(f"❌ [镜像迁移] 失败: {err}")
            traceback.print_exc()
            if not self._is_stopped(task_id):
                self._finish_run(task_id, False, error=err)
        finally:
            db.close()

    def list_scheduled_tasks(self) -> List[dict]:
        """返回启用定时的任务（供调度器使用）。"""
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            rows = (
                db.query(MigrationTask)
                .filter(MigrationTask.schedule_enabled == True)
                .filter(MigrationTask.schedule_cron != "")
                .all()
            )
            return [self._to_dict(r) for r in rows]
        finally:
            db.close()

    def update_next_run_time(self, task_id: str, next_run: datetime):
        from backend.database import get_db_session
        from backend.models import MigrationTask

        db = get_db_session()
        try:
            task = (
                db.query(MigrationTask)
                .filter(MigrationTask.task_id == task_id)
                .first()
            )
            if task:
                task.next_run_time = next_run
                task.updated_at = datetime.now()
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def check_scheduled_migrations(self):
        """检查并触发到期的定时迁移任务。"""
        now = datetime.now()
        tasks = self.list_scheduled_tasks()

        for t in tasks:
            task_id = t.get("task_id")
            cron_expr = (t.get("schedule_cron") or "").strip()
            if not cron_expr or not croniter.is_valid(cron_expr):
                continue

            status = t.get("status")
            if status in ("running", "pending"):
                continue

            next_run = t.get("next_run_time")
            try:
                if next_run is None:
                    cron = croniter(cron_expr, now - timedelta(minutes=1))
                    next_run_time = cron.get_next(datetime)
                    self.update_next_run_time(task_id, next_run_time)
                    if now >= next_run_time - timedelta(minutes=1):
                        print(f"🚀 首次触发定时镜像迁移: {t.get('task_name')}")
                        self.execute_task(task_id, trigger_source="cron")
                        cron = croniter(cron_expr, now)
                        self.update_next_run_time(task_id, cron.get_next(datetime))
                    continue

                next_run_dt = datetime.fromisoformat(next_run)
                if now >= next_run_dt:
                    print(f"🚀 触发定时镜像迁移: {t.get('task_name')}")
                    self.execute_task(task_id, trigger_source="cron")
                    cron = croniter(cron_expr, now)
                    self.update_next_run_time(task_id, cron.get_next(datetime))
            except Exception as e:
                print(f"❌ 处理定时迁移 {task_id} 失败: {e}")

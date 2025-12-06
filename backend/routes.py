# backend/routes.py
"""FastAPI 路由定义"""
import os
from typing import Optional
from fastapi import (
    APIRouter,
    File,
    UploadFile,
    Form,
    Query,
    HTTPException,
    Request,
    Response,
    Body,
)
from fastapi.responses import (
    JSONResponse,
    PlainTextResponse,
    FileResponse,
    StreamingResponse,
)
from pydantic import BaseModel

from backend.handlers import (
    BuildManager,
    ExportTaskManager,
    OperationLogger,
    generate_image_name,
    get_all_templates,
    get_template_path,
    BUILTIN_TEMPLATES_DIR,
    USER_TEMPLATES_DIR,
    EXPORT_DIR,
    natural_sort_key,
    docker_builder,
    DOCKER_AVAILABLE,
)
from backend.config import (
    load_config,
    save_config,
    get_active_registry,
    get_registry_by_name,
    get_all_registries,
)
from backend.utils import get_safe_filename
from backend.auth import authenticate, verify_token
import jwt

def get_current_username(request: Request) -> str:
    """从请求中获取当前用户名"""
    try:
        # FastAPI/Starlette 会将 header 名称标准化为小写
        # 使用小写 'authorization' 是标准做法
        # 注意：request.headers 是 Headers 对象，支持大小写不敏感的查找
        auth_header = request.headers.get('authorization', '')
        
        if not auth_header:
            # 尝试其他可能的名称
            for key in request.headers.keys():
                if key.lower() == 'authorization':
                    auth_header = request.headers[key]
                    break
        
        if not auth_header:
            # 调试：打印所有 header 键（仅用于调试，可以注释掉）
            # header_keys = list(request.headers.keys())
            # print(f"⚠️ 没有找到 Authorization header，可用 headers: {header_keys[:5]}")
            return 'unknown'
        
        # 移除 Bearer 前缀（不区分大小写）
        auth_header_lower = auth_header.lower()
        if auth_header_lower.startswith('bearer '):
            token = auth_header[7:].strip()
        else:
            # 没有 Bearer 前缀，直接使用
            token = auth_header.strip()
        
        if not token:
            return 'unknown'
        
        # 验证 token
        result = verify_token(token)
        if result.get('valid'):
            username = result.get('username')
            if username:
                return username
            else:
                # Token 有效但没有用户名，这不应该发生
                print(f"⚠️ Token 有效但用户名为空")
                return 'unknown'
        else:
            # Token 无效
            error_msg = result.get('error', 'unknown error')
            # 调试信息（可以注释掉）
            # print(f"⚠️ Token 验证失败: {error_msg}")
            return 'unknown'
    except jwt.ExpiredSignatureError:
        # Token 已过期
        return 'unknown'
    except jwt.InvalidTokenError:
        # Token 无效
        return 'unknown'
    except Exception as e:
        # 其他异常，记录但不影响功能
        print(f"⚠️ 获取用户名异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    return 'unknown'
from backend.template_parser import parse_template_variables
from datetime import datetime
import json

router = APIRouter()


# === Pydantic 模型 ===
class LoginRequest(BaseModel):
    username: str
    password: str


class TemplateRequest(BaseModel):
    name: str
    content: str
    project_type: str = "jar"
    original_name: str = None  # 用于更新时的原始名称
    old_project_type: str = None  # 用于项目类型变更


class ParseComposeRequest(BaseModel):
    content: str


class DeleteTemplateRequest(BaseModel):
    name: str
    project_type: str = "jar"


class RegistryModel(BaseModel):
    name: str
    registry: str
    registry_prefix: str = ""
    username: str = ""
    password: str = ""
    active: bool = False


class SaveRegistriesRequest(BaseModel):
    registries: list[RegistryModel]


# === 认证相关 ===
@router.post("/login")
async def login(request: LoginRequest):
    """用户登录"""
    result = authenticate(request.username, request.password)
    if result.get("success"):
        # 记录登录日志
        OperationLogger.log(request.username, "login", {"ip": "unknown"})
        return JSONResponse(result)
    raise HTTPException(status_code=401, detail=result.get("error", "用户名或密码错误"))


@router.post("/logout")
async def logout(request: Request):
    """用户登出"""
    username = get_current_username(request)
    OperationLogger.log(username, "logout", {})
    return JSONResponse({"success": True, "message": "已登出"})


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password")
async def change_password(request: ChangePasswordRequest):
    """修改密码"""
    try:
        from backend.auth import load_users, verify_password, hash_password
        from backend.config import load_config, save_config
        
        users = load_users()
        
        # 获取当前用户（从token中）
        # 这里简化处理，实际应该从token中获取用户名
        # 暂时使用admin作为默认用户
        username = "admin"
        
        if username not in users:
            raise HTTPException(status_code=400, detail="用户不存在")
        
        # 验证旧密码
        if not verify_password(request.old_password, users[username]):
            raise HTTPException(status_code=400, detail="旧密码错误")
        
        # 更新密码
        config = load_config()
        if "users" not in config:
            config["users"] = {}
        config["users"][username] = hash_password(request.new_password)
        save_config(config)
        
        # 记录操作日志
        OperationLogger.log(username, "change_password", {"username": username})
        
        return JSONResponse({"success": True, "message": "密码修改成功"})
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"修改密码失败: {str(e)}")


@router.get("/operation-logs")
async def get_operation_logs(
    limit: int = Query(100, description="返回日志数量"),
    username: Optional[str] = Query(None, description="过滤用户名"),
    operation: Optional[str] = Query(None, description="过滤操作类型"),
):
    """获取操作日志"""
    try:
        logger = OperationLogger()
        logs = logger.get_logs(limit=limit, username=username, operation=operation)
        return JSONResponse({"logs": logs, "total": len(logs)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取操作日志失败: {str(e)}")


@router.delete("/operation-logs")
async def clear_operation_logs(
    request: Request,
    days: Optional[int] = Query(None, description="保留最近 N 天的日志，不传则清空所有"),
):
    """清理操作日志"""
    try:
        username = get_current_username(request)
        logger = OperationLogger()
        removed_count = logger.clear_logs(days=days)
        
        # 记录清理操作
        OperationLogger.log(username, "clear_logs", {
            "removed_count": removed_count,
            "days_kept": days
        })
        
        return JSONResponse({
            "success": True,
            "removed_count": removed_count,
            "message": f"已清理 {removed_count} 条日志" if days else "已清空所有日志"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理操作日志失败: {str(e)}")


# === 配置相关 ===
@router.get("/get-config")
async def get_config():
    """获取配置"""
    try:
        config = load_config()
        docker_config = config.get("docker", {})
        return JSONResponse({"docker": docker_config})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.get("/registries")
async def get_registries():
    """获取所有仓库配置"""
    try:
        registries = get_all_registries()
        return JSONResponse({"registries": registries})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仓库列表失败: {str(e)}")


@router.post("/registries")
async def save_registries(request: SaveRegistriesRequest, http_request: Request):
    """保存仓库配置列表"""
    try:
        username = get_current_username(http_request)
        config = load_config()

        # 转换 Pydantic 模型为字典
        registries_data = [reg.model_dump() for reg in request.registries]

        # 确保至少有一个仓库被激活
        has_active = any(reg.get("active", False) for reg in registries_data)
        if not has_active and registries_data:
            registries_data[0]["active"] = True

        # 更新配置
        if "docker" not in config:
            config["docker"] = {}
        config["docker"]["registries"] = registries_data

        save_config(config)

        # 重新初始化 Docker 构建器
        from backend.handlers import init_docker_builder

        init_docker_builder()

        # 记录操作日志
        OperationLogger.log(username, "save_registries", {
            "registry_count": len(registries_data),
            "registry_names": [r.get("name") for r in registries_data]
        })

        return JSONResponse(
            {"message": "仓库配置保存成功", "registries": registries_data}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"保存仓库配置失败: {str(e)}")


@router.post("/save-config")
async def save_config_route(
    request: Request,
    expose_port: str = Form("8080"),
    default_push: str = Form("false"),
    # 远程 Docker 配置
    use_remote: str = Form("false"),
    remote_host: str = Form(""),
    remote_port: str = Form("2375"),
    remote_use_tls: str = Form("false"),
    remote_cert_path: str = Form(""),
    remote_verify_tls: str = Form("true"),
    # 兼容旧格式（可选参数）
    registry: str = Form(""),
    registry_prefix: str = Form(""),
    username: str = Form(""),
    password: str = Form(""),
):
    """保存 Docker 配置（非仓库配置）"""
    try:
        current_username = get_current_username(request)
        # 转换布尔值
        default_push_bool = default_push.lower() in ("true", "1", "on", "yes")
        use_remote_bool = use_remote.lower() in ("true", "1", "on", "yes")
        remote_use_tls_bool = remote_use_tls.lower() in ("true", "1", "on", "yes")
        remote_verify_tls_bool = remote_verify_tls.lower() in ("true", "1", "on", "yes")

        # 转换端口号
        try:
            expose_port_int = int(expose_port)
        except (ValueError, TypeError):
            expose_port_int = 8080

        try:
            remote_port_int = int(remote_port)
        except (ValueError, TypeError):
            remote_port_int = 2375

        config = load_config()

        # 更新非仓库配置
        if "docker" not in config:
            config["docker"] = {}

        config["docker"]["expose_port"] = expose_port_int
        config["docker"]["default_push"] = default_push_bool
        config["docker"]["use_remote"] = use_remote_bool
        config["docker"]["remote"] = {
            "host": remote_host.strip(),
            "port": remote_port_int,
            "use_tls": remote_use_tls_bool,
            "cert_path": remote_cert_path.strip(),
            "verify_tls": remote_verify_tls_bool,
        }

        save_config(config)

        # 重新初始化 Docker 构建器
        from backend.handlers import init_docker_builder

        init_docker_builder()

        # 记录操作日志
        OperationLogger.log(current_username, "save_config", {
            "expose_port": expose_port_int,
            "default_push": default_push_bool,
            "use_remote": use_remote_bool,
            "remote_host": remote_host.strip() if remote_host else None
        })

        print(f"✅ Docker 配置已更新")
        return JSONResponse(
            {
                "message": "Docker 配置保存成功！",
                "docker": config["docker"],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


# === 构建相关 ===
@router.post("/upload")
async def upload_file(
    request: Request,
    app_file: UploadFile = File(...),
    imagename: str = Form(...),
    tag: str = Form("latest"),
    template: str = Form(...),
    project_type: str = Form("jar"),
    push: str = Form("off"),
    template_params: Optional[str] = Form(None),  # JSON 字符串格式的模板参数
    push_registry: Optional[str] = Form(None),  # 推送时使用的仓库名称
    extract_archive: str = Form("on"),  # 是否解压压缩包（默认解压）
):
    """上传文件并开始构建"""
    try:
        username = get_current_username(request)
        if not app_file or not app_file.filename:
            raise HTTPException(status_code=400, detail="未上传文件")

        # 读取文件内容
        file_data = await app_file.read()

        # 解析模板参数
        params_dict = {}
        if template_params:
            try:
                params_dict = json.loads(template_params)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="模板参数格式错误")

        # 调用构建管理器
        manager = BuildManager()
        build_id = manager.start_build(
            file_data=file_data,
            image_name=imagename,
            tag=tag,
            should_push=(push == "on"),
            selected_template=template,
            original_filename=app_file.filename,
            project_type=project_type,
            template_params=params_dict,  # 传递模板参数
            push_registry=push_registry,  # 传递推送时使用的仓库
            extract_archive=(extract_archive == "on"),  # 传递解压选项
        )

        # 记录操作日志
        OperationLogger.log(username, "build", {
            "build_id": build_id,
            "image": f"{imagename}:{tag}",
            "template": template,
            "project_type": project_type,
            "push": push == "on",
            "filename": app_file.filename
        })

        return JSONResponse(
            {
                "build_id": build_id,
                "message": "构建任务已启动，请通过日志查看进度",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"构建失败: {str(e)}")


@router.get("/get-logs")
async def get_logs(build_id: str = Query(...)):
    """获取构建日志"""
    try:
        manager = BuildManager()
        logs = manager.get_logs(build_id)
        log_text = "".join(logs) if isinstance(logs, list) else str(logs)
        return PlainTextResponse(log_text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


# === 镜像相关 ===
@router.post("/suggest-image-name")
async def suggest_image_name(jar_file: UploadFile = File(...)):
    """根据文件名建议镜像名称"""
    try:
        app_filename = jar_file.filename
        if not app_filename:
            raise HTTPException(status_code=400, detail="未找到文件")

        # 使用激活仓库的 registry_prefix
        active_registry = get_active_registry()
        base_name = active_registry.get("registry_prefix", "")
        suggested_name = generate_image_name(base_name, app_filename)

        return JSONResponse({"suggested_imagename": suggested_name})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成镜像名失败: {str(e)}")


@router.post("/export-image")
async def create_export_task(
    request: Request,
    image: str = Body(..., description="镜像名称"),
    tag: str = Body("latest", description="镜像标签"),
    compress: str = Body("none", description="压缩格式: none, gzip"),
    registry: Optional[str] = Body(None, description="仓库名称（用于获取认证信息）"),
    use_local: bool = Body(False, description="是否使用本地仓库（不执行 pull）"),
):
    """创建导出任务"""
    try:
        username = get_current_username(request)
        if not DOCKER_AVAILABLE:
            raise HTTPException(
                status_code=503, detail="Docker 服务不可用，无法导出镜像"
            )

        image_name = image.strip()
        tag_name = tag.strip()

        if not image_name:
            raise HTTPException(status_code=400, detail="缺少 image 参数")

        # 如果镜像名包含标签，分离出来
        if ":" in image_name and not tag:
            image_name, inferred_tag = image_name.rsplit(":", 1)
            if inferred_tag:
                tag_name = inferred_tag

        # 创建导出任务
        task_manager = ExportTaskManager()
        task_id = task_manager.create_task(
            image=image_name,
            tag=tag_name,
            compress=compress,
            registry=registry,
            use_local=use_local,
        )

        # 记录操作日志
        OperationLogger.log(username, "export", {
            "task_id": task_id,
            "image": f"{image_name}:{tag_name}",
            "compress": compress
        })

        return JSONResponse({
            "task_id": task_id,
            "message": "导出任务已创建，请到任务清单查看进度",
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建导出任务失败: {str(e)}")


@router.get("/export-tasks")
async def list_export_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤: pending, running, completed, failed"),
):
    """获取导出任务列表"""
    try:
        task_manager = ExportTaskManager()
        tasks = task_manager.list_tasks(status=status)
        return JSONResponse({"tasks": tasks})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/export-tasks/{task_id}")
async def get_export_task(task_id: str):
    """获取导出任务详情"""
    try:
        task_manager = ExportTaskManager()
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return JSONResponse({"task": task})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.get("/export-tasks/{task_id}/download")
async def download_export_task(task_id: str):
    """下载导出任务的文件"""
    try:
        task_manager = ExportTaskManager()
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {task['status']}")
        
        file_path = task_manager.get_task_file_path(task_id)
        
        # 确定文件类型
        if file_path.endswith(".gz"):
            content_type = "application/gzip"
        else:
            content_type = "application/x-tar"
        
        # 生成下载文件名
        image = task["image"]
        tag = task["tag"]
        compress = task["compress"]
        filename = f"{image.replace('/', '_')}-{tag}.tar"
        if compress.lower() in ("gzip", "gz", "tgz", "1", "true", "yes"):
            filename += ".gz"
        
        return FileResponse(
            file_path,
            media_type=content_type,
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.delete("/export-tasks/{task_id}")
async def delete_export_task(task_id: str, request: Request):
    """删除导出任务"""
    try:
        username = get_current_username(request)
        task_manager = ExportTaskManager()
        task = task_manager.get_task(task_id)
        success = task_manager.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 记录操作日志
        if task:
            OperationLogger.log(username, "delete_export_task", {
                "task_id": task_id,
                "image": task.get("image"),
                "tag": task.get("tag")
            })
        
        return JSONResponse({"message": "任务已删除"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


# === Compose 相关 ===
@router.post("/parse-compose")
async def parse_compose(request: ParseComposeRequest):
    """解析 Docker Compose 文件"""
    try:
        import yaml

        compose_doc = yaml.safe_load(request.content)

        def split_image_reference(reference: str):
            """分离镜像名和标签"""
            if not reference:
                return "", "latest"
            reference = reference.strip()
            
            # 处理 digest (格式: image@sha256:...)
            if "@" in reference:
                name, digest = reference.split("@", 1)
                return name.strip(), digest.strip()
            
            # 处理 tag (格式: image:tag)
            # 需要找到最后一个冒号，但要排除端口号的情况
            # 例如: registry.com:5000/image:tag
            colon_index = reference.rfind(":")
            if colon_index > 0:
                # 检查冒号前是否有斜杠（说明是 registry:port 格式）
                before_colon = reference[:colon_index]
                if "/" in before_colon:
                    # 有斜杠，说明是 registry:port/image:tag 格式
                    # 找到最后一个斜杠后的冒号
                    last_slash = before_colon.rfind("/")
                    if last_slash >= 0:
                        # 斜杠后的部分
                        after_slash = reference[last_slash + 1:]
                        if ":" in after_slash:
                            # 分离镜像名和标签
                            name = reference[:colon_index]
                            tag = reference[colon_index + 1:].strip()
                            # 如果 tag 为空，使用 latest
                            return name.strip(), tag if tag else "latest"
                
                # 没有斜杠或斜杠在冒号前，直接分离
                name = reference[:colon_index]
                tag = reference[colon_index + 1:].strip()
                # 如果 tag 为空，使用 latest
                return name.strip(), tag if tag else "latest"
            
            # 检查是否以冒号结尾（格式: image:）
            if reference.endswith(":"):
                # 移除末尾的冒号，tag 使用 latest
                return reference[:-1].strip(), "latest"
            
            # 没有冒号，返回原镜像名和 latest
            return reference, "latest"

        # 提取镜像列表
        images = []
        if isinstance(compose_doc, dict):
            services = compose_doc.get("services", {})
            for service_name, service_config in services.items():
                if isinstance(service_config, dict):
                    image_ref = service_config.get("image", "")
                    if image_ref:
                        image_name, tag = split_image_reference(str(image_ref))
                        if image_name:
                            images.append({
                                "service": service_name,
                                "image": image_name,
                                "tag": tag,
                                "raw": image_ref
                            })

        return JSONResponse({"images": images})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析 Compose 文件失败: {str(e)}")


# === 模板相关 ===
@router.get("/list-templates")
async def list_templates():
    """列出所有可用模板"""
    try:
        templates = get_all_templates()
        details = []

        for name, info in templates.items():
            try:
                stat = os.stat(info["path"])
                details.append(
                    {
                        "name": name,
                        "filename": os.path.basename(info["path"]),
                        "size": stat.st_size,
                        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": info["type"],
                        "project_type": info.get("project_type", "jar"),
                        "editable": info["type"] == "user",
                    }
                )
            except OSError:
                continue

        details.sort(key=lambda item: natural_sort_key(item["name"]))
        return JSONResponse(details)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)}")


@router.get("/template-params")
async def get_template_params(
    template: str = Query(..., description="模板名称"),
    project_type: Optional[str] = Query(None, description="项目类型"),
):
    """获取模板的参数列表"""
    try:
        # 获取模板路径
        template_path = get_template_path(template, project_type)
        if not template_path or not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="模板不存在")

        # 读取模板内容
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析参数
        params = parse_template_variables(content)

        return JSONResponse(
            {"template": template, "project_type": project_type, "params": params}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析模板参数失败: {str(e)}")


@router.get("/templates")
async def get_template(name: Optional[str] = Query(None)):
    """获取模板详情或列表"""
    try:
        if name:
            # 获取单个模板内容
            templates = get_all_templates()
            if name not in templates:
                raise HTTPException(status_code=404, detail="模板不存在")

            template_path = templates[name]["path"]
            if not os.path.exists(template_path):
                raise HTTPException(status_code=404, detail="模板文件不存在")

            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()

            return JSONResponse(
                {
                    "name": name,
                    "content": content,
                    "type": templates[name]["type"],
                    "project_type": templates[name].get("project_type", "jar"),
                }
            )
        else:
            # 返回模板列表（前端兼容格式）
            templates = get_all_templates()
            details = []

            for name, info in templates.items():
                try:
                    stat = os.stat(info["path"])
                    details.append(
                        {
                            "name": name,
                            "filename": os.path.basename(info["path"]),
                            "size": stat.st_size,
                            "updated_at": datetime.fromtimestamp(
                                stat.st_mtime
                            ).isoformat(),
                            "type": info["type"],
                            "project_type": info.get("project_type", "jar"),
                            "editable": info["type"] == "user",
                        }
                    )
                except OSError:
                    continue

            details.sort(key=lambda item: natural_sort_key(item["name"]))

            # 返回前端期望的格式
            return JSONResponse(
                {
                    "items": details,
                    "total": len(details),
                    "builtin": sum(1 for d in details if d["type"] == "builtin"),
                    "user": sum(1 for d in details if d["type"] == "user"),
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板失败: {str(e)}")


@router.post("/templates")
async def create_template(request: TemplateRequest, http_request: Request):
    """创建新模板"""
    try:
        username = get_current_username(http_request)
        name = request.name
        content = request.content
        project_type = request.project_type

        print(f"📝 创建模板请求: name={name}, project_type={project_type}")

        # 验证模板名称
        if not name or ".." in name or "/" in name:
            raise HTTPException(status_code=400, detail="非法模板名称")

        # 确定保存路径
        template_dir = os.path.join(USER_TEMPLATES_DIR, project_type)
        print(f"📁 模板目录: {template_dir}")
        os.makedirs(template_dir, exist_ok=True)

        template_path = os.path.join(template_dir, f"{name}.Dockerfile")
        print(f"💾 保存路径: {template_path}")

        if os.path.exists(template_path):
            raise HTTPException(status_code=400, detail="模板已存在")

        # 保存模板
        with open(template_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ 模板已保存: {template_path}")
        print(f"📊 文件大小: {os.path.getsize(template_path)} bytes")

        # 记录操作日志
        OperationLogger.log(username, "template_create", {
            "name": name,
            "project_type": project_type
        })

        return JSONResponse({"message": "模板创建成功", "name": name})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建模板失败: {str(e)}")


@router.put("/templates")
async def update_template(request: TemplateRequest, http_request: Request):
    """更新模板"""
    try:
        username = get_current_username(http_request)
        name = request.name
        content = request.content
        original_name = request.original_name or name  # 支持重命名

        templates = get_all_templates()

        # 如果是重命名，检查原始模板是否存在
        if original_name not in templates:
            raise HTTPException(status_code=404, detail="模板不存在")

        template_info = templates[original_name]

        if template_info["type"] == "builtin":
            raise HTTPException(status_code=403, detail="不能修改内置模板")

        old_path = template_info["path"]

        # 如果项目类型改变或名称改变，需要移动/重命名文件
        if (
            request.old_project_type
            and request.old_project_type != request.project_type
        ):
            # 项目类型改变，需要移动文件
            new_dir = os.path.join(USER_TEMPLATES_DIR, request.project_type)
            os.makedirs(new_dir, exist_ok=True)
            new_path = os.path.join(new_dir, f"{name}.Dockerfile")

            # 保存到新位置
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(content)

            # 删除旧文件
            if os.path.exists(old_path):
                os.remove(old_path)
        elif original_name != name:
            # 仅重命名
            new_path = os.path.join(os.path.dirname(old_path), f"{name}.Dockerfile")
            with open(new_path, "w", encoding="utf-8") as f:
                f.write(content)
            if os.path.exists(old_path) and old_path != new_path:
                os.remove(old_path)
        else:
            # 仅更新内容
            with open(old_path, "w", encoding="utf-8") as f:
                f.write(content)

        # 记录操作日志
        OperationLogger.log(username, "template_update", {
            "name": name,
            "original_name": original_name,
            "project_type": request.project_type
        })

        return JSONResponse({"message": "模板更新成功", "name": name})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新模板失败: {str(e)}")


@router.delete("/templates")
async def delete_template(request: DeleteTemplateRequest, http_request: Request):
    """删除模板"""
    try:
        username = get_current_username(http_request)
        name = request.name
        templates = get_all_templates()

        if name not in templates:
            raise HTTPException(status_code=404, detail="模板不存在")

        template_info = templates[name]

        if template_info["type"] == "builtin":
            raise HTTPException(status_code=403, detail="不能删除内置模板")

        template_path = template_info["path"]

        # 删除文件
        if os.path.exists(template_path):
            os.remove(template_path)

        # 记录操作日志
        OperationLogger.log(username, "template_delete", {
            "name": name,
            "project_type": request.project_type
        })

        return JSONResponse({"message": "模板删除成功", "name": name})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")

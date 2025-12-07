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
    BuildTaskManager,
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
    get_git_config,
    save_git_config,
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


# === Git 配置管理 ===
@router.get("/git-config")
async def get_git_config_route(request: Request):
    """获取 Git 配置"""
    try:
        git_config = get_git_config()
        # 不返回密码和 SSH key 密码（安全考虑）
        safe_config = {
            "username": git_config.get("username", ""),
            "ssh_key_path": git_config.get("ssh_key_path", ""),
        }
        return JSONResponse({"git_config": safe_config})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Git 配置失败: {str(e)}")


@router.post("/git-config")
async def save_git_config_route(
    request: Request,
    username: str = Body(""),
    password: str = Body(""),
    ssh_key_path: str = Body(""),
    ssh_key_password: str = Body(""),
):
    """保存 Git 配置"""
    try:
        username_param = get_current_username(request)
        git_config = {
            "username": username,
            "password": password,
            "ssh_key_path": ssh_key_path,
            "ssh_key_password": ssh_key_password,
        }
        save_git_config(git_config)
        
        # 记录操作日志
        OperationLogger.log(username_param, "save_git_config", {})
        
        return JSONResponse({"success": True, "message": "Git 配置已保存"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存 Git 配置失败: {str(e)}")


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
        task_id = manager.start_build(
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
            "task_id": task_id,
            "image": f"{imagename}:{tag}",
            "template": template,
            "project_type": project_type,
            "push": push == "on",
            "filename": app_file.filename
        })

        return JSONResponse(
            {
                "task_id": task_id,
                "message": "构建任务已启动，请查看任务管理",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"构建失败: {str(e)}")


@router.post("/verify-git-repo")
async def verify_git_repo(
    git_url: str = Body(..., embed=True, description="Git 仓库地址")
):
    """验证 Git 仓库并获取分支和标签列表"""
    import subprocess
    import tempfile
    import shutil
    
    try:
        # 使用 git ls-remote 命令获取远程仓库的分支和标签
        # 这个命令不需要克隆整个仓库，只获取引用信息
        cmd = ["git", "ls-remote", "--heads", "--tags", git_url]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30秒超时
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if "Authentication failed" in error_msg or "Permission denied" in error_msg:
                raise HTTPException(
                    status_code=401,
                    detail="仓库访问被拒绝，请检查 URL 是否正确或配置 SSH 密钥"
                )
            elif "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=404,
                    detail="仓库不存在，请检查 URL 是否正确"
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"无法访问仓库: {error_msg}"
                )
        
        # 解析输出
        branches = []
        tags = []
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) != 2:
                continue
            
            ref = parts[1]
            
            if ref.startswith('refs/heads/'):
                branch_name = ref.replace('refs/heads/', '')
                branches.append(branch_name)
            elif ref.startswith('refs/tags/'):
                tag_name = ref.replace('refs/tags/', '')
                # 跳过带 ^{} 的标签（指向标签对象的注解）
                if not tag_name.endswith('^{}'):
                    tags.append(tag_name)
        
        return JSONResponse({
            "success": True,
            "branches": sorted(branches, key=lambda x: (x != 'main', x != 'master', x)),
            "tags": sorted(tags, reverse=True),  # 标签按降序排列，最新的在前
            "default_branch": next((b for b in branches if b in ['main', 'master']), branches[0] if branches else None)
        })
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail="仓库访问超时，请检查网络连接或仓库地址"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"验证仓库失败: {str(e)}"
        )


@router.post("/build-from-source")
async def build_from_source(
    request: Request,
    project_type: str = Body(...),
    template: str = Body(...),
    git_url: str = Body(...),
    imagename: str = Body(...),
    tag: str = Body("latest"),
    push: str = Body("off"),
    template_params: Optional[str] = Body(None),
    push_registry: Optional[str] = Body(None),
    branch: Optional[str] = Body(None),
    sub_path: Optional[str] = Body(None),
    use_project_dockerfile: bool = Body(True, description="是否优先使用项目中的 Dockerfile"),
):
    """从 Git 源码构建镜像"""
    try:
        username = get_current_username(request)
        
        # 解析模板参数
        params_dict = {}
        if template_params:
            try:
                params_dict = json.loads(template_params)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="模板参数格式错误")

        # 调用构建管理器
        try:
            print(f"📝 开始创建构建任务: git_url={git_url}, image={imagename}:{tag}")
            try:
                manager = BuildManager()
                print(f"✅ BuildManager 初始化成功")
            except Exception as init_error:
                import traceback
                error_trace = traceback.format_exc()
                print(f"❌ BuildManager 初始化失败: {init_error}")
                print(f"错误堆栈:\n{error_trace}")
                raise HTTPException(
                    status_code=500,
                    detail=f"构建管理器初始化失败: {str(init_error)}"
                )
            
            try:
                task_id = manager.start_build_from_source(
                    git_url=git_url,
                    image_name=imagename,
                    tag=tag,
                    should_push=(push == "on"),
                    selected_template=template,
                    project_type=project_type,
                    template_params=params_dict,
                    push_registry=push_registry,
                    branch=branch,
                    sub_path=sub_path,
                    use_project_dockerfile=use_project_dockerfile,
                )
                if not task_id:
                    raise RuntimeError("任务创建失败：未返回 task_id")
                print(f"✅ 任务创建成功: task_id={task_id}")
            except Exception as create_error:
                import traceback
                error_trace = traceback.format_exc()
                print(f"❌ 创建构建任务失败: {create_error}")
                print(f"错误堆栈:\n{error_trace}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"创建构建任务失败: {str(create_error)}"
                )
        except HTTPException:
            raise
        except Exception as create_error:
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ 创建构建任务异常: {create_error}")
            print(f"错误堆栈:\n{error_trace}")
            raise HTTPException(
                status_code=500, 
                detail=f"创建构建任务失败: {str(create_error)}"
            )

        # 记录操作日志
        try:
            OperationLogger.log(username, "build_from_source", {
                "task_id": task_id,
                "image": f"{imagename}:{tag}",
                "template": template,
                "project_type": project_type,
                "git_url": git_url,
                "branch": branch,
                "push": push == "on",
            })
        except Exception as log_error:
            print(f"⚠️ 记录操作日志失败: {log_error}")

        return JSONResponse({
            "task_id": task_id,
            "message": "构建任务已启动，请查看任务管理",
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ 构建请求处理失败: {e}")
        print(f"错误堆栈:\n{error_trace}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"构建失败: {str(e)}")


@router.get("/build-tasks")
async def get_build_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤"),
):
    """获取构建任务列表"""
    try:
        manager = BuildTaskManager()
        tasks = manager.list_tasks(status=status, task_type=task_type)
        return JSONResponse({"tasks": tasks})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取构建任务列表失败: {str(e)}")


@router.get("/tasks")
async def get_all_tasks(
    status: Optional[str] = Query(None, description="任务状态过滤"),
    task_type: Optional[str] = Query(None, description="任务类型过滤: build, build_from_source, export"),
):
    """获取所有任务（构建任务 + 导出任务）"""
    try:
        all_tasks = []
        
        # 获取构建任务
        build_manager = BuildTaskManager()
        build_tasks = build_manager.list_tasks(status=status, task_type=task_type)
        for task in build_tasks:
            task["task_category"] = "build"  # 标记为构建任务
            all_tasks.append(task)
        
        # 获取导出任务
        export_manager = ExportTaskManager()
        export_tasks = export_manager.list_tasks(status=status)
        for task in export_tasks:
            task["task_category"] = "export"  # 标记为导出任务
            all_tasks.append(task)
        
        # 按创建时间倒序排列
        all_tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return JSONResponse({"tasks": all_tasks})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.get("/build-tasks/{task_id}")
async def get_build_task(task_id: str):
    """获取构建任务详情"""
    try:
        manager = BuildTaskManager()
        task = manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return JSONResponse(task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.get("/build-tasks/{task_id}/logs")
async def get_build_task_logs(task_id: str):
    """获取构建任务日志"""
    try:
        manager = BuildTaskManager()
        logs = manager.get_logs(task_id)
        return PlainTextResponse(logs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务日志失败: {str(e)}")


@router.delete("/build-tasks/{task_id}")
async def delete_build_task(task_id: str, request: Request):
    """删除构建任务"""
    try:
        username = get_current_username(request)
        manager = BuildTaskManager()
        if manager.delete_task(task_id):
            OperationLogger.log(username, "delete_build_task", {"task_id": task_id})
            return JSONResponse({"success": True, "message": "任务已删除"})
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.post("/tasks/cleanup")
async def cleanup_tasks(
    request: Request,
    status: Optional[str] = Body(None, description="清理指定状态的任务：completed, failed"),
    days: Optional[int] = Body(None, description="清理N天前的任务"),
    task_type: Optional[str] = Body(None, description="任务类型：build, export"),
):
    """批量清理任务"""
    try:
        username = get_current_username(request)
        removed_count = 0
        
        # 清理构建任务
        if not task_type or task_type == "build":
            build_manager = BuildTaskManager()
            if days:
                # 清理指定天数前的任务
                from datetime import timedelta
                cutoff_time = datetime.now() - timedelta(days=days)
                cutoff_iso = cutoff_time.isoformat()
                
                with build_manager.lock:
                    tasks_to_remove = [
                        task_id for task_id, task in build_manager.tasks.items()
                        if task.get("created_at", "") < cutoff_iso
                        and (not status or task.get("status") == status)
                    ]
                    for task_id in tasks_to_remove:
                        build_manager.delete_task(task_id)
                        removed_count += 1
            elif status:
                # 清理指定状态的任务
                with build_manager.lock:
                    tasks_to_remove = [
                        task_id for task_id, task in build_manager.tasks.items()
                        if task.get("status") == status
                    ]
                    for task_id in tasks_to_remove:
                        build_manager.delete_task(task_id)
                        removed_count += 1
        
        # 清理导出任务
        if not task_type or task_type == "export":
            export_manager = ExportTaskManager()
            if days:
                # 清理指定天数前的任务
                from datetime import timedelta
                cutoff_time = datetime.now() - timedelta(days=days)
                
                with export_manager.lock:
                    tasks_to_remove = [
                        task_id for task_id, task in export_manager.tasks.items()
                        if datetime.fromisoformat(task.get("created_at", "")) < cutoff_time
                        and (not status or task.get("status") == status)
                    ]
                    for task_id in tasks_to_remove:
                        export_manager.delete_task(task_id)
                        removed_count += 1
            elif status:
                with export_manager.lock:
                    tasks_to_remove = [
                        task_id for task_id, task in export_manager.tasks.items()
                        if task.get("status") == status
                    ]
                    for task_id in tasks_to_remove:
                        export_manager.delete_task(task_id)
                        removed_count += 1
        
        # 记录操作日志
        OperationLogger.log(username, "cleanup_tasks", {
            "removed_count": removed_count,
            "status": status,
            "days": days,
            "task_type": task_type
        })
        
        return JSONResponse({
            "success": True,
            "removed_count": removed_count,
            "message": f"已清理 {removed_count} 个任务"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"清理任务失败: {str(e)}")


@router.get("/get-logs")
async def get_logs(build_id: str = Query(...)):
    """获取构建日志（兼容旧接口）"""
    try:
        # 尝试作为 task_id 获取
        task_manager = BuildTaskManager()
        logs = task_manager.get_logs(build_id)
        if logs:
            return PlainTextResponse(logs)
        # 回退到旧的日志系统
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


# === Docker 管理相关 ===
@router.get("/docker/info")
async def get_docker_info():
    """获取 Docker 服务信息"""
    try:
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        info = {
            "connected": DOCKER_AVAILABLE,
            "builder_type": "unknown",
            "version": None,
            "api_version": None,
            "remote_host": None,
            "images_count": 0,
            "images_size": 0,
            "containers_total": 0,
            "containers_running": 0,
            "containers_size": 0,
            "storage_driver": None,
            "os_type": None,
            "arch": None,
            "kernel_version": None,
            "docker_root": None,
            "ncpu": None,
            "mem_total": None,
            "runtime": None,
            "volumes_count": 0,
            "networks_count": 0
        }
        
        if not DOCKER_AVAILABLE or not docker_builder:
            return JSONResponse(info)
        
        # 获取构建器类型
        connection_info = docker_builder.get_connection_info()
        if "本地" in connection_info:
            info["builder_type"] = "local"
        elif "远程" in connection_info:
            info["builder_type"] = "remote"
            import re
            match = re.search(r'\((.+?)\)', connection_info)
            if match:
                info["remote_host"] = match.group(1)
        elif "模拟" in connection_info:
            info["builder_type"] = "mock"
        
        # 获取 Docker 详细信息
        try:
            if hasattr(docker_builder, 'client') and docker_builder.client:
                # 获取版本信息
                version_info = docker_builder.client.version()
                info["version"] = version_info.get('Version', 'Unknown')
                info["api_version"] = version_info.get('ApiVersion', 'Unknown')
                info["os_type"] = version_info.get('Os', 'Unknown')
                info["arch"] = version_info.get('Arch', 'Unknown')
                info["kernel_version"] = version_info.get('KernelVersion', '')
                
                # 获取系统信息
                system_info = docker_builder.client.info()
                info["images_count"] = system_info.get('Images', 0)
                info["containers_total"] = system_info.get('Containers', 0)
                info["containers_running"] = system_info.get('ContainersRunning', 0)
                info["storage_driver"] = system_info.get('Driver', 'Unknown')
                info["docker_root"] = system_info.get('DockerRootDir', '')
                info["ncpu"] = system_info.get('NCPU', 0)
                info["mem_total"] = system_info.get('MemTotal', 0)
                info["runtime"] = system_info.get('DefaultRuntime', 'runc')
                
                # 获取卷和网络数量
                try:
                    info["volumes_count"] = len(docker_builder.client.volumes.list())
                    info["networks_count"] = len(docker_builder.client.networks.list())
                except:
                    pass
                
                # 获取磁盘使用信息
                try:
                    df_info = docker_builder.client.df()
                    if 'Images' in df_info:
                        info["images_size"] = sum(img.get('Size', 0) for img in df_info['Images'])
                    if 'Containers' in df_info:
                        info["containers_size"] = sum(c.get('SizeRw', 0) or 0 for c in df_info['Containers'])
                except:
                    pass
        except Exception as e:
            print(f"⚠️ 获取 Docker 详细信息失败: {e}")
        
        return JSONResponse(info)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取 Docker 信息失败: {str(e)}")


@router.get("/docker/images")
async def get_docker_images(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=1000)):
    """获取 Docker 镜像列表（支持分页）"""
    try:
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            return JSONResponse({"images": [], "total": 0})
        
        if not hasattr(docker_builder, 'client') or not docker_builder.client:
            return JSONResponse({"images": [], "total": 0})
        
        # 获取镜像列表
        images_data = []
        try:
            images = docker_builder.client.images.list()
            for img in images:
                tags = img.tags
                if not tags:
                    images_data.append({
                        "id": img.id,
                        "repository": "<none>",
                        "tag": "<none>",
                        "size": img.attrs.get('Size', 0),
                        "created": img.attrs.get('Created', '')
                    })
                else:
                    for tag in tags:
                        if ':' in tag:
                            repo, tag_name = tag.rsplit(':', 1)
                        else:
                            repo, tag_name = tag, 'latest'
                        images_data.append({
                            "id": img.id,
                            "repository": repo,
                            "tag": tag_name,
                            "size": img.attrs.get('Size', 0),
                            "created": img.attrs.get('Created', '')
                        })
        except Exception as e:
            print(f"⚠️ 获取镜像列表失败: {e}")
        
        total = len(images_data)
        start = (page - 1) * page_size
        end = start + page_size
        return JSONResponse({"images": images_data[start:end], "total": total})
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取镜像列表失败: {str(e)}")


class DeleteImageRequest(BaseModel):
    image_id: str


@router.delete("/docker/images")
async def delete_docker_image(request: DeleteImageRequest, http_request: Request):
    """删除 Docker 镜像"""
    try:
        username = get_current_username(http_request)
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            raise HTTPException(status_code=503, detail="Docker 服务不可用")
        
        if not hasattr(docker_builder, 'client') or not docker_builder.client:
            raise HTTPException(status_code=503, detail="Docker 客户端不可用")
        
        try:
            docker_builder.client.images.remove(request.image_id, force=True)
            OperationLogger.log(username, "docker_image_delete", {"image_id": request.image_id})
            return JSONResponse({"message": "镜像已删除"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除镜像失败: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除镜像失败: {str(e)}")


@router.post("/docker/images/prune")
async def prune_docker_images(http_request: Request):
    """清理未使用的镜像"""
    try:
        username = get_current_username(http_request)
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            raise HTTPException(status_code=503, detail="Docker 服务不可用")
        
        result = docker_builder.client.images.prune()
        space_reclaimed = result.get('SpaceReclaimed', 0)
        OperationLogger.log(username, "docker_images_prune", {"space_reclaimed": space_reclaimed})
        return JSONResponse({"space_reclaimed": space_reclaimed})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理镜像失败: {str(e)}")


# === 容器管理 ===
@router.get("/docker/containers")
async def get_docker_containers(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=1000)):
    """获取容器列表（支持分页）"""
    try:
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            return JSONResponse({"containers": [], "total": 0})
        
        if not hasattr(docker_builder, 'client') or not docker_builder.client:
            return JSONResponse({"containers": [], "total": 0})
        
        containers_data = []
        try:
            containers = docker_builder.client.containers.list(all=True)
            for c in containers:
                # 解析端口映射
                ports_str = ''
                try:
                    ports = c.attrs.get('NetworkSettings', {}).get('Ports', {}) or {}
                    port_list = []
                    for container_port, host_bindings in ports.items():
                        if host_bindings:
                            for binding in host_bindings:
                                host_port = binding.get('HostPort', '')
                                if host_port:
                                    port_list.append(f"{host_port}->{container_port}")
                        else:
                            port_list.append(container_port)
                    ports_str = ', '.join(port_list[:3])  # 最多显示3个
                    if len(port_list) > 3:
                        ports_str += f" (+{len(port_list)-3})"
                except:
                    pass
                
                containers_data.append({
                    "id": c.id,
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                    "status": c.status,
                    "state": c.attrs.get('State', {}).get('Status', 'unknown'),
                    "created": c.attrs.get('Created', ''),
                    "ports": ports_str
                })
        except Exception as e:
            print(f"⚠️ 获取容器列表失败: {e}")
        
        total = len(containers_data)
        start = (page - 1) * page_size
        end = start + page_size
        return JSONResponse({"containers": containers_data[start:end], "total": total})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取容器列表失败: {str(e)}")


@router.post("/docker/containers/{container_id}/start")
async def start_container(container_id: str, http_request: Request):
    """启动容器"""
    try:
        username = get_current_username(http_request)
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            raise HTTPException(status_code=503, detail="Docker 服务不可用")
        
        container = docker_builder.client.containers.get(container_id)
        container.start()
        OperationLogger.log(username, "docker_container_start", {"container_id": container_id})
        return JSONResponse({"message": "容器已启动"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动容器失败: {str(e)}")


@router.post("/docker/containers/{container_id}/stop")
async def stop_container(container_id: str, http_request: Request, force: bool = Query(False)):
    """停止容器，支持强制停止"""
    try:
        username = get_current_username(http_request)
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            raise HTTPException(status_code=503, detail="Docker 服务不可用")
        
        container = docker_builder.client.containers.get(container_id)
        if force:
            container.kill()  # 强制停止
        else:
            container.stop()  # 正常停止
        OperationLogger.log(username, "docker_container_stop", {"container_id": container_id, "force": force})
        return JSONResponse({"message": "容器已停止" if not force else "容器已强制停止"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止容器失败: {str(e)}")


@router.post("/docker/containers/{container_id}/restart")
async def restart_container(container_id: str, http_request: Request):
    """重启容器"""
    try:
        username = get_current_username(http_request)
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            raise HTTPException(status_code=503, detail="Docker 服务不可用")
        
        container = docker_builder.client.containers.get(container_id)
        container.restart()
        OperationLogger.log(username, "docker_container_restart", {"container_id": container_id})
        return JSONResponse({"message": "容器已重启"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重启容器失败: {str(e)}")


@router.delete("/docker/containers/{container_id}")
async def remove_container(container_id: str, http_request: Request):
    """删除容器"""
    try:
        username = get_current_username(http_request)
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            raise HTTPException(status_code=503, detail="Docker 服务不可用")
        
        container = docker_builder.client.containers.get(container_id)
        container.remove(force=True)
        OperationLogger.log(username, "docker_container_remove", {"container_id": container_id})
        return JSONResponse({"message": "容器已删除"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除容器失败: {str(e)}")


@router.post("/docker/containers/prune")
async def prune_containers(http_request: Request):
    """清理已停止的容器"""
    try:
        username = get_current_username(http_request)
        from backend.handlers import docker_builder, DOCKER_AVAILABLE
        
        if not DOCKER_AVAILABLE or not docker_builder:
            raise HTTPException(status_code=503, detail="Docker 服务不可用")
        
        result = docker_builder.client.containers.prune()
        deleted = len(result.get('ContainersDeleted', []) or [])
        OperationLogger.log(username, "docker_containers_prune", {"deleted": deleted})
        return JSONResponse({"deleted": deleted})  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理容器失败: {str(e)}")


# === 流水线管理 ===
from backend.pipeline_manager import PipelineManager


class CreatePipelineRequest(BaseModel):
    name: str
    git_url: str
    branch: Optional[str] = None
    project_type: str = "jar"
    template: Optional[str] = None
    image_name: Optional[str] = None
    tag: str = "latest"
    push: bool = False
    push_registry: Optional[str] = None
    template_params: Optional[dict] = None
    sub_path: Optional[str] = None
    use_project_dockerfile: bool = True
    webhook_secret: Optional[str] = None
    enabled: bool = True
    description: str = ""
    cron_expression: Optional[str] = None


class UpdatePipelineRequest(BaseModel):
    name: Optional[str] = None
    git_url: Optional[str] = None
    branch: Optional[str] = None
    project_type: Optional[str] = None
    template: Optional[str] = None
    image_name: Optional[str] = None
    tag: Optional[str] = None
    push: Optional[bool] = None
    push_registry: Optional[str] = None
    template_params: Optional[dict] = None
    sub_path: Optional[str] = None
    use_project_dockerfile: Optional[bool] = None
    webhook_secret: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None


@router.post("/pipelines")
async def create_pipeline(request: CreatePipelineRequest, http_request: Request):
    """创建流水线配置"""
    try:
        username = get_current_username(http_request)
        manager = PipelineManager()
        
        pipeline_id = manager.create_pipeline(
            name=request.name,
            git_url=request.git_url,
            branch=request.branch,
            project_type=request.project_type,
            template=request.template,
            image_name=request.image_name,
            tag=request.tag,
            push=request.push,
            push_registry=request.push_registry,
            template_params=request.template_params,
            sub_path=request.sub_path,
            use_project_dockerfile=request.use_project_dockerfile,
            webhook_secret=request.webhook_secret,
            enabled=request.enabled,
            description=request.description,
            cron_expression=request.cron_expression,
        )
        
        # 记录操作日志
        OperationLogger.log(username, "pipeline_create", {
            "pipeline_id": pipeline_id,
            "name": request.name,
            "git_url": request.git_url
        })
        
        return JSONResponse({
            "pipeline_id": pipeline_id,
            "message": "流水线创建成功"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建流水线失败: {str(e)}")


@router.get("/pipelines")
async def list_pipelines(enabled: Optional[bool] = Query(None, description="过滤启用状态")):
    """获取流水线列表"""
    try:
        manager = PipelineManager()
        pipelines = manager.list_pipelines(enabled=enabled)
        return JSONResponse({"pipelines": pipelines, "total": len(pipelines)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取流水线列表失败: {str(e)}")


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """获取流水线详情"""
    try:
        manager = PipelineManager()
        pipeline = manager.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="流水线不存在")
        return JSONResponse(pipeline)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取流水线详情失败: {str(e)}")


@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    request: UpdatePipelineRequest,
    http_request: Request
):
    """更新流水线配置"""
    try:
        username = get_current_username(http_request)
        manager = PipelineManager()
        
        success = manager.update_pipeline(
            pipeline_id=pipeline_id,
            name=request.name,
            git_url=request.git_url,
            branch=request.branch,
            project_type=request.project_type,
            template=request.template,
            image_name=request.image_name,
            tag=request.tag,
            push=request.push,
            push_registry=request.push_registry,
            template_params=request.template_params,
            sub_path=request.sub_path,
            use_project_dockerfile=request.use_project_dockerfile,
            webhook_secret=request.webhook_secret,
            enabled=request.enabled,
            description=request.description,
            cron_expression=request.cron_expression,
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="流水线不存在")
        
        # 记录操作日志
        OperationLogger.log(username, "pipeline_update", {
            "pipeline_id": pipeline_id
        })
        
        return JSONResponse({"message": "流水线更新成功"})
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新流水线失败: {str(e)}")


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, http_request: Request):
    """删除流水线配置"""
    try:
        username = get_current_username(http_request)
        manager = PipelineManager()
        
        success = manager.delete_pipeline(pipeline_id)
        if not success:
            raise HTTPException(status_code=404, detail="流水线不存在")
        
        # 记录操作日志
        OperationLogger.log(username, "pipeline_delete", {
            "pipeline_id": pipeline_id
        })
        
        return JSONResponse({"message": "流水线已删除"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除流水线失败: {str(e)}")


@router.post("/pipelines/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, http_request: Request):
    """手动触发流水线执行"""
    try:
        username = get_current_username(http_request)
        manager = PipelineManager()
        
        # 获取流水线配置
        pipeline = manager.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="流水线不存在")
        
        # 启动构建任务
        build_manager = BuildManager()
        task_id = build_manager.start_build_from_source(
            git_url=pipeline["git_url"],
            image_name=pipeline.get("image_name") or "manual-build",
            tag=pipeline.get("tag", "latest"),
            should_push=pipeline.get("push", False),
            selected_template=pipeline.get("template", ""),
            project_type=pipeline.get("project_type", "jar"),
            template_params=pipeline.get("template_params", {}),
            push_registry=pipeline.get("push_registry"),
            branch=pipeline.get("branch"),
            sub_path=pipeline.get("sub_path"),
            use_project_dockerfile=pipeline.get("use_project_dockerfile", True),
        )
        
        # 记录触发
        manager.record_trigger(pipeline_id)
        
        # 记录操作日志
        OperationLogger.log(username, "pipeline_run", {
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline.get("name"),
            "task_id": task_id,
            "branch": pipeline.get("branch"),
        })
        
        return JSONResponse({
            "message": "构建任务已启动",
            "task_id": task_id,
            "pipeline": pipeline.get("name"),
            "branch": pipeline.get("branch"),
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"执行流水线失败: {str(e)}")


# === Webhook 触发 ===
@router.post("/webhook/{webhook_token}")
async def webhook_trigger(webhook_token: str, request: Request):
    """Webhook 触发端点（支持 GitHub/GitLab/Gitee）"""
    try:
        # 获取请求体（原始字节）
        body = await request.body()
        
        # 获取流水线配置
        manager = PipelineManager()
        pipeline = manager.get_pipeline_by_token(webhook_token)
        
        if not pipeline:
            raise HTTPException(status_code=404, detail="流水线不存在")
        
        if not pipeline.get("enabled", False):
            raise HTTPException(status_code=403, detail="流水线已禁用")
        
        # 验证 Webhook 签名（可选）
        webhook_secret = pipeline.get("webhook_secret")
        if webhook_secret:
            # 支持不同平台的签名验证
            signature = None
            signature_header = "sha256"
            
            # GitHub: X-Hub-Signature-256 或 X-Hub-Signature
            if "x-hub-signature-256" in request.headers:
                signature = request.headers["x-hub-signature-256"]
                signature_header = "sha256"
            elif "x-hub-signature" in request.headers:
                signature = request.headers["x-hub-signature"]
                signature_header = "sha1"
            # GitLab: X-Gitlab-Token
            elif "x-gitlab-token" in request.headers:
                gitlab_token = request.headers["x-gitlab-token"]
                if gitlab_token != webhook_secret:
                    raise HTTPException(status_code=403, detail="Webhook 签名验证失败")
            # Gitee: X-Gitee-Token
            elif "x-gitee-token" in request.headers:
                gitee_token = request.headers["x-gitee-token"]
                if gitee_token != webhook_secret:
                    raise HTTPException(status_code=403, detail="Webhook 签名验证失败")
            
            # 验证签名（GitHub）
            if signature:
                if not manager.verify_webhook_signature(body, signature, webhook_secret, signature_header):
                    raise HTTPException(status_code=403, detail="Webhook 签名验证失败")
        
        # 解析 Webhook 负载（尝试解析 JSON）
        try:
            payload = json.loads(body.decode('utf-8'))
        except:
            payload = {}
        
        # 提取分支信息（不同平台格式不同）
        branch = None
        # GitHub: ref = refs/heads/main
        if "ref" in payload:
            ref = payload["ref"]
            if ref.startswith("refs/heads/"):
                branch = ref.replace("refs/heads/", "")
        # GitLab: ref = main
        elif "ref" in payload:
            branch = payload["ref"]
        # Gitee: ref = refs/heads/main
        
        # 如果没有提取到分支，使用流水线配置的分支
        if not branch:
            branch = pipeline.get("branch")
        
        print(f"🔔 Webhook 触发: pipeline={pipeline.get('name')}, branch={branch}")
        
        # 启动构建任务
        build_manager = BuildManager()
        task_id = build_manager.start_build_from_source(
            git_url=pipeline["git_url"],
            image_name=pipeline.get("image_name") or "webhook-build",
            tag=pipeline.get("tag", "latest"),
            should_push=pipeline.get("push", False),
            selected_template=pipeline.get("template", ""),
            project_type=pipeline.get("project_type", "jar"),
            template_params=pipeline.get("template_params", {}),
            push_registry=pipeline.get("push_registry"),
            branch=branch,
            sub_path=pipeline.get("sub_path"),
            use_project_dockerfile=pipeline.get("use_project_dockerfile", True),
        )
        
        # 记录触发
        manager.record_trigger(pipeline["pipeline_id"])
        
        # 记录操作日志
        OperationLogger.log("webhook", "pipeline_trigger", {
            "pipeline_id": pipeline["pipeline_id"],
            "pipeline_name": pipeline.get("name"),
            "task_id": task_id,
            "branch": branch,
        })
        
        return JSONResponse({
            "message": "构建任务已启动",
            "task_id": task_id,
            "pipeline": pipeline.get("name"),
            "branch": branch,
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Webhook 处理失败: {str(e)}")

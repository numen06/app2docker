# backend/routes.py
"""FastAPI 路由定义"""
import os
import shutil
import tempfile
from typing import Optional, List
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
    WebSocket,
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
    BUILD_DIR,
    natural_sort_key,
    docker_builder,
    DOCKER_AVAILABLE,
    parse_dockerfile_services,
    validate_and_clean_image_name,
)
from backend.resource_package_manager import ResourcePackageManager
from backend.host_manager import HostManager
from backend.agent_host_manager import AgentHostManager
from backend.websocket_handler import handle_agent_websocket
from backend.deploy_task_manager import DeployTaskManager
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
        auth_header = request.headers.get("authorization", "")

        if not auth_header:
            # 尝试其他可能的名称
            for key in request.headers.keys():
                if key.lower() == "authorization":
                    auth_header = request.headers[key]
                    break

        if not auth_header:
            # 调试：打印所有 header 键（仅用于调试，可以注释掉）
            # header_keys = list(request.headers.keys())
            # print(f"⚠️ 没有找到 Authorization header，可用 headers: {header_keys[:5]}")
            return "unknown"

        # 移除 Bearer 前缀（不区分大小写）
        auth_header_lower = auth_header.lower()
        if auth_header_lower.startswith("bearer "):
            token = auth_header[7:].strip()
        else:
            # 没有 Bearer 前缀，直接使用
            token = auth_header.strip()

        if not token:
            return "unknown"

        # 验证 token
        result = verify_token(token)
        if result.get("valid"):
            username = result.get("username")
            if username:
                return username
            else:
                # Token 有效但没有用户名，这不应该发生
                print(f"⚠️ Token 有效但用户名为空")
                return "unknown"
        else:
            # Token 无效
            error_msg = result.get("error", "unknown error")
            # 调试信息：打印 token 验证失败的原因
            print(
                f"⚠️ Token 验证失败: {error_msg}, token 前10个字符: {token[:10] if len(token) > 10 else token}"
            )
            return "unknown"
    except jwt.ExpiredSignatureError:
        # Token 已过期
        return "unknown"
    except jwt.InvalidTokenError:
        # Token 无效
        return "unknown"
    except Exception as e:
        # 其他异常，记录但不影响功能
        print(f"⚠️ 获取用户名异常: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    return "unknown"


from backend.template_parser import parse_template_variables
from backend.handlers import parse_dockerfile_services
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
    days: Optional[int] = Query(
        None, description="保留最近 N 天的日志，不传则清空所有"
    ),
):
    """清理操作日志"""
    try:
        username = get_current_username(request)
        logger = OperationLogger()
        removed_count = logger.clear_logs(days=days)

        # 记录清理操作
        OperationLogger.log(
            username, "clear_logs", {"removed_count": removed_count, "days_kept": days}
        )

        return JSONResponse(
            {
                "success": True,
                "removed_count": removed_count,
                "message": (
                    f"已清理 {removed_count} 条日志" if days else "已清空所有日志"
                ),
            }
        )
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
        if username == "unknown":
            # 检查是否有 Authorization header
            auth_header = http_request.headers.get("authorization", "")
            if not auth_header:
                # 没有 token，返回 401（这是真正的认证错误）
                raise HTTPException(status_code=401, detail="未授权，请重新登录")
            else:
                # 有 token 但验证失败（可能是过期），返回 400 避免前端退出登录
                raise HTTPException(
                    status_code=400, detail="Token 已过期或无效，请刷新页面后重试"
                )

        config = load_config()

        # 备份原始配置，以防保存失败
        import copy

        config_backup = copy.deepcopy(config)

        # 转换 Pydantic 模型为字典
        registries_data = [reg.model_dump() for reg in request.registries]

        # 确保至少有一个仓库被激活
        has_active = any(reg.get("active", False) for reg in registries_data)
        if not has_active and registries_data:
            registries_data[0]["active"] = True

        # 更新配置（只更新 docker.registries，不影响其他配置如 server、git、users 等）
        if "docker" not in config:
            config["docker"] = {}

        # 确保保留 docker 配置中的其他字段（如 use_remote、remote 等）
        docker_config = config.get("docker", {})
        docker_config["registries"] = registries_data
        config["docker"] = docker_config

        # 保存配置（使用临时文件确保原子性）
        try:
            save_config(config)
        except Exception as save_error:
            # 如果保存失败，尝试恢复备份
            try:
                import yaml
                import os

                CONFIG_FILE = "data/config.yml"
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    yaml.dump(
                        config_backup,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
            except:
                pass
            raise HTTPException(
                status_code=500, detail=f"保存仓库配置失败: {str(save_error)}"
            )

        # 验证配置是否保存成功且认证配置未被影响
        try:
            verify_config = load_config()
            # 检查 server 配置是否还在
            if "server" not in verify_config:
                # 如果 server 配置丢失，恢复备份
                print("⚠️ 检测到 server 配置丢失，正在恢复...")
                import yaml
                import os

                CONFIG_FILE = "data/config.yml"
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    yaml.dump(
                        config_backup,
                        f,
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
                # 重新保存，但这次只更新 registries
                verify_config = load_config()
                verify_config["docker"]["registries"] = registries_data
                save_config(verify_config)
        except Exception as verify_error:
            print(f"⚠️ 验证配置失败: {verify_error}")
            # 不抛出异常，因为主要操作已成功

        # 重新初始化 Docker 构建器
        try:
            from backend.handlers import init_docker_builder

            init_docker_builder()
        except Exception as init_error:
            print(f"⚠️ 重新初始化 Docker 构建器失败: {init_error}")
            # 不抛出异常，因为配置已保存成功

        # 记录操作日志
        try:
            OperationLogger.log(
                username,
                "save_registries",
                {
                    "registry_count": len(registries_data),
                    "registry_names": [r.get("name") for r in registries_data],
                },
            )
        except Exception as log_error:
            print(f"⚠️ 记录操作日志失败: {log_error}")
            # 不抛出异常，因为主要操作已成功

        return JSONResponse(
            {"message": "仓库配置保存成功", "registries": registries_data}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"保存仓库配置失败: {str(e)}")


class TestRegistryRequest(BaseModel):
    """测试Registry登录请求"""

    name: str
    registry: str
    username: str
    password: str


@router.post("/registries/test")
async def test_registry_login(request: TestRegistryRequest, http_request: Request):
    """测试Registry登录（测试仓库的用户名和密码是否正确）

    注意：
    - 需要系统 token 认证才能使用此功能（安全考虑）
    - 但测试的是仓库的登录信息（request.username 和 request.password），与系统用户无关
    - 如果系统 token 无效，返回 400 而不是 401，避免前端退出登录
    """
    try:
        # 验证系统 token（需要系统认证才能使用此功能）
        username = get_current_username(http_request)
        if username == "unknown":
            # 检查是否有 Authorization header
            auth_header = http_request.headers.get("authorization", "")
            if not auth_header:
                # 没有 token，返回 401（这是真正的系统认证错误）
                print(f"⚠️ 测试仓库接口：没有 Authorization header")
                raise HTTPException(status_code=401, detail="未授权，请先登录系统")
            else:
                # 有 token 但验证失败（可能是过期），返回 400 避免前端退出登录
                # 提取 token 用于调试
                token_preview = (
                    auth_header[:20] + "..." if len(auth_header) > 20 else auth_header
                )
                print(
                    f"⚠️ 测试仓库接口：Token 验证失败，header 前20个字符: {token_preview}"
                )
                raise HTTPException(
                    status_code=400, detail="系统 Token 已过期或无效，请刷新页面后重试"
                )

        # 系统认证通过后，使用传入的仓库用户名和密码测试仓库连接
        # 注意：这里的 username 和 password 是仓库的认证信息，不是系统的
        from backend.handlers import docker_builder

        if not docker_builder or not docker_builder.is_available():
            return JSONResponse(
                {"success": False, "message": "Docker 不可用，请检查 Docker 连接"},
                status_code=400,
            )

        registry_host = request.registry
        username = request.username
        password = request.password

        if not username or not password:
            return JSONResponse(
                {"success": False, "message": "用户名和密码不能为空"}, status_code=400
            )

        # 构建auth_config
        auth_config = {
            "username": username,
            "password": password,
        }

        # 设置serveraddress
        if registry_host and registry_host != "docker.io":
            auth_config["serveraddress"] = registry_host
        else:
            auth_config["serveraddress"] = "https://index.docker.io/v1/"

        try:
            # 尝试登录
            if hasattr(docker_builder, "client") and docker_builder.client:
                login_registry = (
                    registry_host
                    if registry_host and registry_host != "docker.io"
                    else None
                )
                login_result = docker_builder.client.login(
                    username=username,
                    password=password,
                    registry=login_registry,
                )

                # 登录成功
                return JSONResponse(
                    {
                        "success": True,
                        "message": f"登录成功！Registry: {registry_host or 'docker.io'}",
                        "details": str(login_result) if login_result else "认证通过",
                    }
                )
            else:
                return JSONResponse(
                    {"success": False, "message": "Docker 客户端不可用"},
                    status_code=400,
                )
        except Exception as login_error:
            error_msg = str(login_error)

            # 检查是否是认证错误
            if (
                "401" in error_msg
                or "Unauthorized" in error_msg
                or "unauthorized" in error_msg
            ):
                return JSONResponse(
                    {
                        "success": False,
                        "message": "认证失败：用户名或密码不正确",
                        "details": error_msg,
                        "suggestions": [
                            "请检查用户名和密码是否正确",
                            "对于阿里云registry，请使用独立的Registry登录密码（不是阿里云账号密码）",
                            "如果使用访问令牌，请确认令牌未过期",
                        ],
                    },
                    status_code=401,
                )
            else:
                return JSONResponse(
                    {
                        "success": False,
                        "message": f"登录失败: {error_msg}",
                        "details": error_msg,
                    },
                    status_code=400,
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试Registry登录失败: {str(e)}")


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
        OperationLogger.log(
            current_username,
            "save_config",
            {
                "expose_port": expose_port_int,
                "default_push": default_push_bool,
                "use_remote": use_remote_bool,
                "remote_host": remote_host.strip() if remote_host else None,
            },
        )

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
    push_registry: Optional[str] = Form(None),  # 已废弃，保留以兼容旧代码，实际不再使用
    extract_archive: str = Form("on"),  # 是否解压压缩包（默认解压）
    build_steps: Optional[str] = Form(None),  # JSON 字符串格式的构建步骤信息
    resource_package_configs: Optional[str] = Form(None),  # JSON 字符串格式的资源包配置
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

        # 解析构建步骤信息
        build_steps_dict = {}
        if build_steps:
            try:
                build_steps_dict = json.loads(build_steps)
            except json.JSONDecodeError:
                print(f"⚠️ 构建步骤信息格式错误，忽略: {build_steps}")

        # 解析资源包配置
        resource_package_configs_list = []
        if resource_package_configs:
            try:
                resource_package_configs_list = json.loads(resource_package_configs)
            except json.JSONDecodeError:
                print(f"⚠️ 资源包配置格式错误，忽略: {resource_package_configs}")

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
            push_registry=None,  # 已废弃，统一使用激活的registry
            extract_archive=(extract_archive == "on"),  # 传递解压选项
            build_steps=build_steps_dict,  # 传递构建步骤信息
            resource_package_ids=resource_package_configs_list,  # 传递资源包配置
        )

        # 记录操作日志
        OperationLogger.log(
            username,
            "build",
            {
                "task_id": task_id,
                "image": f"{imagename}:{tag}",
                "template": template,
                "project_type": project_type,
                "push": push == "on",
                "filename": app_file.filename,
            },
        )

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
    git_url: str = Body(..., embed=True, description="Git 仓库地址"),
    save_as_source: bool = Body(False, embed=True, description="是否保存为数据源"),
    source_name: Optional[str] = Body(
        None, embed=True, description="数据源名称（保存时必填）"
    ),
    source_description: Optional[str] = Body("", embed=True, description="数据源描述"),
    username: Optional[str] = Body(None, embed=True, description="Git 用户名（可选）"),
    password: Optional[str] = Body(
        None, embed=True, description="Git 密码或 token（可选）"
    ),
    source_id: Optional[str] = Body(
        None, embed=True, description="数据源 ID（如果提供，将使用数据源的认证信息）"
    ),
    branch: Optional[str] = Body(
        None, embed=True, description="指定分支（用于扫描该分支的 Dockerfile）"
    ),
):
    """验证 Git 仓库并获取分支和标签列表"""
    import subprocess
    import tempfile
    import shutil
    from urllib.parse import urlparse, urlunparse

    try:
        # 如果提供了 source_id，从数据源获取认证信息
        if source_id:
            source_manager = GitSourceManager()
            source = source_manager.get_source(source_id, include_password=False)
            if source:
                auth_config = source_manager.get_auth_config(source_id)
                if auth_config.get("username"):
                    username = username or auth_config.get("username")
                if auth_config.get("password"):
                    password = password or auth_config.get("password")

        # 如果提供了用户名和密码，嵌入到 URL 中
        verify_url = git_url
        if username and password and git_url.startswith("https://"):
            parsed = urlparse(git_url)
            verify_url = urlunparse(
                (
                    parsed.scheme,
                    f"{username}:{password}@{parsed.netloc}",
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )

        # 使用 git ls-remote 命令获取远程仓库的分支和标签
        # 这个命令不需要克隆整个仓库，只获取引用信息
        cmd = ["git", "ls-remote", "--heads", "--tags", verify_url]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30  # 30秒超时
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            if (
                "Authentication failed" in error_msg
                or "Permission denied" in error_msg
                or "fatal: could not read Username" in error_msg
            ):
                raise HTTPException(
                    status_code=403,  # 使用 403 而不是 401，避免被前端拦截器误判为登录失效
                    detail="仓库访问被拒绝，请检查认证信息是否正确或配置 SSH 密钥",
                )
            elif "not found" in error_msg.lower():
                raise HTTPException(
                    status_code=404, detail="仓库不存在，请检查 URL 是否正确"
                )
            else:
                raise HTTPException(
                    status_code=400, detail=f"无法访问仓库: {error_msg}"
                )

        # 解析输出
        branches = []
        tags = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) != 2:
                continue

            ref = parts[1]

            if ref.startswith("refs/heads/"):
                branch_name = ref.replace("refs/heads/", "")
                branches.append(branch_name)
            elif ref.startswith("refs/tags/"):
                tag_name = ref.replace("refs/tags/", "")
                # 跳过带 ^{} 的标签（指向标签对象的注解）
                if not tag_name.endswith("^{}"):
                    tags.append(tag_name)

        # 扫描 Dockerfile（需要克隆仓库的指定分支或默认分支）
        dockerfiles = {}
        # 确定默认分支
        default_branch = next(
            (b for b in branches if b in ["main", "master"]),
            branches[0] if branches else None,
        )
        # 如果指定了分支，使用指定分支；否则使用默认分支
        scan_branch = branch if branch and branch in branches else default_branch

        if scan_branch:
            try:
                # 临时克隆仓库以扫描 Dockerfile
                import tempfile

                temp_dir = tempfile.mkdtemp()
                clone_url = verify_url

                # 准备克隆命令
                clone_cmd = [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    scan_branch,
                    clone_url,
                    temp_dir,
                ]

                clone_result = subprocess.run(
                    clone_cmd, capture_output=True, text=True, timeout=60
                )

                if clone_result.returncode == 0:
                    # 扫描 Dockerfile（递归查找）
                    for root, dirs, files in os.walk(temp_dir):
                        # 跳过 .git 目录
                        if ".git" in root.split(os.sep):
                            continue

                        for file in files:
                            # 检查是否是 Dockerfile（不区分大小写，支持多种命名）
                            file_lower = file.lower()
                            if file_lower.startswith(
                                "dockerfile"
                            ) or file_lower.endswith(".dockerfile"):
                                file_path = os.path.join(root, file)
                                relative_path = os.path.relpath(file_path, temp_dir)

                                try:
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        content = f.read()
                                        dockerfiles[relative_path] = content
                                        print(f"✅ 扫描到 Dockerfile: {relative_path}")
                                except Exception as e:
                                    print(
                                        f"⚠️ 读取 Dockerfile 失败 {relative_path}: {e}"
                                    )

                    # 清理临时目录
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                print(f"⚠️ 扫描 Dockerfile 失败: {e}")
                # 清理临时目录（如果存在）
                if "temp_dir" in locals():
                    shutil.rmtree(temp_dir, ignore_errors=True)

        result = {
            "success": True,
            "branches": sorted(branches, key=lambda x: (x != "main", x != "master", x)),
            "tags": sorted(tags, reverse=True),  # 标签按降序排列，最新的在前
            "default_branch": default_branch,
            "dockerfiles": dockerfiles,  # 扫描到的 Dockerfile 列表
        }

        # 如果提供了 source_id，更新数据源的缓存（即使 save_as_source=False）
        if source_id:
            try:
                source_manager = GitSourceManager()
                source = source_manager.get_source(source_id, include_password=False)
                if source:
                    # 更新数据源的分支、标签和默认分支缓存
                    source_manager.update_source(
                        source_id=source_id,
                        branches=result["branches"],
                        tags=result["tags"],
                        default_branch=result["default_branch"],
                    )
                    # 更新扫描到的 Dockerfile
                    if result.get("dockerfiles"):
                        for dockerfile_path, content in result["dockerfiles"].items():
                            source_manager.update_dockerfile(
                                source_id, dockerfile_path, content
                            )
                    print(f"✅ 已更新数据源 {source_id} 的缓存（分支、标签、Dockerfile）")
            except Exception as e:
                print(f"⚠️ 更新数据源缓存失败: {e}")
                # 即使更新失败，也继续返回验证结果

        # 如果需要保存为数据源
        if save_as_source:
            if not source_name:
                raise HTTPException(
                    status_code=400, detail="保存为数据源时必须提供数据源名称"
                )

            try:
                source_manager = GitSourceManager()
                # 检查是否已存在相同 URL 的数据源
                existing_source = source_manager.get_source_by_url(git_url)
                if existing_source:
                    # 更新现有数据源（如果提供了认证信息，也更新）
                    source_manager.update_source(
                        source_id=existing_source["source_id"],
                        name=source_name,
                        description=source_description or "",
                        branches=result["branches"],
                        tags=result["tags"],
                        default_branch=result["default_branch"],
                        username=username if username is not None else None,
                        password=password if password is not None else None,
                    )
                    # 更新扫描到的 Dockerfile
                    if result.get("dockerfiles"):
                        for dockerfile_path, content in result["dockerfiles"].items():
                            source_manager.update_dockerfile(
                                existing_source["source_id"], dockerfile_path, content
                            )
                    result["source_id"] = existing_source["source_id"]
                    result["source_saved"] = True
                    result["source_updated"] = True
                else:
                    # 创建新数据源
                    source_id = source_manager.create_source(
                        name=source_name,
                        git_url=git_url,
                        description=source_description or "",
                        branches=result["branches"],
                        tags=result["tags"],
                        default_branch=result["default_branch"],
                        username=username,
                        password=password,
                    )
                    # 保存扫描到的 Dockerfile
                    if result.get("dockerfiles"):
                        for dockerfile_path, content in result["dockerfiles"].items():
                            source_manager.update_dockerfile(
                                source_id, dockerfile_path, content
                            )
                    result["source_id"] = source_id
                    result["source_saved"] = True
                    result["source_updated"] = False
            except Exception as e:
                print(f"⚠️ 保存数据源失败: {e}")
                # 即使保存失败，也返回验证结果
                result["source_saved"] = False
                result["source_error"] = str(e)

        return JSONResponse(result)

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408, detail="仓库访问超时，请检查网络连接或仓库地址"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"验证仓库失败: {str(e)}")


class ParseDockerfileRequest(BaseModel):
    """解析 Dockerfile 请求模型"""

    dockerfile_content: Optional[str] = None  # 直接提供 Dockerfile 内容
    git_url: Optional[str] = None  # 从 Git 仓库获取
    branch: Optional[str] = None  # Git 分支
    dockerfile_name: str = "Dockerfile"  # Dockerfile 文件名
    source_id: Optional[str] = None  # Git 数据源 ID（可选）


@router.post("/parse-dockerfile-services")
async def parse_dockerfile_services_api(
    request: Request, body: ParseDockerfileRequest = Body(...)
):
    """解析 Dockerfile 并返回服务列表"""
    try:
        dockerfile_content = None

        # 方式1: 直接提供 Dockerfile 内容
        if body.dockerfile_content:
            dockerfile_content = body.dockerfile_content

        # 方式2: 从 Git 仓库获取
        elif body.git_url:
            from backend.git_source_manager import GitSourceManager

            # 创建临时目录
            temp_dir = tempfile.mkdtemp(prefix="dockerfile_parse_")

            try:
                # 获取 Git 配置
                git_config = get_git_config()
                if body.source_id:
                    source_manager = GitSourceManager()
                    source_auth = source_manager.get_auth_config(body.source_id)
                    if source_auth.get("username"):
                        git_config["username"] = source_auth["username"]
                    if source_auth.get("password"):
                        git_config["password"] = source_auth["password"]

                # 克隆仓库
                manager = BuildManager()
                clone_dir = os.path.join(temp_dir, "repo")
                os.makedirs(clone_dir, exist_ok=True)

                clone_success, clone_error = manager._clone_git_repo(
                    body.git_url,
                    clone_dir,
                    body.branch,
                    git_config,
                    lambda x: None,  # 不需要日志
                )

                if not clone_success:
                    error_detail = "无法克隆 Git 仓库，请检查仓库地址和认证信息"
                    if clone_error:
                        error_detail += f": {clone_error}"
                    raise HTTPException(status_code=400, detail=error_detail)

                # 找到仓库目录
                repo_name = body.git_url.rstrip("/").split("/")[-1].replace(".git", "")
                repo_path = os.path.join(clone_dir, repo_name)
                if not os.path.exists(repo_path):
                    items = os.listdir(clone_dir)
                    if items:
                        repo_path = os.path.join(clone_dir, items[0])

                # 读取 Dockerfile
                dockerfile_path = os.path.join(repo_path, body.dockerfile_name)
                if not os.path.exists(dockerfile_path):
                    raise HTTPException(
                        status_code=404,
                        detail=f"在仓库中未找到 Dockerfile: {body.dockerfile_name}",
                    )

                with open(dockerfile_path, "r", encoding="utf-8") as f:
                    dockerfile_content = f.read()

            finally:
                # 清理临时目录
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

        else:
            raise HTTPException(
                status_code=400, detail="必须提供 dockerfile_content 或 git_url"
            )

        if not dockerfile_content:
            raise HTTPException(status_code=400, detail="无法获取 Dockerfile 内容")

        # 解析服务列表
        try:
            services, _ = parse_dockerfile_services(dockerfile_content)
            return JSONResponse({"services": services, "count": len(services)})
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise HTTPException(
                status_code=500, detail=f"解析 Dockerfile 失败: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


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
    push_registry: Optional[str] = Body(None),  # 已废弃，保留以兼容旧代码，实际不再使用
    branch: Optional[str] = Body(None),
    sub_path: Optional[str] = Body(None),
    use_project_dockerfile: bool = Body(
        True, description="是否优先使用项目中的 Dockerfile"
    ),
    dockerfile_name: str = Body(
        "Dockerfile", description="Dockerfile文件名，默认Dockerfile"
    ),
    source_id: Optional[str] = Body(
        None, description="Git 数据源 ID（可选，如果提供将使用数据源的认证信息）"
    ),
    selected_services: Optional[list] = Body(
        None, description="选中的服务列表（多服务构建时使用）"
    ),
    service_push_config: Optional[dict] = Body(
        None, description="每个服务的推送配置（key为服务名，value为是否推送）"
    ),
    push_mode: Optional[str] = Body(
        "multi",
        description="推送模式：'single' 单一推送，'multi' 多阶段推送（仅模板模式）",
    ),
    build_steps: Optional[dict] = Body(None, description="构建步骤信息（JSON对象）"),
    service_template_params: Optional[dict] = Body(
        None, description="服务模板参数（JSON对象）"
    ),
    resource_package_ids: Optional[list] = Body(
        None, description="资源包ID列表（已废弃，使用resource_package_configs）"
    ),
    resource_package_configs: Optional[list] = Body(
        None,
        description="资源包配置列表 [{package_id, target_path}]，target_path 为相对路径，如 'test/b.txt' 或 'resources'",
    ),
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

        # 解析服务模板参数
        service_template_params_dict = {}
        if service_template_params:
            # 如果已经是字典，直接使用；如果是字符串，则解析
            if isinstance(service_template_params, dict):
                service_template_params_dict = service_template_params
            elif isinstance(service_template_params, str):
                try:
                    service_template_params_dict = json.loads(service_template_params)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="服务模板参数格式错误")

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
                    status_code=500, detail=f"构建管理器初始化失败: {str(init_error)}"
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
                    push_registry=None,  # 已废弃，统一使用激活的registry
                    branch=branch,
                    sub_path=sub_path,
                    use_project_dockerfile=use_project_dockerfile,
                    dockerfile_name=dockerfile_name,
                    source_id=source_id,
                    selected_services=selected_services,
                    service_push_config=service_push_config,
                    push_mode=push_mode or "multi",
                    build_steps=build_steps,  # 传递构建步骤信息
                    service_template_params=service_template_params_dict,  # 传递服务模板参数
                    resource_package_ids=resource_package_configs
                    or [],  # 传递资源包配置
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
                    status_code=500, detail=f"创建构建任务失败: {str(create_error)}"
                )
        except HTTPException:
            raise
        except Exception as create_error:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 创建构建任务异常: {create_error}")
            print(f"错误堆栈:\n{error_trace}")
            raise HTTPException(
                status_code=500, detail=f"创建构建任务失败: {str(create_error)}"
            )

        # 记录操作日志
        try:
            OperationLogger.log(
                username,
                "build_from_source",
                {
                    "task_id": task_id,
                    "image": f"{imagename}:{tag}",
                    "template": template,
                    "project_type": project_type,
                    "git_url": git_url,
                    "branch": branch,
                    "push": push == "on",
                },
            )
        except Exception as log_error:
            print(f"⚠️ 记录操作日志失败: {log_error}")

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
    task_type: Optional[str] = Query(
        None, description="任务类型过滤: build, build_from_source, export"
    ),
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


@router.post("/build-tasks/{task_id}/stop")
async def stop_build_task(task_id: str, request: Request):
    """停止构建任务"""
    try:
        username = get_current_username(request)
        manager = BuildTaskManager()
        if manager.stop_task(task_id):
            OperationLogger.log(username, "stop_build_task", {"task_id": task_id})
            return JSONResponse({"success": True, "message": "任务已停止"})
        else:
            raise HTTPException(
                status_code=400,
                detail="任务不存在或无法停止（只有运行中或等待中的任务才能停止）",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}")


@router.get("/build-tasks/{task_id}/config")
async def get_build_task_config(task_id: str):
    """获取构建任务的配置JSON"""
    try:
        manager = BuildTaskManager()
        task = manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 优先返回task_config，如果没有则从任务信息构建
        task_config = task.get("task_config")
        if not task_config:
            # 向后兼容：从任务信息构建配置
            from backend.handlers import build_task_config

            task_config = build_task_config(
                git_url=task.get("git_url", ""),
                image_name=task.get("image", ""),
                tag=task.get("tag", "latest"),
                branch=task.get("branch"),
                project_type=task.get("project_type", "jar"),
                template=task.get("selected_template", ""),
                template_params=task.get("template_params", {}),
                should_push=task.get("should_push", False),
                sub_path=task.get("sub_path"),
                use_project_dockerfile=task.get("use_project_dockerfile", True),
                dockerfile_name=task.get("dockerfile_name", "Dockerfile"),
                source_id=task.get("source_id"),
                selected_services=task.get("selected_services"),
                service_push_config=task.get("service_push_config"),
                service_template_params=task.get("service_template_params"),
                push_mode=task.get("push_mode", "multi"),
                resource_package_ids=task.get("resource_package_ids"),
                pipeline_id=task.get("pipeline_id"),
                trigger_source=task.get("trigger_source", "manual"),
            )

        return JSONResponse(task_config)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务配置失败: {str(e)}")


@router.post("/build-tasks/{task_id}/retry")
async def retry_build_task(task_id: str, request: Request):
    """重试构建任务（使用任务保存的JSON配置）"""
    try:
        username = get_current_username(request)
        manager = BuildTaskManager()
        task = manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 检查任务状态
        if task.get("status") in ["pending", "running"]:
            raise HTTPException(status_code=400, detail="任务正在运行中，无法重试")

        # 获取任务配置
        task_config = task.get("task_config")
        if not task_config:
            # 向后兼容：从任务信息构建配置
            from backend.handlers import build_task_config

            task_config = build_task_config(
                git_url=task.get("git_url", ""),
                image_name=task.get("image", ""),
                tag=task.get("tag", "latest"),
                branch=task.get("branch"),
                project_type=task.get("project_type", "jar"),
                template=task.get("selected_template", ""),
                template_params=task.get("template_params", {}),
                should_push=task.get("should_push", False),
                sub_path=task.get("sub_path"),
                use_project_dockerfile=task.get("use_project_dockerfile", True),
                dockerfile_name=task.get("dockerfile_name", "Dockerfile"),
                source_id=task.get("source_id"),
                selected_services=task.get("selected_services"),
                service_push_config=task.get("service_push_config"),
                service_template_params=task.get("service_template_params"),
                push_mode=task.get("push_mode", "multi"),
                resource_package_ids=task.get("resource_package_ids"),
                pipeline_id=task.get("pipeline_id"),
                trigger_source="retry",  # 标记为重试
            )

        # 使用统一触发函数重新触发任务
        build_manager = BuildManager()
        new_task_id = build_manager._trigger_task_from_config(task_config)

        # 记录操作日志
        OperationLogger.log(
            username,
            "retry_build_task",
            {
                "original_task_id": task_id,
                "new_task_id": new_task_id,
            },
        )

        return JSONResponse(
            {
                "message": "任务重试成功",
                "original_task_id": task_id,
                "new_task_id": new_task_id,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")


@router.delete("/build-tasks/{task_id}")
async def delete_build_task(task_id: str, request: Request):
    """删除构建任务（只有停止、完成或失败的任务才能删除）"""
    try:
        username = get_current_username(request)
        manager = BuildTaskManager()
        task = manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        status = task.get("status")
        if status not in ("stopped", "completed", "failed"):
            raise HTTPException(
                status_code=400,
                detail=f"无法删除任务：只有停止、完成或失败的任务才能删除（当前状态: {status}）",
            )

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
    status: Optional[str] = Body(
        None, description="清理指定状态的任务：completed, failed"
    ),
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

                # 获取所有任务
                all_tasks = build_manager.list_tasks()
                tasks_to_remove = [
                    task["task_id"]
                    for task in all_tasks
                    if task.get("created_at")
                    and datetime.fromisoformat(task["created_at"]) < cutoff_time
                    and (not status or task.get("status") == status)
                ]

                # 执行删除
                for task_id in tasks_to_remove:
                    build_manager.delete_task(task_id)
                    removed_count += 1
            elif status:
                # 清理指定状态的任务
                tasks_to_remove = [
                    task["task_id"] for task in build_manager.list_tasks(status=status)
                ]

                # 执行删除
                for task_id in tasks_to_remove:
                    build_manager.delete_task(task_id)
                    removed_count += 1
            elif not days and not status:
                # 清理全部（只清理非运行中的任务）
                all_tasks = build_manager.list_tasks()
                tasks_to_remove = [
                    task["task_id"]
                    for task in all_tasks
                    if task.get("status") not in ["running", "pending"]
                ]

                # 执行删除
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

                # 获取所有任务
                all_tasks = export_manager.list_tasks()
                tasks_to_remove = [
                    task["task_id"]
                    for task in all_tasks
                    if task.get("created_at")
                    and datetime.fromisoformat(task["created_at"]) < cutoff_time
                    and (not status or task.get("status") == status)
                ]

                # 执行删除
                for task_id in tasks_to_remove:
                    export_manager.delete_task(task_id)
                    removed_count += 1
            elif status:
                # 清理指定状态的任务
                tasks_to_remove = [
                    task["task_id"] for task in export_manager.list_tasks(status=status)
                ]

                # 执行删除
                for task_id in tasks_to_remove:
                    export_manager.delete_task(task_id)
                    removed_count += 1
            elif not days and not status:
                # 清理全部（只清理非运行中的任务）
                all_tasks = export_manager.list_tasks()
                tasks_to_remove = [
                    task["task_id"]
                    for task in all_tasks
                    if task.get("status") not in ["running", "pending"]
                ]

                # 执行删除
                for task_id in tasks_to_remove:
                    export_manager.delete_task(task_id)
                    removed_count += 1

        # 记录操作日志
        OperationLogger.log(
            username,
            "cleanup_tasks",
            {
                "removed_count": removed_count,
                "status": status,
                "days": days,
                "task_type": task_type,
            },
        )

        return JSONResponse(
            {
                "success": True,
                "removed_count": removed_count,
                "message": f"已清理 {removed_count} 个任务",
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"清理任务失败: {str(e)}")


@router.get("/docker-build/stats")
async def get_docker_build_stats(request: Request):
    """获取 docker_build 目录的统计信息（容量、目录数量等）"""
    try:
        if not os.path.exists(BUILD_DIR):
            return {
                "success": True,
                "total_size_mb": 0,
                "dir_count": 0,
                "exists": False,
            }

        total_size = 0
        dir_count = 0

        # 遍历构建目录
        for item in os.listdir(BUILD_DIR):
            item_path = os.path.join(BUILD_DIR, item)
            if not os.path.isdir(item_path):
                continue

            # 跳过 tasks 目录（任务元数据目录）
            if item == "tasks":
                continue

            try:
                # 计算目录大小
                dir_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(item_path)
                    for filename in filenames
                )
                total_size += dir_size
                dir_count += 1
            except Exception as e:
                print(f"⚠️ 计算目录大小失败 ({item_path}): {e}")

        return {
            "success": True,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "dir_count": dir_count,
            "exists": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取构建目录统计失败: {str(e)}")


@router.get("/exports/stats")
async def get_exports_stats(request: Request):
    """获取 exports 目录的统计信息（容量、文件数量等）"""
    try:
        if not os.path.exists(EXPORT_DIR):
            return {
                "success": True,
                "total_size_mb": 0,
                "file_count": 0,
                "exists": False,
            }

        total_size = 0
        file_count = 0

        # 遍历导出目录（包括所有子目录）
        for root, dirs, files in os.walk(EXPORT_DIR):
            # 跳过 tasks.json 元数据文件，但统计 tasks 子目录下的实际导出文件
            for filename in files:
                # 跳过 tasks.json 元数据文件
                if filename == "tasks.json":
                    continue
                file_path = os.path.join(root, filename)
                try:
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    file_count += 1
                except Exception as e:
                    print(f"⚠️ 计算文件大小失败 ({file_path}): {e}")

        return {
            "success": True,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "file_count": file_count,
            "exists": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取导出目录统计失败: {str(e)}")


@router.post("/exports/cleanup")
async def cleanup_exports_dir(
    request: Request,
    days: Optional[int] = Body(
        None, description="清理N天前的导出文件（不传则清理所有）"
    ),
    keep_tasks: bool = Body(True, description="是否保留任务元数据文件（tasks.json）"),
):
    """清理导出目录中的文件"""
    try:
        username = get_current_username(request)
        if username == "unknown":
            raise HTTPException(status_code=401, detail="未授权，请重新登录")

        if not os.path.exists(EXPORT_DIR):
            return JSONResponse(
                {
                    "success": True,
                    "message": "导出目录不存在，无需清理",
                    "removed_count": 0,
                    "freed_space_mb": 0,
                }
            )

        removed_count = 0
        freed_space = 0
        cutoff_time = None

        if days and days > 0:
            from datetime import datetime, timedelta

            cutoff_time = datetime.now() - timedelta(days=days)

        # 遍历导出目录
        for root, dirs, files in os.walk(EXPORT_DIR):
            for filename in files:
                # 如果保留任务元数据，跳过 tasks.json
                if keep_tasks and filename == "tasks.json":
                    continue

                file_path = os.path.join(root, filename)
                try:
                    # 检查文件修改时间
                    if cutoff_time:
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime > cutoff_time:
                            continue  # 文件未过期，跳过

                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    removed_count += 1
                    freed_space += file_size
                    print(f"✅ 清理导出文件: {file_path}")
                except Exception as e:
                    print(f"⚠️ 删除导出文件失败 ({file_path}): {e}")

            # 清理空目录（但保留根目录）
            if root != EXPORT_DIR:
                try:
                    if not os.listdir(root):
                        os.rmdir(root)
                        print(f"✅ 清理空目录: {root}")
                except Exception as e:
                    print(f"⚠️ 删除空目录失败 ({root}): {e}")

        freed_space_mb = round(freed_space / 1024 / 1024, 2)

        # 记录操作日志
        OperationLogger.log(
            username,
            "cleanup_exports",
            {
                "removed_count": removed_count,
                "freed_space_mb": freed_space_mb,
                "days": days,
            },
        )

        message = (
            f"成功清理了 {removed_count} 个文件，释放空间 {freed_space_mb} MB"
            if removed_count > 0
            else "没有需要清理的文件"
        )

        return JSONResponse(
            {
                "success": True,
                "message": message,
                "removed_count": removed_count,
                "freed_space_mb": freed_space_mb,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"清理导出目录失败: {str(e)}")


def force_remove_directory(dir_path: str) -> tuple[bool, str]:
    """
    强制删除目录（适用于Windows）
    返回: (是否成功, 错误信息)
    """
    import errno
    import stat
    import time
    import platform

    def handle_remove_readonly(func, path, exc):
        excvalue = exc[1]
        if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
            try:
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                func(path)
            except Exception:
                raise

    try:
        # 首先尝试使用onerror回调删除
        shutil.rmtree(dir_path, onerror=handle_remove_readonly)

        # 等待文件系统更新
        for _ in range(5):
            time.sleep(0.1)
            if not os.path.exists(dir_path):
                return True, ""

        # 如果还存在，尝试手动删除
        if os.path.exists(dir_path):
            for root, dirs, files in os.walk(dir_path, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        os.chmod(file_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                        os.remove(file_path)
                    except Exception as e:
                        print(f"⚠️ 删除文件失败 ({file_path}): {e}")
                for name in dirs:
                    dir_path_full = os.path.join(root, name)
                    try:
                        os.chmod(
                            dir_path_full, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO
                        )
                        os.rmdir(dir_path_full)
                    except Exception as e:
                        print(f"⚠️ 删除子目录失败 ({dir_path_full}): {e}")
            try:
                os.chmod(dir_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                os.rmdir(dir_path)
            except Exception as e:
                # 最后尝试Windows系统命令
                if platform.system() == "Windows":
                    try:
                        import subprocess

                        result = subprocess.run(
                            ["cmd", "/c", "rmdir", "/s", "/q", dir_path],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        if result.returncode != 0:
                            return (
                                False,
                                f"系统命令删除失败: {result.stderr or result.stdout}",
                            )
                    except Exception as sub_err:
                        return False, f"系统命令执行失败: {sub_err}"
                else:
                    return False, f"删除失败: {e}"

        # 最终验证
        time.sleep(0.2)
        if os.path.exists(dir_path):
            return False, "删除后目录仍然存在"

        return True, ""
    except Exception as e:
        import traceback

        return False, f"删除异常: {str(e)}\n{traceback.format_exc()}"


@router.post("/docker-build/cleanup")
async def cleanup_docker_build_dir(
    request: Request,
    keep_days: Optional[int] = Body(
        0, description="保留最近N天的构建上下文，0表示清空所有"
    ),
    cleanup_orphans_only: Optional[bool] = Body(
        False, description="仅清理异常文件夹（无对应任务的文件夹）"
    ),
):
    """清理 docker_build 目录中的构建上下文"""
    try:
        username = get_current_username(request)

        # 确保 BUILD_DIR 是绝对路径
        build_dir = os.path.abspath(BUILD_DIR)
        print(f"🔍 清理编译目录: {build_dir}")
        print(f"🔍 keep_days: {keep_days}")
        print(f"🔍 cleanup_orphans_only: {cleanup_orphans_only}")

        if not os.path.exists(build_dir):
            print(f"⚠️ 构建目录不存在: {build_dir}")
            return JSONResponse(
                {
                    "success": True,
                    "message": "构建目录不存在，无需清理",
                    "removed_count": 0,
                    "freed_space_mb": 0,
                }
            )

        removed_count = 0
        total_size = 0
        errors = []
        orphan_count = 0  # 异常文件夹计数

        # 获取所有有效任务的构建上下文路径集合
        valid_build_contexts = set()
        try:
            build_manager = BuildTaskManager()
            all_tasks = build_manager.list_tasks()
            for task in all_tasks:
                task_id = task.get("task_id")
                # 获取构建上下文路径（从 image_name 和 task_id 推导）
                image_name = task.get("image", "")
                if image_name:
                    build_context = os.path.join(
                        BUILD_DIR,
                        f"{image_name.replace('/', '_')}_{task_id[:8]}",
                    )
                    if build_context:
                        # 转换为绝对路径并规范化
                        abs_path = os.path.abspath(build_context)
                        valid_build_contexts.add(abs_path)
                        # 同时添加相对路径到 BUILD_DIR 的路径，以防匹配问题
                        if not os.path.isabs(build_context):
                            valid_build_contexts.add(os.path.abspath(build_context))
            print(f"🔍 找到 {len(valid_build_contexts)} 个有效任务的构建上下文")
            if len(valid_build_contexts) > 0:
                print(f"🔍 有效路径示例: {list(valid_build_contexts)[:3]}")
        except Exception as e:
            print(f"⚠️ 获取有效任务列表失败: {e}")

        # 如果仅清理异常文件夹
        if cleanup_orphans_only:
            print(f"🗑️ 开始清理异常文件夹...")
            try:
                items = os.listdir(build_dir)
                print(f"🔍 找到 {len(items)} 个项目")
            except Exception as e:
                print(f"❌ 无法列出目录内容: {e}")
                raise HTTPException(
                    status_code=500, detail=f"无法访问构建目录: {str(e)}"
                )

            for item in items:
                item_path = os.path.join(build_dir, item)
                if not os.path.isdir(item_path):
                    continue

                # 跳过 tasks 目录（任务元数据目录）
                if item == "tasks":
                    continue

                abs_item_path = os.path.abspath(item_path)
                # 尝试多种路径匹配方式
                is_valid = (
                    abs_item_path in valid_build_contexts
                    or item_path in valid_build_contexts
                    or os.path.normpath(abs_item_path)
                    in {os.path.normpath(p) for p in valid_build_contexts}
                )

                # 只清理异常文件夹
                if not is_valid:
                    orphan_count += 1
                    print(f"⚠️ 发现异常文件夹（无对应任务）: {item_path}")
                    try:
                        # 检查目录是否存在
                        if not os.path.exists(item_path):
                            print(f"⏭️ 目录不存在，跳过: {item_path}")
                            continue

                        # 计算目录大小
                        dir_size = 0
                        try:
                            dir_size = sum(
                                os.path.getsize(os.path.join(dirpath, filename))
                                for dirpath, dirnames, filenames in os.walk(item_path)
                                for filename in filenames
                            )
                        except Exception as size_err:
                            print(f"⚠️ 计算目录大小失败 ({item_path}): {size_err}")

                        total_size += dir_size

                        # 删除目录
                        print(f"🗑️ 正在删除目录: {item_path}")
                        success, error_detail = force_remove_directory(item_path)

                        if success:
                            removed_count += 1
                            print(f"✅ 成功清理异常文件夹: {item_path}")
                        else:
                            error_msg = (
                                f"清理异常文件夹失败 ({item_path}): {error_detail}"
                            )
                            print(f"❌ {error_msg}")
                            errors.append(error_msg)
                    except Exception as e:
                        import traceback

                        error_detail = traceback.format_exc()
                        error_msg = (
                            f"清理异常文件夹失败 ({item_path}): {e}\n{error_detail}"
                        )
                        print(f"❌ {error_msg}")
                        errors.append(error_msg)

        # 如果 keep_days 为 0，清空所有目录
        elif keep_days == 0:
            print(f"🗑️ 开始清空所有目录...")
            # 遍历构建目录，删除所有
            try:
                items = os.listdir(build_dir)
                print(f"🔍 找到 {len(items)} 个项目")
            except Exception as e:
                print(f"❌ 无法列出目录内容: {e}")
                raise HTTPException(
                    status_code=500, detail=f"无法访问构建目录: {str(e)}"
                )

            for item in items:
                item_path = os.path.join(build_dir, item)
                if not os.path.isdir(item_path):
                    print(f"⏭️ 跳过非目录项: {item}")
                    continue

                # 跳过 tasks 目录（任务元数据目录）
                if item == "tasks":
                    continue

                try:
                    abs_item_path = os.path.abspath(item_path)
                    is_valid = abs_item_path in valid_build_contexts

                    if not is_valid:
                        orphan_count += 1
                        print(f"⚠️ 发现异常文件夹（无对应任务）: {item_path}")

                    print(f"🗑️ 正在删除: {item_path}")
                    # 计算目录大小
                    dir_size = 0
                    try:
                        for dirpath, dirnames, filenames in os.walk(item_path):
                            for filename in filenames:
                                file_path = os.path.join(dirpath, filename)
                                try:
                                    dir_size += os.path.getsize(file_path)
                                except Exception as e:
                                    print(f"⚠️ 无法获取文件大小 ({file_path}): {e}")
                    except Exception as e:
                        print(f"⚠️ 遍历目录失败 ({item_path}): {e}")

                    total_size += dir_size

                    # 删除目录
                    print(f"🗑️ 正在删除目录: {item_path}")
                    success, error_detail = force_remove_directory(item_path)

                    if success:
                        removed_count += 1
                        print(f"✅ 成功删除: {item_path}")
                    else:
                        error_msg = f"清理目录失败 ({item_path}): {error_detail}"
                        print(f"❌ {error_msg}")
                        errors.append(error_msg)
                except Exception as e:
                    import traceback

                    error_detail = traceback.format_exc()
                    error_msg = f"清理构建上下文失败 ({item_path}): {e}\n{error_detail}"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)
        else:
            # 计算截止时间，清理指定天数前的目录
            from datetime import timedelta

            cutoff_time = datetime.now() - timedelta(days=keep_days)

            # 遍历构建目录
            for item in os.listdir(build_dir):
                item_path = os.path.join(build_dir, item)
                if not os.path.isdir(item_path):
                    continue

                # 跳过 tasks 目录（任务元数据目录）
                if item == "tasks":
                    continue

                abs_item_path = os.path.abspath(item_path)
                # 尝试多种路径匹配方式
                is_valid = (
                    abs_item_path in valid_build_contexts
                    or item_path in valid_build_contexts
                    or os.path.normpath(abs_item_path)
                    in {os.path.normpath(p) for p in valid_build_contexts}
                )

                # 异常文件夹无论时间如何都要清理
                if not is_valid:
                    orphan_count += 1
                    print(f"⚠️ 发现异常文件夹（无对应任务）: {item_path}")
                    try:
                        # 检查目录是否存在
                        if not os.path.exists(item_path):
                            print(f"⏭️ 目录不存在，跳过: {item_path}")
                            continue

                        # 计算目录大小
                        dir_size = 0
                        try:
                            dir_size = sum(
                                os.path.getsize(os.path.join(dirpath, filename))
                                for dirpath, dirnames, filenames in os.walk(item_path)
                                for filename in filenames
                            )
                        except Exception as size_err:
                            print(f"⚠️ 计算目录大小失败 ({item_path}): {size_err}")
                        total_size += dir_size

                        # 删除目录
                        print(f"🗑️ 正在删除异常文件夹: {item_path}")
                        success, error_detail = force_remove_directory(item_path)

                        if success:
                            removed_count += 1
                            print(f"✅ 清理异常文件夹: {item_path}")
                        else:
                            error_msg = (
                                f"清理异常文件夹失败 ({item_path}): {error_detail}"
                            )
                            print(f"❌ {error_msg}")
                            errors.append(error_msg)
                    except Exception as e:
                        import traceback

                        error_detail = traceback.format_exc()
                        error_msg = (
                            f"清理异常文件夹失败 ({item_path}): {e}\n{error_detail}"
                        )
                        print(f"❌ {error_msg}")
                        errors.append(error_msg)
                    continue  # 异常文件夹已处理，跳过时间检查

                # 对于有效文件夹，检查是否超过保留天数
                try:
                    mtime = os.path.getmtime(item_path)
                    is_old = mtime < cutoff_time.timestamp()

                    # 超过保留天数的有效文件夹也要清理
                    if is_old:
                        # 计算目录大小
                        dir_size = 0
                        try:
                            dir_size = sum(
                                os.path.getsize(os.path.join(dirpath, filename))
                                for dirpath, dirnames, filenames in os.walk(item_path)
                                for filename in filenames
                            )
                        except Exception as size_err:
                            print(f"⚠️ 计算目录大小失败 ({item_path}): {size_err}")
                        total_size += dir_size

                        # 删除目录
                        print(f"🗑️ 正在删除目录（超过保留天数）: {item_path}")
                        success, error_detail = force_remove_directory(item_path)

                        if success:
                            removed_count += 1
                            print(f"✅ 清理目录（超过保留天数）: {item_path}")
                        else:
                            error_msg = f"清理目录失败 ({item_path}): {error_detail}"
                            print(f"❌ {error_msg}")
                            errors.append(error_msg)
                except Exception as e:
                    import traceback

                    error_detail = traceback.format_exc()
                    error_msg = f"清理构建上下文失败 ({item_path}): {e}\n{error_detail}"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)

        # 记录操作日志
        try:
            OperationLogger.log(
                username=username,
                operation="清理构建上下文",
                details={
                    "removed_count": removed_count,
                    "freed_space_mb": round(total_size / 1024 / 1024, 2),
                },
            )
        except Exception as log_error:
            print(f"⚠️ 记录操作日志失败: {log_error}")

        freed_space_mb = round(total_size / 1024 / 1024, 2)
        message = f"成功清理了 {removed_count} 个目录，释放空间 {freed_space_mb} MB"
        if orphan_count > 0:
            message += f"（其中 {orphan_count} 个异常文件夹）"

        if errors:
            message += f"\n警告: {len(errors)} 个目录清理失败"
            print(f"⚠️ 清理过程中有错误: {errors}")

        print(f"✅ 清理完成: {message}")

        return JSONResponse(
            {
                "success": True,
                "removed_count": removed_count,
                "freed_space_mb": freed_space_mb,
                "message": message,
                "errors": errors if errors else None,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        print(f"❌ 清理构建上下文异常: {e}")
        print(f"错误堆栈:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"清理构建上下文失败: {str(e)}")


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

        # 验证和清理镜像名称（检查格式，移除协议前缀等）
        try:
            image_name = validate_and_clean_image_name(image_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

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
        OperationLogger.log(
            username,
            "export",
            {
                "task_id": task_id,
                "image": f"{image_name}:{tag_name}",
                "compress": compress,
            },
        )

        return JSONResponse(
            {
                "task_id": task_id,
                "message": "导出任务已创建，请到任务清单查看进度",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建导出任务失败: {str(e)}")


@router.get("/export-tasks")
async def list_export_tasks(
    status: Optional[str] = Query(
        None, description="任务状态过滤: pending, running, completed, failed"
    ),
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
            raise HTTPException(
                status_code=400, detail=f"任务尚未完成，当前状态: {task['status']}"
            )

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


@router.post("/export-tasks/{task_id}/stop")
async def stop_export_task(task_id: str, request: Request):
    """停止导出任务"""
    try:
        username = get_current_username(request)
        task_manager = ExportTaskManager()
        if task_manager.stop_task(task_id):
            OperationLogger.log(username, "stop_export_task", {"task_id": task_id})
            return JSONResponse({"success": True, "message": "任务已停止"})
        else:
            raise HTTPException(
                status_code=400,
                detail="任务不存在或无法停止（只有运行中或等待中的任务才能停止）",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}")


@router.post("/export-tasks/{task_id}/retry")
async def retry_export_task(task_id: str, request: Request):
    """重试导出任务（失败或停止的任务可以重试）"""
    try:
        username = get_current_username(request)
        task_manager = ExportTaskManager()
        if task_manager.retry_task(task_id):
            OperationLogger.log(username, "retry_export_task", {"task_id": task_id})
            return JSONResponse({"success": True, "message": "任务已重新启动"})
        else:
            raise HTTPException(
                status_code=400,
                detail="任务不存在或无法重试（只有失败或停止的任务才能重试）",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")


@router.delete("/export-tasks/{task_id}")
async def delete_export_task(task_id: str, request: Request):
    """删除导出任务（只有停止、完成或失败的任务才能删除）"""
    try:
        username = get_current_username(request)
        task_manager = ExportTaskManager()
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        status = task.get("status")
        if status not in ("stopped", "completed", "failed"):
            raise HTTPException(
                status_code=400,
                detail=f"无法删除任务：只有停止、完成或失败的任务才能删除（当前状态: {status}）",
            )

        success = task_manager.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 记录操作日志
        if task:
            OperationLogger.log(
                username,
                "delete_export_task",
                {
                    "task_id": task_id,
                    "image": task.get("image"),
                    "tag": task.get("tag"),
                },
            )

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
                        after_slash = reference[last_slash + 1 :]
                        if ":" in after_slash:
                            # 分离镜像名和标签
                            name = reference[:colon_index]
                            tag = reference[colon_index + 1 :].strip()
                            # 如果 tag 为空，使用 latest
                            return name.strip(), tag if tag else "latest"

                # 没有斜杠或斜杠在冒号前，直接分离
                name = reference[:colon_index]
                tag = reference[colon_index + 1 :].strip()
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
                            images.append(
                                {
                                    "service": service_name,
                                    "image": image_name,
                                    "tag": tag,
                                    "raw": image_ref,
                                }
                            )

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

        # 解析参数（全局参数）
        all_params = parse_template_variables(content)

        # 解析服务阶段（多阶段构建）
        services, global_param_names = parse_dockerfile_services(content)

        # 区分全局参数和服务参数
        global_params = [p for p in all_params if p["name"] in global_param_names]
        # 服务参数已经在 services 中的 template_params 字段中

        return JSONResponse(
            {
                "template": template,
                "project_type": project_type,
                "params": global_params,  # 全局模板参数
                "services": services,  # 服务列表，每个服务可能包含 template_params
            }
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
        OperationLogger.log(
            username, "template_create", {"name": name, "project_type": project_type}
        )

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
        old_project_type = request.old_project_type or request.project_type  # 使用旧的项目类型或当前项目类型

        templates = get_all_templates()

        # 查找原始模板：优先使用 old_project_type 来匹配
        template_info = None
        
        # 方法1: 如果提供了 old_project_type，直接通过路径查找
        if old_project_type:
            expected_path = os.path.join(USER_TEMPLATES_DIR, old_project_type, f"{original_name}.Dockerfile")
            if os.path.exists(expected_path):
                template_info = {
                    "name": original_name,
                    "path": expected_path,
                    "type": "user",
                    "project_type": old_project_type,
                }
        
        # 方法2: 在 templates 字典中查找匹配的模板（名称和项目类型都匹配）
        if not template_info:
            for tpl_name, tpl_info in templates.items():
                if tpl_name == original_name:
                    # 如果提供了 old_project_type，必须匹配
                    if old_project_type:
                        if tpl_info.get("project_type") == old_project_type:
                            template_info = tpl_info
                            break
                    else:
                        # 如果没有提供 old_project_type，使用第一个匹配的
                        template_info = tpl_info
                        break

        if not template_info:
            error_msg = f"模板不存在: {original_name}"
            if old_project_type:
                error_msg += f" (项目类型: {old_project_type})"
            raise HTTPException(status_code=404, detail=error_msg)

        if template_info.get("type") == "builtin":
            raise HTTPException(status_code=403, detail="不能修改内置模板")

        old_path = template_info.get("path")
        if not old_path:
            # 如果路径不存在，根据项目类型和名称构建路径
            old_path = os.path.join(USER_TEMPLATES_DIR, old_project_type, f"{original_name}.Dockerfile")
        
        # 确保旧文件存在
        if not os.path.exists(old_path):
            raise HTTPException(status_code=404, detail=f"模板文件不存在: {old_path}")

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
        OperationLogger.log(
            username,
            "template_update",
            {
                "name": name,
                "original_name": original_name,
                "project_type": request.project_type,
            },
        )

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
        OperationLogger.log(
            username,
            "template_delete",
            {"name": name, "project_type": request.project_type},
        )

        return JSONResponse({"message": "模板删除成功", "name": name})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除模板失败: {str(e)}")


# === Docker 管理相关 ===
@router.get("/docker/info")
async def get_docker_info(force_refresh: bool = Query(False, description="是否强制刷新缓存")):
    """获取 Docker 服务信息（带30分钟缓存）"""
    try:
        from backend.docker_info_cache import docker_info_cache
        
        # 使用缓存获取Docker信息
        info = docker_info_cache.get_docker_info(force_refresh=force_refresh)
        
        # 添加缓存年龄信息
        cache_age = docker_info_cache.get_cache_age()
        if cache_age is not None:
            info["cache_age_seconds"] = int(cache_age)
            info["cache_age_minutes"] = round(cache_age / 60, 1)
        
        return JSONResponse(info)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取Docker信息失败: {str(e)}")


@router.post("/docker/info/refresh")
async def refresh_docker_info(request: Request):
    """强制刷新Docker信息缓存"""
    try:
        username = get_current_username(request)
        from backend.docker_info_cache import docker_info_cache
        
        # 强制刷新缓存
        info = docker_info_cache.refresh_cache()
        
        # 记录操作日志
        OperationLogger.log(
            username,
            "docker_info_refresh",
            {"cache_age_seconds": docker_info_cache.get_cache_age() or 0}
        )
        
        cache_age = docker_info_cache.get_cache_age()
        if cache_age is not None:
            info["cache_age_seconds"] = int(cache_age)
            info["cache_age_minutes"] = round(cache_age / 60, 1)
        
        return JSONResponse({
            "success": True,
            "message": "Docker信息已刷新",
            "info": info
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"刷新Docker信息失败: {str(e)}")




@router.get("/docker/images")
async def get_docker_images(
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=1000)
):
    """获取 Docker 镜像列表（支持分页）"""
    try:
        from backend.handlers import docker_builder, DOCKER_AVAILABLE

        if not DOCKER_AVAILABLE or not docker_builder:
            return JSONResponse({"images": [], "total": 0})

        if not hasattr(docker_builder, "client") or not docker_builder.client:
            return JSONResponse({"images": [], "total": 0})

        # 获取镜像列表
        images_data = []
        try:
            images = docker_builder.client.images.list()
            for img in images:
                tags = img.tags
                if not tags:
                    images_data.append(
                        {
                            "id": img.id,
                            "repository": "<none>",
                            "tag": "<none>",
                            "size": img.attrs.get("Size", 0),
                            "created": img.attrs.get("Created", ""),
                        }
                    )
                else:
                    for tag in tags:
                        if ":" in tag:
                            repo, tag_name = tag.rsplit(":", 1)
                        else:
                            repo, tag_name = tag, "latest"
                        images_data.append(
                            {
                                "id": img.id,
                                "repository": repo,
                                "tag": tag_name,
                                "size": img.attrs.get("Size", 0),
                                "created": img.attrs.get("Created", ""),
                            }
                        )
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

        if not hasattr(docker_builder, "client") or not docker_builder.client:
            raise HTTPException(status_code=503, detail="Docker 客户端不可用")

        try:
            docker_builder.client.images.remove(request.image_id, force=True)
            OperationLogger.log(
                username, "docker_image_delete", {"image_id": request.image_id}
            )
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
        space_reclaimed = result.get("SpaceReclaimed", 0)
        OperationLogger.log(
            username, "docker_images_prune", {"space_reclaimed": space_reclaimed}
        )
        return JSONResponse({"space_reclaimed": space_reclaimed})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理镜像失败: {str(e)}")


# === 容器管理 ===
@router.get("/docker/containers")
async def get_docker_containers(
    page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=1000)
):
    """获取容器列表（支持分页）"""
    try:
        from backend.handlers import docker_builder, DOCKER_AVAILABLE

        if not DOCKER_AVAILABLE or not docker_builder:
            return JSONResponse({"containers": [], "total": 0})

        if not hasattr(docker_builder, "client") or not docker_builder.client:
            return JSONResponse({"containers": [], "total": 0})

        containers_data = []
        try:
            containers = docker_builder.client.containers.list(all=True)
            for c in containers:
                # 解析端口映射
                ports_str = ""
                try:
                    ports = c.attrs.get("NetworkSettings", {}).get("Ports", {}) or {}
                    port_list = []
                    for container_port, host_bindings in ports.items():
                        if host_bindings:
                            for binding in host_bindings:
                                host_port = binding.get("HostPort", "")
                                if host_port:
                                    port_list.append(f"{host_port}->{container_port}")
                        else:
                            port_list.append(container_port)
                    ports_str = ", ".join(port_list[:3])  # 最多显示3个
                    if len(port_list) > 3:
                        ports_str += f" (+{len(port_list)-3})"
                except:
                    pass

                containers_data.append(
                    {
                        "id": c.id,
                        "name": c.name,
                        "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                        "status": c.status,
                        "state": c.attrs.get("State", {}).get("Status", "unknown"),
                        "created": c.attrs.get("Created", ""),
                        "ports": ports_str,
                    }
                )
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
        OperationLogger.log(
            username, "docker_container_start", {"container_id": container_id}
        )
        return JSONResponse({"message": "容器已启动"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动容器失败: {str(e)}")


@router.post("/docker/containers/{container_id}/stop")
async def stop_container(
    container_id: str, http_request: Request, force: bool = Query(False)
):
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
        OperationLogger.log(
            username,
            "docker_container_stop",
            {"container_id": container_id, "force": force},
        )
        return JSONResponse(
            {"message": "容器已停止" if not force else "容器已强制停止"}
        )
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
        OperationLogger.log(
            username, "docker_container_restart", {"container_id": container_id}
        )
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
        OperationLogger.log(
            username, "docker_container_remove", {"container_id": container_id}
        )
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
        deleted = len(result.get("ContainersDeleted", []) or [])
        OperationLogger.log(username, "docker_containers_prune", {"deleted": deleted})
        return JSONResponse({"deleted": deleted})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理容器失败: {str(e)}")


# === 流水线管理 ===
from backend.pipeline_manager import PipelineManager

# === Git 数据源管理 ===
from backend.git_source_manager import GitSourceManager


class CreatePipelineRequest(BaseModel):
    name: str
    git_url: Optional[str] = None  # 如果提供了 source_id，git_url 可以从数据源获取
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
    dockerfile_name: str = "Dockerfile"  # Dockerfile文件名，默认Dockerfile
    webhook_secret: Optional[str] = None
    webhook_token: Optional[str] = None  # Webhook token（如果为空则自动生成）
    enabled: bool = True
    description: str = ""
    cron_expression: Optional[str] = None
    webhook_branch_filter: bool = False
    webhook_use_push_branch: bool = True
    webhook_allowed_branches: Optional[list] = None  # 允许触发的分支列表
    branch_tag_mapping: Optional[dict] = (
        None  # 分支到标签的映射，如 {"main": "latest", "dev": "dev"}
    )
    source_id: Optional[str] = None  # Git 数据源 ID（可选）
    selected_services: Optional[list] = None  # 选中的服务列表（多服务构建时使用）
    service_push_config: Optional[dict] = (
        None  # 每个服务的推送配置（key为服务名，value为是否推送）
    )
    service_template_params: Optional[dict] = None  # 服务模板参数
    push_mode: Optional[str] = (
        "multi"  # 推送模式：'single' 单一推送，'multi' 多阶段推送
    )
    resource_package_configs: Optional[list] = None  # 资源包配置列表


class RunPipelineRequest(BaseModel):
    """手动触发流水线请求"""

    branch: Optional[str] = None  # 指定构建分支（如果提供则覆盖流水线配置）


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
    dockerfile_name: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_token: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    webhook_branch_filter: Optional[bool] = None
    webhook_use_push_branch: Optional[bool] = None
    webhook_allowed_branches: Optional[list] = None
    branch_tag_mapping: Optional[dict] = None
    source_id: Optional[str] = None
    selected_services: Optional[list] = None
    service_push_config: Optional[dict] = None
    service_template_params: Optional[dict] = None
    push_mode: Optional[str] = None
    resource_package_configs: Optional[list] = None


@router.post("/pipelines")
async def create_pipeline(request: CreatePipelineRequest, http_request: Request):
    """创建流水线配置"""
    try:
        username = get_current_username(http_request)
        manager = PipelineManager()

        # 如果提供了 source_id，从数据源获取 git_url 和 branch
        git_url = request.git_url
        branch = request.branch

        if request.source_id:
            from backend.git_source_manager import GitSourceManager

            source_manager = GitSourceManager()
            source = source_manager.get_source(
                request.source_id, include_password=False
            )
            if source:
                # 如果提供了 source_id，优先使用数据源的 git_url
                if source.get("git_url"):
                    git_url = source["git_url"]
                # 如果没有指定分支，使用数据源的默认分支
                if not branch and source.get("default_branch"):
                    branch = source["default_branch"]
            else:
                raise HTTPException(
                    status_code=404, detail=f"数据源不存在: {request.source_id}"
                )

        # 验证：如果没有 source_id 也没有 git_url，则报错
        if not request.source_id and not git_url:
            raise HTTPException(status_code=400, detail="必须提供 git_url 或 source_id")

        pipeline_id = manager.create_pipeline(
            name=request.name,
            git_url=git_url,
            branch=branch,
            project_type=request.project_type,
            template=request.template,
            image_name=request.image_name,
            tag=request.tag,
            push=request.push,
            push_registry=request.push_registry,
            template_params=request.template_params,
            sub_path=request.sub_path,
            use_project_dockerfile=request.use_project_dockerfile,
            dockerfile_name=request.dockerfile_name,
            webhook_secret=request.webhook_secret,
            webhook_token=request.webhook_token,
            enabled=request.enabled,
            description=request.description,
            cron_expression=request.cron_expression,
            webhook_branch_filter=request.webhook_branch_filter,
            webhook_use_push_branch=request.webhook_use_push_branch,
            webhook_allowed_branches=request.webhook_allowed_branches,
            branch_tag_mapping=request.branch_tag_mapping,
            source_id=request.source_id,
            selected_services=request.selected_services,
            service_push_config=request.service_push_config,
            service_template_params=request.service_template_params,
            push_mode=request.push_mode or "multi",
            resource_package_configs=request.resource_package_configs,
        )

        # 记录操作日志
        OperationLogger.log(
            username,
            "pipeline_create",
            {
                "pipeline_id": pipeline_id,
                "name": request.name,
                "git_url": request.git_url,
            },
        )

        return JSONResponse({"pipeline_id": pipeline_id, "message": "流水线创建成功"})
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建流水线失败: {str(e)}")


@router.post("/pipelines/json")
async def create_pipeline_from_json(pipeline_data: dict, http_request: Request):
    """通过 JSON 创建流水线（功能与任务中另存为流水线一致）

    接收一个 JSON 对象，包含流水线的所有配置字段。
    字段定义与 CreatePipelineRequest 相同。
    """
    try:
        username = get_current_username(http_request)
        manager = PipelineManager()

        # 验证必填字段
        if not pipeline_data.get("name"):
            raise HTTPException(status_code=400, detail="流水线名称不能为空")

        if not pipeline_data.get("git_url") and not pipeline_data.get("source_id"):
            raise HTTPException(status_code=400, detail="必须提供 git_url 或 source_id")

        # 如果提供了 source_id，从数据源获取 git_url 和 branch
        git_url = pipeline_data.get("git_url")
        branch = pipeline_data.get("branch")

        if pipeline_data.get("source_id"):
            from backend.git_source_manager import GitSourceManager

            source_manager = GitSourceManager()
            source = source_manager.get_source(
                pipeline_data["source_id"], include_password=False
            )
            if source:
                # 如果提供了 source_id，优先使用数据源的 git_url
                if source.get("git_url"):
                    git_url = source["git_url"]
                # 如果没有指定分支，使用数据源的默认分支
                if not branch and source.get("default_branch"):
                    branch = source["default_branch"]
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"数据源不存在: {pipeline_data['source_id']}",
                )

        # 创建流水线（使用与 create_pipeline 相同的逻辑）
        pipeline_id = manager.create_pipeline(
            name=pipeline_data["name"],
            git_url=git_url,
            branch=branch,
            project_type=pipeline_data.get("project_type", "jar"),
            template=pipeline_data.get("template"),
            image_name=pipeline_data.get("image_name"),
            tag=pipeline_data.get("tag", "latest"),
            push=pipeline_data.get("push", False),
            push_registry=pipeline_data.get("push_registry"),
            template_params=pipeline_data.get("template_params"),
            sub_path=pipeline_data.get("sub_path"),
            use_project_dockerfile=pipeline_data.get("use_project_dockerfile", True),
            dockerfile_name=pipeline_data.get("dockerfile_name", "Dockerfile"),
            webhook_secret=pipeline_data.get("webhook_secret"),
            webhook_token=pipeline_data.get("webhook_token"),
            enabled=pipeline_data.get("enabled", True),
            description=pipeline_data.get("description", ""),
            cron_expression=pipeline_data.get("cron_expression"),
            webhook_branch_filter=pipeline_data.get("webhook_branch_filter", False),
            webhook_use_push_branch=pipeline_data.get("webhook_use_push_branch", True),
            branch_tag_mapping=pipeline_data.get("branch_tag_mapping"),
            source_id=pipeline_data.get("source_id"),
            selected_services=pipeline_data.get("selected_services"),
            service_push_config=pipeline_data.get("service_push_config"),
            service_template_params=pipeline_data.get("service_template_params"),
            push_mode=pipeline_data.get("push_mode", "multi"),
            resource_package_configs=pipeline_data.get("resource_package_configs"),
        )

        # 记录操作日志
        OperationLogger.log(
            username,
            "pipeline_create",
            {
                "pipeline_id": pipeline_id,
                "name": pipeline_data["name"],
                "git_url": git_url,
                "source": "json",
            },
        )

        return JSONResponse(
            {
                "pipeline_id": pipeline_id,
                "message": "流水线创建成功",
                "data": {
                    "pipeline_id": pipeline_id,
                    "name": pipeline_data["name"],
                },
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建流水线失败: {str(e)}")


@router.get("/pipelines")
async def list_pipelines(
    enabled: Optional[bool] = Query(None, description="过滤启用状态")
):
    """获取流水线列表"""
    try:
        manager = PipelineManager()
        pipelines = manager.list_pipelines(enabled=enabled)

        # 为每个流水线添加当前任务状态和最后一次构建状态
        build_manager = BuildManager()

        # 优化：只查询一次所有任务，然后在内存中过滤（避免重复查询数据库）
        try:
            all_tasks = build_manager.task_manager.list_tasks(
                task_type="build_from_source"
            )
        except Exception as e:
            print(f"⚠️ 查询任务列表失败: {e}")
            import traceback

            traceback.print_exc()
            # 如果查询任务失败，使用空列表继续处理
            all_tasks = []

        # 确保 pipelines 是列表
        if not isinstance(pipelines, list):
            print(f"⚠️ pipelines 不是列表类型: {type(pipelines)}")
            pipelines = []

        # 按 pipeline_id 分组任务，提高查找效率
        tasks_by_pipeline = {}
        for task in all_tasks:
            task_pipeline_id = task.get("pipeline_id")
            if task_pipeline_id:
                if task_pipeline_id not in tasks_by_pipeline:
                    tasks_by_pipeline[task_pipeline_id] = []
                tasks_by_pipeline[task_pipeline_id].append(task)

        for pipeline in pipelines:
            pipeline_id = pipeline.get("pipeline_id")
            if not pipeline_id:
                # 如果流水线没有ID，跳过处理
                pipeline["last_build"] = None
                pipeline["last_build_success"] = None
                pipeline["success_count"] = 0
                pipeline["failed_count"] = 0
                pipeline["queue_length"] = 0
                pipeline["has_queued_tasks"] = False
                continue

            # 获取当前正在运行的任务
            task_id = pipeline.get("current_task_id")
            if task_id:
                try:
                    task = build_manager.task_manager.get_task(task_id)
                    if task:
                        pipeline["current_task_status"] = task.get("status")
                        pipeline["current_task_info"] = {
                            "task_id": task_id,
                            "status": task.get("status"),
                            "created_at": task.get("created_at"),
                            "image": task.get("image"),
                            "tag": task.get("tag"),
                        }
                    else:
                        # 任务不存在，清除绑定
                        manager.unbind_task(pipeline_id)
                        pipeline["current_task_id"] = None
                except Exception as e:
                    # 如果获取任务失败，清除绑定
                    print(f"⚠️ 获取任务 {task_id} 失败: {e}")
                    manager.unbind_task(pipeline_id)
                    pipeline["current_task_id"] = None

            # 从分组后的任务中查找该流水线的任务
            pipeline_tasks = tasks_by_pipeline.get(pipeline_id, [])
            last_task = None
            success_count = 0
            failed_count = 0

            for task in pipeline_tasks:
                # 统计成功和失败数量
                task_status = task.get("status")
                if task_status == "completed":
                    success_count += 1
                elif task_status == "failed":
                    failed_count += 1

                # 查找所有状态的任务，取最新的一个
                task_created_at = task.get("created_at", "")
                if not last_task or (
                    task_created_at
                    and task_created_at > last_task.get("created_at", "")
                ):
                    last_task = task

            # 添加最后一次构建信息（包含所有状态）
            if last_task:
                pipeline["last_build"] = {
                    "task_id": last_task.get("task_id"),
                    "status": last_task.get("status"),
                    "created_at": last_task.get("created_at"),
                    "completed_at": last_task.get("completed_at"),
                    "image": last_task.get("image"),
                    "tag": last_task.get("tag"),
                    "error": last_task.get("error"),
                }
                # 添加一个便捷的成功状态字段（仅对已完成的任务）
                pipeline["last_build_success"] = last_task.get("status") == "completed"
            else:
                pipeline["last_build"] = None
                pipeline["last_build_success"] = None

            # 添加成功/失败统计
            pipeline["success_count"] = success_count
            pipeline["failed_count"] = failed_count

            # 添加队列信息
            try:
                queue_length = manager.get_queue_length(pipeline_id)
                pipeline["queue_length"] = queue_length
                pipeline["has_queued_tasks"] = queue_length > 0
            except Exception as e:
                print(f"⚠️ 获取流水线 {pipeline_id} 队列长度失败: {e}")
                pipeline["queue_length"] = 0
                pipeline["has_queued_tasks"] = False

        return JSONResponse({"pipelines": pipelines, "total": len(pipelines)})
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        print(f"❌ 获取流水线列表失败: {e}")
        print(f"错误详情:\n{error_detail}")
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


@router.get("/pipelines/{pipeline_id}/tasks")
async def get_pipeline_tasks(
    pipeline_id: str,
    status: Optional[str] = Query(None, description="过滤任务状态"),
    limit: Optional[int] = Query(20, description="每页任务数量", ge=1, le=200),
    offset: Optional[int] = Query(0, description="偏移量（分页）", ge=0),
    trigger_source: Optional[str] = Query(
        None, description="过滤触发来源: webhook, manual, cron"
    ),
):
    """获取流水线关联的所有任务历史记录（支持分页）"""
    try:
        # 获取流水线配置
        manager = PipelineManager()
        pipeline = manager.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="流水线不存在")

        # 从PipelineTaskHistory表获取任务历史
        from backend.models import PipelineTaskHistory
        from backend.database import get_db_session
        from datetime import datetime

        db = get_db_session()
        try:
            history_records = (
                db.query(PipelineTaskHistory)
                .filter(PipelineTaskHistory.pipeline_id == pipeline_id)
                .order_by(PipelineTaskHistory.triggered_at.desc())
                .all()
            )

            # 转换为字典列表
            task_history = []
            for record in history_records:
                task_history.append(
                    {
                        "task_id": record.task_id,
                        "trigger_source": record.trigger_source,
                        "triggered_at": (
                            record.triggered_at.isoformat()
                            if isinstance(record.triggered_at, datetime)
                            else record.triggered_at
                        ),
                        "trigger_info": record.trigger_info or {},
                    }
                )
        finally:
            db.close()

        # 获取所有任务并补充详细信息
        build_manager = BuildManager()
        tasks_with_details = []
        task_ids_from_history = set()  # 用于去重

        # 处理历史记录中的任务
        for history_entry in task_history:
            task_id = history_entry.get("task_id")
            if not task_id:
                continue

            # 应用过滤
            if trigger_source and history_entry.get("trigger_source") != trigger_source:
                continue

            task_ids_from_history.add(task_id)

            # 获取任务详情
            task = build_manager.task_manager.get_task(task_id)
            if not task:
                # 任务不存在，但保留历史记录
                task_info = {
                    "task_id": task_id,
                    "status": "deleted",
                    "created_at": history_entry.get("triggered_at"),
                    "image": "未知",
                    "tag": "未知",
                }
            else:
                # 应用状态过滤
                if status and task.get("status") != status:
                    continue

                task_info = {
                    "task_id": task_id,
                    "status": task.get("status"),
                    "created_at": task.get("created_at"),
                    "completed_at": task.get("completed_at"),
                    "image": task.get("image"),
                    "tag": task.get("tag"),
                    "error": task.get("error"),
                }

            # 合并历史记录信息
            task_info.update(
                {
                    "trigger_source": history_entry.get("trigger_source"),
                    "triggered_at": history_entry.get("triggered_at"),
                    "trigger_info": history_entry.get("trigger_info", {}),
                }
            )

            tasks_with_details.append(task_info)

        # 从任务表中查询所有关联该流水线的任务（补充历史记录中没有的任务）
        all_tasks = build_manager.task_manager.list_tasks(task_type="build_from_source")
        for task in all_tasks:
            task_pipeline_id = task.get("pipeline_id")
            if task_pipeline_id == pipeline_id:
                task_id = task.get("task_id")
                # 如果任务不在历史记录中，添加到结果中
                if task_id and task_id not in task_ids_from_history:
                    # 应用状态过滤
                    if status and task.get("status") != status:
                        continue

                    # 应用触发来源过滤（如果没有trigger_source，默认为unknown）
                    task_trigger_source = task.get("trigger_source", "unknown")
                    if trigger_source and task_trigger_source != trigger_source:
                        continue

                    task_info = {
                        "task_id": task_id,
                        "status": task.get("status"),
                        "created_at": task.get("created_at"),
                        "completed_at": task.get("completed_at"),
                        "image": task.get("image"),
                        "tag": task.get("tag"),
                        "error": task.get("error"),
                        "trigger_source": task_trigger_source,
                        "triggered_at": task.get(
                            "created_at"
                        ),  # 使用创建时间作为触发时间
                        "trigger_info": task.get("trigger_info", {}),
                    }
                    tasks_with_details.append(task_info)

        # 按触发时间倒序排列
        tasks_with_details.sort(key=lambda x: x.get("triggered_at", ""), reverse=True)

        # 计算总数（过滤后）
        total = len(tasks_with_details)

        # 应用分页
        paginated_tasks = tasks_with_details[offset : offset + limit]

        return JSONResponse(
            {
                "tasks": paginated_tasks,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total,
                "pipeline_id": pipeline_id,
                "pipeline_name": pipeline.get("name"),
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取流水线任务失败: {str(e)}")


@router.put("/pipelines/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str, request: UpdatePipelineRequest, http_request: Request
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
            dockerfile_name=request.dockerfile_name,
            webhook_secret=request.webhook_secret,
            webhook_token=request.webhook_token,
            enabled=request.enabled,
            description=request.description,
            cron_expression=request.cron_expression,
            webhook_branch_filter=request.webhook_branch_filter,
            webhook_use_push_branch=request.webhook_use_push_branch,
            webhook_allowed_branches=request.webhook_allowed_branches,
            branch_tag_mapping=request.branch_tag_mapping,
            source_id=request.source_id,
            selected_services=request.selected_services,
            service_push_config=request.service_push_config,
            service_template_params=request.service_template_params,
            push_mode=request.push_mode,
            resource_package_configs=request.resource_package_configs,
        )

        if not success:
            raise HTTPException(status_code=404, detail="流水线不存在")

        # 记录操作日志
        OperationLogger.log(username, "pipeline_update", {"pipeline_id": pipeline_id})

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
        OperationLogger.log(username, "pipeline_delete", {"pipeline_id": pipeline_id})

        return JSONResponse({"message": "流水线已删除"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除流水线失败: {str(e)}")


@router.post("/pipelines/{pipeline_id}/run")
async def run_pipeline(
    pipeline_id: str,
    request: Optional[RunPipelineRequest] = Body(None),
    http_request: Request = None,
):
    """手动触发流水线执行"""
    try:
        username = get_current_username(http_request)
        manager = PipelineManager()

        # 获取流水线配置
        pipeline = manager.get_pipeline(pipeline_id)
        if not pipeline:
            raise HTTPException(status_code=404, detail="流水线不存在")

        # 获取请求中的分支参数（如果提供则覆盖流水线配置）
        # 如果请求体存在且有branch字段，使用请求的分支；否则使用流水线配置的分支
        selected_branch = None
        if request:
            # 检查请求对象是否有branch属性
            if hasattr(request, "branch"):
                selected_branch = request.branch
                # 如果branch是空字符串，也视为有效（表示使用默认分支）
                if selected_branch == "":
                    selected_branch = None
        final_branch = (
            selected_branch if selected_branch is not None else pipeline.get("branch")
        )

        # 调试日志 - 详细输出
        print(f"🔍 手动触发流水线 {pipeline_id}:")
        print(f"   - 请求对象类型: {type(request)}")
        print(f"   - 请求对象: {request}")
        if request:
            print(f"   - 请求对象属性: {dir(request)}")
            if hasattr(request, "branch"):
                print(f"   - request.branch值: {repr(request.branch)}")
                print(f"   - request.branch类型: {type(request.branch)}")
        print(f"   - selected_branch: {repr(selected_branch)}")
        print(f"   - selected_branch类型: {type(selected_branch)}")
        print(f"   - 配置分支: {repr(pipeline.get('branch'))}")
        print(f"   - 配置分支类型: {type(pipeline.get('branch'))}")
        print(f"   - 最终分支: {repr(final_branch)}")
        print(f"   - 最终分支类型: {type(final_branch)}")
        print(
            f"   - selected_branch == pipeline.get('branch'): {selected_branch == pipeline.get('branch')}"
        )
        print(f"   - selected_branch is not None: {selected_branch is not None}")

        # 处理分支标签映射（与webhook使用相同的逻辑）
        branch_tag_mapping = pipeline.get("branch_tag_mapping", {})
        default_tag = pipeline.get("tag", "latest")  # 默认标签
        
        # 获取标签列表（支持单个标签或多个标签）
        tags = [default_tag]  # 默认只有一个标签
        
        if final_branch and branch_tag_mapping:
            mapped_tag_value = None
            # 优先精确匹配
            if final_branch in branch_tag_mapping:
                mapped_tag_value = branch_tag_mapping[final_branch]
            else:
                # 尝试通配符匹配（如 feature/* -> feature）
                import fnmatch
                
                for pattern, mapped_tag in branch_tag_mapping.items():
                    if fnmatch.fnmatch(final_branch, pattern):
                        mapped_tag_value = mapped_tag
                        break
            
            # 处理标签值（支持字符串、数组或逗号分隔的字符串）
            if mapped_tag_value:
                if isinstance(mapped_tag_value, list):
                    # 如果是数组，直接使用
                    tags = mapped_tag_value
                elif isinstance(mapped_tag_value, str):
                    # 如果是字符串，检查是否包含逗号
                    if "," in mapped_tag_value:
                        # 逗号分隔的多个标签
                        tags = [
                            t.strip() for t in mapped_tag_value.split(",") if t.strip()
                        ]
                    else:
                        # 单个标签
                        tags = [mapped_tag_value]
        
        # 检查防抖（5秒内重复触发直接加入队列）
        if manager.check_debounce(pipeline_id, debounce_seconds=5):
            from backend.handlers import pipeline_to_task_config
            
            build_manager = BuildManager()
            task_ids = []
            
            # 为每个标签创建任务
            for tag in tags:
                task_config = pipeline_to_task_config(
                    pipeline,
                    trigger_source="manual",
                    branch=final_branch,
                    tag=tag,
                    branch_tag_mapping=branch_tag_mapping,
                )
                task_config["username"] = username
                task_id = build_manager._trigger_task_from_config(task_config)
                task_ids.append(task_id)
            
            queue_length = manager.get_queue_length(pipeline_id)

            OperationLogger.log(
                username,
                "pipeline_run_queued",
                {
                    "pipeline_id": pipeline_id,
                    "pipeline_name": pipeline.get("name"),
                    "task_ids": task_ids if len(task_ids) > 1 else None,
                    "task_id": task_ids[0] if task_ids else None,
                    "queue_length": queue_length,
                    "branch": final_branch,
                    "trigger_source": "manual",
                    "reason": "debounce",
                },
            )

            if len(task_ids) > 1:
                return JSONResponse(
                    {
                        "message": f"触发过于频繁，已创建 {len(task_ids)} 个任务并加入队列",
                        "status": "queued",
                        "task_id": task_ids[0] if task_ids else None,
                        "task_ids": task_ids if len(task_ids) > 1 else None,
                        "queue_length": queue_length,
                        "pipeline": pipeline.get("name"),
                        "branch": final_branch,
                    }
                )
            else:
                return JSONResponse(
                    {
                        "message": "触发过于频繁，任务已加入队列",
                        "status": "queued",
                        "task_id": task_ids[0] if task_ids else None,
                        "queue_length": queue_length,
                        "pipeline": pipeline.get("name"),
                        "branch": final_branch,
                    }
                )

        # 处理分支标签映射（与webhook使用相同的逻辑）
        branch_tag_mapping = pipeline.get("branch_tag_mapping", {})
        default_tag = pipeline.get("tag", "latest")  # 默认标签
        
        # 获取标签列表（支持单个标签或多个标签）
        tags = [default_tag]  # 默认只有一个标签
        
        if final_branch and branch_tag_mapping:
            mapped_tag_value = None
            # 优先精确匹配
            if final_branch in branch_tag_mapping:
                mapped_tag_value = branch_tag_mapping[final_branch]
            else:
                # 尝试通配符匹配（如 feature/* -> feature）
                import fnmatch
                
                for pattern, mapped_tag in branch_tag_mapping.items():
                    if fnmatch.fnmatch(final_branch, pattern):
                        mapped_tag_value = mapped_tag
                        break
            
            # 处理标签值（支持字符串、数组或逗号分隔的字符串）
            if mapped_tag_value:
                if isinstance(mapped_tag_value, list):
                    # 如果是数组，直接使用
                    tags = mapped_tag_value
                elif isinstance(mapped_tag_value, str):
                    # 如果是字符串，检查是否包含逗号
                    if "," in mapped_tag_value:
                        # 逗号分隔的多个标签
                        tags = [
                            t.strip() for t in mapped_tag_value.split(",") if t.strip()
                        ]
                    else:
                        # 单个标签
                        tags = [mapped_tag_value]
        
        # 为每个标签创建任务（与webhook使用相同的逻辑）
        from backend.handlers import pipeline_to_task_config
        
        build_manager = BuildManager()
        task_ids = []
        
        for tag in tags:
            print(f"🔍 调用 pipeline_to_task_config:")
            print(f"   - branch 参数: {final_branch}")
            print(f"   - tag 参数: {tag}")
            task_config = pipeline_to_task_config(
                pipeline,
                trigger_source="manual",
                branch=final_branch,
                tag=tag,
                branch_tag_mapping=branch_tag_mapping,
            )
            task_config["username"] = username
            
            # 检查是否有正在运行的任务
            current_task_id = manager.get_pipeline_running_task(pipeline_id)
            if current_task_id:
                # 检查任务是否真的在运行
                task = build_manager.task_manager.get_task(current_task_id)
                if task and task.get("status") in ["pending", "running"]:
                    # 有任务正在运行，立即创建新任务（状态为 pending，等待执行）
                    task_id = build_manager._trigger_task_from_config(task_config)
                    task_ids.append(task_id)
                else:
                    # 任务已完成或不存在，解绑
                    manager.unbind_task(pipeline_id)
                    # 没有运行中的任务，立即启动构建任务
                    task_id = build_manager._trigger_task_from_config(task_config)
                    task_ids.append(task_id)
            else:
                # 没有运行中的任务，立即启动构建任务
                task_id = build_manager._trigger_task_from_config(task_config)
                task_ids.append(task_id)
        
        # 如果创建了多个任务，只绑定第一个任务
        if task_ids:
            first_task_id = task_ids[0]
            
            # 记录触发并绑定任务（手动触发）
            manager.record_trigger(
                pipeline_id,
                first_task_id,
                trigger_source="manual",
                trigger_info={
                    "username": username,
                    "branch": final_branch,
                },
            )
            
            # 记录操作日志
            OperationLogger.log(
                username,
                "pipeline_run" if len(task_ids) == 1 else "pipeline_run_queued",
                {
                    "pipeline_id": pipeline_id,
                    "pipeline_name": pipeline.get("name"),
                    "task_id": first_task_id,
                    "task_ids": task_ids if len(task_ids) > 1 else None,
                    "branch": final_branch,
                    "trigger_source": "manual",
                },
            )
            
            queue_length = manager.get_queue_length(pipeline_id)
            
            if len(task_ids) > 1:
                return JSONResponse(
                    {
                        "message": f"构建任务已启动（共 {len(task_ids)} 个任务）",
                        "status": "running",
                        "task_id": first_task_id,
                        "task_ids": task_ids,
                        "queue_length": queue_length,
                        "pipeline": pipeline.get("name"),
                        "branch": final_branch,
                    }
                )
            else:
                return JSONResponse(
                    {
                        "message": "构建任务已启动",
                        "status": "running",
                        "task_id": first_task_id,
                        "pipeline": pipeline.get("name"),
                        "branch": final_branch,
                    }
                )
        else:
            raise HTTPException(status_code=500, detail="未能创建构建任务")
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
        # 调试：打印所有请求头
        print(f"🔍 Webhook 请求头:")
        for key, value in request.headers.items():
            print(f"  {key}: {value}")

        # 获取请求体（原始字节）
        body = await request.body()
        print(f"📦 请求体大小: {len(body)} bytes")

        # 获取流水线配置
        manager = PipelineManager()
        pipeline = manager.get_pipeline_by_token(webhook_token)

        if not pipeline:
            print(f"❌ 未找到流水线: webhook_token={webhook_token}")
            raise HTTPException(status_code=404, detail="流水线不存在")

        print(
            f"✅ 找到流水线: {pipeline.get('name')} (pipeline_id={pipeline.get('pipeline_id')})"
        )

        if not pipeline.get("enabled", False):
            print(f"❌ 流水线已禁用: {pipeline.get('name')}")
            raise HTTPException(status_code=403, detail="流水线已禁用")

        # 检查是否是 Gitee ping 事件（测试请求）
        # FastAPI/Starlette 会将 header 名称标准化为小写
        gitee_ping = request.headers.get("x-gitee-ping", "")
        print(f"🔍 X-Gitee-Ping: {gitee_ping}")
        if gitee_ping and gitee_ping.lower() == "true":
            print(f"✅ Gitee Ping 测试请求: pipeline={pipeline.get('name')}")
            return JSONResponse(
                {
                    "message": "Webhook 配置正确",
                    "pipeline": pipeline.get("name"),
                    "status": "ok",
                }
            )

        # 验证 Webhook 签名（可选）
        webhook_secret = pipeline.get("webhook_secret")
        if webhook_secret:
            # 如果配置了 secret，则尝试验证签名
            signature_verified = False
            signature_found = False

            # GitHub: X-Hub-Signature-256 或 X-Hub-Signature
            if "x-hub-signature-256" in request.headers:
                signature = request.headers["x-hub-signature-256"]
                signature_found = True
                signature_verified = manager.verify_webhook_signature(
                    body, signature, webhook_secret, "sha256"
                )
            elif "x-hub-signature" in request.headers:
                signature = request.headers["x-hub-signature"]
                signature_found = True
                signature_verified = manager.verify_webhook_signature(
                    body, signature, webhook_secret, "sha1"
                )
            # GitLab: X-Gitlab-Token
            elif "x-gitlab-token" in request.headers:
                gitlab_token = request.headers["x-gitlab-token"]
                signature_found = True
                signature_verified = gitlab_token == webhook_secret
            # Gitee: X-Gitee-Token
            elif "x-gitee-token" in request.headers:
                gitee_token = request.headers["x-gitee-token"]
                print(
                    f"🔍 X-Gitee-Token: '{gitee_token}' (长度: {len(gitee_token) if gitee_token else 0})"
                )
                # 只有当 token 不为空时才进行验证
                if gitee_token and gitee_token.strip():
                    signature_found = True
                    signature_verified = gitee_token == webhook_secret
                    print(
                        f"🔍 Token 验证: found={signature_found}, verified={signature_verified}"
                    )
                else:
                    # 如果 token 为空，说明 Gitee 没有配置密码，跳过验证
                    print(f"⚠️ Gitee Token 为空，跳过验证")

            # 如果提供了签名但验证失败，则拒绝请求
            if signature_found and not signature_verified:
                print(f"❌ Webhook 签名验证失败: pipeline={pipeline.get('name')}")
                raise HTTPException(status_code=403, detail="Webhook 签名验证失败")

            # 如果没有提供签名，警告但允许通过（容错处理）
            if not signature_found:
                print(
                    f"⚠️ Webhook 请求未提供签名，但配置了 secret，允许通过: pipeline={pipeline.get('name')}"
                )
            else:
                print(f"✅ Webhook 签名验证通过: pipeline={pipeline.get('name')}")
        else:
            # 没有配置 secret，直接允许通过
            print(
                f"🔓 Webhook 未配置签名验证，直接允许通过: pipeline={pipeline.get('name')}"
            )

        # 解析 Webhook 负载（尝试解析 JSON）
        try:
            payload = json.loads(body.decode("utf-8"))
        except:
            payload = {}

        # 提取分支信息（不同平台格式不同）
        webhook_branch = None
        # GitHub: ref = refs/heads/main
        if "ref" in payload:
            ref = payload["ref"]
            print(f"🔍 Webhook ref 字段: {ref}")
            if ref.startswith("refs/heads/"):
                webhook_branch = ref.replace("refs/heads/", "")
                print(f"✅ 从 refs/heads/ 提取分支: {webhook_branch}")
        # GitLab: ref = main (可能已经是分支名)
        if not webhook_branch and "ref" in payload:
            ref = payload["ref"]
            if not ref.startswith("refs/"):
                webhook_branch = ref
                print(f"✅ 从 ref 直接提取分支: {webhook_branch}")
        # Gitee: ref = refs/heads/main (已在上面处理)
        if webhook_branch:
            print(f"📌 提取的 webhook_branch: {webhook_branch}")
        else:
            print(f"⚠️ 未能从 payload 中提取分支信息")

        # 统一分支策略处理（与手动触发保持一致）
        # 支持新的webhook_branch_strategy字段，同时兼容旧的webhook_branch_filter和webhook_use_push_branch字段
        webhook_branch_strategy = pipeline.get("webhook_branch_strategy")
        webhook_allowed_branches = pipeline.get("webhook_allowed_branches", [])
        webhook_branch_filter = pipeline.get("webhook_branch_filter", False)
        webhook_use_push_branch = pipeline.get("webhook_use_push_branch", True)
        configured_branch = pipeline.get("branch")

        # 如果没有新策略字段，根据旧字段推断策略
        if not webhook_branch_strategy:
            if webhook_allowed_branches and len(webhook_allowed_branches) > 0:
                webhook_branch_strategy = "select_branches"
            elif webhook_branch_filter:
                webhook_branch_strategy = "filter_match"
            elif webhook_use_push_branch:
                webhook_branch_strategy = "use_push"
            else:
                webhook_branch_strategy = "use_configured"

        # 调试信息：输出配置值
        print(f"🔍 Webhook 分支配置:")
        print(f"   - webhook_branch_strategy: {webhook_branch_strategy}")
        print(f"   - webhook_allowed_branches: {webhook_allowed_branches}")
        print(f"   - configured_branch: {configured_branch}")
        print(f"   - webhook_branch: {webhook_branch}")

        # 根据分支策略确定使用的分支（统一逻辑）
        branch = None
        if webhook_branch_strategy == "select_branches":
            # 选择分支触发策略：只允许匹配的分支触发
            if webhook_branch:
                if webhook_branch in webhook_allowed_branches:
                    branch = webhook_branch
                    print(f"✅ 分支在允许列表中，使用推送分支: {branch}")
                else:
                    print(f"⚠️ 分支不在允许列表中，忽略触发: webhook_branch={webhook_branch}, allowed={webhook_allowed_branches}")
                    return JSONResponse(
                        {
                            "message": f"分支不在允许列表中，已忽略触发（推送分支: {webhook_branch}）",
                            "pipeline": pipeline.get("name"),
                            "webhook_branch": webhook_branch,
                            "allowed_branches": webhook_allowed_branches,
                            "ignored": True,
                        }
                    )
            else:
                # Webhook未提供分支信息，使用配置的分支
                branch = configured_branch
                print(f"⚠️ Webhook未提供分支信息，使用配置分支: {branch}")
        elif webhook_branch_strategy == "filter_match":
            # 只允许匹配分支触发：检查推送分支是否匹配配置分支
            if webhook_branch:
                if webhook_branch == configured_branch:
                    branch = webhook_branch
                    print(f"✅ 分支匹配，使用推送分支: {branch}")
                else:
                    print(f"⚠️ 分支不匹配，忽略触发: webhook_branch={webhook_branch}, configured={configured_branch}")
                    return JSONResponse(
                        {
                            "message": f"分支不匹配，已忽略触发（推送分支: {webhook_branch}, 配置分支: {configured_branch}）",
                            "pipeline": pipeline.get("name"),
                            "webhook_branch": webhook_branch,
                            "configured_branch": configured_branch,
                            "ignored": True,
                        }
                    )
            else:
                # Webhook未提供分支信息，使用配置的分支
                branch = configured_branch
                print(f"⚠️ Webhook未提供分支信息，使用配置分支: {branch}")
        elif webhook_branch_strategy == "use_push":
            # 使用推送分支构建：优先使用webhook推送的分支
            if webhook_branch:
                branch = webhook_branch
                print(f"✅ 使用推送分支构建: {branch}")
            else:
                # Webhook未提供分支信息，使用配置的分支
                branch = configured_branch
                print(f"⚠️ Webhook未提供分支信息，使用配置分支: {branch}")
        else:  # use_configured
            # 使用配置分支构建：始终使用配置的分支
            branch = configured_branch
            print(f"✅ 使用配置分支构建: {branch}")

        # 如果最终没有确定分支，报错
        if not branch:
            print(f"❌ 无法触发构建: pipeline={pipeline.get('name')}, 无法确定分支")
            return JSONResponse(
                {
                    "message": "无法触发构建：无法确定分支",
                    "pipeline": pipeline.get("name"),
                    "error": "missing_branch",
                },
                status_code=400,
            )

        # 根据推送的分支查找对应的标签（分支标签映射应该基于推送的分支，而不是用于构建的分支）
        branch_tag_mapping = pipeline.get("branch_tag_mapping", {})
        default_tag = pipeline.get("tag", "latest")  # 默认标签

        # 调试信息：输出最终确定的分支
        print(f"🔍 最终确定的分支: {branch}")
        print(f"   - webhook_branch: {webhook_branch}")
        print(f"   - configured_branch: {configured_branch}")
        print(f"   - 最终使用的 branch: {branch}")

        # 使用webhook推送的分支来查找标签映射（如果有的话）
        branch_for_tag_mapping = webhook_branch if webhook_branch else branch

        # 获取标签列表（支持单个标签或多个标签）
        tags = [default_tag]  # 默认只有一个标签

        if branch_for_tag_mapping and branch_tag_mapping:
            mapped_tag_value = None
            # 优先精确匹配
            if branch_for_tag_mapping in branch_tag_mapping:
                mapped_tag_value = branch_tag_mapping[branch_for_tag_mapping]
            else:
                # 尝试通配符匹配（如 feature/* -> feature）
                import fnmatch

                for pattern, mapped_tag in branch_tag_mapping.items():
                    if fnmatch.fnmatch(branch_for_tag_mapping, pattern):
                        mapped_tag_value = mapped_tag
                        break

            # 处理标签值（支持字符串、数组或逗号分隔的字符串）
            if mapped_tag_value:
                if isinstance(mapped_tag_value, list):
                    # 如果是数组，直接使用
                    tags = mapped_tag_value
                elif isinstance(mapped_tag_value, str):
                    # 如果是字符串，检查是否包含逗号
                    if "," in mapped_tag_value:
                        # 逗号分隔的多个标签
                        tags = [
                            t.strip() for t in mapped_tag_value.split(",") if t.strip()
                        ]
                    else:
                        # 单个标签
                        tags = [mapped_tag_value]

        # 为每个标签创建任务
        from backend.handlers import pipeline_to_task_config

        build_manager = BuildManager()
        pipeline_id = pipeline["pipeline_id"]
        task_ids = []

        # 检查防抖（5秒内重复触发直接创建任务，状态为 pending）
        is_debounced = manager.check_debounce(pipeline_id, debounce_seconds=5)

        for tag in tags:
            print(f"🔍 调用 pipeline_to_task_config:")
            print(f"   - branch 参数: {branch}")
            print(f"   - webhook_branch 参数: {webhook_branch}")
            print(f"   - tag 参数: {tag}")
            task_config = pipeline_to_task_config(
                pipeline,
                trigger_source="webhook",
                branch=branch,
                tag=tag,
                webhook_branch=webhook_branch,
                branch_tag_mapping=branch_tag_mapping,
            )
            print(
                f"🔍 pipeline_to_task_config 返回的 task_config.branch: {task_config.get('branch')}"
            )

            if is_debounced:
                task_id = build_manager._trigger_task_from_config(task_config)
                task_ids.append(task_id)

        queue_length = manager.get_queue_length(pipeline_id)

        # 检查防抖（5秒内重复触发直接创建任务，状态为 pending）
        if is_debounced:
            if len(tags) > 1:
                print(
                    f"⚠️ 流水线 {pipeline.get('name')} 触发过于频繁（防抖），已创建 {len(task_ids)} 个任务（pending）"
                )
            else:
                print(
                    f"⚠️ 流水线 {pipeline.get('name')} 触发过于频繁（防抖），已创建任务（pending）"
                )

            return JSONResponse(
                {
                    "message": (
                        f"触发过于频繁，已创建 {len(task_ids)} 个任务并加入队列"
                        if len(tags) > 1
                        else "触发过于频繁，任务已创建并加入队列"
                    ),
                    "status": "queued",
                    "task_id": task_ids[0] if task_ids else None,
                    "task_ids": task_ids if len(task_ids) > 1 else None,
                    "queue_length": queue_length,
                    "pipeline": pipeline.get("name"),
                }
            )

        # 检查是否有正在运行的任务
        current_task_id = manager.get_pipeline_running_task(pipeline_id)
        if current_task_id:
            # 检查任务是否真的在运行
            task = build_manager.task_manager.get_task(current_task_id)
            if task and task.get("status") in ["pending", "running"]:
                # 有任务正在运行，为每个标签创建新任务（状态为 pending，等待执行）
                queued_task_ids = []
                for tag in tags:
                    task_config = pipeline_to_task_config(
                        pipeline,
                        trigger_source="webhook",
                        branch=branch,
                        tag=tag,
                        webhook_branch=webhook_branch,
                        branch_tag_mapping=branch_tag_mapping,
                    )
                    queued_task_id = build_manager._trigger_task_from_config(
                        task_config
                    )
                    queued_task_ids.append(queued_task_id)

                queue_length = manager.get_queue_length(pipeline_id)

                if len(tags) > 1:
                    print(
                        f"⚠️ 流水线 {pipeline.get('name')} 已有正在执行的任务 {current_task_id[:8]}，已创建 {len(queued_task_ids)} 个新任务（pending）"
                    )
                else:
                    print(
                        f"⚠️ 流水线 {pipeline.get('name')} 已有正在执行的任务 {current_task_id[:8]}，已创建新任务（pending）"
                    )

                return JSONResponse(
                    {
                        "message": (
                            f"流水线已有正在执行的任务，已创建 {len(queued_task_ids)} 个任务并加入队列"
                            if len(tags) > 1
                            else "流水线已有正在执行的任务，任务已创建并加入队列"
                        ),
                        "status": "queued",
                        "task_id": queued_task_ids[0] if queued_task_ids else None,
                        "task_ids": (
                            queued_task_ids if len(queued_task_ids) > 1 else None
                        ),
                        "queue_length": queue_length,
                        "current_task_id": current_task_id,
                        "pipeline": pipeline.get("name"),
                    }
                )
            else:
                # 任务已完成或不存在，解绑
                manager.unbind_task(pipeline_id)

        # 没有运行中的任务，为每个标签立即启动构建任务
        started_task_ids = []
        for tag in tags:
            task_config = pipeline_to_task_config(
                pipeline,
                trigger_source="webhook",
                branch=branch,
                tag=tag,
                webhook_branch=webhook_branch,
                branch_tag_mapping=branch_tag_mapping,
            )
            started_task_id = build_manager._trigger_task_from_config(task_config)
            started_task_ids.append(started_task_id)

        task_id = started_task_ids[0] if started_task_ids else None

        # 提取 webhook 相关信息
        webhook_info = {
            "branch": branch,
            "tags": tags,  # 添加标签列表信息
            "event": request.headers.get("x-gitee-event")
            or request.headers.get("x-gitlab-event")
            or request.headers.get("x-github-event", "unknown"),
            "platform": (
                "gitee"
                if "x-gitee-event" in request.headers
                else ("gitlab" if "x-gitlab-event" in request.headers else "github")
            ),
        }

        # 尝试从 payload 中提取更多信息
        if payload:
            if "commits" in payload and payload["commits"]:
                webhook_info["commit_count"] = len(payload["commits"])
                webhook_info["last_commit"] = (
                    payload["commits"][0].get("message", "")[:100]
                    if payload["commits"]
                    else ""
                )
            if "repository" in payload:
                webhook_info["repository"] = payload["repository"].get("name", "")

        # 记录触发并绑定任务（webhook 触发，只绑定第一个任务）
        manager.record_trigger(
            pipeline["pipeline_id"],
            task_id,
            trigger_source="webhook",
            trigger_info=webhook_info,
        )

        # 记录操作日志（记录所有任务）
        OperationLogger.log(
            "webhook",
            "pipeline_trigger",
            {
                "pipeline_id": pipeline["pipeline_id"],
                "pipeline_name": pipeline.get("name"),
                "task_id": task_id,
                "task_ids": started_task_ids if len(started_task_ids) > 1 else None,
                "tags": tags,
                "branch": branch,
                "trigger_source": "webhook",
                "webhook_info": webhook_info,
            },
        )

        if len(tags) > 1:
            print(
                f"🔔 Webhook 触发，已启动 {len(started_task_ids)} 个构建任务: pipeline={pipeline.get('name')}, branch={branch}, tags={tags}"
            )
        else:
            print(
                f"🔔 Webhook 触发，已启动构建任务: pipeline={pipeline.get('name')}, branch={branch}, tag={tags[0]}"
            )

        return JSONResponse(
            {
                "message": (
                    f"已启动 {len(started_task_ids)} 个构建任务"
                    if len(tags) > 1
                    else "构建任务已启动"
                ),
                "status": "started",
                "task_id": task_id,
                "task_ids": started_task_ids if len(started_task_ids) > 1 else None,
                "tags": tags,
                "pipeline": pipeline.get("name"),
                "branch": branch,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Webhook 处理失败: {str(e)}")


# === Git 数据源管理 ===


class CreateGitSourceRequest(BaseModel):
    name: str
    git_url: str
    description: str = ""
    branches: list = []
    tags: list = []
    default_branch: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    dockerfiles: Optional[dict] = None  # Dockerfile 字典


class UpdateGitSourceRequest(BaseModel):
    name: Optional[str] = None
    git_url: Optional[str] = None
    description: Optional[str] = None
    branches: Optional[list] = None
    tags: Optional[list] = None
    default_branch: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    dockerfiles: Optional[dict] = None  # Dockerfile 字典


@router.get("/git-sources")
async def list_git_sources(http_request: Request):
    """获取所有 Git 数据源"""
    try:
        get_current_username(http_request)  # 验证登录
        manager = GitSourceManager()
        sources = manager.list_sources()
        return JSONResponse({"sources": sources, "total": len(sources)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据源列表失败: {str(e)}")


@router.get("/git-sources/{source_id}")
async def get_git_source(source_id: str, http_request: Request):
    """获取 Git 数据源详情"""
    try:
        get_current_username(http_request)  # 验证登录
        manager = GitSourceManager()
        source = manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="数据源不存在")
        return JSONResponse(source)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据源失败: {str(e)}")


@router.post("/git-sources")
async def create_git_source(request: CreateGitSourceRequest, http_request: Request):
    """创建 Git 数据源"""
    try:
        username = get_current_username(http_request)
        manager = GitSourceManager()

        source_id = manager.create_source(
            name=request.name,
            git_url=request.git_url,
            description=request.description,
            branches=request.branches,
            tags=request.tags,
            default_branch=request.default_branch,
            username=request.username,
            password=request.password,
            dockerfiles=request.dockerfiles or {},
        )

        # 记录操作日志
        OperationLogger.log(
            username,
            "git_source_create",
            {
                "source_id": source_id,
                "name": request.name,
                "git_url": request.git_url,
            },
        )

        return JSONResponse({"source_id": source_id, "message": "数据源创建成功"})
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建数据源失败: {str(e)}")


@router.put("/git-sources/{source_id}")
async def update_git_source(
    source_id: str, request: UpdateGitSourceRequest, http_request: Request
):
    """更新 Git 数据源"""
    try:
        username = get_current_username(http_request)
        manager = GitSourceManager()

        success = manager.update_source(
            source_id=source_id,
            name=request.name,
            git_url=request.git_url,
            description=request.description,
            branches=request.branches,
            tags=request.tags,
            default_branch=request.default_branch,
            username=request.username,
            password=request.password,
        )

        if not success:
            raise HTTPException(status_code=404, detail="数据源不存在")

        # 更新 Dockerfile（如果有）
        if request.dockerfiles is not None:
            source = manager.get_source(source_id, include_password=True)
            if source:
                # 先清空现有的 Dockerfile（如果需要完全替换）
                # 这里我们只更新提供的 Dockerfile，不删除其他的
                for dockerfile_path, content in request.dockerfiles.items():
                    manager.update_dockerfile(source_id, dockerfile_path, content)

        # 记录操作日志
        OperationLogger.log(username, "git_source_update", {"source_id": source_id})

        return JSONResponse({"message": "数据源更新成功"})
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新数据源失败: {str(e)}")


@router.delete("/git-sources/{source_id}")
async def delete_git_source(source_id: str, http_request: Request):
    """删除 Git 数据源"""
    try:
        username = get_current_username(http_request)
        manager = GitSourceManager()

        success = manager.delete_source(source_id)
        if not success:
            raise HTTPException(status_code=404, detail="数据源不存在")

        # 记录操作日志
        OperationLogger.log(username, "git_source_delete", {"source_id": source_id})

        return JSONResponse({"message": "数据源已删除"})
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除数据源失败: {str(e)}")


@router.get("/git-sources/{source_id}/dockerfiles")
async def get_dockerfiles(source_id: str, http_request: Request):
    """获取数据源的所有 Dockerfile"""
    try:
        get_current_username(http_request)  # 验证登录
        manager = GitSourceManager()
        source = manager.get_source(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="数据源不存在")

        dockerfiles = source.get("dockerfiles", {})
        return JSONResponse(
            {"dockerfiles": dockerfiles, "dockerfile_paths": list(dockerfiles.keys())}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取 Dockerfile 列表失败: {str(e)}"
        )


@router.post("/git-sources/scan-dockerfiles")
async def scan_dockerfiles(
    git_url: str = Body(..., embed=True, description="Git 仓库地址"),
    branch: str = Body(..., embed=True, description="分支名称"),
    source_id: Optional[str] = Body(
        None, embed=True, description="数据源 ID（如果提供，将使用数据源的认证信息）"
    ),
    username: Optional[str] = Body(None, embed=True, description="Git 用户名（可选）"),
    password: Optional[str] = Body(None, embed=True, description="Git 密码（可选）"),
    http_request: Request = None,
):
    """扫描 Git 仓库指定分支的 Dockerfile"""
    import subprocess
    import tempfile
    import shutil
    import os
    from urllib.parse import urlparse, urlunparse

    try:
        get_current_username(http_request)  # 验证登录

        # 如果提供了 source_id，从数据源获取认证信息
        if source_id:
            source_manager = GitSourceManager()
            source = source_manager.get_source(source_id, include_password=False)
            if source:
                auth_config = source_manager.get_auth_config(source_id)
                if auth_config.get("username"):
                    username = username or auth_config.get("username")
                if auth_config.get("password"):
                    password = password or auth_config.get("password")

        # 如果提供了用户名和密码，嵌入到 URL 中
        clone_url = git_url
        if username and password and git_url.startswith("https://"):
            parsed = urlparse(git_url)
            clone_url = urlunparse(
                (
                    parsed.scheme,
                    f"{username}:{password}@{parsed.netloc}",
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )

        # 临时克隆仓库以扫描 Dockerfile
        temp_dir = tempfile.mkdtemp()
        dockerfiles = {}

        try:
            # 准备克隆命令
            clone_cmd = [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                branch,
                clone_url,
                temp_dir,
            ]

            clone_result = subprocess.run(
                clone_cmd, capture_output=True, text=True, timeout=60
            )

            if clone_result.returncode == 0:
                # 扫描 Dockerfile（递归查找）
                for root, dirs, files in os.walk(temp_dir):
                    # 跳过 .git 目录
                    if ".git" in root.split(os.sep):
                        continue

                    for file in files:
                        # 检查是否是 Dockerfile（不区分大小写，支持多种命名）
                        file_lower = file.lower()
                        if file_lower.startswith("dockerfile") or file_lower.endswith(
                            ".dockerfile"
                        ):
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, temp_dir)

                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    dockerfiles[relative_path] = (
                                        file  # 只保存文件名，不保存内容
                                    )
                                    print(f"✅ 扫描到 Dockerfile: {relative_path}")
                            except Exception as e:
                                print(f"⚠️ 读取 Dockerfile 失败 {relative_path}: {e}")
            else:
                error_msg = clone_result.stderr.strip()
                if (
                    "Authentication failed" in error_msg
                    or "Permission denied" in error_msg
                    or "fatal: could not read Username" in error_msg
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="仓库访问被拒绝，请检查认证信息是否正确",
                    )
                elif (
                    "not found" in error_msg.lower()
                    or "does not exist" in error_msg.lower()
                ):
                    raise HTTPException(
                        status_code=404,
                        detail=f"分支 '{branch}' 不存在或仓库不存在",
                    )
                else:
                    raise HTTPException(
                        status_code=400, detail=f"无法克隆仓库: {error_msg}"
                    )
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)

        # 返回 Dockerfile 文件名列表（按路径排序）
        dockerfile_paths = sorted(dockerfiles.keys())
        return JSONResponse(
            {
                "dockerfiles": dockerfile_paths,
                "dockerfile_map": dockerfiles,  # 路径到文件名的映射
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"扫描 Dockerfile 失败: {str(e)}")


@router.get("/git-sources/{source_id}/dockerfiles/{dockerfile_path:path}")
async def get_dockerfile(source_id: str, dockerfile_path: str, http_request: Request):
    """获取指定 Dockerfile 的内容"""
    try:
        get_current_username(http_request)  # 验证登录
        manager = GitSourceManager()
        content = manager.get_dockerfile(source_id, dockerfile_path)
        if content is None:
            raise HTTPException(status_code=404, detail="Dockerfile 不存在")

        return JSONResponse({"dockerfile_path": dockerfile_path, "content": content})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Dockerfile 失败: {str(e)}")


@router.put("/git-sources/{source_id}/dockerfiles/{dockerfile_path:path}")
async def update_dockerfile(
    source_id: str,
    dockerfile_path: str,
    content: str = Body(..., embed=True, description="Dockerfile 内容"),
    http_request: Request = None,
):
    """更新或创建 Dockerfile"""
    try:
        get_current_username(http_request)  # 验证登录
        manager = GitSourceManager()

        success = manager.update_dockerfile(source_id, dockerfile_path, content)
        if not success:
            raise HTTPException(status_code=404, detail="数据源不存在")

        return JSONResponse(
            {"message": "Dockerfile 已保存", "dockerfile_path": dockerfile_path}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存 Dockerfile 失败: {str(e)}")


@router.delete("/git-sources/{source_id}/dockerfiles/{dockerfile_path:path}")
async def delete_dockerfile(
    source_id: str, dockerfile_path: str, http_request: Request
):
    """删除 Dockerfile"""
    try:
        get_current_username(http_request)  # 验证登录
        manager = GitSourceManager()

        success = manager.delete_dockerfile(source_id, dockerfile_path)
        if not success:
            raise HTTPException(status_code=404, detail="Dockerfile 不存在")

        return JSONResponse(
            {"message": "Dockerfile 已删除", "dockerfile_path": dockerfile_path}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除 Dockerfile 失败: {str(e)}")


@router.post("/git-sources/{source_id}/dockerfiles/{dockerfile_path:path}/commit")
async def commit_dockerfile(
    source_id: str,
    dockerfile_path: str,
    branch: str = Body(..., embed=True, description="目标分支"),
    commit_message: str = Body(None, embed=True, description="提交信息（可选）"),
    http_request: Request = None,
):
    """提交 Dockerfile 到 Git 仓库"""
    import subprocess
    import tempfile
    import shutil
    from urllib.parse import urlparse, urlunparse

    try:
        username = get_current_username(http_request)  # 验证登录
        manager = GitSourceManager()

        # 获取数据源信息
        source = manager.get_source(source_id, include_password=True)
        if not source:
            raise HTTPException(status_code=404, detail="数据源不存在")

        # 获取 Dockerfile 内容
        dockerfile_content = manager.get_dockerfile(source_id, dockerfile_path)
        if not dockerfile_content:
            raise HTTPException(status_code=404, detail="Dockerfile 不存在")

        # 获取认证信息
        auth_config = manager.get_auth_config(source_id)
        git_url = source["git_url"]
        username_auth = auth_config.get("username")
        password_auth = auth_config.get("password")

        # 构建带认证信息的 URL
        verify_url = git_url
        if username_auth and password_auth and git_url.startswith("https://"):
            parsed = urlparse(git_url)
            verify_url = urlunparse(
                (
                    parsed.scheme,
                    f"{username_auth}:{password_auth}@{parsed.netloc}",
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )

        # 创建临时目录
        temp_dir = tempfile.mkdtemp()

        try:
            # 克隆仓库
            clone_cmd = [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                branch,
                verify_url,
                temp_dir,
            ]
            clone_result = subprocess.run(
                clone_cmd, capture_output=True, text=True, timeout=60
            )

            if clone_result.returncode != 0:
                # 如果分支不存在，尝试克隆默认分支然后切换
                if (
                    "not found" in clone_result.stderr.lower()
                    or "does not exist" in clone_result.stderr.lower()
                ):
                    # 先克隆默认分支
                    default_branch = source.get("default_branch") or "main"
                    clone_cmd_default = [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "--branch",
                        default_branch,
                        verify_url,
                        temp_dir,
                    ]
                    clone_result_default = subprocess.run(
                        clone_cmd_default, capture_output=True, text=True, timeout=60
                    )

                    if clone_result_default.returncode != 0:
                        raise HTTPException(
                            status_code=400,
                            detail=f"无法克隆仓库: {clone_result_default.stderr.strip()}",
                        )

                    # 切换到目标分支（如果不存在则创建）
                    checkout_cmd = ["git", "checkout", "-b", branch]
                    checkout_result = subprocess.run(
                        checkout_cmd,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    # 如果分支已存在，直接切换
                    if checkout_result.returncode != 0:
                        checkout_cmd = ["git", "checkout", branch]
                        checkout_result = subprocess.run(
                            checkout_cmd,
                            cwd=temp_dir,
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        if checkout_result.returncode != 0:
                            raise HTTPException(
                                status_code=400,
                                detail=f"无法切换到分支 {branch}: {checkout_result.stderr.strip()}",
                            )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"无法克隆仓库: {clone_result.stderr.strip()}",
                    )

            # 先拉取最新更改，确保与远程同步
            fetch_cmd = ["git", "fetch", "origin", branch]
            fetch_result = subprocess.run(
                fetch_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=30
            )

            # 尝试合并远程更改
            merge_cmd = ["git", "merge", f"origin/{branch}", "--no-edit"]
            merge_result = subprocess.run(
                merge_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=30
            )

            # 如果有冲突，使用本地版本（ours）
            if merge_result.returncode != 0:
                # 检查是否有冲突
                status_cmd = ["git", "status", "--porcelain"]
                status_result = subprocess.run(
                    status_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=10
                )

                if "UU" in status_result.stdout or "AA" in status_result.stdout:
                    # 有冲突，使用本地版本
                    checkout_ours_cmd = ["git", "checkout", "--ours", dockerfile_path]
                    subprocess.run(
                        checkout_ours_cmd,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    # 添加解决冲突的文件
                    add_cmd = ["git", "add", dockerfile_path]
                    subprocess.run(
                        add_cmd,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    # 继续合并
                    continue_cmd = ["git", "merge", "--continue", "--no-edit"]
                    subprocess.run(
                        continue_cmd,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                else:
                    # 其他错误，重置合并
                    abort_cmd = ["git", "merge", "--abort"]
                    subprocess.run(
                        abort_cmd,
                        cwd=temp_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

            # 写入 Dockerfile
            dockerfile_full_path = os.path.join(temp_dir, dockerfile_path)
            os.makedirs(os.path.dirname(dockerfile_full_path), exist_ok=True)

            with open(dockerfile_full_path, "w", encoding="utf-8") as f:
                f.write(dockerfile_content)

            # 配置 Git 用户信息（如果没有配置）
            config_cmd = ["git", "config", "user.name"]
            config_result = subprocess.run(
                config_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=10
            )
            if config_result.returncode != 0 or not config_result.stdout.strip():
                subprocess.run(
                    ["git", "config", "user.name", "app2docker"],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                subprocess.run(
                    ["git", "config", "user.email", "app2docker@localhost"],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

            # 添加文件
            add_cmd = ["git", "add", dockerfile_path]
            add_result = subprocess.run(
                add_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=10
            )

            if add_result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"添加文件到 Git 失败: {add_result.stderr.strip()}",
                )

            # 提交
            commit_msg = commit_message or f"Update {dockerfile_path} via app2docker"
            commit_cmd = ["git", "commit", "-m", commit_msg]
            commit_result = subprocess.run(
                commit_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=30
            )

            if commit_result.returncode != 0:
                # 检查是否没有更改
                if "nothing to commit" in commit_result.stdout.lower():
                    return JSONResponse(
                        {
                            "success": True,
                            "message": "没有更改需要提交",
                            "no_changes": True,
                        }
                    )
                raise HTTPException(
                    status_code=500, detail=f"提交失败: {commit_result.stderr.strip()}"
                )

            # 推送到远程
            push_cmd = ["git", "push", "origin", branch]
            push_result = subprocess.run(
                push_cmd, cwd=temp_dir, capture_output=True, text=True, timeout=60
            )

            if push_result.returncode != 0:
                raise HTTPException(
                    status_code=500, detail=f"推送失败: {push_result.stderr.strip()}"
                )

            # 记录操作日志
            OperationLogger.log(
                username,
                "commit_dockerfile",
                {
                    "source_id": source_id,
                    "dockerfile_path": dockerfile_path,
                    "branch": branch,
                    "commit_message": commit_msg,
                },
            )

            return JSONResponse(
                {
                    "success": True,
                    "message": f"Dockerfile 已成功提交并推送到分支 {branch}",
                    "branch": branch,
                    "commit_message": commit_msg,
                }
            )

        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"提交 Dockerfile 失败: {str(e)}")


# ==================== 资源包管理 API ====================


@router.post("/resource-packages/upload")
async def upload_resource_package(
    request: Request,
    package_file: UploadFile = File(...),
    description: str = Form(""),
    extract: bool = Form(True),
):
    """上传资源包"""
    try:
        username = get_current_username(request)

        # 读取文件数据
        file_data = await package_file.read()

        if not file_data:
            raise HTTPException(status_code=400, detail="文件为空")

        # 上传资源包
        manager = ResourcePackageManager()
        package_info = manager.upload_package(
            file_data=file_data,
            filename=package_file.filename,
            description=description,
            extract=extract,
        )

        # 记录操作日志
        OperationLogger.log(
            username,
            "resource_package_upload",
            {
                "package_id": package_info["package_id"],
                "filename": package_file.filename,
                "size": package_info["size"],
            },
        )

        return JSONResponse(
            {
                "success": True,
                "package": package_info,
                "message": "资源包上传成功",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"上传资源包失败: {str(e)}")


@router.get("/resource-packages")
async def list_resource_packages(request: Request):
    """获取资源包列表"""
    try:
        manager = ResourcePackageManager()
        packages = manager.list_packages()

        return JSONResponse(
            {
                "success": True,
                "packages": packages,
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取资源包列表失败: {str(e)}")


@router.get("/resource-packages/{package_id}")
async def get_resource_package(request: Request, package_id: str):
    """获取资源包信息"""
    try:
        manager = ResourcePackageManager()
        package_info = manager.get_package(package_id)

        if not package_info:
            raise HTTPException(status_code=404, detail="资源包不存在")

        return JSONResponse(
            {
                "success": True,
                "package": package_info,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取资源包信息失败: {str(e)}")


@router.delete("/resource-packages/{package_id}")
async def delete_resource_package(request: Request, package_id: str):
    """删除资源包"""
    try:
        username = get_current_username(request)

        manager = ResourcePackageManager()
        success = manager.delete_package(package_id)

        if not success:
            raise HTTPException(status_code=404, detail="资源包不存在")

        # 记录操作日志
        OperationLogger.log(
            username,
            "resource_package_delete",
            {
                "package_id": package_id,
            },
        )

        return JSONResponse(
            {
                "success": True,
                "message": "资源包已删除",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除资源包失败: {str(e)}")


@router.get("/resource-packages/{package_id}/content")
async def get_resource_package_content(request: Request, package_id: str):
    """获取资源包文件内容（仅文本文件）"""
    try:
        manager = ResourcePackageManager()
        package_info = manager.get_package(package_id)

        if not package_info:
            raise HTTPException(status_code=404, detail="资源包不存在")

        # 检查是否为文本文件
        filename = package_info.get("filename", "")
        text_extensions = [
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".properties",
            ".conf",
            ".config",
            ".ini",
            ".env",
            ".sh",
            ".bash",
            ".py",
            ".js",
            ".ts",
            ".java",
            ".go",
            ".rs",
            ".md",
            ".log",
            ".sql",
            ".csv",
            ".html",
            ".css",
            ".scss",
            ".less",
            ".vue",
            ".tsx",
            ".jsx",
            ".dockerfile",
            ".gitignore",
            ".gitattributes",
            ".editorconfig",
        ]

        filename_lower = filename.lower()
        is_text_file = any(filename_lower.endswith(ext) for ext in text_extensions)

        if not is_text_file:
            raise HTTPException(
                status_code=400, detail="该文件不是文本文件，无法在线编辑"
            )

        # 读取文件内容
        package_dir = os.path.join("data/resource_packages", package_id)
        file_path = os.path.join(package_dir, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 检查文件大小（限制为1MB）
        file_size = os.path.getsize(file_path)
        if file_size > 1024 * 1024:
            raise HTTPException(
                status_code=400, detail="文件过大（超过1MB），无法在线编辑"
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
            except:
                raise HTTPException(
                    status_code=400, detail="文件编码不支持，无法在线编辑"
                )

        return JSONResponse(
            {
                "success": True,
                "content": content,
                "filename": filename,
                "encoding": "utf-8",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取资源包内容失败: {str(e)}")


@router.put("/resource-packages/{package_id}/content")
async def update_resource_package_content(
    request: Request,
    package_id: str,
    content: str = Body(..., embed=True, description="文件内容"),
):
    """更新资源包文件内容（仅文本文件）"""
    try:
        username = get_current_username(request)

        manager = ResourcePackageManager()
        package_info = manager.get_package(package_id)

        if not package_info:
            raise HTTPException(status_code=404, detail="资源包不存在")

        # 检查是否为文本文件
        filename = package_info.get("filename", "")
        text_extensions = [
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".properties",
            ".conf",
            ".config",
            ".ini",
            ".env",
            ".sh",
            ".bash",
            ".py",
            ".js",
            ".ts",
            ".java",
            ".go",
            ".rs",
            ".md",
            ".log",
            ".sql",
            ".csv",
            ".html",
            ".css",
            ".scss",
            ".less",
            ".vue",
            ".tsx",
            ".jsx",
            ".dockerfile",
            ".gitignore",
            ".gitattributes",
            ".editorconfig",
        ]

        filename_lower = filename.lower()
        is_text_file = any(filename_lower.endswith(ext) for ext in text_extensions)

        if not is_text_file:
            raise HTTPException(
                status_code=400, detail="该文件不是文本文件，无法在线编辑"
            )

        # 保存文件内容
        package_dir = os.path.join("data/resource_packages", package_id)
        file_path = os.path.join(package_dir, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 备份原文件
        backup_path = file_path + ".bak"
        try:
            import shutil

            shutil.copy2(file_path, backup_path)
        except:
            pass

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # 更新文件大小
            new_size = len(content.encode("utf-8"))
            metadata = manager._load_metadata()
            if package_id in metadata:
                metadata[package_id]["size"] = new_size
                metadata[package_id]["updated_at"] = datetime.now().isoformat()
                manager._save_metadata(metadata)

            # 删除备份文件
            if os.path.exists(backup_path):
                os.remove(backup_path)

            # 记录操作日志
            OperationLogger.log(
                username,
                "resource_package_edit",
                {
                    "package_id": package_id,
                    "filename": filename,
                },
            )

            return JSONResponse(
                {
                    "success": True,
                    "message": "文件已保存",
                }
            )
        except Exception as e:
            # 恢复备份
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
            raise e

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新资源包内容失败: {str(e)}")


# === 主机资源管理 ===
class HostRequest(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key: Optional[str] = None
    key_password: Optional[str] = None
    description: str = ""


class HostUpdateRequest(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    key_password: Optional[str] = None
    docker_enabled: Optional[bool] = None
    docker_version: Optional[str] = None
    description: Optional[str] = None


class SSHTestRequest(BaseModel):
    host: str
    port: int = 22
    username: str = ""
    password: Optional[str] = None
    private_key: Optional[str] = None
    key_password: Optional[str] = None


@router.post("/hosts/test-ssh")
async def test_ssh_connection(request: Request, ssh_test: SSHTestRequest):
    """测试SSH连接"""
    try:
        username = get_current_username(request)
        manager = HostManager()

        result = manager.test_ssh_connection(
            host=ssh_test.host,
            port=ssh_test.port,
            username=ssh_test.username,
            password=ssh_test.password,
            private_key=ssh_test.private_key,
            key_password=ssh_test.key_password,
        )

        # 记录操作日志
        OperationLogger.log(
            username,
            "host_test_ssh",
            {"host": ssh_test.host, "success": result.get("success", False)},
        )

        return JSONResponse(result)
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"测试SSH连接失败: {str(e)}")


@router.post("/hosts/{host_id}/test-ssh")
async def test_host_ssh_connection(request: Request, host_id: str):
    """使用已保存的配置测试SSH连接"""
    try:
        username = get_current_username(request)
        manager = HostManager()

        # 获取完整的主机信息（包含密码/私钥）
        host_info = manager.get_host_full(host_id)
        if not host_info:
            raise HTTPException(status_code=404, detail="主机不存在")

        # 使用已保存的配置进行测试
        result = manager.test_ssh_connection(
            host=host_info["host"],
            port=host_info["port"],
            username=host_info["username"],
            password=host_info.get("password"),
            private_key=host_info.get("private_key"),
            key_password=host_info.get("key_password"),
        )

        # 如果测试成功且检测到Docker版本，更新主机信息
        if result.get("success") and result.get("docker_version"):
            manager.update_host(
                host_id=host_id, docker_version=result.get("docker_version")
            )

        # 记录操作日志
        OperationLogger.log(
            username,
            "host_test_ssh",
            {
                "host_id": host_id,
                "host": host_info["host"],
                "success": result.get("success", False),
                "docker_available": result.get("docker_available", False),
            },
        )

        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"测试SSH连接失败: {str(e)}")


@router.get("/hosts")
async def list_hosts(request: Request):
    """获取主机列表"""
    try:
        username = get_current_username(request)
        manager = HostManager()
        hosts = manager.list_hosts()
        return JSONResponse({"hosts": hosts})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取主机列表失败: {str(e)}")


@router.get("/hosts/{host_id}")
async def get_host(request: Request, host_id: str):
    """获取主机详情"""
    try:
        username = get_current_username(request)
        manager = HostManager()
        host = manager.get_host(host_id)
        if not host:
            raise HTTPException(status_code=404, detail="主机不存在")
        return JSONResponse(host)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取主机详情失败: {str(e)}")


@router.post("/hosts")
async def add_host(request: Request, host_req: HostRequest):
    """添加主机"""
    try:
        username = get_current_username(request)
        manager = HostManager()

        host_info = manager.add_host(
            name=host_req.name,
            host=host_req.host,
            port=host_req.port,
            username=host_req.username,
            password=host_req.password,
            private_key=host_req.private_key,
            key_password=host_req.key_password,
            docker_enabled=False,  # 默认不支持，通过检测后自动更新
            description=host_req.description,
        )

        # 记录操作日志
        OperationLogger.log(
            username,
            "host_add",
            {
                "host_id": host_info["host_id"],
                "name": host_info["name"],
                "host": host_info["host"],
            },
        )

        return JSONResponse({"success": True, "host": host_info})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"添加主机失败: {str(e)}")


@router.put("/hosts/{host_id}")
async def update_host(request: Request, host_id: str, host_req: HostUpdateRequest):
    """更新主机"""
    try:
        username = get_current_username(request)
        manager = HostManager()

        host_info = manager.update_host(
            host_id=host_id,
            name=host_req.name,
            host=host_req.host,
            port=host_req.port,
            username=host_req.username,
            password=host_req.password,
            private_key=host_req.private_key,
            key_password=host_req.key_password,
            docker_enabled=host_req.docker_enabled,
            docker_version=host_req.docker_version,
            description=host_req.description,
        )

        if not host_info:
            raise HTTPException(status_code=404, detail="主机不存在")

        # 记录操作日志
        OperationLogger.log(
            username, "host_update", {"host_id": host_id, "name": host_info.get("name")}
        )

        return JSONResponse({"success": True, "host": host_info})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新主机失败: {str(e)}")


@router.delete("/hosts/{host_id}")
async def delete_host(request: Request, host_id: str):
    """删除主机"""
    try:
        username = get_current_username(request)
        manager = HostManager()

        success = manager.delete_host(host_id)
        if not success:
            raise HTTPException(status_code=404, detail="主机不存在")

        # 记录操作日志
        OperationLogger.log(username, "host_delete", {"host_id": host_id})

        return JSONResponse({"success": True, "message": "主机已删除"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除主机失败: {str(e)}")


# ==================== Agent主机管理 ====================

class AgentHostRequest(BaseModel):
    name: str
    host_type: str = "agent"  # agent 或 portainer
    description: str = ""
    portainer_url: Optional[str] = None
    portainer_api_key: Optional[str] = None
    portainer_endpoint_id: Optional[int] = None


class AgentHostUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    portainer_url: Optional[str] = None
    portainer_api_key: Optional[str] = None
    portainer_endpoint_id: Optional[int] = None


class PortainerTestRequest(BaseModel):
    portainer_url: str
    api_key: str
    endpoint_id: int


class PortainerListEndpointsRequest(BaseModel):
    portainer_url: str
    api_key: str
    endpoint_id: int = 0  # 获取列表时不需要真实的 endpoint_id


class DeployTaskCreateRequest(BaseModel):
    config_content: str
    registry: Optional[str] = None
    tag: Optional[str] = None


class DeployTaskExecuteRequest(BaseModel):
    target_names: Optional[List[str]] = None


@router.post("/agent-hosts/test-portainer")
async def test_portainer_connection(request: Request, test_req: PortainerTestRequest):
    """测试 Portainer 连接"""
    try:
        manager = AgentHostManager()
        result = manager.test_portainer_connection(
            test_req.portainer_url,
            test_req.api_key,
            test_req.endpoint_id
        )
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试连接失败: {str(e)}")


@router.post("/agent-hosts/list-portainer-endpoints")
async def list_portainer_endpoints(request: Request, test_req: PortainerListEndpointsRequest):
    """获取 Portainer Endpoints 列表"""
    try:
        from backend.portainer_client import PortainerClient
        client = PortainerClient(test_req.portainer_url, test_req.api_key, 0)  # endpoint_id 暂时不需要
        
        # 获取所有 endpoints
        endpoints = client._request('GET', '/endpoints', timeout=5)
        
        return JSONResponse({
            "success": True,
            "endpoints": [
                {"id": ep.get('Id'), "name": ep.get('Name'), "type": ep.get('Type')}
                for ep in endpoints
            ]
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({
            "success": False,
            "message": f"获取 Endpoints 列表失败: {str(e)}",
            "endpoints": []
        })


@router.post("/agent-hosts")
async def add_agent_host(request: Request, host_req: AgentHostRequest):
    """创建主机（支持 Agent 和 Portainer 类型）"""
    try:
        username = get_current_username(request)
        manager = AgentHostManager()

        host_info = manager.add_agent_host(
            name=host_req.name,
            host_type=host_req.host_type,
            description=host_req.description,
            portainer_url=host_req.portainer_url,
            portainer_api_key=host_req.portainer_api_key,
            portainer_endpoint_id=host_req.portainer_endpoint_id,
        )

        # 如果是 Portainer 类型，创建后立即更新状态
        if host_req.host_type == "portainer" and host_info:
            try:
                updated_info = manager.update_portainer_host_status(host_info["host_id"])
                if updated_info:
                    host_info = updated_info
            except Exception as e:
                # 状态更新失败不影响创建，记录日志即可
                import logging
                logging.warning(f"创建 Portainer 主机后更新状态失败: {e}")

        # 记录操作日志
        OperationLogger.log(
            username,
            "agent_host_add",
            {
                "host_id": host_info["host_id"],
                "name": host_info["name"],
            },
        )

        return JSONResponse({"success": True, "host": host_info})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建Agent主机失败: {str(e)}")


@router.get("/agent-hosts")
async def list_agent_hosts(request: Request):
    """获取Agent主机列表"""
    try:
        username = get_current_username(request)
        manager = AgentHostManager()
        hosts = manager.list_agent_hosts()
        return JSONResponse({"hosts": hosts})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent主机列表失败: {str(e)}")


@router.get("/agent-hosts/{host_id}")
async def get_agent_host(request: Request, host_id: str):
    """获取Agent主机详情"""
    try:
        username = get_current_username(request)
        manager = AgentHostManager()
        host = manager.get_agent_host(host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Agent主机不存在")
        return JSONResponse(host)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent主机详情失败: {str(e)}")


@router.put("/agent-hosts/{host_id}")
async def update_agent_host(request: Request, host_id: str, host_req: AgentHostUpdateRequest):
    """更新Agent主机信息"""
    try:
        username = get_current_username(request)
        manager = AgentHostManager()

        host_info = manager.update_host_info(
            host_id=host_id,
            name=host_req.name,
            description=host_req.description,
            portainer_url=host_req.portainer_url,
            portainer_api_key=host_req.portainer_api_key,
            portainer_endpoint_id=host_req.portainer_endpoint_id,
        )

        if not host_info:
            raise HTTPException(status_code=404, detail="Agent主机不存在")

        # 如果是 Portainer 类型，更新后立即刷新状态
        if host_info.get("host_type") == "portainer":
            try:
                updated_info = manager.update_portainer_host_status(host_id)
                if updated_info:
                    host_info = updated_info
            except Exception as e:
                # 状态更新失败不影响更新，记录日志即可
                import logging
                logging.warning(f"更新 Portainer 主机后刷新状态失败: {e}")

        # 记录操作日志
        OperationLogger.log(
            username,
            "agent_host_update",
            {"host_id": host_id, "name": host_info.get("name")},
        )

        return JSONResponse({"success": True, "host": host_info})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新Agent主机失败: {str(e)}")


@router.post("/agent-hosts/{host_id}/refresh-status")
async def refresh_agent_host_status(request: Request, host_id: str):
    """刷新Agent主机状态"""
    try:
        manager = AgentHostManager()
        host = manager.get_agent_host(host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Agent主机不存在")
        
        # 根据主机类型刷新状态
        if host.get("host_type") == "portainer":
            updated_info = manager.update_portainer_host_status(host_id)
            if updated_info:
                return JSONResponse({"success": True, "host": updated_info})
            else:
                return JSONResponse({"success": False, "message": "状态更新失败"})
        else:
            # Agent 类型的主机状态通过 WebSocket 心跳更新
            return JSONResponse({"success": True, "host": host, "message": "Agent 类型主机状态通过 WebSocket 心跳更新"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新状态失败: {str(e)}")


@router.delete("/agent-hosts/{host_id}")
async def delete_agent_host(request: Request, host_id: str):
    """删除Agent主机"""
    try:
        username = get_current_username(request)
        manager = AgentHostManager()

        success = manager.delete_agent_host(host_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent主机不存在")

        # 记录操作日志
        OperationLogger.log(username, "agent_host_delete", {"host_id": host_id})

        return JSONResponse({"success": True, "message": "Agent主机已删除"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除Agent主机失败: {str(e)}")


@router.get("/agent-hosts/{host_id}/deploy-command")
async def get_deploy_command(
    request: Request,
    host_id: str,
    type: str = Query("run", description="部署类型: run 或 stack"),
    agent_image: str = Query("registry.cn-hangzhou.aliyuncs.com/51jbm/app2docker-agent:latest", description="Agent镜像"),
    server_url: Optional[str] = Query(None, description="服务器URL（可选）"),
):
    """获取Agent部署命令"""
    try:
        username = get_current_username(request)
        manager = AgentHostManager()

        if type not in ["run", "stack"]:
            raise HTTPException(status_code=400, detail="部署类型必须是 'run' 或 'stack'")

        result = manager.generate_deploy_command(
            host_id=host_id,
            deploy_type=type,
            agent_image=agent_image,
            server_url=server_url,
        )

        return JSONResponse(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成部署命令失败: {str(e)}")


@router.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket, token: str = Query(...)):
    """Agent WebSocket连接端点（通过查询参数传递token）"""
    await handle_agent_websocket(websocket, token)


# ==================== 部署任务管理 ====================

@router.post("/deploy-tasks")
async def create_deploy_task(request: Request, task_req: DeployTaskCreateRequest):
    """创建部署任务"""
    try:
        username = get_current_username(request)
        task_manager = DeployTaskManager()
        
        task = task_manager.create_task(
            config_content=task_req.config_content,
            registry=task_req.registry,
            tag=task_req.tag
        )
        
        # 记录操作日志
        OperationLogger.log(
            username,
            "deploy_task_create",
            {"task_id": task["task_id"]}
        )
        
        return JSONResponse({
            "success": True,
            "task": task
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建部署任务失败: {str(e)}")


@router.get("/deploy-tasks")
async def list_deploy_tasks(request: Request):
    """列出所有部署任务"""
    try:
        username = get_current_username(request)
        task_manager = DeployTaskManager()
        
        tasks = task_manager.list_tasks()
        
        return JSONResponse({
            "success": True,
            "tasks": tasks
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取部署任务列表失败: {str(e)}")


@router.get("/deploy-tasks/{task_id}")
async def get_deploy_task(request: Request, task_id: str):
    """获取部署任务详情"""
    try:
        username = get_current_username(request)
        task_manager = DeployTaskManager()
        
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="部署任务不存在")
        
        return JSONResponse({
            "success": True,
            "task": task
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取部署任务失败: {str(e)}")


@router.post("/deploy-tasks/{task_id}/execute")
async def execute_deploy_task(
    request: Request,
    task_id: str,
    execute_req: Optional[DeployTaskExecuteRequest] = None
):
    """执行部署任务"""
    try:
        username = get_current_username(request)
        task_manager = DeployTaskManager()
        
        target_names = None
        if execute_req and execute_req.target_names:
            target_names = execute_req.target_names
        
        result = await task_manager.execute_task(task_id, target_names=target_names)
        
        # 记录操作日志
        OperationLogger.log(
            username,
            "deploy_task_execute",
            {"task_id": task_id, "target_names": target_names}
        )
        
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"执行部署任务失败: {str(e)}")


@router.post("/deploy-tasks/import")
async def import_deploy_task(request: Request, file: UploadFile = File(...)):
    """导入部署任务（从YAML文件）"""
    try:
        username = get_current_username(request)
        
        # 读取文件内容
        content = await file.read()
        config_content = content.decode("utf-8")
        
        task_manager = DeployTaskManager()
        task = task_manager.create_task(config_content=config_content)
        
        # 记录操作日志
        OperationLogger.log(
            username,
            "deploy_task_import",
            {"task_id": task["task_id"], "filename": file.filename}
        )
        
        return JSONResponse({
            "success": True,
            "task": task
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"导入部署任务失败: {str(e)}")


@router.get("/deploy-tasks/{task_id}/export")
async def export_deploy_task(request: Request, task_id: str):
    """导出部署任务（YAML格式）"""
    try:
        username = get_current_username(request)
        task_manager = DeployTaskManager()
        
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="部署任务不存在")
        
        config_content = task.get("config_content", "")
        
        return PlainTextResponse(
            content=config_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f'attachment; filename="deploy-task-{task_id}.yaml"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"导出部署任务失败: {str(e)}")


@router.delete("/deploy-tasks/{task_id}")
async def delete_deploy_task(request: Request, task_id: str):
    """删除部署任务"""
    try:
        username = get_current_username(request)
        task_manager = DeployTaskManager()
        
        success = task_manager.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="部署任务不存在")
        
        # 记录操作日志
        OperationLogger.log(username, "deploy_task_delete", {"task_id": task_id})
        
        return JSONResponse({"success": True, "message": "部署任务已删除"})
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除部署任务失败: {str(e)}")

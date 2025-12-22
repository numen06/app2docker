# handlers.py
import json
import os
import re
import shutil
import subprocess
import threading
import urllib
import uuid
import gzip
import zipfile
import tarfile
from datetime import datetime, timedelta
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler
from urllib import parse
from typing import Optional, List
import yaml

from backend.config import (
    load_config,
    save_config,
    CONFIG_FILE,
    get_git_config,
    get_registry_by_name,
    get_active_registry,
    get_all_registries,
)
from backend.utils import generate_image_name, get_safe_filename
from backend.auth import authenticate, verify_token, require_auth

# 目录配置
UPLOAD_DIR = "data/uploads"
BUILD_DIR = "data/docker_build"
EXPORT_DIR = "data/exports"
LOGS_DIR = "data/logs"  # 操作日志目录
# 模板目录：内置模板（只读）+ 用户自定义模板（可读写）
BUILTIN_TEMPLATES_DIR = "templates"  # 内置模板，打包到Docker镜像中
USER_TEMPLATES_DIR = "data/templates"  # 用户自定义模板，通过Docker映射持久化
# 前端文件
DIST_DIR = "dist"  # 前端构建产物
INDEX_FILE = "dist/index.html"  # 前端入口文件

# 导入 Docker 构建器
from backend.docker_builder import create_docker_builder

# 全局 Docker 构建器（在配置更新时会重新创建）
docker_builder = None
DOCKER_AVAILABLE = False


def init_docker_builder():
    """初始化 Docker 构建器"""
    global docker_builder, DOCKER_AVAILABLE
    config = load_config()
    docker_config = config.get("docker", {})
    docker_builder = create_docker_builder(docker_config)
    DOCKER_AVAILABLE = docker_builder.is_available()
    print(f"🐳 Docker 构建器已初始化: {docker_builder.get_connection_info()}")
    return docker_builder


# 在模块加载时初始化
try:
    init_docker_builder()
except Exception as e:
    print(f"⚠️ 初始化 Docker 构建器失败: {e}")


def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)
    ]


def validate_and_clean_image_name(image_name: str) -> str:
    """
    验证和清理镜像名称

    Args:
        image_name: 原始镜像名称

    Returns:
        清理后的镜像名称

    Raises:
        ValueError: 如果镜像名称格式无效
    """
    if not image_name:
        raise ValueError("镜像名称不能为空")

    # 去除首尾空格
    image_name = image_name.strip()

    if not image_name:
        raise ValueError("镜像名称不能为空")

    # 检查协议前缀（http:// 或 https://）- Docker API 不接受协议前缀
    if image_name.startswith("https://") or image_name.startswith("http://"):
        # 提取正确的镜像名称（移除协议前缀）
        if image_name.startswith("https://"):
            cleaned_name = image_name[8:]
        else:
            cleaned_name = image_name[7:]

        raise ValueError(
            f"镜像名称不能包含协议前缀（http:// 或 https://）。"
            f"请使用格式: {cleaned_name}，而不是 {image_name}"
        )

    # 验证镜像名称格式（Docker 镜像名称的基本规则）
    # 镜像名称不能包含空格、特殊字符等
    if " " in image_name:
        raise ValueError("镜像名称不能包含空格")

    # 验证镜像名称长度
    if len(image_name) > 255:
        raise ValueError("镜像名称长度不能超过 255 个字符")

    return image_name


# === 模板目录辅助函数 ===
def get_all_templates():
    """获取所有模板列表（内置 + 用户自定义），支持子目录分类，用户模板优先"""
    templates = {}

    def scan_templates(base_dir, template_type):
        """扫描模板目录，支持子目录（项目类型）"""
        if not os.path.exists(base_dir):
            return

        # 扫描根目录的模板（向后兼容）
        for f in os.listdir(base_dir):
            if f.endswith(".Dockerfile"):
                name = f.replace(".Dockerfile", "")
                # 从文件名推断项目类型（兼容模式）
                project_type = "nodejs" if "node" in name.lower() else "jar"
                templates[name] = {
                    "name": name,
                    "path": os.path.join(base_dir, f),
                    "type": template_type,
                    "project_type": project_type,
                }

        # 扫描子目录（项目类型目录）
        for project_type in os.listdir(base_dir):
            type_dir = os.path.join(base_dir, project_type)
            if not os.path.isdir(type_dir):
                continue

            # 跳过隐藏目录和特殊目录
            if project_type.startswith(".") or project_type.startswith("_"):
                continue

            for f in os.listdir(type_dir):
                if f.endswith(".Dockerfile"):
                    name = f.replace(".Dockerfile", "")
                    templates[name] = {
                        "name": name,
                        "path": os.path.join(type_dir, f),
                        "type": template_type,
                        "project_type": project_type,
                    }

    # 1. 先加载内置模板
    scan_templates(BUILTIN_TEMPLATES_DIR, "builtin")

    # 2. 再加载用户自定义模板（会覆盖同名内置模板）
    scan_templates(USER_TEMPLATES_DIR, "user")

    return templates


def get_template_path(template_name, project_type=None):
    """获取指定模板的文件路径，支持子目录，优先返回用户自定义模板"""
    filename = f"{template_name}.Dockerfile"

    # 如果指定了项目类型，优先在对应子目录中查找
    if project_type:
        # 优先查找用户自定义模板（子目录）
        user_type_path = os.path.join(USER_TEMPLATES_DIR, project_type, filename)
        if os.path.exists(user_type_path):
            return user_type_path

        # 查找内置模板（子目录）
        builtin_type_path = os.path.join(BUILTIN_TEMPLATES_DIR, project_type, filename)
        if os.path.exists(builtin_type_path):
            return builtin_type_path

    # 如果没有指定项目类型，遍历所有子目录查找
    if not project_type:
        for ptype in ["jar", "nodejs", "python", "go", "rust", "web"]:
            # 用户模板目录
            user_type_path = os.path.join(USER_TEMPLATES_DIR, ptype, filename)
            if os.path.exists(user_type_path):
                return user_type_path

            # 内置模板目录
            builtin_type_path = os.path.join(BUILTIN_TEMPLATES_DIR, ptype, filename)
            if os.path.exists(builtin_type_path):
                return builtin_type_path

    # 在根目录查找（向后兼容）
    user_path = os.path.join(USER_TEMPLATES_DIR, filename)
    if os.path.exists(user_path):
        return user_path

    builtin_path = os.path.join(BUILTIN_TEMPLATES_DIR, filename)
    if os.path.exists(builtin_path):
        return builtin_path

    return None


def get_user_template_path(template_name, project_type="jar"):
    """获取用户模板的保存路径（用于新建/编辑），保存到对应的项目类型子目录"""
    type_dir = os.path.join(USER_TEMPLATES_DIR, project_type)
    os.makedirs(type_dir, exist_ok=True)
    return os.path.join(type_dir, f"{template_name}.Dockerfile")


def parse_dockerfile_services(dockerfile_content: str) -> tuple:
    """
    解析 Dockerfile，识别所有服务阶段（FROM ... AS <stage_name>）
    返回服务列表，包含服务名称和所有动态参数

    Args:
        dockerfile_content: Dockerfile 内容字符串

    Returns:
        (services, global_param_names): 元组
        - services: 服务列表，每个服务包含：
          - name: 服务名称（阶段名）
          - template_params: 该服务的模板参数列表（如果有）
          - 其他动态参数（port, user, workdir, env, cmd, entrypoint 等）
        - global_param_names: 全局模板参数名称集合（在第一个 FROM 之前）
    """
    services = []

    # 需要排除的非服务阶段名称（常见的构建阶段）
    # 注意：只排除明确的构建阶段，不要排除可能作为最终镜像的阶段
    excluded_stages = {"builder", "build", "runtime", "deps", "dependencies"}
    # 排除以 -builder 结尾的阶段（如 frontend-builder），但保留 -base 结尾的（如 backend-base 可能是最终镜像）
    excluded_suffixes = ["-builder"]

    def is_excluded_stage(stage_name: str) -> bool:
        """检查阶段名称是否应该被排除（不识别为服务）"""
        stage_lower = stage_name.lower()
        # 完全匹配排除列表
        if stage_lower in excluded_stages:
            return True
        # 匹配排除的后缀（如 -builder）
        for suffix in excluded_suffixes:
            if stage_lower.endswith(suffix):
                return True
        return False

    lines = dockerfile_content.split("\n")
    current_stage = None
    current_params = {}  # 存储当前阶段的所有参数
    global_params = set()  # 存储全局模板参数（在第一个 FROM 之前）
    first_from_found = False

    # 正则表达式
    from_as_pattern = re.compile(r"FROM\s+.*?\s+AS\s+([a-zA-Z0-9_-]+)", re.IGNORECASE)
    from_pattern = re.compile(r"FROM\s+.*?(?:\s+AS\s+([a-zA-Z0-9_-]+))?", re.IGNORECASE)
    expose_pattern = re.compile(r"EXPOSE\s+(\d+)", re.IGNORECASE)
    user_pattern = re.compile(r"USER\s+([a-zA-Z0-9_-]+|\d+)", re.IGNORECASE)
    workdir_pattern = re.compile(r"WORKDIR\s+(.+)", re.IGNORECASE)
    # ENV 支持两种格式：ENV KEY=value 或 ENV KEY value
    env_pattern = re.compile(r"ENV\s+(.+)", re.IGNORECASE)
    cmd_pattern = re.compile(r"CMD\s+(.+)", re.IGNORECASE)
    entrypoint_pattern = re.compile(r"ENTRYPOINT\s+(.+)", re.IGNORECASE)
    arg_pattern = re.compile(r"ARG\s+([A-Z_][A-Z0-9_]*)(?:=(.+))?", re.IGNORECASE)
    # 模板变量模式：{{VAR_NAME}} 或 {{VAR_NAME:default}}
    template_var_pattern = re.compile(r"\{\{([A-Z_][A-Z0-9_]*?)(?::([^}]+))?\}\}")

    for line in lines:
        # 移除注释和前后空白
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 匹配 FROM ... AS <stage_name>
        from_as_match = from_as_pattern.search(line)
        if from_as_match:
            if not first_from_found:
                first_from_found = True
            # 如果之前有阶段，先保存
            if current_stage and not is_excluded_stage(current_stage):
                service_data = {"name": current_stage, **current_params}
                services.append(service_data)

            # 开始新阶段
            current_stage = from_as_match.group(1)
            current_params = {}
            continue

        # 匹配 FROM（可能没有 AS）
        from_match = from_pattern.search(line)
        if from_match and from_match.group(1):
            if not first_from_found:
                first_from_found = True
            # 如果之前有阶段，先保存
            if current_stage and not is_excluded_stage(current_stage):
                service_data = {"name": current_stage, **current_params}
                services.append(service_data)

            # 开始新阶段
            current_stage = from_match.group(1)
            current_params = {}
            continue

        # 在第一个 FROM 之前，收集全局模板参数
        if not first_from_found:
            for match in template_var_pattern.finditer(line):
                var_name = match.group(1)
                global_params.add(var_name)
            continue

        # 如果当前有阶段，收集信息
        if current_stage:
            # 匹配 EXPOSE
            expose_match = expose_pattern.search(line)
            if expose_match:
                current_params["port"] = int(expose_match.group(1))

            # 匹配 USER
            user_match = user_pattern.search(line)
            if user_match:
                current_params["user"] = user_match.group(1)

            # 匹配 WORKDIR
            workdir_match = workdir_pattern.search(line)
            if workdir_match:
                current_params["workdir"] = workdir_match.group(1).strip().strip("\"'")

            # 匹配 ENV（支持 ENV KEY=value 和 ENV KEY value 两种格式）
            env_match = env_pattern.search(line)
            if env_match:
                if "env" not in current_params:
                    current_params["env"] = {}
                env_line = env_match.group(1).strip()
                # ENV 可能有两种格式：
                # 1. ENV KEY=value
                # 2. ENV KEY value
                if "=" in env_line:
                    # 格式1: KEY=value（可能多个，用空格分隔）
                    parts = env_line.split()
                    for part in parts:
                        if "=" in part:
                            key, value = part.split("=", 1)
                            current_params["env"][key.strip()] = value.strip().strip(
                                "\"'"
                            )
                else:
                    # 格式2: KEY value（单个环境变量）
                    parts = env_line.split(None, 1)
                    if len(parts) >= 2:
                        key = parts[0].strip()
                        value = parts[1].strip().strip("\"'")
                        current_params["env"][key] = value

            # 匹配 CMD
            cmd_match = cmd_pattern.search(line)
            if cmd_match:
                current_params["cmd"] = cmd_match.group(1).strip().strip("[]\"'")

            # 匹配 ENTRYPOINT
            entrypoint_match = entrypoint_pattern.search(line)
            if entrypoint_match:
                current_params["entrypoint"] = (
                    entrypoint_match.group(1).strip().strip("[]\"'")
                )

            # 匹配 ARG（构建参数）
            arg_match = arg_pattern.search(line)
            if arg_match:
                if "args" not in current_params:
                    current_params["args"] = {}
                key = arg_match.group(1).strip()
                value = (
                    arg_match.group(2).strip().strip("\"'")
                    if arg_match.group(2)
                    else ""
                )
                current_params["args"][key] = value

            # 匹配模板变量（{{VAR_NAME}} 或 {{VAR_NAME:default}}）
            for match in template_var_pattern.finditer(line):
                var_name = match.group(1)
                default_value = match.group(2) or ""
                if "template_params" not in current_params:
                    current_params["template_params"] = []
                # 检查是否已存在
                existing = next(
                    (
                        p
                        for p in current_params["template_params"]
                        if p["name"] == var_name
                    ),
                    None,
                )
                if not existing:
                    from backend.template_parser import _get_var_description

                    current_params["template_params"].append(
                        {
                            "name": var_name,
                            "default": default_value.strip(),
                            "required": not bool(default_value),
                            "description": _get_var_description(var_name),
                            "type": "template",
                        }
                    )

    # 保存最后一个阶段
    if current_stage and not is_excluded_stage(current_stage):
        service_data = {"name": current_stage, **current_params}
        services.append(service_data)

    return services, global_params


class App2DockerHandler(BaseHTTPRequestHandler):
    server_version = "App2Docker/1.0"

    def _send_json(self, code, data):
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            )
        except Exception as e:
            print(f"❌ 发送 JSON 响应失败: {e}")

    def _send_html(self, content):
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if isinstance(content, str):
                content = content.encode("utf-8")
            self.wfile.write(content)
        except Exception as e:
            print(f"❌ 发送 HTML 响应失败: {e}")

    def _get_content_type(self, filepath):
        """根据文件扩展名返回 MIME 类型"""
        ext = os.path.splitext(filepath)[1].lower()
        mime_types = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".woff": "application/font-woff",
            ".woff2": "font/woff2",
            ".ttf": "application/font-sfnt",
            ".otf": "application/font-sfnt",
            ".eot": "application/vnd.ms-fontobject",
            ".html": "text/html",
            ".htm": "text/html",
            ".xml": "text/xml",
            ".txt": "text/plain",
        }
        return mime_types.get(ext, "application/octet-stream")

    def _send_file(
        self, filepath, content_type="application/octet-stream", download_name=None
    ):
        try:
            if not os.path.exists(filepath):
                self.send_error(404, "File not found")
                return False

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            if download_name:
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{download_name}"'
                )
            self.send_header("Content-Length", str(os.path.getsize(filepath)))
            self.end_headers()

            with open(filepath, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
            return True
        except Exception as e:
            print(f"❌ 发送文件 {filepath} 失败: {e}")
            return False

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/get-config":
            self.handle_get_config()
        elif path == "/get-logs":
            # 在 do_GET 中：
            parsed_url = parse.urlparse(self.path)
            query_params = parse.parse_qs(parsed_url.query)  # 返回 dict，值是 list
            build_id = query_params.get("build_id", [None])[0]
            if build_id:
                self.handle_get_logs(build_id)
            else:
                self.send_error(400, "缺少 build_id 参数")
        elif path == "/list-templates":
            self.handle_list_templates()
        elif path == "/templates":
            parsed_url = parse.urlparse(self.path)
            query_params = parse.parse_qs(parsed_url.query)
            template_name = (query_params.get("name", [None])[0] or "").strip()
            if template_name:
                self.handle_get_template(template_name)
            else:
                self.handle_templates_summary()
        elif path.startswith("/templates/"):
            rel_path = path[len("/templates/") :].lstrip("/")
            if ".." in rel_path or rel_path.startswith("/"):
                self.send_error(400, "非法模板路径")
                return
            filepath = os.path.join(TEMPLATES_DIR, rel_path)
            abs_templates = os.path.abspath(TEMPLATES_DIR)
            abs_target = os.path.abspath(filepath)
            try:
                if os.path.commonpath([abs_templates, abs_target]) != abs_templates:
                    self.send_error(400, "非法模板路径")
                    return
            except ValueError:
                self.send_error(400, "非法模板路径")
                return
            if os.path.exists(filepath):
                self._send_file(filepath, "text/plain; charset=utf-8")
            else:
                self.send_error(404, "模板不存在")
        elif path == "/export-image":
            parsed_url = parse.urlparse(self.path)
            query_params = parse.parse_qs(parsed_url.query)
            self.handle_export_image(query_params)
        elif path == "/" or path == "/index.html":
            self.serve_index()
        elif path.startswith("/static/"):
            filepath = path.lstrip("/")
            if os.path.exists(filepath):
                # 根据文件扩展名确定 MIME 类型
                content_type = self._get_content_type(filepath)
                self._send_file(filepath, content_type)
            else:
                self.send_error(404)
        elif path.startswith("/favicon"):
            # 处理 favicon 请求
            filepath = path.lstrip("/")
            if os.path.exists(filepath):
                content_type = self._get_content_type(filepath)
                self._send_file(filepath, content_type)
            else:
                self.send_error(404)
        elif path == "/generate_favicon.html":
            # Favicon 生成工具页面
            if os.path.exists("generate_favicon.html"):
                self._send_file("generate_favicon.html", "text/html")
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_PUT(self):
        path = self.path.split("?")[0]
        if path == "/templates":
            self.handle_update_template()
        else:
            self.send_error(404)

    def do_DELETE(self):
        path = self.path.split("?")[0]
        if path == "/templates":
            self.handle_delete_template()
        else:
            self.send_error(404)

    # === 新增：获取日志 ===
    def handle_get_logs(self, build_id):
        try:
            manager = BuildManager()
            logs = manager.get_logs(build_id)  # 假设返回 list[str] 或 str
            log_text = "".join(logs) if isinstance(logs, list) else str(logs)

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(log_text.encode("utf-8"))
        except Exception as e:
            self.send_error(500, f"获取日志失败: {e}")

    def serve_index(self):
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_html(content)
        else:
            self.send_error(404, "index.html not found")

    def handle_login(self):
        """处理登录请求"""
        try:
            data = self._read_json_body()
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()

            if not username or not password:
                self._send_json(400, {"error": "用户名和密码不能为空"})
                return

            result = authenticate(username, password)

            if result["success"]:
                self._send_json(
                    200,
                    {
                        "success": True,
                        "token": result["token"],
                        "username": result["username"],
                        "expires_in": result["expires_in"],
                    },
                )
            else:
                self._send_json(401, {"error": result["error"]})
        except Exception as e:
            self._send_json(500, {"error": f"登录失败: {str(e)}"})

    def handle_logout(self):
        """处理登出请求"""
        # JWT 是无状态的，登出主要在客户端删除 token
        self._send_json(200, {"success": True, "message": "登出成功"})

    def handle_get_config(self):
        try:
            config = load_config()
            docker_config = config.get("docker", {})
            self._send_json(200, {"docker": docker_config})
        except Exception as e:
            import traceback

            traceback.print_exc()
            self._send_json(500, {"error": f"获取配置失败: {str(e)}"})

    def handle_list_templates(self):
        try:
            details = self._collect_template_details()
            templates = [item["name"] for item in details]
            self._send_json(200, {"templates": templates, "template_details": details})
        except Exception as e:
            import traceback

            traceback.print_exc()
            self._send_json(500, {"error": "获取模板列表失败"})

    def handle_templates_summary(self):
        try:
            details = self._collect_template_details()
            self._send_json(
                200, {"templates": [item["name"] for item in details], "items": details}
            )
        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            self._send_json(
                500, {"error": f"获取模板信息失败: {clean_msg or '未知错误'}"}
            )

    def handle_get_template(self, template_name):
        try:
            template_path, clean_name, filename = self._resolve_template_path(
                template_name
            )
            if not os.path.exists(template_path):
                self._send_json(404, {"error": "模板不存在"})
                return
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
            self._send_json(
                200, {"name": clean_name, "filename": filename, "content": content}
            )
        except ValueError as ve:
            self._send_json(400, {"error": str(ve)})
        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            self._send_json(500, {"error": f"获取模板失败: {clean_msg or '未知错误'}"})

    def handle_export_image(self, query_params):
        if not DOCKER_AVAILABLE:
            self._send_json(503, {"error": "Docker 服务不可用，无法导出镜像"})
            return

        image_input = (query_params.get("image", [None])[0] or "").strip()
        tag_param = (query_params.get("tag", [""])[0] or "").strip()
        compress_param = (
            (query_params.get("compress", ["none"])[0] or "none").strip().lower()
        )

        if not image_input:
            self._send_json(400, {"error": "缺少 image 参数"})
            return

        image_name = image_input
        tag = tag_param or "latest"

        if ":" in image_name and not tag_param:
            image_name, inferred_tag = image_name.rsplit(":", 1)
            if inferred_tag:
                tag = inferred_tag

        # 验证和清理镜像名称（检查格式，移除协议前缀等）
        try:
            image_name = validate_and_clean_image_name(image_name)
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
            return

        full_tag = f"{image_name}:{tag}"
        compress_enabled = compress_param in ("gzip", "gz", "tgz", "1", "true", "yes")
        config = load_config()
        docker_cfg = config.get("docker", {})
        username = docker_cfg.get("username")
        password = docker_cfg.get("password")
        auth_config = None
        if username and password:
            auth_config = {"username": username, "password": password}

        try:
            # 使用 docker_builder
            pull_stream = docker_builder.pull_image(image_name, tag, auth_config)
            for chunk in pull_stream:
                if "error" in chunk:
                    raise RuntimeError(chunk["error"])

            docker_builder.get_image(full_tag)  # 确认镜像存在

            os.makedirs(EXPORT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_base = get_safe_filename(image_name.replace("/", "_") or "image")
            tar_filename = f"{safe_base}-{tag}-{timestamp}.tar"
            tar_path = os.path.join(EXPORT_DIR, tar_filename)

            image_stream = docker_builder.export_image(full_tag)
            with open(tar_path, "wb") as f:
                for chunk in image_stream:
                    f.write(chunk)

            final_path = tar_path
            download_name = tar_filename
            content_type = "application/x-tar"

            if compress_enabled:
                final_path = f"{tar_path}.gz"
                download_name = os.path.basename(final_path)
                content_type = "application/gzip"
                with open(tar_path, "rb") as src, gzip.open(final_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                os.remove(tar_path)

            success = self._send_file(
                final_path, content_type, download_name=download_name
            )
            if success:
                try:
                    os.remove(final_path)
                except OSError:
                    pass
        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip() or "未知错误"
            self._send_json(500, {"error": f"导出镜像失败: {clean_msg}"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/login":
            self.handle_login()
        elif path == "/logout":
            self.handle_logout()
        elif path == "/upload":
            self.handle_upload()
        elif path == "/save-config":
            self.handle_save_config()
        elif path == "/suggest-image-name":
            self.handle_suggest_image_name()
        elif path == "/parse-compose":
            self.handle_parse_compose()
        elif path == "/templates":
            self.handle_create_template()
        else:
            self.send_error(404)

    def handle_suggest_image_name(self):
        try:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)

            boundary = self.headers["Content-Type"].split("boundary=")[1].encode()
            parts = body.split(b"--" + boundary)

            app_filename = None
            for part in parts[1:-1]:
                if (
                    b"\r\n\r\n" in part
                    and b'name="jar_file"' in part
                    and b'filename="' in part
                ):
                    headers = part[: part.find(b"\r\n\r\n")].decode(
                        "utf-8", errors="ignore"
                    )
                    match = re.search(r'filename="(.+?)"', headers)
                    if match:
                        app_filename = match.group(1)
                        break

            if not app_filename:
                self._send_json(400, {"error": "未找到文件"})
                return

            # 使用激活仓库的 registry_prefix
            from backend.config import get_active_registry

            active_registry = get_active_registry()
            base_name = active_registry.get("registry_prefix", "")
            suggested_name = generate_image_name(base_name, app_filename)
            self._send_json(200, {"suggested_imagename": suggested_name})

        except Exception as e:
            import traceback

            traceback.print_exc()
            self._send_json(500, {"error": f"生成镜像名失败: {str(e)}"})

    def handle_save_config(self):
        try:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)

            boundary = self.headers["Content-Type"].split("boundary=")[1].encode()
            parts = body.split(b"--" + boundary)
            form_data = {}

            for part in parts[1:-1]:
                if b"\r\n\r\n" in part:
                    header_end = part.find(b"\r\n\r\n")
                    headers = part[:header_end].decode("utf-8", errors="ignore")
                    data = part[header_end + 4 :].rstrip(b"\r\n")

                    if 'name="' in headers:
                        try:
                            field_name = headers.split('name="')[1].split('"')[0]
                            form_data[field_name] = data.decode(
                                "utf-8", errors="ignore"
                            )
                        except:
                            continue

            config = load_config()
            new_docker_config = {
                "registry": form_data.get("registry", "docker.io").strip(),
                "registry_prefix": form_data.get("registry_prefix", "")
                .strip()
                .rstrip("/"),
                "default_push": (form_data.get("default_push") == "on"),
                "username": form_data.get("username", "").strip(),
                "password": form_data.get("password", "").strip(),
                "expose_port": (
                    int(form_data.get("expose_port", "8080"))
                    if form_data.get("expose_port", "").isdigit()
                    else 8080
                ),
                # 远程 Docker 配置
                "use_remote": (form_data.get("use_remote") == "on"),
                "remote": {
                    "host": form_data.get("remote_host", "").strip(),
                    "port": (
                        int(form_data.get("remote_port", "2375"))
                        if form_data.get("remote_port", "").isdigit()
                        else 2375
                    ),
                    "use_tls": (form_data.get("remote_use_tls") == "on"),
                    "cert_path": form_data.get("remote_cert_path", "").strip(),
                    "verify_tls": (form_data.get("remote_verify_tls", "on") == "on"),
                },
            }

            if "docker" not in config:
                config["docker"] = {}
            config["docker"].update(new_docker_config)

            save_config(config)

            # 重新初始化 Docker 构建器
            global docker_builder, DOCKER_AVAILABLE
            docker_builder = init_docker_builder()
            DOCKER_AVAILABLE = docker_builder.is_available()

            print(f"✅ 配置已更新: {config['docker']}")
            self._send_json(
                200,
                {"message": "Docker 配置保存成功！", "docker_config": config["docker"]},
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            error_msg = str(e)
            clean_error_msg = re.sub(r"[\x00-\x1F\x7F]", " ", error_msg).strip()
            self._send_json(500, {"error": f"保存配置失败: {clean_error_msg}"})

    def _collect_template_details(self):
        """收集所有模板详情（内置 + 用户自定义）"""
        details = []
        templates = get_all_templates()

        for name, info in templates.items():
            try:
                stat = os.stat(info["path"])
                details.append(
                    {
                        "name": name,
                        "filename": os.path.basename(info["path"]),
                        "size": stat.st_size,
                        "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": info["type"],  # 'builtin' 或 'user'
                        "project_type": info.get(
                            "project_type", "jar"
                        ),  # 项目类型：jar 或 nodejs
                        "editable": info["type"] == "user",  # 只有用户模板可编辑
                    }
                )
            except OSError:
                continue

        details.sort(key=lambda item: natural_sort_key(item["name"]))
        return details

    def _extract_images_from_compose(self, compose_doc):
        images = []
        if not isinstance(compose_doc, dict):
            return images
        services = compose_doc.get("services", {})
        if isinstance(services, dict):
            for service_name, service_conf in services.items():
                if not isinstance(service_conf, dict):
                    continue
                image_ref = service_conf.get("image")
                if image_ref:
                    image_name, tag = self._split_image_reference(
                        str(image_ref).strip()
                    )
                    if image_name:
                        images.append(
                            {
                                "service": service_name,
                                "image": image_name,
                                "tag": tag,
                                "raw": image_ref,
                            }
                        )
        return images

    def _split_image_reference(self, reference: str):
        if not reference:
            return "", "latest"
        if "@" in reference:
            name, digest = reference.split("@", 1)
            return name or "", digest or "latest"
        slash_index = reference.rfind("/")
        colon_index = reference.rfind(":")
        if colon_index > slash_index:
            name = reference[:colon_index]
            tag = reference[colon_index + 1 :] or "latest"
            return name or "", tag
        return reference, "latest"

    def _resolve_template_path(self, template_name, for_write=False):
        """解析模板路径
        Args:
            template_name: 模板名称
            for_write: 是否用于写入操作（新建/编辑/删除）
        Returns:
            (filepath, clean_name, filename)
        """
        clean_name = (
            get_safe_filename(template_name).replace(".Dockerfile", "").strip("_-. ")
        )
        if not clean_name:
            raise ValueError("模板名称无效")
        filename = f"{clean_name}.Dockerfile"

        # 写入操作：只能操作用户模板目录
        if for_write:
            filepath = os.path.join(USER_TEMPLATES_DIR, filename)
        else:
            # 读取操作：优先使用用户模板，否则使用内置模板
            filepath = get_template_path(clean_name)
            if not filepath:
                # 模板不存在，返回用户模板路径（用于后续判断）
                filepath = os.path.join(USER_TEMPLATES_DIR, filename)

        return filepath, clean_name, filename

    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"请求体不是有效 JSON: {e}")

    def handle_parse_compose(self):
        try:
            data = self._read_json_body()
        except ValueError as ve:
            self._send_json(400, {"error": str(ve)})
            return

        content = (data.get("content") or "").strip()
        if not content:
            self._send_json(400, {"error": "compose 内容不能为空"})
            return

        try:
            documents = list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            self._send_json(
                400, {"error": f"解析 YAML 失败: {clean_msg or '未知错误'}"}
            )
            return

        images = []
        seen = set()
        for doc in documents:
            for item in self._extract_images_from_compose(doc):
                key = f"{item['image']}:{item['tag']}"
                if key in seen:
                    continue
                seen.add(key)
                images.append(item)

        self._send_json(200, {"images": images})

    def handle_create_template(self):
        try:
            data = self._read_json_body()
            name = (data.get("name") or "").strip()
            content = data.get("content")
            project_type = (data.get("project_type") or "jar").strip()

            if not name:
                self._send_json(400, {"error": "模板名称不能为空"})
                return
            if not content:
                self._send_json(400, {"error": "模板内容不能为空"})
                return

            # 验证项目类型格式：只允许小写字母、数字、下划线和连字符
            if not re.match(r"^[a-z0-9_-]+$", project_type):
                self._send_json(
                    400, {"error": "项目类型只能包含小写字母、数字、下划线和连字符"}
                )
                return

            # 使用项目类型子目录保存
            filepath = get_user_template_path(name, project_type)
            if os.path.exists(filepath):
                self._send_json(
                    400, {"error": f"用户模板中已存在同名模板（{project_type}）"}
                )
                return

            # 写入文件
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            self._send_json(
                201,
                {
                    "message": f"模板创建成功（保存到用户模板/{project_type}/目录）",
                    "template": {
                        "name": name,
                        "project_type": project_type,
                        "filename": os.path.basename(filepath),
                    },
                },
            )
        except ValueError as ve:
            self._send_json(400, {"error": str(ve)})
        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            self._send_json(500, {"error": f"创建模板失败: {clean_msg or '未知错误'}"})

    def handle_update_template(self):
        try:
            data = self._read_json_body()
            original_name = (
                data.get("original_name") or data.get("name") or ""
            ).strip()
            new_name = (data.get("name") or "").strip()
            content = data.get("content")
            project_type = (data.get("project_type") or "").strip()

            if not original_name:
                self._send_json(400, {"error": "缺少原始模板名称"})
                return
            if content is None:
                self._send_json(400, {"error": "模板内容不能为空"})
                return

            # 检查原模板是否存在
            templates = get_all_templates()
            if original_name not in templates:
                self._send_json(404, {"error": "原模板不存在"})
                return

            original_template = templates[original_name]
            is_builtin = original_template["type"] == "builtin"
            original_project_type = original_template["project_type"]

            # 使用提供的项目类型，如果没有则使用原模板的项目类型
            target_project_type = project_type or original_project_type

            # 验证项目类型格式
            if target_project_type and not re.match(
                r"^[a-z0-9_-]+$", target_project_type
            ):
                self._send_json(
                    400, {"error": "项目类型只能包含小写字母、数字、下划线和连字符"}
                )
                return

            target_name = new_name or original_name

            # 如果是内置模板，只能在用户目录创建同名覆盖
            if is_builtin:
                if new_name and new_name != original_name:
                    self._send_json(
                        403,
                        {
                            "error": "内置模板不能重命名，只能在用户模板中创建同名模板进行覆盖"
                        },
                    )
                    return
                # 内置模板不允许修改项目类型
                if target_project_type != original_project_type:
                    self._send_json(
                        403,
                        {"error": "内置模板的项目类型不可修改"},
                    )
                    return
                # 在用户目录的对应项目类型子目录中创建
                dst_path = get_user_template_path(target_name, target_project_type)
            else:
                # 用户模板可以编辑和重命名
                src_path = original_template["path"]
                dst_path = get_user_template_path(target_name, target_project_type)

                # 检查目标路径是否已存在（且不是原文件）
                if dst_path != src_path and os.path.exists(dst_path):
                    self._send_json(400, {"error": "目标模板名称已存在"})
                    return

            # 写入新内容
            tmp_path = dst_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, dst_path)

            # 如果是用户模板的重命名或项目类型修改，删除原文件
            if not is_builtin and dst_path != original_template["path"]:
                try:
                    os.remove(original_template["path"])
                except OSError:
                    pass  # 如果删除失败也不影响

            # 构建成功消息
            if is_builtin:
                message = "模板已保存到用户目录"
            elif target_project_type != original_project_type:
                message = f"模板已更新并移动到 {target_project_type} 目录"
            else:
                message = "模板更新成功"

            self._send_json(
                200,
                {
                    "message": message,
                    "template": {
                        "name": target_name,
                        "project_type": target_project_type,
                        "filename": os.path.basename(dst_path),
                    },
                },
            )
        except ValueError as ve:
            self._send_json(400, {"error": str(ve)})
        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            self._send_json(500, {"error": f"更新模板失败: {clean_msg or '未知错误'}"})

    def handle_delete_template(self):
        try:
            data = self._read_json_body()
            name = (data.get("name") or "").strip()
            if not name:
                self._send_json(400, {"error": "模板名称不能为空"})
                return

            # 检查是否为内置模板
            templates = get_all_templates()
            if name in templates and templates[name]["type"] == "builtin":
                self._send_json(
                    403,
                    {"error": "内置模板不可删除，请在用户模板中创建同名模板进行覆盖"},
                )
                return

            filepath, clean_name, filename = self._resolve_template_path(
                name, for_write=True
            )
            if not os.path.exists(filepath):
                self._send_json(404, {"error": "模板不存在"})
                return
            os.remove(filepath)
            self._send_json(200, {"message": "模板已删除"})
        except ValueError as ve:
            self._send_json(400, {"error": str(ve)})
        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            self._send_json(500, {"error": f"删除模板失败: {clean_msg or '未知错误'}"})

    def handle_upload(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)

        try:
            boundary = self.headers["Content-Type"].split("boundary=")[1].encode()
            parts = body.split(b"--" + boundary)
            form_data = {}
            file_data = None
            file_name = None

            for part in parts[1:-1]:
                if b"\r\n\r\n" not in part:
                    continue
                header_end = part.find(b"\r\n\r\n")
                headers = part[:header_end].decode("utf-8", errors="ignore")
                data = part[header_end + 4 :].rstrip(b"\r\n")

                if "filename=" in headers:
                    try:
                        filename = headers.split("filename=")[1].split('"')[1]
                        # 支持多种文件类型：jar, zip, tar, tar.gz
                        if filename.endswith(
                            (".jar", ".zip", ".tar", ".tar.gz", ".tgz")
                        ):
                            file_data = data
                            file_name = filename
                            form_data["original_filename"] = filename
                    except Exception as e:
                        print(f"⚠️ 解析文件名失败: {e}")
                        continue
                else:
                    try:
                        field_name = headers.split('name="')[1].split('"')[0]
                        form_data[field_name] = data.decode("utf-8", errors="ignore")
                    except Exception as e:
                        print(f"⚠️ 解析字段失败: {e}")
                        continue

            if not file_data:
                self._send_json(400, {"error": "未上传文件"})
                return

            # 获取项目类型
            project_type = form_data.get("project_type", "jar")  # jar 或 nodejs

            # 生成基础名称
            base_name = file_name
            for ext in [".jar", ".zip", ".tar.gz", ".tgz", ".tar"]:
                if base_name.endswith(ext):
                    base_name = base_name[: -len(ext)]
                    break

            image_name = form_data.get("imagename") or f"myapp/{base_name}"
            tag = form_data.get("tag") or "latest"
            should_push = form_data.get("push") == "on"
            selected_template = form_data.get("template") or (
                "node20" if project_type == "nodejs" else "dragonwell17"
            )

            # 👇 启动后台构建，立即返回 build_id
            build_manager = BuildManager()
            build_id = build_manager.start_build(
                file_data=file_data,
                image_name=image_name,
                tag=tag,
                should_push=should_push,
                selected_template=selected_template,
                original_filename=file_name,
                project_type=project_type,
            )

            self._send_json(
                200,
                {
                    "build_id": build_id,
                    "message": "构建任务已启动，请通过 WebSocket 订阅日志",
                },
            )

        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            print(f"❌ 上传处理失败: {clean_msg}")
            import traceback

            traceback.print_exc()
            self._send_json(500, {"error": f"服务器错误: {clean_msg}"})

    def log_message(self, format, *args):
        return  # 静音日志


def _retry_login_and_push(
    docker_builder,
    repository: str,
    tag: str,
    auth_config: dict,
    username: str = None,
    password: str = None,
    registry_host: str = None,
    log_func=None,
):
    """
    在推送失败时尝试重新登录并重试推送

    Args:
        docker_builder: Docker构建器实例
        repository: 镜像仓库名称
        tag: 镜像标签
        auth_config: 认证配置字典
        username: 用户名（用于重试登录）
        password: 密码（用于重试登录）
        registry_host: Registry地址（用于重试登录）
        log_func: 日志函数

    Returns:
        bool: 是否成功重新登录
    """
    if log_func is None:
        log_func = print

    if not (username and password):
        return False

    try:
        if hasattr(docker_builder, "client") and docker_builder.client:
            login_registry = (
                registry_host
                if registry_host and registry_host != "docker.io"
                else None
            )
            log_func(f"🔑 重新登录到registry: {login_registry or 'docker.io'}\n")
            login_result = docker_builder.client.login(
                username=username,
                password=password,
                registry=login_registry,
            )
            log_func(f"✅ 重新登录成功\n")
            return True
    except Exception as e:
        log_func(f"❌ 重新登录失败: {str(e)}\n")
    return False


class BuildManager:
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
        self.logs = defaultdict(deque)  # build_id -> deque[str] (保留用于兼容)
        self.lock = threading.Lock()
        self.tasks = {}  # build_id -> Thread (保留用于兼容)
        self.task_manager = BuildTaskManager()  # 使用任务管理器

    def start_build(
        self,
        file_data: bytes,
        image_name: str,
        tag: str,
        should_push: bool,
        selected_template: str,
        original_filename: str,
        project_type: str = "jar",
        template_params: dict = None,
        push_registry: str = None,  # 已废弃，保留以兼容旧代码，实际不再使用
        extract_archive: bool = True,  # 是否解压压缩包（默认解压）
        build_steps: dict = None,  # 构建步骤信息
        resource_package_ids: list = None,  # 资源包ID列表
    ):
        # 创建任务
        task_id = self.task_manager.create_task(
            task_type="build",
            image_name=image_name,
            tag=tag,
            should_push=should_push,
            selected_template=selected_template,
            original_filename=original_filename,
            project_type=project_type,
            template_params=template_params or {},
            push_registry=push_registry,
            extract_archive=extract_archive,
            build_steps=build_steps or {},  # 传递构建步骤信息
            resource_package_ids=resource_package_ids or [],  # 传递资源包配置
        )

        thread = threading.Thread(
            target=self._build_task,
            args=(
                task_id,
                file_data,
                image_name,
                tag,
                should_push,
                selected_template,
                original_filename,
                project_type,
                template_params or {},
                push_registry,
                extract_archive,
                resource_package_ids or [],
            ),
            daemon=True,
        )
        thread.start()
        with self.lock:
            self.tasks[task_id] = thread
        return task_id

    def _build_task(
        self,
        task_id: str,
        file_data: bytes,
        image_name: str,
        tag: str,
        should_push: bool,
        selected_template: str,
        original_filename: str,
        project_type: str = "jar",
        template_params: dict = None,
        push_registry: str = None,  # 已废弃，保留以兼容旧代码，实际不再使用
        extract_archive: bool = True,  # 是否解压压缩包（默认解压）
        resource_package_ids: list = None,  # 资源包ID列表
    ):
        full_tag = f"{image_name}:{tag}"
        # 使用 task_id 作为构建上下文目录名的一部分，避免冲突
        build_context = os.path.join(
            BUILD_DIR, f"{image_name.replace('/', '_')}_{task_id[:8]}"
        )

        # 构建上下文路径不需要保存到数据库（临时路径）
        # 如果需要，可以通过 task_id 和 image_name 推导

        def log(msg: str):
            """添加日志，自动确保以换行符结尾"""
            if not msg.endswith("\n"):
                msg = msg + "\n"
            # 使用任务管理器记录日志
            self.task_manager.add_log(task_id, msg)
            # 保留旧的日志系统用于兼容
            with self.lock:
                self.logs[task_id].append(msg)

        # 更新任务状态为运行中
        self.task_manager.update_task_status(task_id, "running")

        def do_extract_archive(file_path: str, extract_to: str):
            """解压压缩文件"""
            try:
                # 获取压缩包大小
                archive_size = os.path.getsize(file_path)
                if archive_size < 1024:
                    archive_size_str = f"{archive_size} B"
                elif archive_size < 1024 * 1024:
                    archive_size_str = f"{archive_size / 1024:.2f} KB"
                else:
                    archive_size_str = f"{archive_size / (1024 * 1024):.2f} MB"

                log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
                log(f"📦 开始解压压缩包\n")
                log(f"  文件路径: {file_path}\n")
                log(f"  文件大小: {archive_size_str}\n")
                log(f"  解压目标: {extract_to}\n")
                log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

                if file_path.endswith(".zip"):
                    log("📦 检测到 ZIP 格式，开始解压...\n")
                    with zipfile.ZipFile(file_path, "r") as zip_ref:
                        # 获取压缩包内的文件列表
                        file_list = zip_ref.namelist()
                        log(f"  压缩包内包含 {len(file_list)} 个文件/目录\n")
                        zip_ref.extractall(extract_to)
                elif file_path.endswith((".tar.gz", ".tgz")):
                    log("📦 检测到 TAR.GZ 格式，开始解压...\n")
                    with tarfile.open(file_path, "r:gz") as tar_ref:
                        # 获取压缩包内的文件列表
                        file_list = tar_ref.getnames()
                        log(f"  压缩包内包含 {len(file_list)} 个文件/目录\n")
                        tar_ref.extractall(extract_to)
                elif file_path.endswith(".tar"):
                    log("📦 检测到 TAR 格式，开始解压...\n")
                    with tarfile.open(file_path, "r") as tar_ref:
                        # 获取压缩包内的文件列表
                        file_list = tar_ref.getnames()
                        log(f"  压缩包内包含 {len(file_list)} 个文件/目录\n")
                        tar_ref.extractall(extract_to)
                else:
                    log(f"❌ 不支持的压缩格式: {file_path}\n")
                    return False

                log("✅ 解压操作完成\n")
                log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

                # 列出解压后的目录概况和文件
                try:
                    log("📂 解压后构建根目录概况：\n")
                    log(f"  构建上下文路径: {extract_to}\n")

                    if os.path.exists(extract_to):
                        # 统计根目录下的直接内容
                        root_items = os.listdir(extract_to)
                        dirs = []
                        files = []
                        total_size = 0
                        total_files = 0

                        for item in root_items:
                            item_path = os.path.join(extract_to, item)
                            if os.path.isdir(item_path):
                                dirs.append(item)
                            elif os.path.isfile(item_path):
                                files.append(item)

                        # 递归统计所有文件大小和数量
                        for root, dirs_list, files_list in os.walk(extract_to):
                            for f in files_list:
                                file_path_full = os.path.join(root, f)
                                if os.path.isfile(file_path_full):
                                    total_size += os.path.getsize(file_path_full)
                                    total_files += 1

                        # 格式化大小
                        if total_size < 1024:
                            size_str = f"{total_size} B"
                        elif total_size < 1024 * 1024:
                            size_str = f"{total_size / 1024:.2f} KB"
                        elif total_size < 1024 * 1024 * 1024:
                            size_str = f"{total_size / (1024 * 1024):.2f} MB"
                        else:
                            size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"

                        log(f"  📁 根目录下目录数: {len(dirs)}\n")
                        log(f"  📄 根目录下文件数: {len(files)}\n")
                        log(f"  📊 解压后总文件数: {total_files}\n")
                        log(f"  💾 解压后总大小: {size_str}\n")
                        log(f"\n")

                        if dirs:
                            log("  📁 根目录下的目录列表：\n")
                            for d in sorted(dirs)[:20]:  # 最多显示20个
                                dir_path = os.path.join(extract_to, d)
                                if os.path.isdir(dir_path):
                                    # 统计目录下的文件数
                                    dir_file_count = sum(
                                        len(files) for _, _, files in os.walk(dir_path)
                                    )
                                    log(f"    📂 {d}/ ({dir_file_count} 个文件)\n")
                            if len(dirs) > 20:
                                log(f"    ... 还有 {len(dirs) - 20} 个目录\n")
                            log(f"\n")

                        if files:
                            log("  📄 根目录下的文件列表：\n")
                            for f in sorted(files)[:30]:  # 最多显示30个
                                file_path_full = os.path.join(extract_to, f)
                                if os.path.isfile(file_path_full):
                                    size = os.path.getsize(file_path_full)
                                    if size < 1024:
                                        f_size_str = f"{size} B"
                                    elif size < 1024 * 1024:
                                        f_size_str = f"{size / 1024:.2f} KB"
                                    elif size < 1024 * 1024 * 1024:
                                        f_size_str = f"{size / (1024 * 1024):.2f} MB"
                                    else:
                                        f_size_str = (
                                            f"{size / (1024 * 1024 * 1024):.2f} GB"
                                        )
                                    log(f"    📄 {f} ({f_size_str})\n")
                            if len(files) > 30:
                                log(f"    ... 还有 {len(files) - 30} 个文件\n")
                            log(f"\n")

                        log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
                        log(f"✅ 解压完成，构建上下文已准备就绪\n")
                        log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
                except Exception as e:
                    log(f"⚠️  无法列出目录内容: {str(e)}\n")
                    import traceback

                    log(f"    {traceback.format_exc()}\n")

                return True
            except Exception as e:
                log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
                log(f"❌ 解压失败: {str(e)}\n")
                import traceback

                log(f"    {traceback.format_exc()}\n")
                log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
                return False

        try:
            log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            log(f"🚀 开始构建任务\n")
            log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            log(f"📦 开始处理上传: {original_filename}\n")
            log(f"📝 上传的文件名: {original_filename}\n")
            log(f"🏷️ 镜像名: {full_tag}\n")
            log(f"🧱 模板: {selected_template}\n")
            log(f"📂 项目类型: {project_type}\n")
            log(f"📁 构建上下文路径: {build_context}\n")

            # 判断文件类型
            is_jar = original_filename.lower().endswith(".jar")
            is_archive = any(
                original_filename.lower().endswith(ext)
                for ext in [".zip", ".tar", ".tar.gz", ".tgz"]
            )

            if is_archive:
                log(f"📦 文件类型: 压缩包\n")
                log(
                    f"🔧 解压选项: {'已启用（将解压到构建根目录）' if extract_archive else '未启用（保持压缩包原样）'}\n"
                )
            elif is_jar:
                log(f"📦 文件类型: JAR 文件\n")
            else:
                log(f"📦 文件类型: 普通文件\n")
            log(f"\n")

            # === 模拟模式 ===
            if not DOCKER_AVAILABLE:
                config = load_config()
                os.makedirs(build_context, exist_ok=True)

                # 判断文件类型并处理（模拟模式）
                is_jar = original_filename.lower().endswith(".jar")
                is_archive = any(
                    original_filename.lower().endswith(ext)
                    for ext in [".zip", ".tar", ".tar.gz", ".tgz"]
                )

                if is_archive:
                    # 压缩包：根据用户选择决定是否解压
                    file_path = os.path.join(build_context, original_filename)
                    log(f"🧪 模拟模式：保存压缩包文件...\n")
                    log(f"  构建上下文路径: {build_context}\n")
                    log(f"  压缩包文件路径: {file_path}\n")

                    with open(file_path, "wb") as f:
                        f.write(file_data)

                    file_size = os.path.getsize(file_path)
                    if file_size < 1024:
                        file_size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        file_size_str = f"{file_size / 1024:.2f} KB"
                    else:
                        file_size_str = f"{file_size / (1024 * 1024):.2f} MB"
                    log(f"  文件大小: {file_size_str}\n")
                    log(f"✅ 模拟模式：压缩包文件保存完成\n\n")

                    if extract_archive:
                        # 用户选择解压
                        log(f"🧪 模拟模式：解压选项已启用（将解压到构建根目录）\n")
                        if do_extract_archive(file_path, build_context):
                            log(
                                f"🧪 模拟模式：压缩包已解压到构建上下文根目录（原始文件名: {original_filename}）\n"
                            )
                            try:
                                os.remove(file_path)
                                log(f"🧪 模拟模式：原始压缩包文件已删除\n\n")
                            except:
                                pass
                        else:
                            log("⚠️ 模拟模式：解压失败（不支持的格式）\n")
                    else:
                        # 用户选择不解压，保持压缩包原样
                        log(f"🧪 模拟模式：解压选项未启用（保持压缩包原样）\n")
                        log(
                            f"🧪 模拟模式：压缩包已保存: {original_filename}（未解压，保持原样）\n"
                        )
                        log(f"  构建时将使用压缩包文件本身\n\n")
                elif is_jar:
                    # JAR 文件：保存为固定名称 app.jar
                    with open(os.path.join(build_context, "app.jar"), "wb") as f:
                        f.write(file_data)
                    log(
                        f"🧪 模拟模式：JAR 文件已保存为: app.jar（原始文件名: {original_filename}）\n"
                    )
                else:
                    # 其他文件：保持原文件名
                    file_path = os.path.join(build_context, original_filename)
                    with open(file_path, "wb") as f:
                        f.write(file_data)
                    log(
                        f"🧪 模拟模式：文件已保存: {original_filename}（保持原文件名）\n"
                    )

                for line in [
                    "🧪 模拟模式：Docker 服务不可用\n",
                    f"Step 1/4 : FROM {'node:20-alpine' if project_type == 'nodejs' else 'openjdk:17-jre-slim'} (模拟)\n",
                    "Step 2/4 : COPY . . (模拟)\n",
                    "Step 3/4 : WORKDIR /app (模拟)\n",
                    f"Step 4/4 : CMD (模拟)\n",
                    f"✅ 模拟构建成功: {full_tag}\n",
                ]:
                    log(line)

                if should_push:
                    # 推送时统一使用激活的registry
                    from backend.config import get_active_registry

                    push_registry_config = get_active_registry()

                    log("🚀 开始模拟推送...\n")
                    log(
                        f"🎯 使用激活仓库: {push_registry_config.get('name', 'Unknown')}\n"
                    )
                    username = push_registry_config.get("username", None)
                    log(f"🚀 账号: {username}\n")
                    for i in range(1, 4):
                        log(f"📡 Pushing layer {i}/3...\n")
                    log(
                        f"✅ 模拟推送完成到 {push_registry_config.get('registry', 'Unknown')}\n"
                    )
                else:
                    log("🚀 模拟推送跳过（未启用推送）\n")

                log("\n✅✅✅ 所有操作已完成（模拟）✅✅✅\n")
                return

            # === 真实构建 ===
            os.makedirs(build_context, exist_ok=True)

            # 判断文件类型并处理
            is_jar = original_filename.lower().endswith(".jar")
            is_archive = any(
                original_filename.lower().endswith(ext)
                for ext in [".zip", ".tar", ".tar.gz", ".tgz"]
            )

            if is_archive:
                # 压缩包：根据用户选择决定是否解压
                file_path = os.path.join(build_context, original_filename)
                log(f"📦 保存压缩包文件到构建上下文...\n")
                log(f"  构建上下文路径: {build_context}\n")
                log(f"  压缩包文件路径: {file_path}\n")

                with open(file_path, "wb") as f:
                    f.write(file_data)

                file_size = os.path.getsize(file_path)
                if file_size < 1024:
                    file_size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    file_size_str = f"{file_size / 1024:.2f} KB"
                else:
                    file_size_str = f"{file_size / (1024 * 1024):.2f} MB"
                log(f"  文件大小: {file_size_str}\n")
                log(f"✅ 压缩包文件保存完成\n\n")

                if extract_archive:
                    # 用户选择解压
                    log(f"🔧 解压选项: 已启用（将解压到构建根目录）\n")
                    if do_extract_archive(file_path, build_context):
                        # 解压成功，删除临时文件
                        log(f"🗑️  删除原始压缩包文件: {original_filename}\n")
                        try:
                            os.remove(file_path)
                            log(f"✅ 原始压缩包文件已删除\n\n")
                        except Exception as e:
                            log(f"⚠️  删除原始压缩包文件失败: {str(e)}\n")
                    else:
                        log(f"❌ 解压失败: {original_filename}\n")
                        self.task_manager.update_task_status(task_id, "failed")
                        return
                else:
                    # 用户选择不解压，保持压缩包原样
                    log(f"🔧 解压选项: 未启用（保持压缩包原样）\n")
                    log(f"📦 压缩包已保存: {original_filename}（未解压，保持原样）\n")
                    log(f"  构建时将使用压缩包文件本身\n\n")
            elif is_jar:
                # JAR 文件：保存为固定名称 app.jar
                jar_path = os.path.join(build_context, "app.jar")
                with open(jar_path, "wb") as f:
                    f.write(file_data)
                log(
                    f"✅ JAR 文件已保存为: app.jar（原始文件名: {original_filename}）\n"
                )
            else:
                # 其他文件：保持原文件名
                file_path = os.path.join(build_context, original_filename)
                with open(file_path, "wb") as f:
                    f.write(file_data)
                log(f"✅ 文件已保存: {original_filename}（保持原文件名）\n")

            # 获取模板路径（优先用户模板，否则使用内置模板）
            template_file = get_template_path(selected_template, project_type)
            if not template_file:
                log(f"❌ 模板不存在: {selected_template}\n")
                return

            with open(template_file, "r", encoding="utf-8") as f:
                dockerfile_content = f.read()

            # 替换模板变量
            config = load_config()

            # 准备变量替换字典
            template_vars = template_params or {}

            # 自动添加上传的文件名变量（供模板判断使用）
            template_vars["UPLOADED_FILENAME"] = original_filename

            # 如果没有传入 EXPOSE_PORT，使用配置中的默认值
            if "EXPOSE_PORT" not in template_vars:
                template_vars["EXPOSE_PORT"] = str(
                    config.get("docker", {}).get("expose_port", 8080)
                )

            # 替换所有变量
            from backend.template_parser import replace_template_variables

            try:
                dockerfile_content = replace_template_variables(
                    dockerfile_content, template_vars
                )
            except ValueError as e:
                log(f"❌ 模板变量替换失败: {e}\n")
                return

            with open(
                os.path.join(build_context, "Dockerfile"), "w", encoding="utf-8"
            ) as f:
                f.write(dockerfile_content)
            log(f"✅ 已生成 Dockerfile\n")

            # 复制资源包到构建上下文
            if resource_package_ids:
                try:
                    from backend.resource_package_manager import ResourcePackageManager

                    package_manager = ResourcePackageManager()
                    # 如果 resource_package_ids 是列表，转换为配置格式
                    if (
                        isinstance(resource_package_ids, list)
                        and len(resource_package_ids) > 0
                    ):
                        if isinstance(resource_package_ids[0], dict):
                            # 已经是配置格式
                            package_configs = resource_package_ids
                        else:
                            # 只是ID列表，使用默认目录
                            package_configs = [
                                {"package_id": pid, "target_dir": "resources"}
                                for pid in resource_package_ids
                            ]
                        copied_packages = (
                            package_manager.copy_packages_to_build_context(
                                package_configs, build_context
                            )
                        )
                        if copied_packages:
                            log(
                                f"✅ 已复制 {len(copied_packages)} 个资源包到构建上下文\n"
                            )
                            # 输出每个资源包的详细信息
                            for config in package_configs:
                                package_id = config.get("package_id")
                                if package_id in copied_packages:
                                    target_path = config.get(
                                        "target_path"
                                    ) or config.get("target_dir", "resources")
                                    log(f"   📦 {package_id} -> {target_path}\n")
                        else:
                            log(f"⚠️ 资源包复制失败或资源包不存在\n")
                except Exception as e:
                    log(f"⚠️ 复制资源包失败: {str(e)}\n")

            log(f"\n🚀 开始构建镜像: {full_tag}\n")
            connection_info = docker_builder.get_connection_info()
            log(f"🐳 使用构建器: {connection_info}\n")

            # 检查连接错误
            if hasattr(docker_builder, "get_connection_error"):
                connection_error = docker_builder.get_connection_error()
                if connection_error and connection_error != "未知错误":
                    log(f"⚠️ 连接警告: {connection_error}\n")

            # 拉取基础镜像时，Docker 会默认到所有仓库中寻找，不需要指定认证仓库

            build_stream = docker_builder.build_image(
                path=build_context, tag=full_tag, pull=True  # 自动拉取基础镜像
            )
            build_succeeded = False
            last_error = None

            for chunk in build_stream:
                # 检查是否请求停止（通过任务状态判断）
                from backend.database import get_db_session
                from backend.models import Task

                db = get_db_session()
                try:
                    task = db.query(Task).filter(Task.task_id == task_id).first()
                    if task and task.status == "stopped":
                        log(f"\n⚠️ 任务已被用户停止\n")
                        return
                finally:
                    db.close()

                if "stream" in chunk:
                    stream_msg = chunk["stream"]
                    log(f"🏗️  {stream_msg}")
                    # 检查构建成功消息（docker buildx build 会输出 "Successfully built and tagged"）
                    if (
                        "Successfully built" in stream_msg
                        or "Successfully tagged" in stream_msg
                    ):
                        build_succeeded = True
                elif "error" in chunk:
                    last_error = chunk["error"]
                    log(f"\n🔥 [DOCKER ERROR]: {last_error}\n")

                    # 检测是否是镜像拉取失败的错误
                    if "manifest" in last_error.lower() and (
                        "not found" in last_error.lower()
                        or "unknown" in last_error.lower()
                    ):
                        import re

                        image_match = re.search(
                            r"manifest for ([^\s]+) not found", last_error
                        )
                        if image_match:
                            image_name = image_match.group(1)
                            log(f"\n💡 镜像拉取失败分析:\n")
                            log(f"   无法拉取基础镜像: {image_name}\n")
                            log(f"   可能的原因:\n")
                            log(f"   1. 镜像不存在或已被删除\n")
                            log(f"   2. 镜像标签不正确\n")
                            log(f"   3. 网络连接问题或仓库访问受限\n")
                            log(f"   4. 需要认证但未配置认证信息\n")
                            log(
                                f"   建议: 检查 Dockerfile 中的 FROM 指令，确认镜像名称和标签是否正确\n"
                            )
                elif "errorDetail" in chunk:
                    err_msg = chunk["errorDetail"].get("message", "Unknown")
                    last_error = err_msg
                    log(f"\n💥 [ERROR DETAIL]: {err_msg}\n")

                    # 检测是否是镜像拉取失败的错误
                    if "manifest" in err_msg.lower() and (
                        "not found" in err_msg.lower() or "unknown" in err_msg.lower()
                    ):
                        import re

                        image_match = re.search(
                            r"manifest for ([^\s]+) not found", err_msg
                        )
                        if image_match:
                            image_name = image_match.group(1)
                            log(f"\n💡 镜像拉取失败分析:\n")
                            log(f"   无法拉取基础镜像: {image_name}\n")
                            log(f"   可能的原因:\n")
                            log(f"   1. 镜像不存在或已被删除\n")
                            log(f"   2. 镜像标签不正确\n")
                            log(f"   3. 网络连接问题或仓库访问受限\n")
                            log(f"   4. 需要认证但未配置认证信息\n")
                            log(
                                f"   建议: 检查 Dockerfile 中的 FROM 指令，确认镜像名称和标签是否正确\n"
                            )
                elif "aux" in chunk and "ID" in chunk["aux"]:
                    build_succeeded = True

            if not build_succeeded:
                log(f"\n❌ 构建失败！最后错误: {last_error or '未知错误'}\n")
                return

            log(f"\n✅ 镜像构建成功: {full_tag}\n")

            if should_push:
                # 推送时直接使用构建好的镜像名，根据镜像名找到对应的registry获取认证信息
                from backend.config import (
                    get_active_registry,
                    get_all_registries,
                    get_registry_by_name,
                )

                # 根据镜像名找到对应的registry配置
                def find_matching_registry_for_push(image_name):
                    """根据镜像名找到匹配的registry配置"""
                    # 如果镜像名包含斜杠，提取registry部分
                    parts = image_name.split("/")
                    if len(parts) >= 2 and "." in parts[0]:
                        # 镜像名格式: registry.com/namespace/image
                        image_registry = parts[0]
                        all_registries = get_all_registries()
                        for reg in all_registries:
                            reg_address = reg.get("registry", "")
                            if reg_address and (
                                image_registry == reg_address
                                or image_registry.startswith(reg_address)
                                or reg_address.startswith(image_registry)
                            ):
                                # 使用get_registry_by_name获取包含解密密码的完整配置
                                return get_registry_by_name(reg.get("name"))
                    return None

                # 尝试根据镜像名找到匹配的registry
                push_registry_config = find_matching_registry_for_push(image_name)
                if not push_registry_config:
                    # 如果找不到匹配的，使用激活的registry
                    push_registry_config = get_active_registry()
                    log(
                        f"\n⚠️  未找到匹配的registry配置，使用激活仓库: {push_registry_config.get('name', 'Unknown')}\n"
                    )
                else:
                    log(
                        f"\n🎯 找到匹配的registry配置: {push_registry_config.get('name', 'Unknown')}\n"
                    )

                log(f"📤 开始推送镜像: {full_tag}\n")

                # 直接使用构建时的镜像名
                push_repository = image_name
                log(f"📦 推送镜像: {full_tag}\n")

                push_username = push_registry_config.get("username")
                push_password = push_registry_config.get("password")
                push_registry_host = push_registry_config.get("registry", "")

                log(
                    f"🔐 Registry配置 - 地址: {push_registry_host}, 用户名: {push_username}, 密码: {'***' if push_password else '(未配置)'}\n"
                )

                auth_config = None
                if push_username and push_password:
                    # 构建auth_config，包含registry信息
                    # docker-py的push API需要serveraddress字段来指定registry
                    auth_config = {
                        "username": push_username,
                        "password": push_password,
                    }
                    # 对于非docker.io的registry，必须设置serveraddress
                    if push_registry_host:
                        if push_registry_host != "docker.io":
                            auth_config["serveraddress"] = push_registry_host
                        else:
                            # docker.io也可以显式设置
                            auth_config["serveraddress"] = "https://index.docker.io/v1/"
                    else:
                        # 如果没有registry_host，默认使用docker.io
                        auth_config["serveraddress"] = "https://index.docker.io/v1/"

                    log(f"✅ 已配置认证信息\n")
                    log(
                        f"🔐 Auth配置: username={push_username}, serveraddress={auth_config.get('serveraddress', 'docker.io')}\n"
                    )

                    # 推送前先登录到registry（重要：确保认证生效）
                    try:
                        if hasattr(docker_builder, "client") and docker_builder.client:
                            # 对于阿里云等registry，需要确保使用正确的registry地址
                            login_registry = (
                                push_registry_host
                                if push_registry_host
                                and push_registry_host != "docker.io"
                                else None
                            )
                            log(
                                f"🔑 正在登录到registry: {login_registry or 'docker.io'}\n"
                            )
                            log(f"🔑 用户名: {push_username}\n")

                            # 执行登录
                            login_result = docker_builder.client.login(
                                username=push_username,
                                password=push_password,
                                registry=login_registry,
                            )
                            log(f"✅ 登录成功: {login_result}\n")
                        else:
                            log(f"⚠️  Docker客户端不可用，跳过登录\n")
                    except Exception as login_error:
                        error_msg = str(login_error)
                        log(f"❌ 登录失败: {error_msg}\n")

                        # 检查是否是认证错误
                        if (
                            "401" in error_msg
                            or "Unauthorized" in error_msg
                            or "unauthorized" in error_msg
                        ):
                            log(f"⚠️  认证失败，可能的原因：\n")
                            log(f"   1. 用户名或密码不正确\n")
                            log(f"   2. 对于阿里云registry，请确认：\n")
                            log(
                                f"      - 用户名：使用阿里云账号或独立的镜像仓库用户名\n"
                            )
                            log(f"      - 密码：使用阿里云账号密码或镜像仓库独立密码\n")
                            log(f"      - 如果使用访问令牌，请确认令牌未过期\n")
                            log(f"   3. 请检查registry配置中的认证信息是否正确\n")
                            log(
                                f"⚠️  继续尝试推送（推送时会使用auth_config，但可能仍然失败）\n"
                            )
                        else:
                            log(f"⚠️  继续尝试推送（推送时会使用auth_config）\n")
                else:
                    log(f"⚠️  registry未配置认证信息，推送可能失败\n")

                try:
                    log(f"🚀 开始推送，repository: {push_repository}, tag: {tag}\n")
                    if auth_config:
                        log(
                            f"🔐 使用认证信息: username={auth_config.get('username')}, serveraddress={auth_config.get('serveraddress', 'docker.io')}\n"
                        )
                    else:
                        log(f"⚠️  未使用认证信息\n")

                    push_stream = docker_builder.push_image(
                        push_repository, tag, auth_config=auth_config
                    )
                    for chunk in push_stream:
                        status = (
                            chunk.get("status")
                            or chunk.get("progress")
                            or chunk.get("id")
                        )
                        if status:
                            log(f"📡 {status}\n")
                        if "error" in chunk:
                            error_detail = chunk.get("errorDetail", {})
                            error_msg = chunk["error"]
                            log(f"\n❌ 推送失败: {error_msg}\n")
                            if error_detail:
                                log(f"❌ 错误详情: {error_detail}\n")
                            return
                    log(f"\n✅ 推送完成: {full_tag}\n")
                except Exception as e:
                    error_str = str(e)
                    log(f"\n❌ 推送异常: {error_str}\n")

                    # 如果是认证错误，提供更详细的提示
                    if (
                        "denied" in error_str.lower()
                        or "unauthorized" in error_str.lower()
                        or "401" in error_str
                    ):
                        log(f"💡 推送认证失败，建议：\n")
                        log(f"   1. 确认registry配置中的用户名和密码正确\n")
                        log(f"   2. 对于阿里云registry，请使用独立的Registry登录密码\n")
                        log(f"   3. 可以尝试手动执行以下命令测试：\n")
                        log(
                            f"      docker login --username={push_username} {push_registry_host}\n"
                        )
                        log(f"      docker push {full_tag}\n")
                        log(
                            f"   4. 如果手动命令成功，说明配置有问题；如果也失败，说明认证信息不正确\n"
                        )

            log("\n🎉🎉🎉 所有操作已完成！🎉🎉🎉\n")
            # 更新任务状态为完成（确保状态更新）
            print(f"🔍 准备更新任务 {task_id[:8]} 状态为 completed")
            try:
                self.task_manager.update_task_status(task_id, "completed")
                print(f"✅ 任务 {task_id[:8]} 状态已更新为 completed")
                # 验证状态是否真的更新了
                updated_task = self.task_manager.get_task(task_id)
                if updated_task and updated_task.get("status") == "completed":
                    print(
                        f"✅ 任务 {task_id[:8]} 状态验证成功: {updated_task.get('status')}"
                    )
                else:
                    print(
                        f"⚠️ 任务 {task_id[:8]} 状态验证失败，当前状态: {updated_task.get('status') if updated_task else 'None'}"
                    )
            except Exception as status_error:
                print(f"❌ 更新任务状态失败: {status_error}")
                import traceback

                traceback.print_exc()
            # 从任务字典中移除已完成的线程
            with self.lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
                    print(f"✅ 任务 {task_id[:8]} 线程已清理")

        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            log(f"\n❌ 构建异常: {clean_msg}\n")
            # 更新任务状态为失败
            self.task_manager.update_task_status(task_id, "failed", error=clean_msg)
            # 从任务字典中移除失败的线程
            with self.lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
                    print(f"✅ 任务 {task_id[:8]} 线程已清理（失败）")
            import traceback

            traceback.print_exc()
        finally:
            if os.getenv("KEEP_BUILD_CONTEXT", "0") != "1":
                try:
                    shutil.rmtree(build_context, ignore_errors=True)
                except Exception as e:
                    print(f"⚠️ 清理失败: {e}")

    def get_logs(self, build_id: str):
        with self.lock:
            return list(self.logs[build_id])

    def _trigger_task_from_config(self, task_config: dict) -> str:
        """
        统一的任务触发函数，从任务配置JSON触发任务

        Args:
            task_config: 标准化的任务配置字典

        Returns:
            task_id: 任务ID
        """
        # 从配置中提取参数
        git_url = task_config.get("git_url")
        image_name = task_config.get("image_name")
        tag = task_config.get("tag", "latest")
        branch = task_config.get("branch")

        # 调试日志：检查任务配置中的分支
        import json

        print(f"🔍 _trigger_task_from_config:")
        print(f"   - task_config中的branch: {repr(branch)}")
        print(
            f"   - task_config完整内容: {json.dumps({k: v for k, v in task_config.items() if k != 'template_params'}, indent=2, ensure_ascii=False, default=str)}"
        )
        project_type = task_config.get("project_type", "jar")
        template = task_config.get("template", "")
        template_params = task_config.get("template_params", {})
        should_push = task_config.get("should_push", False)
        sub_path = task_config.get("sub_path")
        use_project_dockerfile = task_config.get("use_project_dockerfile", True)
        dockerfile_name = task_config.get("dockerfile_name", "Dockerfile")
        source_id = task_config.get("source_id")
        selected_services = task_config.get("selected_services")
        service_push_config = task_config.get("service_push_config")
        service_template_params = task_config.get("service_template_params", {})
        push_mode = task_config.get("push_mode", "multi")
        resource_package_ids = task_config.get("resource_package_ids", [])
        pipeline_id = task_config.get("pipeline_id")
        trigger_source = task_config.get("trigger_source", "manual")

        # 调用原有的start_build_from_source方法
        return self.start_build_from_source(
            git_url=git_url,
            image_name=image_name,
            tag=tag,
            should_push=should_push,
            selected_template=template,
            project_type=project_type,
            template_params=template_params,
            push_registry=None,  # 已废弃
            branch=branch,
            sub_path=sub_path,
            use_project_dockerfile=use_project_dockerfile,
            dockerfile_name=dockerfile_name,
            pipeline_id=pipeline_id,
            source_id=source_id,
            selected_services=selected_services,
            service_push_config=service_push_config,
            push_mode=push_mode,
            build_steps={},  # 构建步骤信息
            service_template_params=service_template_params,
            resource_package_ids=resource_package_ids,
            trigger_source=trigger_source,
        )

    def start_build_from_source(
        self,
        git_url: str,
        image_name: str,
        tag: str,
        should_push: bool,
        selected_template: str,
        project_type: str = "jar",
        template_params: dict = None,
        push_registry: str = None,
        branch: str = None,
        sub_path: str = None,
        use_project_dockerfile: bool = True,  # 是否优先使用项目中的 Dockerfile
        dockerfile_name: str = "Dockerfile",  # Dockerfile文件名，默认Dockerfile
        pipeline_id: str = None,  # 流水线ID（可选）
        source_id: str = None,  # 数据源ID（可选，如果提供将使用数据源的认证信息）
        selected_services: list = None,  # 选中的服务列表（多服务构建时使用）
        service_push_config: dict = None,  # 每个服务的推送配置（key为服务名，value为是否推送）
        push_mode: str = "multi",  # 推送模式：'single' 单一推送，'multi' 多阶段推送（仅模板模式）
        build_steps: dict = None,  # 构建步骤信息
        service_template_params: dict = None,  # 服务模板参数
        resource_package_ids: list = None,  # 资源包ID列表或配置列表
        trigger_source: str = "manual",  # 触发来源
    ):
        """从 Git 源码开始构建"""
        try:
            # 创建任务
            print(f"📝 正在创建构建任务: image={image_name}:{tag}, git_url={git_url}")
            task_id = self.task_manager.create_task(
                task_type="build_from_source",
                image_name=image_name,
                tag=tag,
                git_url=git_url,
                should_push=should_push,
                selected_template=selected_template,
                project_type=project_type,
                template_params=template_params or {},
                push_registry=push_registry,
                branch=branch,
                sub_path=sub_path,
                use_project_dockerfile=use_project_dockerfile,
                dockerfile_name=dockerfile_name,
                pipeline_id=pipeline_id,  # 传递流水线ID
                source_id=source_id,  # 传递数据源ID
                selected_services=selected_services,  # 传递选中的服务列表
                service_push_config=service_push_config,  # 传递服务推送配置
                push_mode=push_mode,  # 传递推送模式
                build_steps=build_steps or {},  # 传递构建步骤信息
                service_template_params=service_template_params
                or {},  # 传递服务模板参数
                resource_package_ids=resource_package_ids or [],  # 传递资源包ID列表
                trigger_source=trigger_source,  # 传递触发来源
            )
            print(f"✅ 任务创建成功: task_id={task_id}")
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 创建任务失败: {e}")
            print(f"错误堆栈:\n{error_trace}")
            raise RuntimeError(f"创建构建任务失败: {str(e)}")

        try:
            thread = threading.Thread(
                target=self._build_from_source_task,
                args=(
                    task_id,
                    git_url,
                    image_name,
                    tag,
                    should_push,
                    selected_template,
                    project_type,
                    template_params or {},
                    push_registry,
                    branch,
                    sub_path,
                    use_project_dockerfile,
                    dockerfile_name,
                    source_id,
                    selected_services,
                    service_push_config,
                    push_mode,
                    service_template_params,  # 传递服务模板参数
                    resource_package_ids or [],  # 传递资源包ID列表
                ),
                daemon=True,
            )
            thread.start()
            print(f"✅ 构建线程已启动: task_id={task_id}")
            with self.lock:
                self.tasks[task_id] = thread
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 启动构建线程失败: {e}")
            print(f"错误堆栈:\n{error_trace}")
            # 尝试更新任务状态为失败
            try:
                self.task_manager.update_task_status(
                    task_id, "failed", error=f"启动构建线程失败: {str(e)}"
                )
            except:
                pass
            raise RuntimeError(f"启动构建线程失败: {str(e)}")

        return task_id

    def _build_from_source_task(
        self,
        task_id: str,
        git_url: str,
        image_name: str,
        tag: str,
        should_push: bool,
        selected_template: str,
        project_type: str = "jar",
        template_params: dict = None,
        push_registry: str = None,
        branch: str = None,
        sub_path: str = None,
        use_project_dockerfile: bool = True,  # 是否优先使用项目中的 Dockerfile
        dockerfile_name: str = "Dockerfile",  # Dockerfile文件名，默认Dockerfile
        source_id: str = None,  # 数据源ID（可选）
        selected_services: list = None,  # 选中的服务列表（多服务构建时使用）
        service_push_config: dict = None,  # 每个服务的推送配置（key为服务名，value为是否推送）
        push_mode: str = "multi",  # 推送模式：'single' 单一推送，'multi' 多阶段推送（仅模板模式）
        service_template_params: dict = None,  # 服务模板参数
        resource_package_ids: list = None,  # 资源包ID列表
    ):
        """从 Git 源码构建任务"""
        full_tag = f"{image_name}:{tag}"
        # 使用 task_id 作为构建上下文目录名的一部分，避免冲突
        build_context = os.path.join(
            BUILD_DIR, f"{image_name.replace('/', '_')}_{task_id[:8]}"
        )

        # 构建上下文路径不需要保存到数据库（临时路径）
        # 如果需要，可以通过 task_id 和 image_name 推导

        def log(msg: str):
            """添加日志（增强错误处理）"""
            try:
                if not msg.endswith("\n"):
                    msg = msg + "\n"
                # 使用任务管理器记录日志
                try:
                    self.task_manager.add_log(task_id, msg)
                except Exception as e:
                    # 如果任务管理器记录失败，至少打印到控制台
                    print(f"⚠️ 任务日志记录失败 (task_id={task_id}): {e}")
                    print(f"日志内容: {msg}")
                # 保留旧的日志系统用于兼容
                try:
                    with self.lock:
                        if task_id not in self.logs:
                            self.logs[task_id] = deque()
                        self.logs[task_id].append(msg)
                except Exception as e:
                    print(f"⚠️ 旧日志系统记录失败: {e}")
            except Exception as e:
                # 即使日志函数本身失败，也要打印到控制台
                print(f"⚠️ 日志函数异常: {e}")
                print(f"原始消息: {msg}")

        # 更新任务状态为运行中
        try:
            self.task_manager.update_task_status(task_id, "running")
        except Exception as e:
            print(f"⚠️ 更新任务状态失败: {e}")

        try:
            log(f"🚀 开始从 Git 源码构建: {git_url}\n")

            # 打印构建配置信息（过滤敏感信息）
            def sanitize_config(config_dict):
                """过滤敏感信息"""
                if not isinstance(config_dict, dict):
                    return config_dict

                sensitive_patterns = [
                    "password",
                    "token",
                    "secret",
                    "credential",
                    "auth",
                    "access_token",
                    "api_key",
                    "apikey",
                    "private_key",
                    "privatekey",
                    "pwd",
                    "passwd",
                ]
                sanitized = {}
                for k, v in config_dict.items():
                    key_lower = k.lower()
                    # 检查键名是否包含敏感词（但排除一些安全的键，如 image_name, tag_name 等）
                    is_sensitive = any(
                        pattern in key_lower for pattern in sensitive_patterns
                    )
                    # 排除一些安全的键名（即使包含敏感词）
                    safe_keys = [
                        "image_name",
                        "tag",
                        "tag_name",
                        "dockerfile_name",
                        "template_name",
                    ]
                    if k in safe_keys:
                        is_sensitive = False

                    if is_sensitive:
                        sanitized[k] = "***已隐藏***"
                    elif isinstance(v, dict):
                        sanitized[k] = sanitize_config(v)
                    elif isinstance(v, list):
                        sanitized[k] = [
                            sanitize_config(item) if isinstance(item, dict) else item
                            for item in v
                        ]
                    else:
                        sanitized[k] = v
                return sanitized

            build_config = {
                "git_url": git_url,
                "image_name": image_name,
                "tag": tag,
                "should_push": should_push,
                "selected_template": selected_template,
                "project_type": project_type,
                "template_params": template_params or {},
                "branch": branch,
                "sub_path": sub_path,
                "use_project_dockerfile": use_project_dockerfile,
                "dockerfile_name": dockerfile_name,
                "source_id": source_id,
                "selected_services": selected_services,
                "service_push_config": service_push_config,
                "push_mode": push_mode,
                "service_template_params": service_template_params or {},
                "resource_package_ids": resource_package_ids or [],
            }

            sanitized_config = sanitize_config(build_config)

            # 判断构建模式
            is_multi_service = selected_services and len(selected_services) > 1
            build_mode = "多服务构建" if is_multi_service else "单服务构建"
            if is_multi_service:
                build_mode += f" (共 {len(selected_services)} 个服务)"

            log(f"📋 构建配置解析结果:\n")
            log(f"   构建模式: {build_mode}\n")
            log(
                f"   配置详情:\n{json.dumps(sanitized_config, indent=4, ensure_ascii=False)}\n"
            )

            # 清理旧的构建上下文
            if os.path.exists(build_context):
                try:
                    shutil.rmtree(build_context)
                except Exception as e:
                    log(f"⚠️ 清理旧构建上下文失败: {e}\n")
            os.makedirs(build_context, exist_ok=True)

            # 克隆 Git 仓库
            log(f"📥 正在克隆 Git 仓库...\n")
            # 创建临时目录用于克隆（Git clone 会在目标目录下创建仓库目录）
            temp_clone_dir = os.path.join(build_context, "source_temp")
            os.makedirs(temp_clone_dir, exist_ok=True)

            # 获取 Git 配置，优先使用数据源的认证信息
            git_config = get_git_config()
            if source_id:
                from backend.git_source_manager import GitSourceManager

                source_manager = GitSourceManager()
                source_auth = source_manager.get_auth_config(source_id)
                # 如果数据源有认证信息，优先使用数据源的
                if source_auth.get("username"):
                    git_config["username"] = source_auth["username"]
                if source_auth.get("password"):
                    git_config["password"] = source_auth["password"]
                log(f"🔐 使用数据源的认证信息\n")
            elif git_config.get("username") or git_config.get("password"):
                log(f"🔐 使用全局 Git 配置的认证信息\n")

            # Git clone 会在目标目录下创建仓库目录，所以目标目录应该是父目录
            # 调试日志：检查构建时使用的分支
            print(f"🔍 _build_from_source_task:")
            print(f"   - 参数branch: {branch}")
            print(f"   - git_url: {git_url}")
            log(f"📌 准备克隆分支: {branch or '默认分支'}\n")
            clone_success, clone_error = self._clone_git_repo(
                git_url, temp_clone_dir, branch, git_config, log
            )

            if not clone_success:
                error_msg = f"Git 克隆失败"
                if clone_error:
                    error_msg += f": {clone_error}"
                raise RuntimeError(error_msg)

            # Git clone 会在目标目录下创建仓库目录，找到实际的仓库目录
            # 通常仓库目录名是 URL 的最后一部分（去掉 .git）
            repo_name = git_url.rstrip("/").split("/")[-1].replace(".git", "")
            actual_clone_dir = os.path.join(temp_clone_dir, repo_name)

            # 如果找不到，尝试查找 temp_clone_dir 下的第一个目录
            if not os.path.exists(actual_clone_dir):
                items = os.listdir(temp_clone_dir)
                if items:
                    actual_clone_dir = os.path.join(temp_clone_dir, items[0])

            if not os.path.exists(actual_clone_dir):
                raise RuntimeError("无法找到克隆的仓库目录")

            # 如果指定了子目录，使用子目录作为构建上下文
            source_dir = actual_clone_dir
            if sub_path:
                source_dir = os.path.join(actual_clone_dir, sub_path)
                if not os.path.exists(source_dir):
                    raise RuntimeError(f"指定的子目录不存在: {sub_path}")
                log(f"📂 使用子目录作为构建上下文: {sub_path}\n")

            # 将源码复制到构建上下文根目录（排除不必要的文件）
            log(f"📋 准备构建上下文...\n")

            # 定义需要排除的文件和目录（类似 .dockerignore）
            exclude_patterns = {
                ".git",
                ".gitignore",
                ".dockerignore",
                "__pycache__",
                "*.pyc",
                ".pytest_cache",
                "node_modules",
                ".venv",
                "venv",
                ".idea",
                ".vscode",
                ".cursor",
                "*.md",
                "*.log",
                ".DS_Store",
                "test_*.py",
                "*_test.py",
            }

            def should_exclude(item_name):
                """判断文件/目录是否应该被排除"""
                # 直接匹配
                if item_name in exclude_patterns:
                    return True
                # 通配符匹配
                import fnmatch

                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(item_name, pattern):
                        return True
                return False

            copied_count = 0
            excluded_count = 0

            for item in os.listdir(source_dir):
                if should_exclude(item):
                    excluded_count += 1
                    log(f"⏭️  跳过: {item}\n")
                    continue

                src = os.path.join(source_dir, item)
                dst = os.path.join(build_context, item)

                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                    copied_count += 1
                except Exception as e:
                    log(f"⚠️  复制失败 {item}: {e}\n")

            log(f"✅ 已复制 {copied_count} 个文件/目录，跳过 {excluded_count} 个\n")

            # 检查项目中是否存在 Dockerfile（使用自定义文件名或路径）
            # 规范化路径分隔符（Git 路径使用 /，但 Windows 使用 \）
            normalized_dockerfile_name = dockerfile_name.replace("/", os.sep).replace(
                "\\", os.sep
            )
            project_dockerfile_path = os.path.join(
                source_dir, normalized_dockerfile_name
            )
            has_project_dockerfile = os.path.exists(project_dockerfile_path)

            # 决定使用项目中的 Dockerfile 还是模板
            if has_project_dockerfile and use_project_dockerfile:
                # 计算相对路径，用于日志显示
                dockerfile_relative_path = os.path.relpath(
                    project_dockerfile_path, source_dir
                )
                log(
                    f"📄 检测到项目中的 Dockerfile: {dockerfile_relative_path}，使用项目中的 Dockerfile\n"
                )
                # 复制项目中的 Dockerfile 到构建上下文
                # 重要：无论原始文件名是什么，都统一复制为 "Dockerfile"
                # 这样可以避免 buildx 的文件名识别问题，确保构建时使用默认文件名
                dockerfile_path = os.path.join(build_context, "Dockerfile")
                shutil.copy2(project_dockerfile_path, dockerfile_path)
                log(
                    f"✅ 已从 {dockerfile_relative_path} 复制到构建上下文的 Dockerfile\n"
                )
            else:
                if has_project_dockerfile and not use_project_dockerfile:
                    log(f"📋 项目中有 Dockerfile，但用户选择使用模板\n")
                else:
                    log(f"📋 项目中没有 Dockerfile，使用模板生成\n")

                # 使用模板生成 Dockerfile
                template_path = get_template_path(selected_template, project_type)
                if not template_path or not os.path.exists(template_path):
                    raise RuntimeError(f"模板不存在: {selected_template}")

                dockerfile_path = os.path.join(build_context, "Dockerfile")
                from backend.template_parser import parse_template

                # 合并全局模板参数和服务模板参数（如果有多个服务，使用第一个服务的参数作为默认值）
                all_template_params = {
                    "PROJECT_TYPE": project_type,
                    "UPLOADED_FILENAME": "app.jar",  # 源码构建不需要这个
                    **template_params,
                }

                # 如果有服务模板参数，合并到全局参数中（用于单服务构建）
                if service_template_params:
                    # 如果只有一个服务，直接使用该服务的参数
                    if len(service_template_params) == 1:
                        service_name = list(service_template_params.keys())[0]
                        all_template_params.update(
                            service_template_params[service_name]
                        )
                    else:
                        # 多个服务时，合并所有服务的参数（可能会有冲突，但先这样处理）
                        for service_params in service_template_params.values():
                            all_template_params.update(service_params)

                parse_template(
                    template_path,
                    dockerfile_path,
                    all_template_params,
                )
                log(f"✅ 已生成 Dockerfile\n")

            # 复制资源包到构建上下文
            log(f"📦 检查资源包配置...\n")
            if resource_package_ids:
                log(f"📋 发现 {len(resource_package_ids)} 个资源包配置\n")
                try:
                    from backend.resource_package_manager import ResourcePackageManager

                    package_manager = ResourcePackageManager()
                    # 如果 resource_package_ids 是列表，转换为配置格式
                    if (
                        isinstance(resource_package_ids, list)
                        and len(resource_package_ids) > 0
                    ):
                        if isinstance(resource_package_ids[0], dict):
                            # 已经是配置格式
                            package_configs = resource_package_ids
                        else:
                            # 只是ID列表，使用默认目录
                            package_configs = [
                                {"package_id": pid, "target_dir": "resources"}
                                for pid in resource_package_ids
                            ]
                        copied_packages = (
                            package_manager.copy_packages_to_build_context(
                                package_configs, build_context
                            )
                        )
                        if copied_packages:
                            log(
                                f"✅ 已复制 {len(copied_packages)} 个资源包到构建上下文\n"
                            )
                            # 输出每个资源包的详细信息
                            for config in package_configs:
                                package_id = config.get("package_id")
                                if package_id in copied_packages:
                                    target_path = config.get(
                                        "target_path"
                                    ) or config.get("target_dir", "resources")
                                    log(f"   📦 {package_id} -> {target_path}\n")
                        else:
                            log(f"⚠️ 资源包复制失败或资源包不存在\n")
                except Exception as e:
                    log(f"⚠️ 复制资源包失败: {str(e)}\n")
            else:
                log(f"ℹ️  未配置资源包，跳过资源包复制\n")

            # Docker API 需要相对于构建上下文的 Dockerfile 路径
            dockerfile_relative = os.path.relpath(dockerfile_path, build_context)
            log(f"📄 Dockerfile 相对路径: {dockerfile_relative}\n")
            # 创建 .dockerignore 文件以进一步优化构建上下文
            dockerignore_path = os.path.join(build_context, ".dockerignore")
            if not os.path.exists(dockerignore_path):
                log(f"📝 创建 .dockerignore 文件...\n")
                with open(dockerignore_path, "w") as f:
                    f.write(
                        """# Git 相关
.git
.gitignore
.gitattributes

# Python 缓存
__pycache__
*.pyc
*.pyo
*.pyd
.Python
.pytest_cache
.venv
venv/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.idea/
.vscode/
.cursor/
*.swp
*.swo
.DS_Store

# 测试和文档
test_*.py
*_test.py
*.md
README*
LICENSE

# 日志
*.log
logs/
"""
                    )
                log(f"✅ .dockerignore 已创建\n")

            # 多服务构建逻辑（只有当服务数量大于1时才进入多服务构建）
            if selected_services and len(selected_services) > 1:
                log(f"🔨 开始多服务构建，共 {len(selected_services)} 个服务\n")
                log(f"📋 选中的服务: {', '.join(selected_services)}\n")
                log(f"📦 推送模式: {push_mode}\n")

                service_push_config = service_push_config or {}
                built_services = []

                # 单一推送模式：构建所有服务到一个镜像
                if push_mode == "single":
                    log(f"🔨 单一推送模式：所有服务将构建到一个镜像中\n")
                    log(f"📦 镜像标签: {full_tag}\n")
                    log(f"📂 构建上下文: {build_context}\n")

                    # 从 Dockerfile 中解析实际的阶段名称
                    dockerfile_path = os.path.join(build_context, dockerfile_relative)
                    target_stage = None

                    if os.path.exists(dockerfile_path):
                        try:
                            with open(dockerfile_path, "r", encoding="utf-8") as f:
                                dockerfile_content = f.read()
                            services, _ = parse_dockerfile_services(dockerfile_content)
                            if services and len(services) > 0:
                                # 使用 Dockerfile 中最后一个阶段
                                target_stage = services[-1].get("name")
                                log(
                                    f"🔍 从 Dockerfile 解析到阶段: {[s.get('name') for s in services]}\n"
                                )
                                log(f"🚀 使用最后阶段: {target_stage}\n")
                            else:
                                log(
                                    f"⚠️ Dockerfile 中没有找到多阶段，将构建默认阶段（不指定 target）\n"
                                )
                        except Exception as e:
                            log(
                                f"⚠️ 解析 Dockerfile 阶段失败: {e}，将构建默认阶段（不指定 target）\n"
                            )
                            import traceback

                            log(f"详细错误:\n{traceback.format_exc()}\n")
                            # 解析失败时，不指定 target，构建默认阶段
                            target_stage = None
                    else:
                        log(
                            f"⚠️ Dockerfile 不存在: {dockerfile_path}，将构建默认阶段（不指定 target）\n"
                        )
                        # Dockerfile 不存在时，不指定 target，构建默认阶段
                        target_stage = None

                    try:
                        build_kwargs = {
                            "path": build_context,
                            "tag": full_tag,
                            "dockerfile": dockerfile_relative,
                        }
                        # 只有在有明确的 target stage 时才添加 target 参数
                        if target_stage:
                            build_kwargs["target"] = target_stage
                            log(f"🚀 构建目标阶段: {target_stage}\n")
                        else:
                            log(f"🚀 构建默认阶段（无 target）\n")

                        build_stream = docker_builder.build_image(**build_kwargs)
                        log(f"✅ Docker 构建流已启动\n")
                    except Exception as e:
                        log(f"❌ 启动 Docker 构建失败: {str(e)}\n")
                        import traceback

                        log(f"详细错误:\n{traceback.format_exc()}\n")
                        raise

                    log(f"🔍 开始处理 Docker 构建流输出...\n")
                    chunk_count = 0
                    for chunk in build_stream:
                        chunk_count += 1
                        if isinstance(chunk, dict):
                            if "stream" in chunk:
                                log(chunk["stream"])
                            if "status" in chunk:
                                log(f"📊 {chunk['status']}\n")
                            if "progress" in chunk:
                                log(f"⏳ {chunk['progress']}\n")
                            if "error" in chunk:
                                error_msg = chunk["error"]
                                log(f"❌ 构建错误: {error_msg}\n")
                                raise RuntimeError(f"构建失败: {error_msg}")
                            if "errorDetail" in chunk:
                                error_detail = chunk["errorDetail"]
                                log(f"💥 错误详情: {error_detail}\n")
                        else:
                            log(f"📦 原始输出: {str(chunk)}\n")

                    log(f"✅ 镜像构建完成: {full_tag}\n")
                    built_services = selected_services

                    # 单一推送模式的推送逻辑（使用全局推送配置）
                    if should_push:
                        log(f"📡 开始推送镜像: {full_tag}\n")
                        # 使用单服务构建的推送逻辑
                        # ... (推送逻辑将在后面添加)
                    else:
                        log(f"⏭️  跳过推送\n")

                # 多阶段推送模式：每个服务独立构建和推送
                else:
                    # 从 Dockerfile 中解析实际的阶段名称映射
                    dockerfile_path = os.path.join(build_context, dockerfile_relative)
                    service_to_stage_map = {}  # 服务名称到 Dockerfile 阶段的映射

                    if os.path.exists(dockerfile_path):
                        try:
                            with open(dockerfile_path, "r", encoding="utf-8") as f:
                                dockerfile_content = f.read()
                            services, _ = parse_dockerfile_services(dockerfile_content)
                            if services and len(services) > 0:
                                # 构建服务名称到阶段的映射
                                # ✅ 配置的服务：只做「精确匹配」，不再做模糊/索引匹配
                                # 这样可以避免 app2docker 误匹配到 app2docker-agent 等情况
                                for service_name in selected_services:
                                    for service in services:
                                        stage_name = service.get("name")
                                        if (
                                            stage_name
                                            and service_name.lower()
                                            == stage_name.lower()
                                        ):
                                            service_to_stage_map[service_name] = (
                                                stage_name
                                            )
                                            break

                                log(
                                    f"🔍 从 Dockerfile 解析到阶段映射: {service_to_stage_map}\n"
                                )
                                log(
                                    f"🔍 解析到的所有阶段: {[s.get('name') for s in services]}\n"
                                )
                            else:
                                log(f"⚠️ Dockerfile 中没有找到多阶段\n")
                        except Exception as e:
                            log(f"⚠️ 解析 Dockerfile 阶段失败: {e}\n")
                            import traceback

                            log(f"详细错误:\n{traceback.format_exc()}\n")

                    for service_name in selected_services:
                        log(f"\n{'='*60}\n")
                        log(f"🚀 开始构建服务: {service_name}\n")

                        # 获取服务的配置（支持每个服务独立的镜像名、tag 和 registry）
                        service_config = service_push_config.get(service_name, {})
                        if isinstance(service_config, dict):
                            # 新格式：包含 push, imageName, tag, registry
                            service_image_name = service_config.get(
                                "imageName", f"{image_name}-{service_name}"
                            )
                            service_tag_value = service_config.get("tag", tag)
                            service_registry = service_config.get("registry", "")
                        else:
                            # 兼容旧格式：只有 push 布尔值
                            service_image_name = f"{image_name}-{service_name}"
                            service_tag_value = tag
                            service_registry = ""

                        service_tag = f"{service_image_name}:{service_tag_value}"
                        log(f"📦 镜像标签: {service_tag}\n")
                        log(f"📂 构建上下文: {build_context}\n")

                        # 确定要构建的 target stage
                        target_stage = service_to_stage_map.get(service_name)
                        if not target_stage:
                            log(
                                f"⚠️ 服务 '{service_name}' 没有对应的 Dockerfile 阶段，将构建默认阶段（不指定 target）\n"
                            )

                        try:
                            build_kwargs = {
                                "path": build_context,
                                "tag": service_tag,
                                "dockerfile": dockerfile_relative,
                            }
                            # 只有在有明确的 target stage 时才添加 target 参数
                            if target_stage:
                                build_kwargs["target"] = target_stage
                                log(f"🚀 构建目标阶段: {target_stage}\n")
                            else:
                                log(f"🚀 构建默认阶段（不指定 target）\n")

                            build_stream = docker_builder.build_image(**build_kwargs)
                            log(f"✅ Docker 构建流已启动\n")
                        except Exception as e:
                            log(f"❌ 启动 Docker 构建失败: {str(e)}\n")
                            import traceback

                            log(f"详细错误:\n{traceback.format_exc()}\n")
                            raise

                        log(f"🔍 开始处理 Docker 构建流输出...\n")
                        chunk_count = 0
                        for chunk in build_stream:
                            chunk_count += 1
                            if isinstance(chunk, dict):
                                if "stream" in chunk:
                                    log(f"[{service_name}] {chunk['stream']}")
                                if "status" in chunk:
                                    log(f"[{service_name}] 📊 {chunk['status']}\n")
                                if "progress" in chunk:
                                    log(f"[{service_name}] ⏳ {chunk['progress']}\n")
                                if "error" in chunk:
                                    error_msg = chunk["error"]
                                    log(f"[{service_name}] ❌ 构建错误: {error_msg}\n")

                                    # 检测是否是镜像拉取失败的错误
                                    if "manifest" in error_msg.lower() and (
                                        "not found" in error_msg.lower()
                                        or "unknown" in error_msg.lower()
                                    ):
                                        # 提取镜像名称
                                        import re

                                        image_match = re.search(
                                            r"manifest for ([^\s]+) not found",
                                            error_msg,
                                        )
                                        if image_match:
                                            image_name = image_match.group(1)
                                            enhanced_error = (
                                                f"服务 {service_name} 构建失败: 无法拉取基础镜像 {image_name}\n"
                                                f"可能的原因：\n"
                                                f"1. 镜像不存在或已被删除\n"
                                                f"2. 镜像标签不正确\n"
                                                f"3. 网络连接问题或仓库访问受限\n"
                                                f"4. 需要认证但未配置认证信息\n"
                                                f"建议：检查 Dockerfile 中的 FROM 指令，确认镜像名称和标签是否正确"
                                            )
                                            log(
                                                f"[{service_name}] 💡 {enhanced_error}\n"
                                            )
                                            raise RuntimeError(enhanced_error)

                                    raise RuntimeError(
                                        f"服务 {service_name} 构建失败: {error_msg}"
                                    )
                                if "errorDetail" in chunk:
                                    error_detail = chunk["errorDetail"]
                                    log(
                                        f"[{service_name}] 💥 错误详情: {error_detail}\n"
                                    )
                            else:
                                log(f"[{service_name}] 📦 原始输出: {str(chunk)}\n")

                        log(f"✅ 服务 {service_name} 构建完成\n")
                        built_services.append(service_name)

                        # 根据推送配置决定是否推送
                        should_push_service = False
                        if isinstance(service_config, dict):
                            should_push_service = service_config.get("push", False)
                        else:
                            # 兼容旧格式
                            should_push_service = bool(service_config)

                        if should_push_service:
                            log(f"📡 开始推送服务镜像: {service_tag}\n")
                            try:
                                # 初始化 registry_config
                                registry_config = None

                                # 根据镜像名找到对应的registry配置（与单服务构建逻辑一致）
                                def find_matching_registry_for_push(img_name):
                                    """根据镜像名找到匹配的registry配置，扫描所有仓库配置"""
                                    # 如果镜像名包含斜杠，提取registry部分
                                    parts = img_name.split("/")
                                    if len(parts) >= 2 and "." in parts[0]:
                                        # 镜像名格式: registry.com/namespace/image
                                        img_registry = parts[0]
                                        log(
                                            f"🔍 从镜像名提取registry: {img_registry}\n"
                                        )
                                        all_registries = get_all_registries()
                                        log(
                                            f"🔍 扫描所有 {len(all_registries)} 个registry配置...\n"
                                        )

                                        # 优先匹配：完全匹配
                                        for reg in all_registries:
                                            reg_address = reg.get("registry", "")
                                            reg_name = reg.get("name", "Unknown")
                                            if (
                                                reg_address
                                                and img_registry == reg_address
                                            ):
                                                log(
                                                    f"✅ 找到完全匹配的registry: {reg_name} (地址: {reg_address})\n"
                                                )
                                                # 使用 get_registry_by_name 获取包含解密密码的配置
                                                return get_registry_by_name(reg_name)

                                        # 次优匹配：包含关系
                                        for reg in all_registries:
                                            reg_address = reg.get("registry", "")
                                            reg_name = reg.get("name", "Unknown")
                                            if reg_address and (
                                                img_registry.startswith(reg_address)
                                                or reg_address.startswith(img_registry)
                                                or img_registry in reg_address
                                                or reg_address in img_registry
                                            ):
                                                log(
                                                    f"✅ 找到部分匹配的registry: {reg_name} (地址: {reg_address})\n"
                                                )
                                                # 使用 get_registry_by_name 获取包含解密密码的配置
                                                return get_registry_by_name(reg_name)

                                        log(f"⚠️  未找到匹配的registry配置\n")
                                    return None

                                # 如果服务配置中指定了 registry，优先使用指定的 registry
                                if service_registry:
                                    log(
                                        f"🔍 使用服务指定的 registry: {service_registry}\n"
                                    )
                                    # 使用 get_registry_by_name 获取包含解密密码的配置
                                    registry_config = get_registry_by_name(
                                        service_registry
                                    )
                                    if registry_config:
                                        log(
                                            f"✅ 找到指定的 registry 配置: {service_registry}\n"
                                        )
                                    else:
                                        log(
                                            f"⚠️  未找到指定的 registry: {service_registry}，将尝试从镜像名匹配\n"
                                        )
                                        registry_config = None

                                # 如果未指定 registry 或找不到指定的 registry，尝试根据镜像名找到匹配的registry
                                if not registry_config:
                                    registry_config = find_matching_registry_for_push(
                                        service_image_name
                                    )

                                if not registry_config:
                                    # 如果仍然找不到匹配的，使用激活的registry作为后备
                                    registry_config = get_active_registry()
                                    log(
                                        f"⚠️  未找到匹配的registry配置，使用激活仓库作为后备: {registry_config.get('name', 'Unknown')}\n"
                                    )
                                else:
                                    log(
                                        f"🎯 使用registry配置: {registry_config.get('name', 'Unknown')} (地址: {registry_config.get('registry', 'Unknown')})\n"
                                    )

                                username = registry_config.get("username")
                                password = registry_config.get("password")
                                registry_host = registry_config.get("registry", "")

                                auth_config = None
                                if username and password:
                                    auth_config = {
                                        "username": username,
                                        "password": password,
                                    }
                                    if registry_host and registry_host != "docker.io":
                                        auth_config["serveraddress"] = registry_host
                                    else:
                                        auth_config["serveraddress"] = (
                                            "https://index.docker.io/v1/"
                                        )

                                # 使用完整的镜像名和 tag 进行推送
                                # service_image_name 格式: image_name-service_name (可能包含 registry 前缀)
                                push_repository = service_image_name
                                push_tag = service_tag_value  # 使用服务配置的 tag

                                # 推送并处理错误（支持重试）
                                push_retried = False

                                try:
                                    push_stream = docker_builder.push_image(
                                        push_repository,
                                        push_tag,
                                        auth_config=auth_config,
                                    )

                                    for chunk in push_stream:
                                        if isinstance(chunk, dict):
                                            if "status" in chunk:
                                                log(
                                                    f"[{service_name}] {chunk['status']}\n"
                                                )
                                            elif "error" in chunk:
                                                error_msg = chunk["error"]
                                                error_detail = chunk.get(
                                                    "errorDetail", {}
                                                )
                                                log(
                                                    f"[{service_name}] ❌ 推送错误: {error_msg}\n"
                                                )

                                                # 检查是否是认证错误
                                                is_auth_error = (
                                                    "denied" in error_msg.lower()
                                                    or "unauthorized"
                                                    in error_msg.lower()
                                                    or "401"
                                                    in str(error_detail).lower()
                                                    or "authentication required"
                                                    in error_msg.lower()
                                                )

                                                if is_auth_error and not push_retried:
                                                    # 尝试重新登录并重试
                                                    log(
                                                        f"[{service_name}] 🔄 检测到认证错误，尝试重新登录...\n"
                                                    )
                                                    if _retry_login_and_push(
                                                        docker_builder,
                                                        push_repository,
                                                        push_tag,
                                                        auth_config,
                                                        username,
                                                        password,
                                                        registry_host,
                                                        log,
                                                    ):
                                                        # 重新登录成功，重试推送
                                                        log(
                                                            f"[{service_name}] 🔄 重新登录成功，重试推送...\n"
                                                        )
                                                        push_retried = True
                                                        push_stream = (
                                                            docker_builder.push_image(
                                                                push_repository,
                                                                push_tag,
                                                                auth_config=auth_config,
                                                            )
                                                        )
                                                        for retry_chunk in push_stream:
                                                            if isinstance(
                                                                retry_chunk, dict
                                                            ):
                                                                if (
                                                                    "status"
                                                                    in retry_chunk
                                                                ):
                                                                    log(
                                                                        f"[{service_name}] {retry_chunk['status']}\n"
                                                                    )
                                                                elif (
                                                                    "error"
                                                                    in retry_chunk
                                                                ):
                                                                    retry_error_msg = (
                                                                        retry_chunk[
                                                                            "error"
                                                                        ]
                                                                    )
                                                                    log(
                                                                        f"[{service_name}] ❌ 重试推送仍然失败: {retry_error_msg}\n"
                                                                    )
                                                                    raise RuntimeError(
                                                                        f"服务 {service_name} 推送失败（已重试）: {retry_error_msg}"
                                                                    )
                                                        # 重试成功，跳出外层循环
                                                        break
                                                    else:
                                                        raise RuntimeError(
                                                            f"服务 {service_name} 推送失败: {error_msg}（重新登录失败）"
                                                        )
                                                else:
                                                    raise RuntimeError(
                                                        f"服务 {service_name} 推送失败: {error_msg}"
                                                    )

                                    log(f"✅ 服务 {service_name} 推送完成\n")

                                except RuntimeError:
                                    raise
                                except Exception as e:
                                    error_str = str(e)
                                    # 检查是否是认证错误
                                    is_auth_error = (
                                        "denied" in error_str.lower()
                                        or "unauthorized" in error_str.lower()
                                        or "401" in error_str
                                        or "authentication required"
                                        in error_str.lower()
                                    )

                                    if is_auth_error and not push_retried:
                                        log(
                                            f"[{service_name}] 🔄 检测到认证错误，尝试重新登录...\n"
                                        )
                                        if _retry_login_and_push(
                                            docker_builder,
                                            push_repository,
                                            push_tag,
                                            auth_config,
                                            username,
                                            password,
                                            registry_host,
                                            log,
                                        ):
                                            # 重新登录成功，重试推送
                                            log(
                                                f"[{service_name}] 🔄 重新登录成功，重试推送...\n"
                                            )
                                            try:
                                                push_stream = docker_builder.push_image(
                                                    push_repository,
                                                    push_tag,
                                                    auth_config=auth_config,
                                                )
                                                for retry_chunk in push_stream:
                                                    if isinstance(retry_chunk, dict):
                                                        if "status" in retry_chunk:
                                                            log(
                                                                f"[{service_name}] {retry_chunk['status']}\n"
                                                            )
                                                        elif "error" in retry_chunk:
                                                            retry_error_msg = (
                                                                retry_chunk["error"]
                                                            )
                                                            log(
                                                                f"[{service_name}] ❌ 重试推送仍然失败: {retry_error_msg}\n"
                                                            )
                                                            raise RuntimeError(
                                                                f"服务 {service_name} 推送失败（已重试）: {retry_error_msg}"
                                                            )
                                                log(
                                                    f"✅ 服务 {service_name} 推送完成（重试成功）\n"
                                                )
                                            except Exception as retry_error:
                                                raise RuntimeError(
                                                    f"服务 {service_name} 推送失败（已重试）: {str(retry_error)}"
                                                )
                                        else:
                                            raise RuntimeError(
                                                f"服务 {service_name} 推送失败: {error_str}（重新登录失败）"
                                            )
                                    else:
                                        raise
                            except Exception as e:
                                log(f"❌ 服务 {service_name} 推送失败: {str(e)}\n")
                                # 推送失败不影响构建成功
                        else:
                            log(f"⏭️  服务 {service_name} 跳过推送\n")

                log(f"\n{'='*60}\n")
                log(f"✅ 所有服务构建完成，共构建 {len(built_services)} 个服务\n")
                log(f"📋 已构建的服务: {', '.join(built_services)}\n")

            else:
                # 单服务构建（原有逻辑）
                log(f"🔨 开始构建镜像: {full_tag}\n")
                log(f"📂 构建上下文: {build_context}\n")
                log(f"📄 Dockerfile 绝对路径: {dockerfile_path}\n")

                log(f"🐳 准备调用 Docker 构建器...\n")
                try:
                    build_stream = docker_builder.build_image(
                        path=build_context, tag=full_tag, dockerfile=dockerfile_relative
                    )
                    log(f"✅ Docker 构建流已启动\n")
                except Exception as e:
                    log(f"❌ 启动 Docker 构建失败: {str(e)}\n")
                    import traceback

                    log(f"详细错误:\n{traceback.format_exc()}\n")
                    raise

                log(f"🔍 开始处理 Docker 构建流输出...\n")
                chunk_count = 0
                for chunk in build_stream:
                    chunk_count += 1
                    if isinstance(chunk, dict):
                        # 记录所有字段，确保不遗漏任何信息
                        if "stream" in chunk:
                            log(chunk["stream"])  # 编译日志在这里
                        if "status" in chunk:
                            log(f"📊 {chunk['status']}\n")
                        if "progress" in chunk:
                            log(f"⏳ {chunk['progress']}\n")
                        if "error" in chunk:
                            error_msg = chunk["error"]
                            log(f"❌ 构建错误: {error_msg}\n")
                            raise RuntimeError(error_msg)
                        if "errorDetail" in chunk:
                            error_detail = chunk["errorDetail"]
                            log(f"💥 错误详情: {error_detail}\n")
                        # 记录其他未知字段
                        unknown_keys = set(chunk.keys()) - {
                            "stream",
                            "status",
                            "progress",
                            "error",
                            "errorDetail",
                            "aux",
                            "id",
                        }
                        if unknown_keys:
                            log(f"🔧 其他信息: {chunk}\n")
                    else:
                        log(f"📦 原始输出: {str(chunk)}\n")
                log(f"✅ Docker 构建流处理完成，共 {chunk_count} 个数据块\n")

                log(f"✅ 镜像构建完成: {full_tag}\n")

            # 如果需要推送，直接使用构建好的镜像名推送，从激活的registry获取认证信息
            if should_push:
                log(f"📡 开始推送镜像...\n")
                # 直接使用构建时的镜像名和标签进行推送
                # full_tag 格式: image_name:tag，可能包含registry路径
                # 例如: registry.cn-shanghai.aliyuncs.com/51jbm/app2docker:dev
                push_repository = image_name  # 直接使用构建时的镜像名

                # 根据镜像名找到对应的registry配置
                def find_matching_registry_for_push(image_name):
                    """根据镜像名找到匹配的registry配置"""
                    # 如果镜像名包含斜杠，提取registry部分
                    parts = image_name.split("/")
                    if len(parts) >= 2 and "." in parts[0]:
                        # 镜像名格式: registry.com/namespace/image
                        image_registry = parts[0]
                        log(f"🔍 从镜像名提取registry: {image_registry}\n")
                        all_registries = get_all_registries()
                        log(f"🔍 共有 {len(all_registries)} 个registry配置\n")
                        for reg in all_registries:
                            reg_address = reg.get("registry", "")
                            reg_name = reg.get("name", "Unknown")
                            log(f"🔍 检查registry: {reg_name}, 地址: {reg_address}\n")
                            if reg_address and (
                                image_registry == reg_address
                                or image_registry.startswith(reg_address)
                                or reg_address.startswith(image_registry)
                            ):
                                log(f"✅ 找到匹配的registry: {reg_name}\n")
                                # 使用get_registry_by_name获取包含解密密码的完整配置
                                return get_registry_by_name(reg_name)
                    return None

                # 尝试根据镜像名找到匹配的registry
                registry_config = find_matching_registry_for_push(image_name)
                if not registry_config:
                    # 如果找不到匹配的，使用激活的registry
                    registry_config = get_active_registry()
                    log(
                        f"⚠️  未找到匹配的registry配置，使用激活仓库: {registry_config.get('name', 'Unknown')}\n"
                    )
                else:
                    log(
                        f"🎯 找到匹配的registry配置: {registry_config.get('name', 'Unknown')}\n"
                    )

                log(f"📦 推送镜像: {full_tag}\n")

                # 从registry配置中获取认证信息
                username = registry_config.get("username")
                password = registry_config.get("password")
                registry_host = registry_config.get("registry", "")

                log(
                    f"🔐 Registry配置 - 地址: {registry_host}, 用户名: {username}, 密码: {'***' if password else '(未配置)'}\n"
                )

                auth_config = None
                if username and password:
                    # 构建auth_config，包含registry信息
                    # docker-py的push API需要serveraddress字段来指定registry
                    auth_config = {
                        "username": username,
                        "password": password,
                    }
                    # 对于非docker.io的registry，必须设置serveraddress
                    # 注意：对于阿里云等registry，直接使用registry地址，不需要加协议
                    if registry_host:
                        if registry_host != "docker.io":
                            # 对于阿里云等registry，直接使用registry地址
                            auth_config["serveraddress"] = registry_host
                        else:
                            # docker.io使用标准地址
                            auth_config["serveraddress"] = "https://index.docker.io/v1/"
                    else:
                        # 如果没有registry_host，默认使用docker.io
                        auth_config["serveraddress"] = "https://index.docker.io/v1/"

                    log(f"✅ 已配置认证信息\n")
                    log(
                        f"🔐 Auth配置: username={username}, serveraddress={auth_config.get('serveraddress', 'docker.io')}\n"
                    )

                    # 对于阿里云registry，添加特殊提示
                    if registry_host and "aliyuncs.com" in registry_host:
                        log(
                            f"ℹ️  检测到阿里云registry，请确保使用独立的Registry登录密码\n"
                        )

                    # 推送前先登录到registry（重要：确保认证生效）
                    try:
                        if hasattr(docker_builder, "client") and docker_builder.client:
                            # 对于阿里云等registry，需要确保使用正确的registry地址
                            login_registry = (
                                registry_host
                                if registry_host and registry_host != "docker.io"
                                else None
                            )
                            log(
                                f"🔑 正在登录到registry: {login_registry or 'docker.io'}\n"
                            )
                            log(f"🔑 用户名: {username}\n")

                            # 执行登录
                            login_result = docker_builder.client.login(
                                username=username,
                                password=password,
                                registry=login_registry,
                            )
                            log(f"✅ 登录成功: {login_result}\n")
                        else:
                            log(f"⚠️  Docker客户端不可用，跳过登录\n")
                    except Exception as login_error:
                        error_msg = str(login_error)
                        log(f"❌ 登录失败: {error_msg}\n")

                        # 检查是否是认证错误
                        if (
                            "401" in error_msg
                            or "Unauthorized" in error_msg
                            or "unauthorized" in error_msg
                        ):
                            log(f"⚠️  认证失败，可能的原因：\n")
                            log(f"   1. 用户名或密码不正确\n")
                            log(f"   2. 对于阿里云registry，请确认：\n")
                            log(
                                f"      - 用户名：使用阿里云账号或独立的镜像仓库用户名\n"
                            )
                            log(f"      - 密码：使用阿里云账号密码或镜像仓库独立密码\n")
                            log(f"      - 如果使用访问令牌，请确认令牌未过期\n")
                            log(f"   3. 请检查registry配置中的认证信息是否正确\n")
                            log(
                                f"⚠️  继续尝试推送（推送时会使用auth_config，但可能仍然失败）\n"
                            )
                        else:
                            log(f"⚠️  继续尝试推送（推送时会使用auth_config）\n")
                else:
                    log(f"⚠️  registry未配置认证信息，推送可能失败\n")

                # 推送并处理错误（支持重试）
                push_retried = False
                try:
                    # 直接推送构建好的镜像
                    log(f"🚀 开始推送，repository: {push_repository}, tag: {tag}\n")
                    if auth_config:
                        log(
                            f"🔐 使用认证信息: username={auth_config.get('username')}, serveraddress={auth_config.get('serveraddress', 'docker.io')}\n"
                        )
                    else:
                        log(f"⚠️  未使用认证信息\n")
                    push_stream = docker_builder.push_image(
                        push_repository, tag, auth_config=auth_config
                    )
                    for chunk in push_stream:
                        if isinstance(chunk, dict):
                            if "status" in chunk:
                                log(chunk["status"] + "\n")
                            elif "error" in chunk:
                                error_detail = chunk.get("errorDetail", {})
                                error_msg = chunk["error"]
                                log(f"❌ 推送错误: {error_msg}\n")
                                if error_detail:
                                    log(f"❌ 错误详情: {error_detail}\n")

                                # 检查是否是认证错误
                                is_auth_error = (
                                    "denied" in error_msg.lower()
                                    or "unauthorized" in error_msg.lower()
                                    or "401" in str(error_detail).lower()
                                    or "authentication required" in error_msg.lower()
                                )

                                if is_auth_error and not push_retried:
                                    # 尝试重新登录并重试
                                    log(f"🔄 检测到认证错误，尝试重新登录...\n")
                                    if _retry_login_and_push(
                                        docker_builder,
                                        push_repository,
                                        tag,
                                        auth_config,
                                        username,
                                        password,
                                        registry_host,
                                        log,
                                    ):
                                        # 重新登录成功，重试推送
                                        log(f"🔄 重新登录成功，重试推送...\n")
                                        push_retried = True
                                        push_stream = docker_builder.push_image(
                                            push_repository,
                                            tag,
                                            auth_config=auth_config,
                                        )
                                        for retry_chunk in push_stream:
                                            if isinstance(retry_chunk, dict):
                                                if "status" in retry_chunk:
                                                    log(retry_chunk["status"] + "\n")
                                                elif "error" in retry_chunk:
                                                    retry_error_detail = (
                                                        retry_chunk.get(
                                                            "errorDetail", {}
                                                        )
                                                    )
                                                    retry_error_msg = retry_chunk[
                                                        "error"
                                                    ]
                                                    log(
                                                        f"❌ 重试推送仍然失败: {retry_error_msg}\n"
                                                    )
                                                    if retry_error_detail:
                                                        log(
                                                            f"❌ 错误详情: {retry_error_detail}\n"
                                                        )
                                                    raise RuntimeError(
                                                        f"推送失败（已重试）: {retry_error_msg}"
                                                    )
                                        # 重试成功，跳出外层循环
                                        break
                                    else:
                                        raise RuntimeError(
                                            f"推送失败: {error_msg}（重新登录失败）"
                                        )
                                else:
                                    raise RuntimeError(chunk["error"])
                        else:
                            log(str(chunk))

                    log(f"✅ 推送完成: {full_tag}\n")
                except RuntimeError:
                    raise
                except Exception as e:
                    error_str = str(e)
                    log(f"❌ 推送异常: {error_str}\n")

                    # 检查是否是认证错误
                    is_auth_error = (
                        "denied" in error_str.lower()
                        or "unauthorized" in error_str.lower()
                        or "401" in error_str
                        or "authentication required" in error_str.lower()
                    )

                    if is_auth_error:
                        # 如果还没有重试过，尝试重新登录并重试
                        if username and password and not push_retried:
                            log(f"🔄 检测到认证错误，尝试重新登录...\n")
                            if _retry_login_and_push(
                                docker_builder,
                                push_repository,
                                tag,
                                auth_config,
                                username,
                                password,
                                registry_host,
                                log,
                            ):
                                # 重新登录成功，重试推送
                                log(f"🔄 重新登录成功，重试推送...\n")
                                try:
                                    push_stream = docker_builder.push_image(
                                        push_repository, tag, auth_config=auth_config
                                    )
                                    for retry_chunk in push_stream:
                                        if isinstance(retry_chunk, dict):
                                            if "status" in retry_chunk:
                                                log(retry_chunk["status"] + "\n")
                                            elif "error" in retry_chunk:
                                                retry_error_msg = retry_chunk["error"]
                                                log(
                                                    f"❌ 重试推送仍然失败: {retry_error_msg}\n"
                                                )
                                                raise RuntimeError(
                                                    f"推送失败（已重试）: {retry_error_msg}"
                                                )
                                    log(f"✅ 推送完成（重试成功）: {full_tag}\n")
                                except Exception as retry_error:
                                    raise RuntimeError(
                                        f"推送失败（已重试）: {str(retry_error)}"
                                    )
                            else:
                                # 重新登录失败，提供详细提示
                                log(f"💡 推送认证失败，建议：\n")
                                log(f"   1. 确认registry配置中的用户名和密码正确\n")
                                log(
                                    f"   2. 对于阿里云registry，请使用独立的Registry登录密码\n"
                                )
                                log(f"   3. 检查认证信息是否过期（如访问令牌）\n")
                                log(f"   4. 可以尝试手动执行以下命令测试：\n")
                                log(
                                    f"      docker login --username={username} {registry_host or ''}\n"
                                )
                                log(f"      docker push {full_tag}\n")
                                log(
                                    f"   5. 如果手动命令成功，说明配置有问题；如果也失败，说明认证信息不正确\n"
                                )
                                raise RuntimeError(
                                    f"推送失败: {error_str}（重新登录失败）"
                                )
                        else:
                            # 已经重试过或没有认证信息，提供详细提示
                            log(f"💡 推送认证失败，建议：\n")
                            log(f"   1. 确认registry配置中的用户名和密码正确\n")
                            log(
                                f"   2. 对于阿里云registry，请使用独立的Registry登录密码\n"
                            )
                            log(f"   3. 检查认证信息是否过期（如访问令牌）\n")
                            log(f"   4. 可以尝试手动执行以下命令测试：\n")
                            log(
                                f"      docker login --username={username or 'YOUR_USERNAME'} {registry_host or ''}\n"
                            )
                            log(f"      docker push {full_tag}\n")
                            log(
                                f"   5. 如果手动命令成功，说明配置有问题；如果也失败，说明认证信息不正确\n"
                            )
                            raise

                    # 推送失败不影响构建成功，记录错误但继续完成任务
                    log(f"⚠️ 推送失败，但构建已完成，任务将继续完成\n")

            log(f"✅ 所有操作已完成\n")
            # 更新任务状态为完成（确保状态更新）
            print(f"🔍 准备更新任务 {task_id[:8]} 状态为 completed")
            try:
                self.task_manager.update_task_status(task_id, "completed")
                print(f"✅ 任务 {task_id[:8]} 状态已更新为 completed")
                # 验证状态是否真的更新了
                updated_task = self.task_manager.get_task(task_id)
                if updated_task and updated_task.get("status") == "completed":
                    print(
                        f"✅ 任务 {task_id[:8]} 状态验证成功: {updated_task.get('status')}"
                    )
                else:
                    print(
                        f"⚠️ 任务 {task_id[:8]} 状态验证失败，当前状态: {updated_task.get('status') if updated_task else 'None'}"
                    )
            except Exception as status_error:
                print(f"❌ 更新任务状态失败: {status_error}")
                import traceback

                traceback.print_exc()
            # 从任务字典中移除已完成的线程
            with self.lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
                    print(f"✅ 任务 {task_id[:8]} 线程已清理")

        except Exception as e:
            import traceback

            error_msg = str(e)
            error_trace = traceback.format_exc()

            # 尝试记录错误日志，即使log函数失败也要确保错误被记录
            try:
                log(f"❌ 构建失败: {error_msg}\n")
                log(f"📋 错误堆栈:\n{error_trace}\n")
            except Exception as log_error:
                # 如果log函数失败，直接使用任务管理器记录
                print(f"⚠️ 日志记录失败，直接记录错误: {log_error}")
                try:
                    self.task_manager.add_log(task_id, f"❌ 构建失败: {error_msg}\n")
                    self.task_manager.add_log(task_id, f"📋 错误堆栈:\n{error_trace}\n")
                except Exception as add_log_error:
                    print(f"⚠️ 直接记录日志也失败: {add_log_error}")
                    # 最后的手段：打印到控制台
                    print(f"❌ 构建失败 (task_id={task_id}): {error_msg}")
                    print(f"📋 错误堆栈:\n{error_trace}")

            # 更新任务状态为失败
            try:
                self.task_manager.update_task_status(task_id, "failed", error=error_msg)
            except Exception as status_error:
                print(f"⚠️ 更新任务状态失败: {status_error}")
                print(f"任务ID: {task_id}, 错误: {error_msg}")

            # 从任务字典中移除失败的线程
            with self.lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
                    print(f"✅ 任务 {task_id[:8]} 线程已清理（异常失败）")

            traceback.print_exc()
        finally:
            # 清理构建上下文（可选，保留用于调试）
            pass
            # if os.path.exists(build_context):
            #     try:
            #         shutil.rmtree(build_context, ignore_errors=True)
            #     except Exception as e:
            #         print(f"⚠️ 清理失败: {e}")

    def _clone_git_repo(
        self,
        git_url: str,
        clone_dir: str,
        branch: str = None,
        git_config: dict = None,
        log_func=None,
    ):
        """克隆 Git 仓库"""
        try:
            git_config = git_config or {}
            log = log_func or (lambda x: None)

            # 准备 Git 命令
            cmd = ["git", "clone"]

            # 如果是 HTTPS URL 且有用户名密码，嵌入到 URL 中
            if (
                git_url.startswith("https://")
                and git_config.get("username")
                and git_config.get("password")
            ):
                # 将用户名密码嵌入 URL
                from urllib.parse import urlparse, urlunparse

                parsed = urlparse(git_url)
                auth_url = urlunparse(
                    (
                        parsed.scheme,
                        f"{git_config['username']}:{git_config['password']}@{parsed.netloc}",
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )
                git_url = auth_url
                log("🔐 使用配置的用户名密码进行认证\n")

            # 如果是 SSH URL 且有 SSH key，配置 SSH
            if git_url.startswith("git@") and git_config.get("ssh_key_path"):
                ssh_key_path = git_config["ssh_key_path"]
                if os.path.exists(ssh_key_path):
                    # 设置 GIT_SSH_COMMAND 使用指定的 SSH key
                    os.environ["GIT_SSH_COMMAND"] = (
                        f"ssh -i {ssh_key_path} -o StrictHostKeyChecking=no"
                    )
                    log(f"🔑 使用 SSH key: {ssh_key_path}\n")

            # 如果指定了分支，需要在 URL 之前添加 -b 参数
            # 调试日志
            print(f"🔍 _clone_git_repo:")
            print(f"   - branch参数: {repr(branch)}")
            print(f"   - branch类型: {type(branch)}")
            print(f"   - branch是否为真值: {bool(branch)}")

            if branch:
                cmd.extend(["-b", branch])
                log(f"📌 检出分支: {branch}\n")
            else:
                log(f"📌 使用默认分支（未指定分支）\n")

            # Git clone 会在目标目录下创建仓库目录
            # 确定仓库名称（从 URL 提取）
            repo_name = git_url.rstrip("/").split("/")[-1].replace(".git", "")
            target_dir = os.path.join(clone_dir, repo_name)

            cmd.append(git_url)
            cmd.append(target_dir)

            # 执行克隆
            # 确保父目录存在
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)
            # 使用绝对路径，避免路径问题
            abs_target_dir = os.path.abspath(target_dir)
            abs_clone_dir = os.path.abspath(clone_dir)
            # 更新命令中的目标路径为绝对路径
            cmd[-1] = abs_target_dir

            # 调试日志：打印完整命令
            log(f"🔧 完整命令: {' '.join(cmd)}\n")

            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(abs_clone_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip() or "未知错误"
                log(f"❌ Git 克隆失败: {error_msg}\n")
                # 清理环境变量
                if "GIT_SSH_COMMAND" in os.environ:
                    del os.environ["GIT_SSH_COMMAND"]
                return (False, error_msg)

            log(f"✅ Git 仓库克隆成功\n")
            log(f"📂 仓库已克隆到: {abs_target_dir}\n")

            # 清理环境变量
            if "GIT_SSH_COMMAND" in os.environ:
                del os.environ["GIT_SSH_COMMAND"]

            return (True, None)

        except subprocess.TimeoutExpired:
            error_msg = "Git 克隆超时（超过5分钟）"
            log(f"❌ {error_msg}\n")
            # 清理环境变量
            if "GIT_SSH_COMMAND" in os.environ:
                del os.environ["GIT_SSH_COMMAND"]
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Git 克隆异常: {str(e)}"
            log(f"❌ {error_msg}\n")
            # 清理环境变量
            if "GIT_SSH_COMMAND" in os.environ:
                del os.environ["GIT_SSH_COMMAND"]
            return (False, error_msg)


# ============ 队列处理函数 ============
def _process_next_queued_task(pipeline_manager, pipeline_id: str):
    """处理队列中的下一个任务（相同流水线）- 从实际任务列表中获取

    Args:
        pipeline_manager: PipelineManager 实例
        pipeline_id: 流水线 ID
    """
    try:
        # 检查当前是否还有运行中的任务（防止并发问题）
        current_task_id = pipeline_manager.get_pipeline_running_task(pipeline_id)
        if current_task_id:
            # 检查任务是否真的在运行
            build_manager = BuildManager()
            task = build_manager.task_manager.get_task(current_task_id)
            if task and task.get("status") in ["pending", "running"]:
                # 还有任务在运行，不处理队列
                return
            else:
                # 任务已完成或不存在，解绑
                pipeline_manager.unbind_task(pipeline_id)

        # 从实际任务列表中获取下一个 pending 任务
        build_manager = BuildManager()
        pending_tasks = build_manager.task_manager.list_tasks(status="pending")

        # 找到属于该流水线的最早创建的 pending 任务
        next_task = None
        for task in pending_tasks:
            task_config = task.get("task_config", {})
            task_pipeline_id = task_config.get("pipeline_id")
            if task_pipeline_id == pipeline_id:
                # 按创建时间排序，找到最早的任务
                if next_task is None or task.get("created_at", "") < next_task.get(
                    "created_at", ""
                ):
                    next_task = task

        if not next_task:
            # 没有 pending 任务，检查是否还有 task_queue 中的任务（向后兼容）
            queued_task = pipeline_manager.get_next_queued_task(pipeline_id)
            if queued_task:
                # 从 task_queue 中创建任务（向后兼容）
                task_config = queued_task.get("task_config", {})
                task_config["pipeline_id"] = pipeline_id
                task_id = build_manager._trigger_task_from_config(task_config)
                pipeline_manager.remove_queued_task(
                    pipeline_id, queued_task.get("queue_id")
                )
                pipeline_manager.record_trigger(
                    pipeline_id,
                    task_id,
                    trigger_source=task_config.get("trigger_source", "manual"),
                    trigger_info={
                        "username": task_config.get("username", "system"),
                        "branch": task_config.get("branch"),
                        "from_queue": True,
                    },
                )
                print(
                    f"✅ 队列任务已启动（从task_queue）: 流水线 {pipeline_id[:8]}, 任务 {task_id[:8]}"
                )
            return

        # 找到下一个 pending 任务，开始执行
        task_id = next_task.get("task_id")
        task_config = next_task.get("task_config", {})

        # 绑定任务到流水线
        pipeline_manager.record_trigger(
            pipeline_id,
            task_id,
            trigger_source=task_config.get("trigger_source", "manual"),
            trigger_info={
                "username": task_config.get("username", "system"),
                "branch": task_config.get("branch"),
                "from_queue": True,  # 标记来自队列
            },
        )

        # 重新调用构建逻辑来开始执行任务
        # 从任务配置中提取参数
        git_url = task_config.get("git_url")
        image_name = task_config.get("image_name")
        tag = task_config.get("tag", "latest")
        branch = task_config.get("branch")
        project_type = task_config.get("project_type", "jar")
        template = task_config.get("template", "")
        template_params = task_config.get("template_params", {})
        should_push = task_config.get("should_push", False)
        sub_path = task_config.get("sub_path")
        use_project_dockerfile = task_config.get("use_project_dockerfile", True)
        dockerfile_name = task_config.get("dockerfile_name", "Dockerfile")
        source_id = task_config.get("source_id")
        selected_services = task_config.get("selected_services")
        service_push_config = task_config.get("service_push_config")
        service_template_params = task_config.get("service_template_params", {})
        push_mode = task_config.get("push_mode", "multi")
        resource_package_ids = task_config.get("resource_package_ids", [])
        trigger_source = task_config.get("trigger_source", "manual")

        # 启动构建线程（使用已有的任务ID）
        import threading

        thread = threading.Thread(
            target=build_manager._build_from_source_task,
            args=(
                task_id,
                git_url,
                image_name,
                tag,
                should_push,
                template,
                project_type,
                template_params or {},
                None,  # push_registry
                branch,
                sub_path,
                use_project_dockerfile,
                dockerfile_name,
                source_id,
                selected_services,
                service_push_config,
                push_mode,
                service_template_params,
                resource_package_ids or [],
            ),
            daemon=True,
        )
        thread.start()
        with build_manager.lock:
            build_manager.tasks[task_id] = thread

        print(f"✅ 队列任务已启动: 流水线 {pipeline_id[:8]}, 任务 {task_id[:8]}")

    except Exception as e:
        print(f"⚠️ 处理队列任务失败: {e}")
        import traceback

        traceback.print_exc()


# ============ 任务配置JSON结构辅助函数 ============
def build_task_config(
    git_url: str,
    image_name: str,
    tag: str = "latest",
    branch: str = None,
    project_type: str = "jar",
    template: str = None,
    template_params: dict = None,
    should_push: bool = False,
    push_registry: str = None,
    sub_path: str = None,
    use_project_dockerfile: bool = True,
    dockerfile_name: str = "Dockerfile",
    source_id: str = None,
    selected_services: list = None,
    service_push_config: dict = None,
    service_template_params: dict = None,
    push_mode: str = "multi",
    resource_package_ids: list = None,
    pipeline_id: str = None,
    trigger_source: str = "manual",
    **kwargs,
) -> dict:
    """
    构建统一的任务配置JSON结构

    Args:
        git_url: Git仓库地址
        image_name: 镜像名称
        tag: 镜像标签
        branch: 分支名称
        project_type: 项目类型
        template: 模板名称
        template_params: 模板参数
        should_push: 是否推送
        push_registry: 推送仓库（已废弃，保留向后兼容）
        sub_path: 子路径
        use_project_dockerfile: 是否使用项目Dockerfile
        dockerfile_name: Dockerfile文件名
        source_id: Git数据源ID
        selected_services: 选中的服务列表
        service_push_config: 服务推送配置
        service_template_params: 服务模板参数
        push_mode: 推送模式
        resource_package_ids: 资源包ID列表
        pipeline_id: 流水线ID
        trigger_source: 触发来源
        **kwargs: 其他参数

    Returns:
        标准化的任务配置字典
    """
    # 确保字段对齐：在单服务模式下，should_push 应该与 service_push_config 中第一个服务的 push 字段一致
    normalized_service_push_config = service_push_config or {}
    if push_mode == "single" and selected_services and len(selected_services) > 0:
        first_service = selected_services[0]
        service_config = normalized_service_push_config.get(first_service, {})
        if isinstance(service_config, dict):
            # 确保 should_push 与 service_push_config 中的 push 字段对齐
            service_push = service_config.get("push", False)
            if should_push != service_push:
                print(
                    f"⚠️ 字段对齐：should_push ({should_push}) 与 service_push_config[{first_service}].push ({service_push}) 不一致，使用 service_push_config 的值"
                )
                should_push = service_push
            # 确保 service_push_config 中的 push 字段与 should_push 一致
            if service_config.get("push") != should_push:
                normalized_service_push_config = normalized_service_push_config.copy()
                normalized_service_push_config[first_service] = service_config.copy()
                normalized_service_push_config[first_service]["push"] = should_push

    config = {
        "git_url": git_url,
        "image_name": image_name,
        "tag": tag,
        "branch": branch,
        "project_type": project_type,
        "template": template or "",
        "template_params": template_params or {},
        "should_push": should_push,
        "sub_path": sub_path,
        "use_project_dockerfile": use_project_dockerfile,
        "dockerfile_name": dockerfile_name,
        "source_id": source_id,
        "selected_services": selected_services or [],
        "service_push_config": normalized_service_push_config,
        "service_template_params": service_template_params or {},
        "push_mode": push_mode,
        "resource_package_ids": resource_package_ids or [],
        "pipeline_id": pipeline_id,
        "trigger_source": trigger_source,
    }

    # 添加其他参数
    config.update(kwargs)

    # 移除None值（保留空列表和空字典）
    return {k: v for k, v in config.items() if v is not None}


def replace_tag_date_placeholders(tag: str) -> str:
    """
    替换标签中的动态日期占位符

    支持的格式：
    - ${DATE} -> YYYYMMDD (例如: 20241225)
    - ${DATE:FORMAT} -> 自定义格式 (例如: ${DATE:YYYY-MM-DD} -> 2024-12-25)
    - ${TIMESTAMP} -> 时间戳 (例如: 1703520000)

    Args:
        tag: 原始标签字符串

    Returns:
        替换后的标签字符串
    """
    if not tag:
        return tag

    now = datetime.now()

    # 替换 ${DATE:FORMAT} 格式（自定义格式）
    import re

    date_format_pattern = r"\$\{DATE:([^}]+)\}"

    def replace_date_format(match):
        format_str = match.group(1)
        try:
            # 将 YYYY-MM-DD 格式转换为 Python 的 strftime 格式
            format_str = (
                format_str.replace("YYYY", "%Y").replace("MM", "%m").replace("DD", "%d")
            )
            format_str = (
                format_str.replace("HH", "%H").replace("mm", "%M").replace("ss", "%S")
            )
            return now.strftime(format_str)
        except:
            return match.group(0)  # 如果格式错误，返回原字符串

    tag = re.sub(date_format_pattern, replace_date_format, tag)

    # 替换 ${DATE} -> YYYYMMDD
    tag = tag.replace("${DATE}", now.strftime("%Y%m%d"))

    # 替换 ${TIMESTAMP} -> 时间戳
    tag = tag.replace("${TIMESTAMP}", str(int(now.timestamp())))

    return tag


def pipeline_to_task_config(
    pipeline: dict,
    trigger_source: str = "manual",
    branch: str = None,
    tag: str = None,
    webhook_branch: str = None,
    branch_tag_mapping: dict = None,
    **kwargs,
) -> dict:
    """
    将流水线配置转换为任务配置JSON

    Args:
        pipeline: 流水线配置字典
        trigger_source: 触发来源
        branch: 构建分支（如果指定则覆盖流水线配置）
        tag: 镜像标签（如果指定则覆盖流水线配置）
        webhook_branch: Webhook推送的分支（用于标签映射）
        branch_tag_mapping: 分支标签映射（如果提供则使用，否则从pipeline获取）
        **kwargs: 其他覆盖参数

    Returns:
        标准化的任务配置字典
    """
    # 确定使用的分支和标签
    # 如果明确提供了branch参数（不为None），使用它；否则使用流水线配置的分支
    # 注意：空字符串也是有效的分支名（表示默认分支），所以只检查 None
    if branch is not None:
        final_branch = branch
    else:
        final_branch = pipeline.get("branch")

    # 保存流水线的原始标签（用于多服务模式下的标签更新判断）
    pipeline_original_tag = pipeline.get("tag", "latest")

    # 如果传入了tag参数，使用它；否则使用流水线配置的标签
    # 注意：即使传入了tag参数，我们仍然需要检查分支标签映射，因为tag可能是外层已经映射过的
    final_tag = tag if tag is not None else pipeline_original_tag

    # 调试日志
    print(f"🔍 pipeline_to_task_config:")
    print(f"   - 传入branch参数: {branch}")
    print(f"   - 流水线配置branch: {pipeline.get('branch')}")
    print(f"   - 最终使用branch: {final_branch}")
    print(f"   - 传入tag参数: {tag}")
    print(f"   - 流水线原始tag: {pipeline_original_tag}")
    print(f"   - 初始final_tag: {final_tag}")

    # 替换标签中的动态日期占位符
    final_tag = replace_tag_date_placeholders(final_tag)

    # 处理分支标签映射（webhook和manual触发时都应用）
    # 注意：即使传入了tag参数，我们仍然需要检查分支标签映射，确保多服务模式下的标签正确更新
    if trigger_source in ["webhook", "manual"]:
        mapping = branch_tag_mapping or pipeline.get("branch_tag_mapping", {})
        # webhook触发时，优先使用webhook推送的分支；手动触发时，使用实际使用的分支
        branch_for_mapping = (
            webhook_branch
            if (trigger_source == "webhook" and webhook_branch)
            else final_branch
        )
        print(f"🔍 分支标签映射处理:")
        print(f"   - trigger_source: {trigger_source}")
        print(f"   - branch_for_mapping: {branch_for_mapping}")
        print(f"   - mapping: {mapping}")
        print(f"   - 当前final_tag: {final_tag}")
        if branch_for_mapping and mapping:
            mapped_tag_value = None
            if branch_for_mapping in mapping:
                mapped_tag_value = mapping[branch_for_mapping]
            else:
                # 尝试通配符匹配
                import fnmatch

                for pattern, mapped_tag in mapping.items():
                    if fnmatch.fnmatch(branch_for_mapping, pattern):
                        mapped_tag_value = mapped_tag
                        break

            if mapped_tag_value:
                # 处理标签值（支持字符串、数组或逗号分隔的字符串）
                # 如果传入了tag参数，且该tag在映射值中，使用传入的tag；否则使用映射值的第一个
                tag_list = []
                if isinstance(mapped_tag_value, list):
                    tag_list = mapped_tag_value
                elif isinstance(mapped_tag_value, str):
                    if "," in mapped_tag_value:
                        # 逗号分隔的多个标签
                        tag_list = [
                            t.strip() for t in mapped_tag_value.split(",") if t.strip()
                        ]
                    else:
                        # 单个标签
                        tag_list = [mapped_tag_value]

                # 如果传入了tag参数，且该tag在映射值列表中，使用传入的tag
                # 这样可以支持多个标签的场景（如test分支映射到dev,test两个标签）
                if tag and tag in tag_list:
                    final_tag = tag
                    print(f"   - 使用传入的tag参数: {tag} (在映射值中)")
                elif tag_list:
                    # 否则使用映射值的第一个标签
                    final_tag = tag_list[0]
                    print(f"   - 使用映射值的第一个标签: {tag_list[0]}")
                else:
                    # 映射值为空，保持当前final_tag
                    pass

            # 替换映射标签中的动态日期占位符
            final_tag = replace_tag_date_placeholders(final_tag)
            print(f"   - 映射后的final_tag: {final_tag}")

    # 调试日志：确认传递给 build_task_config 的分支
    print(f"🔍 pipeline_to_task_config 准备调用 build_task_config:")
    print(f"   - final_branch: {repr(final_branch)}")

    # 根据 push_mode 和 service_push_config 确定 should_push
    push_mode = pipeline.get("push_mode", "multi")
    service_push_config = pipeline.get("service_push_config", {})
    selected_services = pipeline.get("selected_services", [])

    # 在多服务模式下，如果标签已被映射更新，需要同步到 service_push_config 中每个服务的 tag
    if push_mode == "multi" and trigger_source in ["webhook", "manual"]:
        # 使用流水线的原始标签作为基准，用于判断是否需要更新服务标签
        # 如果final_tag与原始标签不同，说明标签已被映射更新，需要同步到多服务配置
        if final_tag != pipeline_original_tag:
            # 标签已被映射更新，需要同步到多服务配置中
            if selected_services and service_push_config:
                # 深拷贝 service_push_config，避免修改原始 pipeline 数据
                import copy

                service_push_config = copy.deepcopy(service_push_config)

                # 更新每个服务的 tag（强制使用映射后的标签，因为这是分支标签映射的结果）
                # 注意：即使服务配置中已经有tag，也要更新为映射后的标签，因为这是分支标签映射的要求
                for service_name in selected_services:
                    if service_name in service_push_config:
                        service_config = service_push_config[service_name]
                        if isinstance(service_config, dict):
                            # 深拷贝服务配置，避免修改原始对象
                            service_config = service_config.copy()
                            # 强制更新为映射后的标签（分支标签映射的优先级最高）
                            service_config["tag"] = final_tag
                            service_push_config[service_name] = service_config
                            print(
                                f"   - 更新服务 {service_name} 的标签为: {final_tag} (分支标签映射)"
                            )
                        else:
                            # 兼容旧格式：只有 push 布尔值，转换为新格式
                            service_push_config[service_name] = {
                                "enabled": True,
                                "push": bool(service_config),
                                "imageName": "",
                                "tag": final_tag,
                            }
                            print(
                                f"   - 为服务 {service_name} 转换并设置标签为: {final_tag} (分支标签映射)"
                            )
                    else:
                        # 如果服务没有配置，创建一个默认配置并使用映射后的标签
                        service_push_config[service_name] = {
                            "enabled": True,
                            "push": False,
                            "imageName": "",
                            "tag": final_tag,
                        }
                        print(
                            f"   - 为服务 {service_name} 创建配置，标签为: {final_tag} (分支标签映射)"
                        )

    should_push = False
    if push_mode == "single":
        # 单服务模式：从第一个服务的 service_push_config 中获取 push 配置
        if selected_services and len(selected_services) > 0:
            first_service = selected_services[0]
            service_config = service_push_config.get(first_service, {})
            if isinstance(service_config, dict):
                should_push = service_config.get("push", False)
            else:
                should_push = bool(service_config)
    else:
        # 多服务模式：使用旧的 push 字段（向后兼容）
        should_push = pipeline.get("push", False)

    print(f"🔍 should_push 计算:")
    print(f"   - push_mode: {push_mode}")
    print(f"   - selected_services: {selected_services}")
    print(f"   - service_push_config: {service_push_config}")
    print(f"   - should_push: {should_push}")

    task_config_result = build_task_config(
        git_url=pipeline.get("git_url"),
        image_name=pipeline.get("image_name") or "pipeline-build",
        tag=final_tag,
        branch=final_branch,
        project_type=pipeline.get("project_type", "jar"),
        template=pipeline.get("template"),
        template_params=pipeline.get("template_params", {}),
        should_push=should_push,
        sub_path=pipeline.get("sub_path"),
        use_project_dockerfile=pipeline.get("use_project_dockerfile", True),
        dockerfile_name=pipeline.get("dockerfile_name", "Dockerfile"),
        source_id=pipeline.get("source_id"),
        selected_services=selected_services,
        service_push_config=service_push_config,
        service_template_params=pipeline.get("service_template_params", {}),
        push_mode=push_mode,
        resource_package_ids=pipeline.get("resource_package_configs", []),
        pipeline_id=pipeline.get("pipeline_id"),
        trigger_source=trigger_source,
        **kwargs,
    )

    # 调试日志：确认返回的任务配置中的分支
    print(f"🔍 build_task_config 返回的配置:")
    print(f"   - branch字段: {repr(task_config_result.get('branch'))}")

    return task_config_result


# ============ 构建任务管理器 ============
class BuildTaskManager:
    """构建任务管理器 - 管理镜像构建任务，支持异步构建和日志存储"""

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
        except:
            pass
        self.lock = threading.Lock()
        self.tasks_dir = os.path.join(BUILD_DIR, "tasks")
        os.makedirs(self.tasks_dir, exist_ok=True)

        # 启动时，将 running/pending 状态的任务标记为失败
        self._mark_lost_tasks_as_failed()

        # 启动自动清理任务
        self._start_cleanup_task()

    def _mark_lost_tasks_as_failed(self):
        """将服务重启时丢失的任务标记为失败"""
        from backend.database import get_db_session
        from backend.models import Task

        db = get_db_session()
        try:
            lost_tasks = (
                db.query(Task).filter(Task.status.in_(["running", "pending"])).all()
            )
            if lost_tasks:
                for task in lost_tasks:
                    task.status = "failed"
                    task.error = "服务重启，任务中断"
                    task.completed_at = datetime.now()
                db.commit()
                print(f"⚠️ 已将 {len(lost_tasks)} 个丢失的任务标记为失败")
        except Exception as e:
            db.rollback()
            print(f"⚠️ 标记丢失任务失败: {e}")
        finally:
            db.close()

    def _start_cleanup_task(self):
        """启动自动清理过期任务的后台线程"""

        def cleanup_loop():
            import time

            while True:
                try:
                    time.sleep(3600)  # 每小时检查一次
                    self.cleanup_expired_tasks()
                except Exception as e:
                    print(f"⚠️ 清理构建任务出错: {e}")

        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()

    def create_task(
        self,
        task_type: str,  # "build" 或 "build_from_source"
        image_name: str,
        tag: str = "latest",
        **kwargs,  # 其他任务参数
    ) -> str:
        """创建构建任务"""
        try:
            task_id = str(uuid.uuid4())
            created_at = datetime.now()

            # 确保 kwargs 中的值可以序列化
            serializable_kwargs = {}
            for key, value in kwargs.items():
                try:
                    # 尝试序列化以检查是否可序列化
                    json.dumps(value)
                    serializable_kwargs[key] = value
                except (TypeError, ValueError) as e:
                    # 如果无法序列化，转换为字符串
                    print(f"⚠️ 参数 {key} 无法序列化，转换为字符串: {e}")
                    serializable_kwargs[key] = str(value)

            # 确定任务来源
            source = "手动构建"
            if serializable_kwargs.get("pipeline_id"):
                source = "流水线"
            elif serializable_kwargs.get("git_url"):
                source = "Git源码"
            elif serializable_kwargs.get("original_filename"):
                source = "文件上传"
            elif serializable_kwargs.get("build_steps"):
                source = "镜像构建"

            # 构建任务配置JSON（对所有类型都保存）
            task_config = None
            try:
                if task_type == "build_from_source":
                    # Git源码构建
                    task_config = build_task_config(
                        git_url=serializable_kwargs.get("git_url", ""),
                        image_name=image_name,
                        tag=tag,
                        branch=serializable_kwargs.get("branch"),
                        project_type=serializable_kwargs.get("project_type", "jar"),
                        template=serializable_kwargs.get("selected_template"),
                        template_params=serializable_kwargs.get("template_params", {}),
                        should_push=serializable_kwargs.get("should_push", False),
                        sub_path=serializable_kwargs.get("sub_path"),
                        use_project_dockerfile=serializable_kwargs.get(
                            "use_project_dockerfile", True
                        ),
                        dockerfile_name=serializable_kwargs.get(
                            "dockerfile_name", "Dockerfile"
                        ),
                        source_id=serializable_kwargs.get("source_id"),
                        selected_services=serializable_kwargs.get("selected_services"),
                        service_push_config=serializable_kwargs.get(
                            "service_push_config"
                        ),
                        service_template_params=serializable_kwargs.get(
                            "service_template_params"
                        ),
                        push_mode=serializable_kwargs.get("push_mode", "multi"),
                        resource_package_ids=serializable_kwargs.get(
                            "resource_package_ids"
                        ),
                        pipeline_id=serializable_kwargs.get("pipeline_id"),
                        trigger_source=serializable_kwargs.get(
                            "trigger_source", "manual"
                        ),
                    )
                elif task_type == "build":
                    # 文件上传构建（文件上传没有git_url，但可以保存其他配置）
                    task_config = build_task_config(
                        git_url="",  # 文件上传没有git_url
                        image_name=image_name,
                        tag=tag,
                        branch=None,  # 文件上传没有分支
                        project_type=serializable_kwargs.get("project_type", "jar"),
                        template=serializable_kwargs.get("selected_template"),
                        template_params=serializable_kwargs.get("template_params", {}),
                        should_push=serializable_kwargs.get("should_push", False),
                        sub_path=None,
                        use_project_dockerfile=False,  # 文件上传默认不使用项目Dockerfile
                        dockerfile_name="Dockerfile",
                        source_id=None,
                        selected_services=None,
                        service_push_config=None,
                        service_template_params=None,
                        push_mode="single",  # 文件上传默认单服务模式
                        resource_package_ids=serializable_kwargs.get(
                            "resource_package_ids"
                        ),
                        pipeline_id=serializable_kwargs.get("pipeline_id"),
                        trigger_source=serializable_kwargs.get(
                            "trigger_source", "manual"
                        ),
                    )
            except Exception as e:
                print(f"⚠️ 构建任务配置JSON失败: {e}")
                import traceback

                traceback.print_exc()

            # 保存任务到数据库
            from backend.database import get_db_session
            from backend.models import Task

            db = get_db_session()
            try:
                task_obj = Task(
                    task_id=task_id,
                    task_type=task_type,
                    image=image_name,
                    tag=tag,
                    status="pending",
                    created_at=created_at,
                    task_config=task_config,
                    source=source,
                    pipeline_id=serializable_kwargs.get("pipeline_id"),
                    git_url=serializable_kwargs.get("git_url"),
                    branch=serializable_kwargs.get("branch"),
                    project_type=serializable_kwargs.get("project_type", "jar"),
                    template=serializable_kwargs.get("selected_template"),
                    should_push=serializable_kwargs.get("should_push", False),
                    sub_path=serializable_kwargs.get("sub_path"),
                    use_project_dockerfile=serializable_kwargs.get(
                        "use_project_dockerfile", True
                    ),
                    dockerfile_name=serializable_kwargs.get(
                        "dockerfile_name", "Dockerfile"
                    ),
                    trigger_source=serializable_kwargs.get("trigger_source", "manual"),
                )

                db.add(task_obj)
                db.commit()
                print(f"✅ 任务创建成功: task_id={task_id}, type={task_type}")
                return task_id
            except Exception as save_error:
                db.rollback()
                print(f"⚠️ 保存任务失败，但任务已创建 (task_id={task_id}): {save_error}")
                # 即使保存失败，也继续返回 task_id
                return task_id
            finally:
                db.close()
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 创建任务异常: {e}")
            print(f"错误堆栈:\n{error_trace}")
            raise

    def _to_dict(self, task: "Task", include_logs: bool = False) -> dict:
        """将数据库模型转换为字典"""
        if not task:
            return {}

        # 获取日志（只在明确需要时加载，列表查询时不加载以提高性能）
        logs = []
        if include_logs:
            try:
                # 尝试访问关系，如果已加载则使用，否则查询
                if hasattr(task, "logs") and task.logs:
                    logs = [
                        log.log_message
                        for log in sorted(task.logs, key=lambda x: x.log_time)
                    ]
            except Exception:
                # 如果关系未加载或访问失败，返回空列表
                logs = []

        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "image": task.image,
            "tag": task.tag,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "error": task.error,
            "logs": logs,
            "source": task.source,
            "pipeline_id": task.pipeline_id,
            "task_config": task.task_config or {},
            # 向后兼容字段
            "git_url": task.git_url,
            "branch": task.branch,
            "project_type": task.project_type,
            "template": task.template,
            "should_push": task.should_push,
            "sub_path": task.sub_path,
            "use_project_dockerfile": task.use_project_dockerfile,
            "dockerfile_name": task.dockerfile_name,
            "trigger_source": task.trigger_source,
        }

    def get_task(self, task_id: str) -> dict:
        """获取任务信息"""
        from backend.database import get_db_session
        from backend.models import Task, TaskLog

        db = get_db_session()
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                return {}

            # 获取日志（单个任务查询时加载日志）
            logs = (
                db.query(TaskLog)
                .filter(TaskLog.task_id == task_id)
                .order_by(TaskLog.log_time.asc())
                .all()
            )
            log_messages = [log.log_message for log in logs]

            result = self._to_dict(task)
            result["logs"] = log_messages  # 覆盖 _to_dict 中的空日志列表
            return result
        finally:
            db.close()

    def list_tasks(self, status: str = None, task_type: str = None) -> list:
        """列出所有任务"""
        from backend.database import get_db_session
        from backend.models import Task

        db = get_db_session()
        try:
            query = db.query(Task)
            if status:
                query = query.filter(Task.status == status)
            if task_type:
                query = query.filter(Task.task_type == task_type)
            tasks = query.order_by(Task.created_at.desc()).all()
            return [self._to_dict(t) for t in tasks]
        finally:
            db.close()

    def update_task_status(self, task_id: str, status: str, error: str = None):
        """更新任务状态"""
        from backend.database import get_db_session
        from backend.models import Task

        print(f"🔍 [update_task_status] 开始更新任务 {task_id[:8]} 状态为 {status}")
        db = get_db_session()
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                print(f"⚠️ [update_task_status] 任务 {task_id[:8]} 不存在，无法更新状态")
                return

            old_status = task.status
            print(
                f"🔍 [update_task_status] 任务 {task_id[:8]} 当前状态: {old_status}, 目标状态: {status}"
            )
            task.status = status
            if error:
                task.error = error
            if status == "running":
                # 任务开始执行时，设置开始时间
                if not task.started_at:
                    task.started_at = datetime.now()
                    print(f"🔍 [update_task_status] 设置开始时间: {task.started_at}")
            if status in ("completed", "failed", "stopped"):
                task.completed_at = datetime.now()
                print(f"🔍 [update_task_status] 设置完成时间: {task.completed_at}")

            # 提交事务
            print(f"🔍 [update_task_status] 准备提交事务...")
            db.commit()
            print(
                f"✅ [update_task_status] 事务已提交，任务 {task_id[:8]} 状态已更新: {old_status} -> {status}"
            )

            # 验证更新是否成功
            db.refresh(task)
            print(
                f"🔍 [update_task_status] 验证更新后状态: {task.status}, 完成时间: {task.completed_at}"
            )

            # 任务完成、失败或停止时，解绑流水线并处理队列
            if status in ("completed", "failed", "stopped"):
                try:
                    from backend.pipeline_manager import PipelineManager

                    pipeline_manager = PipelineManager()
                    pipeline_id = pipeline_manager.find_pipeline_by_task(task_id)

                    if pipeline_id:
                        pipeline_manager.unbind_task(pipeline_id)
                        print(
                            f"✅ 任务 {task_id[:8]} 已结束，解绑流水线 {pipeline_id[:8]}, 状态={status}"
                        )

                        # 如果任务成功完成，触发构建后webhook
                        if status == "completed":
                            print(
                                f"🔔 任务 {task_id[:8]} 已完成，准备触发构建后webhook: pipeline_id={pipeline_id[:8]}"
                            )
                            try:
                                # 在后台线程中异步触发webhook
                                import threading

                                def trigger_webhooks():
                                    import asyncio

                                    try:
                                        print(
                                            f"🔔 开始异步触发构建后webhook: pipeline_id={pipeline_id[:8]}, task_id={task_id[:8]}"
                                        )
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        loop.run_until_complete(
                                            _trigger_post_build_webhooks(
                                                pipeline_id,
                                                task_id,
                                                task,
                                                pipeline_manager,
                                            )
                                        )
                                        loop.close()
                                        print(
                                            f"✅ 构建后webhook触发完成: pipeline_id={pipeline_id[:8]}"
                                        )
                                    except Exception as e:
                                        print(f"⚠️ 触发构建后webhook异常: {e}")
                                        import traceback

                                        traceback.print_exc()

                                thread = threading.Thread(
                                    target=trigger_webhooks, daemon=True
                                )
                                thread.start()
                                print(
                                    f"✅ 已启动构建后webhook触发线程: pipeline_id={pipeline_id[:8]}"
                                )
                            except Exception as webhook_error:
                                print(f"⚠️ 触发构建后webhook失败: {webhook_error}")
                                import traceback

                                traceback.print_exc()
                    else:
                        print(
                            f"ℹ️ 任务 {task_id[:8]} 未关联流水线，跳过构建后webhook触发"
                        )

                    # 处理队列中的下一个任务（相同流水线）
                    if pipeline_id:
                        _process_next_queued_task(pipeline_manager, pipeline_id)
                except Exception as e:
                    print(f"⚠️ 解绑流水线失败: {e}")
                    import traceback

                    traceback.print_exc()
        except Exception as e:
            db.rollback()
            print(f"❌ 更新任务状态失败 (task_id={task_id[:8]}, status={status}): {e}")
            import traceback

            traceback.print_exc()
            raise
        finally:
            db.close()

    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        from backend.database import get_db_session
        from backend.models import Task, TaskLog

        db = get_db_session()
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                return False

            # 只有运行中或等待中的任务才能停止
            if task.status not in ("running", "pending"):
                return False

            # 设置停止标志
            task.status = "stopped"
            task.completed_at = datetime.now()
            task.error = "任务已停止"

            # 添加停止日志
            stop_log = TaskLog(
                task_id=task_id,
                log_message="⚠️ 任务已被用户停止\n",
                log_time=datetime.now(),
            )
            db.add(stop_log)

            db.commit()
            print(f"✅ 任务 {task_id[:8]} 已停止")

            # 如果是部署任务，取消所有相关的Future
            if task.task_type == "deploy":
                try:
                    from backend.websocket_handler import connection_manager
                    from backend.deploy_task_manager import DeployTaskManager

                    # 获取任务配置，找到所有目标
                    deploy_manager = DeployTaskManager()
                    task_config = task.task_config or {}
                    config = task_config.get("config", {})
                    targets = config.get("targets", [])

                    # 取消所有目标的Future
                    for target in targets:
                        target_name = target.get("name", "")
                        if target_name:
                            future_key = f"{task_id}:{target_name}"
                            connection_manager.cancel_deploy_result_future(future_key)
                            print(f"✅ 已取消Future: {future_key}")
                except Exception as e:
                    print(f"⚠️ 取消Future失败: {e}")
                    import traceback

                    traceback.print_exc()

            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def add_log(self, task_id: str, log_message: str):
        """添加任务日志（基于数据库）"""
        from backend.database import get_db_session
        from backend.models import Task, TaskLog

        db = get_db_session()
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                print(f"⚠️ 任务不存在 (task_id={task_id})，无法记录日志")
                print(f"日志内容: {log_message}")
                return

            # 添加日志到 TaskLog 表
            task_log = TaskLog(
                task_id=task_id,
                log_message=log_message,
                log_time=datetime.now(),
            )
            db.add(task_log)

            # 限制日志数量（保留最近10000条）
            log_count = db.query(TaskLog).filter(TaskLog.task_id == task_id).count()
            if log_count > 10000:
                # 删除最旧的日志
                oldest_logs = (
                    db.query(TaskLog)
                    .filter(TaskLog.task_id == task_id)
                    .order_by(TaskLog.log_time.asc())
                    .limit(log_count - 10000)
                    .all()
                )
                for log in oldest_logs:
                    db.delete(log)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"⚠️ 添加任务日志异常 (task_id={task_id}): {e}")
            print(f"日志内容: {log_message}")
        finally:
            db.close()

    def get_logs(self, task_id: str) -> str:
        """获取任务日志"""
        from backend.database import get_db_session
        from backend.models import TaskLog

        db = get_db_session()
        try:
            logs = (
                db.query(TaskLog)
                .filter(TaskLog.task_id == task_id)
                .order_by(TaskLog.log_time.asc())
                .all()
            )
            return "".join([log.log_message for log in logs])
        finally:
            db.close()

    def delete_task(self, task_id: str) -> bool:
        """删除任务（只有停止、完成或失败的任务才能删除）"""
        from backend.database import get_db_session
        from backend.models import Task, TaskLog, DeployConfig

        db = get_db_session()
        try:
            # 先尝试作为config_id查找DeployConfig（部署配置删除）
            deploy_config = (
                db.query(DeployConfig).filter(DeployConfig.config_id == task_id).first()
            )

            if deploy_config:
                # 这是部署配置，删除DeployConfig和相关Task记录
                # 查找配置对应的Task记录
                # 在Python层面过滤，因为SQLite的JSON查询支持有限
                config_tasks = db.query(Task).filter(Task.task_type == "deploy").all()
                config_task = None
                for t in config_tasks:
                    task_config = t.task_config or {}
                    if task_config.get("config_id") == task_id:
                        config_task = t
                        break

                # 删除DeployConfig
                db.delete(deploy_config)

                # 删除配置Task记录（如果存在）
                if config_task:
                    # 删除配置任务的日志
                    db.query(TaskLog).filter(
                        TaskLog.task_id == config_task.task_id
                    ).delete()
                    db.delete(config_task)

                # 注意：不删除执行任务，保留执行历史

                db.commit()
                print(f"✅ 部署配置已删除: config_id={task_id}")
                return True

            # 否则，作为普通Task删除
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                return False

            # 如果是部署执行任务，允许删除停止/完成/失败状态的任务
            if task.task_type == "deploy":
                task_config = task.task_config or {}
                if task_config.get("source_config_id"):
                    # 这是执行任务，允许删除停止/完成/失败状态的任务
                    if task.status not in ("stopped", "completed", "failed"):
                        return False
                else:
                    # 配置任务，按普通任务规则处理（停止/完成/失败都可以删除）
                    if task.status not in ("stopped", "completed", "failed"):
                        return False
            else:
                # 其他类型的任务，停止/完成/失败都可以删除
                if task.status not in ("stopped", "completed", "failed"):
                    return False

            # 获取构建上下文路径
            build_context = None
            image_name = task.image
            if image_name:
                build_context = os.path.join(
                    BUILD_DIR, f"{image_name.replace('/', '_')}_{task_id[:8]}"
                )

            # 删除任务日志
            db.query(TaskLog).filter(TaskLog.task_id == task_id).delete()

            # 删除任务
            db.delete(task)
            db.commit()

            # 清理构建上下文目录
            if build_context and os.path.exists(build_context):
                try:
                    import shutil

                    shutil.rmtree(build_context, ignore_errors=True)
                    print(f"🧹 已清理构建上下文: {build_context}")
                except Exception as e:
                    print(f"⚠️ 清理构建上下文失败 ({build_context}): {e}")

            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def cleanup_expired_tasks(self):
        """清理过期任务（超过1天）"""
        from backend.database import get_db_session
        from backend.models import Task, TaskLog

        cutoff_time = datetime.now() - timedelta(days=1)

        db = get_db_session()
        try:
            expired_tasks = db.query(Task).filter(Task.created_at < cutoff_time).all()

            expired_tasks_info = []
            cleaned_count = 0
            for task in expired_tasks:
                # 获取构建上下文路径
                build_context = None
                image_name = task.image
                if image_name:
                    build_context = os.path.join(
                        BUILD_DIR, f"{image_name.replace('/', '_')}_{task.task_id[:8]}"
                    )
                expired_tasks_info.append((task.task_id, build_context))

                # 删除任务日志
                db.query(TaskLog).filter(TaskLog.task_id == task.task_id).delete()

                # 删除任务
                db.delete(task)

            db.commit()

            # 清理构建上下文目录
            for task_id, build_context in expired_tasks_info:
                if build_context and os.path.exists(build_context):
                    try:
                        import shutil

                        shutil.rmtree(build_context, ignore_errors=True)
                        cleaned_count += 1
                    except Exception as e:
                        print(f"⚠️ 清理构建上下文失败 ({build_context}): {e}")

            if expired_tasks_info:
                print(
                    f"🧹 已清理 {len(expired_tasks_info)} 个过期构建任务，清理了 {cleaned_count} 个构建上下文目录"
                )
        except Exception as e:
            db.rollback()
            print(f"⚠️ 清理过期任务失败: {e}")
        finally:
            db.close()

    def create_deploy_task(
        self,
        config_content: str,
        registry: Optional[str] = None,
        tag: Optional[str] = None,
        source_config_id: Optional[str] = None,
        webhook_token: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        webhook_branch_strategy: Optional[str] = None,
        webhook_allowed_branches: Optional[List[str]] = None,
        trigger_source: str = "manual",
        source: Optional[str] = None,
    ) -> str:
        """
        创建部署任务并保存到数据库

        Args:
            config_content: YAML 配置内容
            registry: 镜像仓库地址（可选）
            tag: 镜像标签（可选）
            source_config_id: 原始配置ID（如果提供，表示这是从配置触发的任务）
            webhook_token: Webhook token（可选，如果为空则自动生成）
            webhook_secret: Webhook 密钥（可选）
            webhook_branch_strategy: 分支策略（可选）
            webhook_allowed_branches: 允许触发的分支列表（可选）

        Returns:
            任务ID
        """
        from backend.deploy_config_parser import DeployConfigParser

        try:
            # 解析YAML配置
            parser = DeployConfigParser()
            config = parser.parse_yaml_content(config_content)

            # 生成任务ID
            task_id = str(uuid.uuid4())
            created_at = datetime.now()

            # 生成 Webhook Token（如果没有提供）
            if not webhook_token and not source_config_id:  # 只有配置任务才生成token
                webhook_token = str(uuid.uuid4())

            # 构建任务配置
            task_config = {
                "config_content": config_content,
                "config": config,
                "registry": registry,
                "tag": tag,
                "targets": config.get("targets", []),
            }

            # 添加webhook配置（只有配置任务才保存webhook信息）
            if not source_config_id:
                if webhook_token:
                    task_config["webhook_token"] = webhook_token
                if webhook_secret:
                    task_config["webhook_secret"] = webhook_secret
                if webhook_branch_strategy:
                    task_config["webhook_branch_strategy"] = webhook_branch_strategy
                if webhook_allowed_branches:
                    task_config["webhook_allowed_branches"] = webhook_allowed_branches

            # 如果提供了 source_config_id，说明这是从配置触发的任务
            if source_config_id:
                task_config["source_config_id"] = source_config_id

            # 保存任务到数据库
            from backend.database import get_db_session
            from backend.models import Task

            db = get_db_session()
            try:
                task_obj = Task(
                    task_id=task_id,
                    task_type="deploy",
                    image=None,  # 部署任务可能没有镜像名称
                    tag=tag,
                    status="pending",
                    created_at=created_at,
                    task_config=task_config,
                    # 任务来源文案：允许调用方自定义，否则根据是否有 source_config_id 给一个默认
                    source=source
                    or ("部署配置（执行）" if source_config_id else "手动部署"),
                    pipeline_id=None,
                    git_url=None,
                    branch=None,
                    project_type=None,
                    template=None,
                    should_push=False,
                    sub_path=None,
                    use_project_dockerfile=False,
                    dockerfile_name=None,
                    # 触发来源：manual / webhook / cron / retry 等
                    trigger_source=trigger_source or "manual",
                )

                db.add(task_obj)
                db.commit()
                print(f"✅ 部署任务创建成功: task_id={task_id}")
                return task_id
            except Exception as save_error:
                db.rollback()
                print(f"⚠️ 保存部署任务失败: {save_error}")
                raise
            finally:
                db.close()
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 创建部署任务异常: {e}")
            print(f"错误堆栈:\n{error_trace}")
            raise

    def update_deploy_task(
        self,
        task_id: str,
        config_content: str,
        registry: Optional[str] = None,
        tag: Optional[str] = None,
        webhook_token: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        webhook_branch_strategy: Optional[str] = None,
        webhook_allowed_branches: Optional[List[str]] = None,
    ) -> bool:
        """
        更新部署任务配置

        Args:
            task_id: 任务ID
            config_content: YAML 配置内容
            registry: 镜像仓库地址（可选）
            tag: 镜像标签（可选）
            webhook_token: Webhook token（可选）
            webhook_secret: Webhook 密钥（可选）
            webhook_branch_strategy: 分支策略（可选）
            webhook_allowed_branches: 允许触发的分支列表（可选）

        Returns:
            是否更新成功
        """
        from backend.deploy_config_parser import DeployConfigParser
        from backend.database import get_db_session
        from backend.models import Task

        try:
            # 解析YAML配置
            parser = DeployConfigParser()
            config = parser.parse_yaml_content(config_content)

            db = get_db_session()
            try:
                # 获取任务
                task = db.query(Task).filter(Task.task_id == task_id).first()
                if not task or task.task_type != "deploy":
                    return False

                # 检查是否是配置任务（没有source_config_id的任务）
                task_config = task.task_config or {}
                if task_config.get("source_config_id"):
                    # 这是执行产生的任务，不能更新
                    return False

                # 更新任务配置
                task_config["config_content"] = config_content
                task_config["config"] = config
                if registry is not None:
                    task_config["registry"] = registry
                if tag is not None:
                    task_config["tag"] = tag
                task_config["targets"] = config.get("targets", [])

                # 更新webhook配置
                print(f"🔍 接收到的webhook配置参数:")
                print(
                    f"  - webhook_token: {webhook_token if webhook_token is None else (webhook_token[:8] + '...' if webhook_token else '(空字符串)')}"
                )
                print(
                    f"  - webhook_secret: {webhook_secret if webhook_secret is None else ('***' if webhook_secret else '(空字符串)')}"
                )
                print(f"  - webhook_branch_strategy: {webhook_branch_strategy}")
                print(f"  - webhook_allowed_branches: {webhook_allowed_branches}")

                # 如果提供了webhook_token（包括空字符串），则更新
                if webhook_token is not None:
                    # 如果token为空字符串，生成新的token
                    if webhook_token == "":
                        webhook_token = str(uuid.uuid4())
                        print(f"🔄 生成新的webhook_token: {webhook_token[:8]}...")
                    task_config["webhook_token"] = webhook_token
                    print(f"✅ 更新webhook_token: {webhook_token[:8]}...")
                else:
                    print(f"⚠️ webhook_token为None，不更新")

                # 如果提供了webhook_secret（包括空字符串），则更新
                if webhook_secret is not None:
                    task_config["webhook_secret"] = webhook_secret
                    print(
                        f"✅ 更新webhook_secret: {'已设置' if webhook_secret else '已清空'}"
                    )
                else:
                    print(f"⚠️ webhook_secret为None，不更新")

                # 如果提供了webhook_branch_strategy，则更新
                if webhook_branch_strategy is not None:
                    task_config["webhook_branch_strategy"] = webhook_branch_strategy
                    print(f"✅ 更新webhook_branch_strategy: {webhook_branch_strategy}")
                else:
                    print(f"⚠️ webhook_branch_strategy为None，不更新")

                # 如果提供了webhook_allowed_branches，则更新（包括空列表）
                if webhook_allowed_branches is not None:
                    task_config["webhook_allowed_branches"] = webhook_allowed_branches
                    print(
                        f"✅ 更新webhook_allowed_branches: {webhook_allowed_branches}"
                    )
                else:
                    print(f"⚠️ webhook_allowed_branches为None，不更新")

                # 更新任务的tag字段（向后兼容）
                if tag is not None:
                    task.tag = tag

                # 保存更新
                task.task_config = task_config
                # 标记JSON字段已修改（SQLAlchemy需要这个来检测JSON字段的变化）
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(task, "task_config")
                db.commit()
                print(f"✅ 部署任务更新成功: task_id={task_id}")
                return True
            except Exception as save_error:
                db.rollback()
                print(f"⚠️ 更新部署任务失败: {save_error}")
                raise
            finally:
                db.close()
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 更新部署任务异常: {e}")
            print(f"错误堆栈:\n{error_trace}")
            raise

    def execute_deploy_task(
        self,
        task_id: str,
        target_names: Optional[List[str]] = None,
        trigger_source: str = "manual",
    ) -> str:
        """
        在后台线程中执行部署任务
        每次执行都会创建一个新的任务，而不是重用原有任务

        Args:
            task_id: 原始任务ID（用于获取配置）
            target_names: 要执行的目标名称列表（如果为 None，则执行所有目标）

        Returns:
            新创建的任务ID
        """
        # 检查原始任务是否存在
        original_task = self.get_task(task_id)
        if not original_task:
            raise ValueError(f"部署任务不存在: {task_id}")

        if original_task.get("task_type") != "deploy":
            raise ValueError(f"任务类型不是部署任务: {task_id}")

        # 获取原始任务的配置
        task_config = original_task.get("task_config", {})
        config_content = task_config.get("config_content", "")
        registry = task_config.get("registry")
        tag = task_config.get("tag")

        if not config_content:
            raise ValueError(f"部署任务配置内容为空，无法执行: {task_id}")

        # 创建新任务（每次执行都创建新任务，并标记为从配置触发）
        new_task_id = self.create_deploy_task(
            config_content=config_content,
            registry=registry,
            tag=tag,
            source_config_id=task_id,  # 标记这是从配置触发的任务
            trigger_source=trigger_source,
            source=("Webhook" if trigger_source == "webhook" else "手动"),
        )

        # 更新原始配置的执行统计
        from backend.database import get_db_session
        from backend.models import Task

        db = get_db_session()
        try:
            # 更新原始配置的执行统计
            original_task_obj = db.query(Task).filter(Task.task_id == task_id).first()
            if original_task_obj:
                original_task_config = original_task_obj.task_config or {}
                # 更新执行次数和最后执行时间
                execution_count = original_task_config.get("execution_count", 0) + 1
                original_task_config["execution_count"] = execution_count
                original_task_config["last_executed_at"] = datetime.now().isoformat()
                original_task_obj.task_config = original_task_config
                db.commit()
        except Exception as e:
            db.rollback()
            print(f"⚠️ 更新配置统计信息失败: {e}")
            import traceback

            traceback.print_exc()
        finally:
            db.close()

        print(
            f"🆕 基于任务 {task_id[:8]} 创建新部署任务: {new_task_id[:8]}，trigger_source={trigger_source}"
        )

        # 更新新任务状态为运行中
        self.update_task_status(new_task_id, "running")

        # 在后台线程中执行新任务
        thread = threading.Thread(
            target=self._execute_deploy_task_in_thread,
            args=(new_task_id, target_names),
            daemon=True,
        )
        thread.start()

        return new_task_id

    def _execute_deploy_task_in_thread(
        self, task_id: str, target_names: Optional[List[str]] = None
    ):
        """
        在后台线程中执行部署任务的实际逻辑

        Args:
            task_id: 任务ID
            target_names: 要执行的目标名称列表
        """
        import asyncio

        try:
            # 创建新的事件循环（因为在线程中）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 执行部署任务
            loop.run_until_complete(
                self._execute_deploy_task_async(task_id, target_names)
            )
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 执行部署任务异常: {e}")
            print(f"错误堆栈:\n{error_trace}")

            # 更新任务状态为失败
            self.update_task_status(task_id, "failed", error=str(e))
            self.add_log(task_id, f"❌ 部署任务执行失败: {str(e)}\n")

    async def _execute_deploy_task_async(
        self, task_id: str, target_names: Optional[List[str]] = None
    ):
        """
        异步执行部署任务

        Args:
            task_id: 任务ID
            target_names: 要执行的目标名称列表
        """
        from backend.deploy_task_manager import DeployTaskManager

        try:
            # 获取任务信息
            task = self.get_task(task_id)
            if not task:
                raise ValueError(f"部署任务不存在: {task_id}")

            task_config = task.get("task_config", {})
            config_content = task_config.get("config_content", "")
            config = task_config.get("config", {})
            registry = task_config.get("registry")
            tag = task_config.get("tag")

            if not config_content:
                raise ValueError("部署任务配置内容为空")

            # 创建DeployTaskManager实例（简化版，只用于执行）
            deploy_manager = DeployTaskManager()

            # 执行部署任务（传入task_manager用于状态更新）
            result = await deploy_manager.execute_task_with_manager(
                task_id=task_id,
                config_content=config_content,
                config=config,
                registry=registry,
                tag=tag,
                target_names=target_names,
                task_manager=self,
            )

            # 检查执行结果
            if result.get("success"):
                # 检查是否有失败的目标
                results = result.get("results", {})
                has_failed = any(not r.get("success", False) for r in results.values())
                if has_failed:
                    self.update_task_status(task_id, "failed", error="部分目标部署失败")
                else:
                    self.update_task_status(task_id, "completed")
            else:
                self.update_task_status(
                    task_id, "failed", error=result.get("message", "部署失败")
                )

        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 执行部署任务异常: {e}")
            print(f"错误堆栈:\n{error_trace}")

            # 更新任务状态为失败
            self.update_task_status(task_id, "failed", error=str(e))
            self.add_log(task_id, f"❌ 部署任务执行失败: {str(e)}\n")

    def retry_deploy_task(self, task_id: str) -> bool:
        """
        重试失败或停止的部署任务（在原任务上重试，不创建新任务）

        Args:
            task_id: 任务ID

        Returns:
            是否成功重试
        """
        from backend.database import get_db_session
        from backend.models import Task

        db = get_db_session()
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                print(f"⚠️ 部署任务 {task_id[:8]} 不存在")
                return False

            # 验证任务类型（确保是部署任务）
            if task.task_type != "deploy":
                print(
                    f"⚠️ 任务 {task_id[:8]} 不是部署任务（task_type={task.task_type}），无法重试"
                )
                return False

            # 只有失败、停止或已完成的任务才能重试
            if task.status not in ("failed", "stopped", "completed"):
                print(
                    f"⚠️ 部署任务 {task_id[:8]} 状态为 {task.status}，无法重试（只有失败、停止或已完成的任务才能重试）"
                )
                return False

            # 验证必要配置
            task_config = task.task_config or {}
            config_content = task_config.get("config_content", "")
            if not config_content:
                print(f"⚠️ 部署任务 {task_id[:8]} 缺少配置内容，无法重试")
                task.error = "任务缺少配置内容，无法重试"
                task.status = "failed"
                db.commit()
                return False

            # 重置任务状态（在原任务上重试，不创建新任务）
            task.status = "pending"
            task.error = None
            task.completed_at = None
            task.started_at = None  # 重置开始时间，重试时重新计时
            db.commit()

            print(f"🔄 重试部署任务: {task_id[:8]}（在原任务上重试）")

            # 直接执行原任务（不创建新任务）
            self.update_task_status(task_id, "running")

            # 在后台线程中执行任务
            thread = threading.Thread(
                target=self._execute_deploy_task_in_thread,
                args=(task_id, None),  # target_names 为 None，执行所有目标
                daemon=True,
            )
            thread.start()

            return True
        except Exception as e:
            db.rollback()
            import traceback

            print(f"❌ 重试部署任务失败: {e}")
            traceback.print_exc()
            return False
        finally:
            db.close()


# ============ 导出任务管理器 ============
class ExportTaskManager:
    """导出任务管理器 - 管理镜像导出任务，支持异步导出和文件存储"""

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
        except:
            pass
        self.lock = threading.Lock()
        self.tasks_dir = os.path.join(EXPORT_DIR, "tasks")
        os.makedirs(self.tasks_dir, exist_ok=True)

        # 启动时，将 running/pending 状态的任务标记为失败
        self._mark_lost_tasks_as_failed()

        # 启动自动清理任务
        self._start_cleanup_task()

    def _mark_lost_tasks_as_failed(self):
        """将服务重启时丢失的任务标记为失败（只标记运行中的任务，pending 状态的任务可以继续执行）"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            # 只标记 running 状态的任务为失败，pending 状态的任务可以继续执行
            lost_tasks = (
                db.query(ExportTask).filter(ExportTask.status == "running").all()
            )
            if lost_tasks:
                for task in lost_tasks:
                    task.status = "failed"
                    task.error = "服务重启，任务中断"
                    task.completed_at = datetime.now()
                db.commit()
                print(f"⚠️ 已将 {len(lost_tasks)} 个运行中的导出任务标记为失败")

            # pending 状态的任务保持原样，可以继续执行
            pending_tasks = (
                db.query(ExportTask).filter(ExportTask.status == "pending").all()
            )
            if pending_tasks:
                print(
                    f"ℹ️ 发现 {len(pending_tasks)} 个待执行的导出任务，将保持 pending 状态"
                )
        except Exception as e:
            db.rollback()
            print(f"⚠️ 标记丢失导出任务失败: {e}")
        finally:
            db.close()

    def _start_cleanup_task(self):
        """启动自动清理过期任务的后台线程"""

        def cleanup_loop():
            import time

            while True:
                try:
                    time.sleep(3600)  # 每小时检查一次
                    self.cleanup_expired_tasks()
                except Exception as e:
                    print(f"⚠️ 清理任务出错: {e}")

        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()

    def create_task(
        self,
        image: str,
        tag: str = "latest",
        compress: str = "none",
        registry: str = None,
        use_local: bool = False,
    ) -> str:
        """创建导出任务"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        task_id = str(uuid.uuid4())
        created_at = datetime.now()

        db = get_db_session()
        try:
            task_obj = ExportTask(
                task_id=task_id,
                task_type="export",
                image=image,
                tag=tag,
                compress=compress,
                registry=registry,
                use_local=use_local,
                status="pending",
                source="手动导出",
                created_at=created_at,
            )

            db.add(task_obj)
            db.commit()

            # 启动导出任务
            thread = threading.Thread(
                target=self._export_task,
                args=(task_id,),
                daemon=True,
            )
            thread.start()

            return task_id
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def _update_task_status(
        self,
        task_id: str,
        status: str,
        error: str = None,
        file_path: str = None,
        file_size: int = None,
    ):
        """更新任务状态（辅助方法）"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            task = db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
            if not task:
                return False

            task.status = status
            if error is not None:
                task.error = error
            if file_path is not None:
                task.file_path = file_path
            if file_size is not None:
                task.file_size = file_size
            if status in ("completed", "failed", "stopped"):
                task.completed_at = datetime.now()

            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"⚠️ 更新任务状态失败: {e}")
            return False
        finally:
            db.close()

    def _get_task_from_db(self, task_id: str):
        """从数据库获取任务对象"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            return db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
        finally:
            db.close()

    def _export_task(self, task_id: str):
        """执行导出任务（明确标识为导出任务，避免与其他任务混淆）"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        print(f"📦 [导出任务] 开始执行导出任务: {task_id[:8]}")

        # 检查任务是否存在
        db = get_db_session()
        try:
            task = db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
            if not task:
                print(f"❌ [导出任务] 任务 {task_id[:8]} 不存在")
                return

            # 验证任务类型（确保是导出任务）
            if task.task_type != "export":
                error_msg = f"任务类型错误: 期望 'export'，实际 '{task.task_type}'，这不是导出任务"
                print(f"❌ [导出任务] {error_msg}")
                self._update_task_status(task_id, "failed", error=error_msg)
                return

            # 检查是否已请求停止（通过状态判断）
            # 注意：只有在任务真正被用户停止时才返回，不要因为其他原因自动停止
            if task.status == "stopped":
                print(f"⚠️ [导出任务] 任务 {task_id[:8]} 已被用户停止，不执行")
                return

            # 更新状态为 running（只有在 pending 状态时才更新）
            if task.status == "pending":
                task.status = "running"
                db.commit()
                print(f"🔄 [导出任务] 任务 {task_id[:8]} 状态已更新为 running")

            image = task.image
            tag = task.tag
            compress = task.compress
            registry = task.registry
            use_local = task.use_local

            # 清理镜像名称：移除 http:// 或 https:// 前缀（Docker API 不接受协议前缀）
            # 注意：虽然创建任务时已经验证，但这里再次清理以确保安全
            if image:
                image = image.strip()
                if image.startswith("https://"):
                    image = image[8:]
                elif image.startswith("http://"):
                    image = image[7:]

                # 验证清理后的镜像名称格式
                if not image:
                    raise ValueError("镜像名称不能为空（清理协议前缀后为空）")
                if " " in image:
                    raise ValueError("镜像名称不能包含空格")

            print(
                f"📋 [导出任务] 任务配置: image={image}, tag={tag}, compress={compress}, registry={registry}, use_local={use_local}"
            )
        except Exception as e:
            db.rollback()
            import traceback

            error_msg = f"获取导出任务失败: {e}"
            print(f"❌ [导出任务] {error_msg}")
            traceback.print_exc()
            self._update_task_status(task_id, "failed", error=error_msg)
            return
        finally:
            db.close()

        try:
            # 检查停止标志
            task = self._get_task_from_db(task_id)
            if not task or task.status == "stopped":
                return

            if not DOCKER_AVAILABLE:
                raise RuntimeError("Docker 服务不可用，无法导出镜像")

            # 获取认证信息
            from backend.config import (
                get_all_registries,
                get_active_registry,
                get_registry_by_name,
            )

            registry_config = None
            if registry:
                registry_config = get_registry_by_name(registry)
                if not registry_config:
                    raise RuntimeError(f"指定的仓库 '{registry}' 不存在")

            if not registry_config:
                # 尝试智能匹配仓库
                def find_matching_registry_for_export(image_name):
                    parts = image_name.split("/")
                    if len(parts) >= 2 and "." in parts[0]:
                        image_registry = parts[0]
                        all_registries = get_all_registries()
                        for reg in all_registries:
                            reg_address = reg.get("registry", "")
                            if reg_address and (
                                image_registry == reg_address
                                or image_registry.startswith(reg_address)
                                or reg_address.startswith(image_registry)
                            ):
                                return reg
                    return None

                registry_config = find_matching_registry_for_export(image)
            if not registry_config:
                registry_config = get_active_registry()

            if not use_local:
                # 需要从远程仓库拉取镜像
                username = registry_config.get("username")
                password = registry_config.get("password")
                auth_config = None
                if username and password:
                    auth_config = {"username": username, "password": password}

                # 拉取镜像
                pull_stream = docker_builder.pull_image(image, tag, auth_config)
                chunk_count = 0
                for chunk in pull_stream:
                    chunk_count += 1
                    # 减少停止标志检查频率（每 10 个 chunk 检查一次，避免频繁查询数据库）
                    if chunk_count % 10 == 0:
                        task = self._get_task_from_db(task_id)
                        if not task:
                            return
                        # 只有在明确被用户停止时才停止
                        if task.status == "stopped":
                            print(
                                f"⚠️ 导出任务 {task_id[:8]} 在拉取镜像过程中被用户停止"
                            )
                            return
                    if "error" in chunk:
                        # 有错误时先检查是否被停止
                        task = self._get_task_from_db(task_id)
                        if not task or task.status == "stopped":
                            return
                        raise RuntimeError(chunk["error"])

            # 再次检查停止标志（只在关键节点检查）
            task = self._get_task_from_db(task_id)
            if not task:
                return
            # 只有在明确被用户停止时才停止，不要因为其他状态变化而停止
            if task.status == "stopped":
                print(f"⚠️ 导出任务 {task_id[:8]} 在拉取镜像后被用户停止")
                return

            full_tag = f"{image}:{tag}"
            # 检查镜像是否存在（本地或已拉取）
            docker_builder.get_image(full_tag)

            # 创建任务文件目录
            task_dir = os.path.join(self.tasks_dir, task_id)
            os.makedirs(task_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            safe_base = get_safe_filename(image.replace("/", "_") or "image")
            tar_filename = f"{safe_base}-{tag}-{timestamp}.tar"
            tar_path = os.path.join(task_dir, tar_filename)

            # 导出镜像
            image_stream = docker_builder.export_image(full_tag)
            chunk_count = 0
            with open(tar_path, "wb") as f:
                for chunk in image_stream:
                    chunk_count += 1
                    # 减少停止标志检查频率（每 100 个 chunk 检查一次，避免频繁查询数据库）
                    if chunk_count % 100 == 0:
                        task = self._get_task_from_db(task_id)
                        if not task:
                            # 任务不存在，停止写入
                            try:
                                if os.path.exists(tar_path):
                                    os.remove(tar_path)
                            except:
                                pass
                            return
                        # 只有在明确被用户停止时才停止
                        if task.status == "stopped":
                            print(f"⚠️ 导出任务 {task_id[:8]} 在导出过程中被用户停止")
                            # 删除部分文件
                            try:
                                if os.path.exists(tar_path):
                                    os.remove(tar_path)
                            except:
                                pass
                            return
                    f.write(chunk)

            final_path = tar_path
            file_size = os.path.getsize(tar_path)

            # 如果需要压缩
            if compress.lower() in ("gzip", "gz", "tgz", "1", "true", "yes"):
                final_path = f"{tar_path}.gz"
                with open(tar_path, "rb") as src, gzip.open(final_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                os.remove(tar_path)
                file_size = os.path.getsize(final_path)

            # 更新任务状态
            print(f"✅ [导出任务] 任务 {task_id[:8]} 执行成功: {final_path}")
            self._update_task_status(
                task_id, "completed", file_path=final_path, file_size=file_size
            )

        except Exception as e:
            import traceback

            error_msg = str(e)
            print(f"❌ [导出任务] 任务 {task_id[:8]} 执行失败: {error_msg}")
            traceback.print_exc()
            self._update_task_status(task_id, "failed", error=error_msg)

    def _to_dict(self, task: "ExportTask") -> dict:
        """将数据库模型转换为字典"""
        if not task:
            return {}

        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "image": task.image,
            "tag": task.tag,
            "compress": task.compress,
            "registry": task.registry,
            "use_local": task.use_local,
            "status": task.status,
            "file_path": task.file_path,
            "file_size": task.file_size,
            "source": task.source,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "error": task.error,
        }

    def get_task(self, task_id: str) -> dict:
        """获取任务信息"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            task = db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
            return self._to_dict(task)
        finally:
            db.close()

    def list_tasks(self, status: str = None) -> list:
        """列出所有任务"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            query = db.query(ExportTask)
            if status:
                query = query.filter(ExportTask.status == status)
            tasks = query.order_by(ExportTask.created_at.desc()).all()
            return [self._to_dict(t) for t in tasks]
        finally:
            db.close()

    def get_task_file_path(self, task_id: str) -> str:
        """获取任务文件路径"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            task = db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
            if not task:
                raise ValueError(f"任务 {task_id} 不存在")
            if task.status != "completed":
                raise ValueError(f"任务 {task_id} 尚未完成")
            file_path = task.file_path
            if not file_path or not os.path.exists(file_path):
                raise ValueError(f"任务文件不存在: {file_path}")
            return file_path
        finally:
            db.close()

    def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            task = db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
            if not task:
                return False

            # 只有运行中或等待中的任务才能停止
            if task.status not in ("running", "pending"):
                return False

            # 设置停止状态
            task.status = "stopped"
            task.completed_at = datetime.now()
            task.error = "任务已停止"

            db.commit()
            print(f"✅ 导出任务 {task_id[:8]} 已停止")
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def retry_task(self, task_id: str) -> bool:
        """重试失败或停止的任务（确保是导出任务）"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            task = db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
            if not task:
                print(f"⚠️ 导出任务 {task_id[:8]} 不存在")
                return False

            # 验证任务类型（确保是导出任务）
            if task.task_type != "export":
                print(
                    f"⚠️ 任务 {task_id[:8]} 不是导出任务（task_type={task.task_type}），无法重试"
                )
                return False

            # 只有失败或停止的任务才能重试
            if task.status not in ("failed", "stopped"):
                print(
                    f"⚠️ 导出任务 {task_id[:8]} 状态为 {task.status}，无法重试（只有失败或停止的任务才能重试）"
                )
                return False

            # 验证必要参数
            if not task.image:
                print(f"⚠️ 导出任务 {task_id[:8]} 缺少镜像名称，无法重试")
                task.error = "任务缺少镜像名称，无法重试"
                task.status = "failed"
                db.commit()
                return False

            # 重置任务状态
            task.status = "pending"
            task.error = None
            task.completed_at = None
            # 保留原有的 file_path 和 file_size，但会在新任务完成时更新

            db.commit()

            # 启动导出任务（明确调用导出任务方法）
            print(f"🔄 重新启动导出任务: {task_id[:8]}, image={task.image}:{task.tag}")
            thread = threading.Thread(
                target=self._export_task,
                args=(task_id,),
                daemon=True,
            )
            thread.start()

            print(f"✅ 导出任务 {task_id[:8]} 已重新启动")
            return True
        except Exception as e:
            db.rollback()
            import traceback

            print(f"❌ 重试导出任务失败: {e}")
            traceback.print_exc()
            raise
        finally:
            db.close()

    def delete_task(self, task_id: str) -> bool:
        """删除任务及其文件（只有停止、完成或失败的任务才能删除）"""
        from backend.database import get_db_session
        from backend.models import ExportTask

        db = get_db_session()
        try:
            task = db.query(ExportTask).filter(ExportTask.task_id == task_id).first()
            if not task:
                return False

            # 只有停止、完成或失败的任务才能删除
            if task.status not in ("stopped", "completed", "failed"):
                return False

            file_path = task.file_path
            task_dir = os.path.join(self.tasks_dir, task_id)

            # 删除文件
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"⚠️ 删除文件失败: {e}")

            # 删除任务目录
            if os.path.exists(task_dir):
                try:
                    shutil.rmtree(task_dir, ignore_errors=True)
                except Exception as e:
                    print(f"⚠️ 删除目录失败: {e}")

            # 删除任务记录
            db.delete(task)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()

    def cleanup_expired_tasks(self, days: int = 1):
        """清理过期任务（默认保留1天）"""
        from backend.database import get_db_session
        from backend.models import ExportTask
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(days=days)

        db = get_db_session()
        try:
            expired_tasks = (
                db.query(ExportTask).filter(ExportTask.created_at < cutoff_time).all()
            )

            for task in expired_tasks:
                try:
                    self.delete_task(task.task_id)
                    print(f"🗑️ 已清理过期任务: {task.task_id}")
                except Exception as e:
                    print(f"⚠️ 清理任务失败 {task.task_id}: {e}")
        finally:
            db.close()


# ============ 操作日志管理器 ============
class OperationLogger:
    """操作日志管理器 - 记录用户操作（基于数据库）"""

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
        except:
            pass
        self.lock = threading.Lock()

    @classmethod
    def log(cls, username: str, operation: str, details: dict = None):
        """记录操作日志"""
        from backend.database import get_db_session
        from backend.models import OperationLog

        db = get_db_session()
        try:
            log_entry = OperationLog(
                username=username,
                action=operation,
                details=details or {},
                timestamp=datetime.now(),
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"⚠️ 记录操作日志失败: {e}")
        finally:
            db.close()

    def get_logs(self, limit: int = 100, username: str = None, operation: str = None):
        """获取操作日志"""
        from backend.database import get_db_session
        from backend.models import OperationLog

        db = get_db_session()
        try:
            query = db.query(OperationLog)

            if username:
                query = query.filter(OperationLog.username == username)
            if operation:
                query = query.filter(OperationLog.action == operation)

            logs = query.order_by(OperationLog.timestamp.desc()).limit(limit).all()

            return [
                {
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "username": log.username,
                    "operation": log.action,
                    "details": log.details or {},
                }
                for log in logs
            ]
        except Exception as e:
            print(f"⚠️ 读取操作日志失败: {e}")
            return []
        finally:
            db.close()

    def clear_logs(self, days: int = None):
        """清理操作日志

        Args:
            days: 保留最近 N 天的日志，如果为 None 则清空所有日志

        Returns:
            清理的日志条数
        """
        from backend.database import get_db_session
        from backend.models import OperationLog

        db = get_db_session()
        try:
            if days is None:
                # 清空所有日志
                count = db.query(OperationLog).count()
                db.query(OperationLog).delete()
                db.commit()
                return count
            else:
                # 保留最近 N 天的日志
                cutoff_time = datetime.now() - timedelta(days=days)
                deleted = (
                    db.query(OperationLog)
                    .filter(OperationLog.timestamp < cutoff_time)
                    .delete()
                )
                db.commit()
                return deleted
        except Exception as e:
            db.rollback()
            print(f"⚠️ 清理操作日志失败: {e}")
            return 0
        finally:
            db.close()


async def _trigger_post_build_webhooks(
    pipeline_id: str, task_id: str, task_obj, pipeline_manager
):
    """
    触发构建后的webhook

    Args:
        pipeline_id: 流水线ID
        task_id: 任务ID
        task_obj: 任务对象
        pipeline_manager: 流水线管理器实例
    """
    try:
        # 获取流水线配置
        pipeline = pipeline_manager.get_pipeline(pipeline_id)
        if not pipeline:
            print(f"⚠️ 流水线不存在: {pipeline_id}")
            return

        # 获取构建后webhook列表
        post_build_webhooks = pipeline.get("post_build_webhooks", [])
        if not post_build_webhooks:
            print(f"ℹ️ 流水线 {pipeline.get('name')} 没有配置构建后Webhook")
            return

        print(
            f"🔔 开始触发构建后Webhook: pipeline={pipeline.get('name')}, task_id={task_id[:8]}, webhook数量={len(post_build_webhooks)}"
        )

        # 构建模板变量上下文
        task_config = task_obj.task_config or {}
        context = {
            "task_id": task_id,
            "image": task_obj.image or "",
            "tag": task_obj.tag or "",
            "status": task_obj.status,
            "branch": task_obj.branch or "",
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline.get("name", ""),
            "created_at": (
                task_obj.created_at.isoformat() if task_obj.created_at else ""
            ),
            "completed_at": (
                task_obj.completed_at.isoformat() if task_obj.completed_at else ""
            ),
        }

        # 触发每个启用的webhook
        from backend.webhook_trigger import trigger_webhook, render_template

        for idx, webhook_config in enumerate(post_build_webhooks):
            if not webhook_config.get("enabled", True):
                print(f"⏭️ Webhook {idx + 1} 已禁用，跳过")
                continue

            url = webhook_config.get("url")
            if not url:
                print(f"⚠️ Webhook {idx + 1} 配置缺少URL，跳过")
                continue

            method = webhook_config.get("method", "POST")
            headers = webhook_config.get("headers", {})
            body_template = webhook_config.get("body_template", "{}")

            # 渲染请求体模板
            try:
                body = render_template(body_template, context)
                print(f"🔍 Webhook {idx + 1} 模板渲染成功: url={url}")
            except Exception as e:
                print(f"⚠️ Webhook {idx + 1} 渲染模板失败: {e}")
                import traceback

                traceback.print_exc()
                body = body_template

            # 发送webhook请求
            print(
                f"🔔 触发构建后webhook {idx + 1}: pipeline={pipeline.get('name')}, url={url}, method={method}"
            )
            try:
                result = await trigger_webhook(url, method, headers, body)

                if result.get("success"):
                    print(
                        f"✅ Webhook {idx + 1} 触发成功: url={url}, status_code={result.get('status_code')}"
                    )
                else:
                    error_msg = result.get("error", "unknown")
                    status_code = result.get("status_code")
                    response_text = result.get("response_text", "")[:200]
                    print(
                        f"❌ Webhook {idx + 1} 触发失败: url={url}, error={error_msg}, status_code={status_code}, response={response_text}"
                    )
            except Exception as e:
                print(f"❌ Webhook {idx + 1} 触发异常: url={url}, error={str(e)}")
                import traceback

                traceback.print_exc()
    except Exception as e:
        print(f"⚠️ 触发构建后webhook异常: {e}")
        import traceback

        traceback.print_exc()

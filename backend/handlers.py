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


class Jar2DockerHandler(BaseHTTPRequestHandler):
    server_version = "Jar2Docker/1.0"

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
    ):
        full_tag = f"{image_name}:{tag}"
        # 使用 task_id 作为构建上下文目录名的一部分，避免冲突
        build_context = os.path.join(
            BUILD_DIR, f"{image_name.replace('/', '_')}_{task_id[:8]}"
        )

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
                if file_path.endswith(".zip"):
                    log("📦 解压 ZIP 文件...\n")
                    with zipfile.ZipFile(file_path, "r") as zip_ref:
                        zip_ref.extractall(extract_to)
                elif file_path.endswith((".tar.gz", ".tgz")):
                    log("📦 解压 TAR.GZ 文件...\n")
                    with tarfile.open(file_path, "r:gz") as tar_ref:
                        tar_ref.extractall(extract_to)
                elif file_path.endswith(".tar"):
                    log("📦 解压 TAR 文件...\n")
                    with tarfile.open(file_path, "r") as tar_ref:
                        tar_ref.extractall(extract_to)
                else:
                    return False
                log("✅ 解压完成\n")

                # 列出解压后的目录概况和文件
                try:
                    log("📂 解压后目录概况：\n")
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
                        else:
                            size_str = f"{total_size / (1024 * 1024):.2f} MB"

                        log(f"  📁 根目录下目录数: {len(dirs)}\n")
                        log(f"  📄 根目录下文件数: {len(files)}\n")
                        log(f"  📊 总文件数: {total_files}\n")
                        log(f"  💾 总大小: {size_str}\n")

                        if dirs:
                            log("  📁 根目录列表：\n")
                            for d in sorted(dirs)[:20]:  # 最多显示20个
                                log(f"    - {d}/\n")
                            if len(dirs) > 20:
                                log(f"    ... 还有 {len(dirs) - 20} 个目录\n")

                        if files:
                            log("  📄 根目录文件列表：\n")
                            for f in sorted(files)[:30]:  # 最多显示30个
                                file_path_full = os.path.join(extract_to, f)
                                if os.path.isfile(file_path_full):
                                    size = os.path.getsize(file_path_full)
                                    if size < 1024:
                                        f_size_str = f"{size} B"
                                    elif size < 1024 * 1024:
                                        f_size_str = f"{size / 1024:.2f} KB"
                                    else:
                                        f_size_str = f"{size / (1024 * 1024):.2f} MB"
                                    log(f"    - {f} ({f_size_str})\n")
                            if len(files) > 30:
                                log(f"    ... 还有 {len(files) - 30} 个文件\n")
                except Exception as e:
                    log(f"⚠️  无法列出目录内容: {str(e)}\n")

                return True
            except Exception as e:
                log(f"❌ 解压失败: {str(e)}\n")
                return False

        try:
            log(f"📦 开始处理上传: {original_filename}\n")
            log(f"📝 上传的文件名: {original_filename}（在构建上下文中已统一处理）\n")
            log(f"🏷️ 镜像名: {full_tag}\n")
            log(f"🧱 模板: {selected_template}\n")
            log(f"📂 项目类型: {project_type}\n")

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
                    with open(file_path, "wb") as f:
                        f.write(file_data)

                    if extract_archive:
                        # 用户选择解压
                        log(
                            f"🧪 模拟模式：检测到压缩包: {original_filename}，开始解压...\n"
                        )
                        if do_extract_archive(file_path, build_context):
                            log(
                                f"🧪 模拟模式：压缩包已解压到构建上下文根目录（原始文件名: {original_filename}）\n"
                            )
                            try:
                                os.remove(file_path)
                            except:
                                pass
                        else:
                            log("⚠️ 模拟模式：解压失败（不支持的格式）\n")
                    else:
                        # 用户选择不解压，保持压缩包原样
                        log(
                            f"🧪 模拟模式：压缩包已保存: {original_filename}（未解压，保持原样）\n"
                        )
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
                with open(file_path, "wb") as f:
                    f.write(file_data)

                if extract_archive:
                    # 用户选择解压
                    log(f"📦 检测到压缩包: {original_filename}，开始解压...\n")
                    if do_extract_archive(file_path, build_context):
                        # 解压成功，删除临时文件
                        log(
                            f"✅ 压缩包已解压到构建上下文根目录（原始文件名: {original_filename}）\n"
                        )
                        try:
                            os.remove(file_path)
                        except:
                            pass
                    else:
                        log(f"❌ 解压失败: {original_filename}\n")
                        return
                else:
                    # 用户选择不解压，保持压缩包原样
                    log(f"📦 压缩包已保存: {original_filename}（未解压，保持原样）\n")
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

            log(f"\n🚀 开始构建镜像: {full_tag}\n")
            log(f"🐳 使用构建器: {docker_builder.get_connection_info()}\n")

            # 拉取基础镜像时，Docker 会默认到所有仓库中寻找，不需要指定认证仓库

            build_stream = docker_builder.build_image(
                path=build_context, tag=full_tag, pull=True  # 自动拉取基础镜像
            )
            build_succeeded = False
            last_error = None

            for chunk in build_stream:
                if "stream" in chunk:
                    log(f"🏗️  {chunk['stream']}")
                elif "error" in chunk:
                    last_error = chunk["error"]
                    log(f"\n🔥 [DOCKER ERROR]: {last_error}\n")
                elif "errorDetail" in chunk:
                    err_msg = chunk["errorDetail"].get("message", "Unknown")
                    last_error = err_msg
                    log(f"\n💥 [ERROR DETAIL]: {err_msg}\n")
                elif "aux" in chunk and "ID" in chunk["aux"]:
                    build_succeeded = True

            if not build_succeeded:
                log(f"\n❌ 构建失败！最后错误: {last_error or '未知错误'}\n")
                return

            log(f"\n✅ 镜像构建成功: {full_tag}\n")

            if should_push:
                # 推送时直接使用构建好的镜像名，根据镜像名找到对应的registry获取认证信息
                from backend.config import get_active_registry, get_all_registries

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
                                return reg
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
            # 更新任务状态为完成
            self.task_manager.update_task_status(task_id, "completed")

        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            log(f"\n❌ 构建异常: {clean_msg}\n")
            # 更新任务状态为失败
            self.task_manager.update_task_status(task_id, "failed", error=clean_msg)
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
        pipeline_id: str = None,  # 流水线ID（可选）
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
                pipeline_id=pipeline_id,  # 传递流水线ID
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
    ):
        """从 Git 源码构建任务"""
        full_tag = f"{image_name}:{tag}"
        # 使用 task_id 作为构建上下文目录名的一部分，避免冲突
        build_context = os.path.join(
            BUILD_DIR, f"{image_name.replace('/', '_')}_{task_id[:8]}"
        )

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

            git_config = get_git_config()
            # Git clone 会在目标目录下创建仓库目录，所以目标目录应该是父目录
            clone_success = self._clone_git_repo(
                git_url, temp_clone_dir, branch, git_config, log
            )

            if not clone_success:
                raise RuntimeError("Git 克隆失败")

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

            # 检查项目中是否存在 Dockerfile
            project_dockerfile_path = os.path.join(source_dir, "Dockerfile")
            has_project_dockerfile = os.path.exists(project_dockerfile_path)

            # 决定使用项目中的 Dockerfile 还是模板
            if has_project_dockerfile and use_project_dockerfile:
                log(f"📄 检测到项目中的 Dockerfile，使用项目中的 Dockerfile\n")
                # 复制项目中的 Dockerfile 到构建上下文
                dockerfile_path = os.path.join(build_context, "Dockerfile")
                shutil.copy2(project_dockerfile_path, dockerfile_path)
                log(f"✅ 已使用项目中的 Dockerfile\n")
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

                parse_template(
                    template_path,
                    dockerfile_path,
                    {
                        "PROJECT_TYPE": project_type,
                        "UPLOADED_FILENAME": "app.jar",  # 源码构建不需要这个
                        **template_params,
                    },
                )
                log(f"✅ 已生成 Dockerfile\n")

            # 构建镜像
            log(f"🔨 开始构建镜像: {full_tag}\n")
            log(f"📂 构建上下文: {build_context}\n")
            log(f"📄 Dockerfile 绝对路径: {dockerfile_path}\n")
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
                # 例如: registry.cn-shanghai.aliyuncs.com/51jbm/jar2docker:dev
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
                                return reg
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
                                raise RuntimeError(chunk["error"])
                        else:
                            log(str(chunk))

                    log(f"✅ 推送完成: {full_tag}\n")
                except Exception as e:
                    error_str = str(e)
                    log(f"❌ 推送异常: {error_str}\n")

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
                            f"      docker login --username={username} {registry_host}\n"
                        )
                        log(f"      docker push {full_tag}\n")
                        log(
                            f"   4. 如果手动命令成功，说明配置有问题；如果也失败，说明认证信息不正确\n"
                        )

                    raise

            log(f"✅ 所有操作已完成\n")
            # 更新任务状态为完成
            self.task_manager.update_task_status(task_id, "completed")

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
            if branch:
                cmd.extend(["-b", branch])
                log(f"📌 检出分支: {branch}\n")

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
                log(f"❌ Git 克隆失败: {result.stderr}\n")
                # 清理环境变量
                if "GIT_SSH_COMMAND" in os.environ:
                    del os.environ["GIT_SSH_COMMAND"]
                return False

            log(f"✅ Git 仓库克隆成功\n")
            log(f"📂 仓库已克隆到: {abs_target_dir}\n")

            # 清理环境变量
            if "GIT_SSH_COMMAND" in os.environ:
                del os.environ["GIT_SSH_COMMAND"]

            return True

        except subprocess.TimeoutExpired:
            log("❌ Git 克隆超时（超过5分钟）\n")
            # 清理环境变量
            if "GIT_SSH_COMMAND" in os.environ:
                del os.environ["GIT_SSH_COMMAND"]
            return False
        except Exception as e:
            log(f"❌ Git 克隆异常: {str(e)}\n")
            # 清理环境变量
            if "GIT_SSH_COMMAND" in os.environ:
                del os.environ["GIT_SSH_COMMAND"]
            return False


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
        self.tasks = {}  # task_id -> task_info
        self.lock = threading.Lock()
        self.tasks_dir = os.path.join(BUILD_DIR, "tasks")
        os.makedirs(self.tasks_dir, exist_ok=True)
        self.tasks_file = os.path.join(self.tasks_dir, "tasks.json")

        # 从文件加载任务
        self._load_tasks()

        # 启动自动清理任务
        self._start_cleanup_task()

    def _load_tasks(self):
        """从文件加载任务列表"""
        if not os.path.exists(self.tasks_file):
            return

        try:
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)

            need_save = False
            with self.lock:
                self.tasks = {}
                for task in tasks_data:
                    task_id = task["task_id"]
                    # 如果任务状态是 running 或 pending，标记为失败（因为任务线程已丢失）
                    if task.get("status") in ("running", "pending"):
                        task["status"] = "failed"
                        task["error"] = "服务重启，任务中断"
                        task["completed_at"] = datetime.now().isoformat()
                        need_save = True
                    self.tasks[task_id] = task

            # 如果有任务被标记为失败，保存更新
            if need_save:
                self._save_tasks()

            print(f"✅ 已加载 {len(self.tasks)} 个构建任务")
        except Exception as e:
            print(f"⚠️ 加载构建任务列表失败: {e}")
            self.tasks = {}

    def _save_tasks(self):
        """保存任务列表到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.tasks_file), exist_ok=True)

            with self.lock:
                # 创建可序列化的任务列表
                tasks_list = []
                for task in self.tasks.values():
                    try:
                        # 尝试创建任务副本并验证可序列化
                        task_copy = task.copy()
                        # 确保 logs 是列表
                        if "logs" not in task_copy:
                            task_copy["logs"] = []
                        # 限制 logs 长度以避免序列化问题
                        if (
                            isinstance(task_copy.get("logs"), list)
                            and len(task_copy["logs"]) > 20000
                        ):
                            task_copy["logs"] = task_copy["logs"][-10000:]
                        tasks_list.append(task_copy)
                    except Exception as task_error:
                        print(
                            f"⚠️ 处理任务时出错 (task_id={task.get('task_id', 'unknown')}): {task_error}"
                        )
                        # 跳过有问题的任务，继续处理其他任务
                        continue

            # 尝试序列化以验证
            try:
                json.dumps(tasks_list)
            except (TypeError, ValueError) as json_error:
                print(f"⚠️ 任务列表无法序列化: {json_error}")
                # 尝试清理无法序列化的数据
                for task in tasks_list:
                    # 移除可能无法序列化的字段
                    if "logs" in task and isinstance(task["logs"], list):
                        # 确保所有日志项都是字符串
                        task["logs"] = [
                            str(log) if not isinstance(log, str) else log
                            for log in task["logs"]
                        ]

            temp_file = f"{self.tasks_file}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(tasks_list, f, ensure_ascii=False, indent=2)

            if os.path.exists(self.tasks_file):
                os.replace(temp_file, self.tasks_file)
            else:
                os.rename(temp_file, self.tasks_file)
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"⚠️ 保存构建任务列表失败: {e}")
            print(f"错误堆栈:\n{error_trace}")
            temp_file = f"{self.tasks_file}.tmp"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            # 不抛出异常，允许任务创建继续

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

            task_info = {
                "task_id": task_id,
                "task_type": task_type,  # "build" 或 "build_from_source"
                "image": image_name,
                "tag": tag,
                "status": "pending",  # pending, running, completed, failed
                "created_at": created_at.isoformat(),
                "completed_at": None,
                "error": None,
                "logs": [],  # 任务日志
                **serializable_kwargs,  # 其他任务参数
            }

            with self.lock:
                self.tasks[task_id] = task_info

            # 保存任务，即使失败也不影响返回 task_id
            try:
                self._save_tasks()
            except Exception as save_error:
                print(f"⚠️ 保存任务失败，但任务已创建 (task_id={task_id}): {save_error}")
                # 即使保存失败，也继续返回 task_id

            print(f"✅ 任务创建成功: task_id={task_id}, type={task_type}")
            return task_id
        except Exception as e:
            import traceback

            error_trace = traceback.format_exc()
            print(f"❌ 创建任务异常: {e}")
            print(f"错误堆栈:\n{error_trace}")
            raise

    def get_task(self, task_id: str) -> dict:
        """获取任务信息"""
        with self.lock:
            return self.tasks.get(task_id, {}).copy()

    def list_tasks(self, status: str = None, task_type: str = None) -> list:
        """列出所有任务"""
        with self.lock:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t["status"] == status]
            if task_type:
                tasks = [t for t in tasks if t.get("task_type") == task_type]
            # 按创建时间倒序排列
            tasks.sort(key=lambda x: x["created_at"], reverse=True)
            return [t.copy() for t in tasks]

    def update_task_status(self, task_id: str, status: str, error: str = None):
        """更新任务状态"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = status
                if error:
                    self.tasks[task_id]["error"] = error
                if status in ("completed", "failed"):
                    self.tasks[task_id]["completed_at"] = datetime.now().isoformat()

                    # 任务完成或失败时，解绑流水线
                    try:
                        from backend.pipeline_manager import PipelineManager

                        pipeline_manager = PipelineManager()
                        pipeline_id = pipeline_manager.find_pipeline_by_task(task_id)
                        if pipeline_id:
                            pipeline_manager.unbind_task(pipeline_id)
                            print(
                                f"✅ 任务 {task_id[:8]} 已完成，解绑流水线 {pipeline_id[:8]}"
                            )
                    except Exception as e:
                        print(f"⚠️ 解绑流水线失败: {e}")
        self._save_tasks()

    def add_log(self, task_id: str, log_message: str):
        """添加任务日志（增强错误处理）"""
        try:
            with self.lock:
                if task_id in self.tasks:
                    if "logs" not in self.tasks[task_id]:
                        self.tasks[task_id]["logs"] = []
                    # 限制日志数量，避免内存过大
                    if len(self.tasks[task_id]["logs"]) > 10000:
                        self.tasks[task_id]["logs"] = self.tasks[task_id]["logs"][
                            -5000:
                        ]
                    self.tasks[task_id]["logs"].append(log_message)
                else:
                    # 任务不存在，至少打印到控制台
                    print(f"⚠️ 任务不存在 (task_id={task_id})，无法记录日志")
                    print(f"日志内容: {log_message}")

            # 每100条日志保存一次，或者如果是关键日志（错误、完成）则立即保存
            should_save = False
            with self.lock:
                if task_id in self.tasks:
                    log_count = len(self.tasks[task_id].get("logs", []))
                    # 关键日志关键词
                    is_critical = any(
                        keyword in log_message
                        for keyword in ["❌", "✅", "ERROR", "FAIL", "完成", "失败"]
                    )
                    # 每100条或关键日志保存
                    should_save = (log_count % 100 == 0) or is_critical

            if should_save:
                try:
                    self._save_tasks()
                except Exception as save_error:
                    print(f"⚠️ 保存任务日志失败: {save_error}")
        except Exception as e:
            # 即使记录日志失败，也要打印到控制台
            print(f"⚠️ 添加任务日志异常 (task_id={task_id}): {e}")
            print(f"日志内容: {log_message}")

    def get_logs(self, task_id: str) -> str:
        """获取任务日志"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return ""
            logs = task.get("logs", [])
            return "".join(logs)

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            del self.tasks[task_id]
        self._save_tasks()
        return True

    def cleanup_expired_tasks(self):
        """清理过期任务（超过1天）"""
        cutoff_time = datetime.now() - timedelta(days=1)
        cutoff_iso = cutoff_time.isoformat()

        with self.lock:
            expired_tasks = [
                task_id
                for task_id, task in self.tasks.items()
                if task.get("created_at", "") < cutoff_iso
            ]

            for task_id in expired_tasks:
                del self.tasks[task_id]

        if expired_tasks:
            self._save_tasks()
            print(f"🧹 已清理 {len(expired_tasks)} 个过期构建任务")


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
        self.tasks = {}  # task_id -> task_info
        self.lock = threading.Lock()
        self.tasks_dir = os.path.join(EXPORT_DIR, "tasks")
        os.makedirs(self.tasks_dir, exist_ok=True)
        self.tasks_file = os.path.join(self.tasks_dir, "tasks.json")

        # 从文件加载任务
        self._load_tasks()

        # 启动自动清理任务
        self._start_cleanup_task()

    def _load_tasks(self):
        """从文件加载任务列表"""
        if not os.path.exists(self.tasks_file):
            return

        try:
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)

            need_save = False
            with self.lock:
                self.tasks = {}
                for task in tasks_data:
                    task_id = task["task_id"]
                    # 如果任务状态是 running 或 pending，标记为失败（因为任务线程已丢失）
                    if task.get("status") in ("running", "pending"):
                        task["status"] = "failed"
                        task["error"] = "服务重启，任务中断"
                        task["completed_at"] = datetime.now().isoformat()
                        need_save = True
                    # 如果任务已完成但文件不存在，标记为失败
                    elif task.get("status") == "completed":
                        file_path = task.get("file_path")
                        if file_path and not os.path.exists(file_path):
                            task["status"] = "failed"
                            task["error"] = "任务文件已丢失"
                            task["completed_at"] = datetime.now().isoformat()
                            need_save = True
                    self.tasks[task_id] = task

            # 如果有任务被标记为失败，保存更新（在锁外调用，避免死锁）
            if need_save:
                self._save_tasks()

            print(f"✅ 已加载 {len(self.tasks)} 个导出任务")
        except Exception as e:
            print(f"⚠️ 加载任务列表失败: {e}")
            self.tasks = {}

    def _save_tasks(self):
        """保存任务列表到文件（不持有锁，避免死锁）"""
        try:
            # 先复制数据，避免长时间持有锁
            with self.lock:
                tasks_list = [task.copy() for task in self.tasks.values()]

            # 使用临时文件，然后原子性替换
            temp_file = f"{self.tasks_file}.tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(tasks_list, f, ensure_ascii=False, indent=2)

            # 原子性替换
            if os.path.exists(self.tasks_file):
                os.replace(temp_file, self.tasks_file)
            else:
                os.rename(temp_file, self.tasks_file)
        except Exception as e:
            print(f"⚠️ 保存任务列表失败: {e}")
            # 清理临时文件
            temp_file = f"{self.tasks_file}.tmp"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

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
        task_id = str(uuid.uuid4())
        created_at = datetime.now()

        task_info = {
            "task_id": task_id,
            "task_type": "export",  # 添加任务类型标识
            "image": image,
            "tag": tag,
            "compress": compress,
            "registry": registry,
            "use_local": use_local,  # 是否使用本地仓库（不执行 pull）
            "status": "pending",  # pending, running, completed, failed
            "created_at": created_at.isoformat(),
            "completed_at": None,
            "file_path": None,
            "file_size": None,
            "error": None,
        }

        with self.lock:
            self.tasks[task_id] = task_info

        # 保存到文件
        self._save_tasks()

        # 启动导出任务
        thread = threading.Thread(
            target=self._export_task,
            args=(task_id,),
            daemon=True,
        )
        thread.start()

        return task_id

    def _export_task(self, task_id: str):
        """执行导出任务"""
        with self.lock:
            if task_id not in self.tasks:
                return
            task_info = self.tasks[task_id]
            task_info["status"] = "running"

        # 保存状态更新
        self._save_tasks()

        try:
            image = task_info["image"]
            tag = task_info["tag"]
            compress = task_info["compress"]
            registry = task_info["registry"]

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

            # 检查是否使用本地仓库
            use_local = task_info.get("use_local", False)

            if not use_local:
                # 需要从远程仓库拉取镜像
                username = registry_config.get("username")
                password = registry_config.get("password")
                auth_config = None
                if username and password:
                    auth_config = {"username": username, "password": password}

                # 拉取镜像
                pull_stream = docker_builder.pull_image(image, tag, auth_config)
                for chunk in pull_stream:
                    if "error" in chunk:
                        raise RuntimeError(chunk["error"])

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
            with open(tar_path, "wb") as f:
                for chunk in image_stream:
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
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id]["status"] = "completed"
                    self.tasks[task_id]["completed_at"] = datetime.now().isoformat()
                    self.tasks[task_id]["file_path"] = final_path
                    self.tasks[task_id]["file_size"] = file_size

            # 保存到文件
            self._save_tasks()

        except Exception as e:
            import traceback

            error_msg = str(e)
            traceback.print_exc()
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id]["status"] = "failed"
                    self.tasks[task_id]["completed_at"] = datetime.now().isoformat()
                    self.tasks[task_id]["error"] = error_msg

            # 保存到文件
            self._save_tasks()

    def get_task(self, task_id: str) -> dict:
        """获取任务信息"""
        with self.lock:
            return self.tasks.get(task_id, {}).copy()

    def list_tasks(self, status: str = None) -> list:
        """列出所有任务"""
        with self.lock:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t["status"] == status]
            # 按创建时间倒序排列
            tasks.sort(key=lambda x: x["created_at"], reverse=True)
            return [t.copy() for t in tasks]

    def get_task_file_path(self, task_id: str) -> str:
        """获取任务文件路径"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                raise ValueError(f"任务 {task_id} 不存在")
            if task["status"] != "completed":
                raise ValueError(f"任务 {task_id} 尚未完成")
            file_path = task.get("file_path")
            if not file_path or not os.path.exists(file_path):
                raise ValueError(f"任务文件不存在: {file_path}")
            return file_path

    def delete_task(self, task_id: str) -> bool:
        """删除任务及其文件"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            task = self.tasks[task_id]
            file_path = task.get("file_path")
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
            del self.tasks[task_id]

        # 保存到文件
        self._save_tasks()
        return True

    def cleanup_expired_tasks(self, days: int = 1):
        """清理过期任务（默认保留1天）"""
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(days=days)

        expired_task_ids = []
        with self.lock:
            for task_id, task in self.tasks.items():
                created_at = datetime.fromisoformat(task["created_at"])
                if created_at < cutoff_time:
                    expired_task_ids.append(task_id)

        for task_id in expired_task_ids:
            try:
                self.delete_task(task_id)
                print(f"🗑️ 已清理过期任务: {task_id}")
            except Exception as e:
                print(f"⚠️ 清理任务失败 {task_id}: {e}")


# ============ 操作日志管理器 ============
class OperationLogger:
    """操作日志管理器 - 记录用户操作"""

    _instance_lock = threading.Lock()
    _instance = None
    _logs_file = None

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        os.makedirs(LOGS_DIR, exist_ok=True)
        self._logs_file = os.path.join(LOGS_DIR, "operations.jsonl")
        self.lock = threading.Lock()

    @classmethod
    def log(cls, username: str, operation: str, details: dict = None):
        """记录操作日志"""
        instance = cls()
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "username": username,
            "operation": operation,
            "details": details or {},
        }

        try:
            with instance.lock:
                with open(instance._logs_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ 记录操作日志失败: {e}")

    def get_logs(self, limit: int = 100, username: str = None, operation: str = None):
        """获取操作日志"""
        if not os.path.exists(self._logs_file):
            return []

        logs = []
        try:
            with open(self._logs_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        log_entry = json.loads(line)
                        # 过滤
                        if username and log_entry.get("username") != username:
                            continue
                        if operation and log_entry.get("operation") != operation:
                            continue
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue

            # 按时间倒序排列
            logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return logs[:limit]
        except Exception as e:
            print(f"⚠️ 读取操作日志失败: {e}")
            return []

    def clear_logs(self, days: int = None):
        """清理操作日志

        Args:
            days: 保留最近 N 天的日志，如果为 None 则清空所有日志

        Returns:
            清理的日志条数
        """
        if not os.path.exists(self._logs_file):
            return 0

        try:
            with self.lock:
                if days is None:
                    # 清空所有日志
                    with open(self._logs_file, "w", encoding="utf-8") as f:
                        f.write("")
                    return 0
                else:
                    # 保留最近 N 天的日志
                    cutoff_time = datetime.now() - timedelta(days=days)
                    cutoff_iso = cutoff_time.isoformat()

                    kept_logs = []
                    removed_count = 0

                    with open(self._logs_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            try:
                                log_entry = json.loads(line)
                                timestamp = log_entry.get("timestamp", "")
                                if timestamp >= cutoff_iso:
                                    kept_logs.append(line)
                                else:
                                    removed_count += 1
                            except json.JSONDecodeError:
                                continue

                    # 写回保留的日志
                    with open(self._logs_file, "w", encoding="utf-8") as f:
                        for line in kept_logs:
                            f.write(line)

                    return removed_count
        except Exception as e:
            print(f"⚠️ 清理操作日志失败: {e}")
            raise

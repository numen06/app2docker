# handlers.py
import json
import os
import re
import shutil
import threading
import urllib
import uuid
import gzip
import zipfile
import tarfile
from datetime import datetime
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler
from urllib import parse
import yaml

from backend.config import load_config, save_config, CONFIG_FILE
from backend.utils import generate_image_name, get_safe_filename
from backend.auth import authenticate, verify_token, require_auth

# 目录配置
UPLOAD_DIR = "data/uploads"
BUILD_DIR = "data/docker_build"
EXPORT_DIR = "data/exports"
# 模板目录：内置模板（只读）+ 用户自定义模板（可读写）
BUILTIN_TEMPLATES_DIR = "templates"  # 内置模板，打包到Docker镜像中
USER_TEMPLATES_DIR = "data/templates"  # 用户自定义模板，通过Docker映射持久化
# 前端文件
DIST_DIR = "dist"  # 前端构建产物
INDEX_FILE = "dist/index.html"  # 前端入口文件

try:
    import docker

    try:
        client = docker.from_env()
        # 测试连接是否有效
        client.ping()
        DOCKER_AVAILABLE = True
        print("✅ Docker 模块加载成功，已连接到 Docker 服务")
    except Exception as e:
        print(f"⚠️ Docker 服务未运行或连接失败: {e}")
        print("🔧 启用模拟构建模式（仅输出日志，不真实构建）")
        DOCKER_AVAILABLE = False

        # 创建一个轻量模拟器，仅用于返回构建日志流
        class MockDockerClient:
            class MockImages:
                def build(self, **kwargs):
                    yield '{"stream":"模拟模式：Docker 服务不可用\\n"}\n'
                    yield '{"stream":"Step 1/4 : FROM openjdk:17-jre-slim (模拟)\\n"}\n'
                    yield '{"stream":"Step 2/4 : COPY . . (模拟)\\n"}\n'
                    yield '{"stream":"Step 3/4 : EXPOSE 8080 (模拟)\\n"}\n'
                    yield '{"stream":"Step 4/4 : ENTRYPOINT [\\"java\\", \\"-jar\\", \\"app.jar\\"] (模拟)\\n"}\n'
                    yield '{"stream":"Successfully built模拟镜像ID12345\\n"}\n'
                    yield '{"stream":"Successfully tagged 模拟镜像:latest\\n"}\n'

                def push(self, repository, tag=None, **kwargs):
                    yield '{"status":"模拟推送：推送镜像 " + repository + ":" + (tag or "latest") + " (未真实推送)"}\n'
                    yield '{"status":"模拟推送完成，耗时 0.01 秒"}\n'

            def __init__(self):
                self.images = self.MockImages()

        client = MockDockerClient()
except (ImportError, ModuleNotFoundError) as e:
    print(f"⚠️ 未安装 docker SDK 模块: {e}")
    print("🔧 启用模拟构建模式（仅输出日志，不真实构建）")
    DOCKER_AVAILABLE = False

    # 创建一个轻量模拟器，仅用于返回构建日志流
    class MockDockerClient:
        class MockImages:
            def build(self, **kwargs):
                yield '{"stream":"模拟模式：未安装 docker 模块或 Docker 服务不可用\\n"}\n'
                yield '{"stream":"Step 1/4 : FROM openjdk:17-jre-slim (模拟)\\n"}\n'
                yield '{"stream":"Step 2/4 : COPY . . (模拟)\\n"}\n'
                yield '{"stream":"Step 3/4 : EXPOSE 8080 (模拟)\\n"}\n'
                yield '{"stream":"Step 4/4 : ENTRYPOINT [\\"java\\", \\"-jar\\", \\"app.jar\\"] (模拟)\\n"}\n'
                yield '{"stream":"Successfully built模拟镜像ID12345\\n"}\n'
                yield '{"stream":"Successfully tagged 模拟镜像:latest\\n"}\n'

            def push(self, repository, tag=None, **kwargs):
                yield '{"status":"模拟推送：推送镜像 " + repository + ":" + (tag or "latest") + " (未真实推送)"}\n'
                yield '{"status":"模拟推送完成，耗时 0.01 秒"}\n'

        def __init__(self):
            self.images = self.MockImages()

    client = MockDockerClient()


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
            if project_type.startswith('.') or project_type.startswith('_'):
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
        for ptype in ['jar', 'nodejs']:
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
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            
            if not username or not password:
                self._send_json(400, {"error": "用户名和密码不能为空"})
                return
            
            result = authenticate(username, password)
            
            if result['success']:
                self._send_json(200, {
                    "success": True,
                    "token": result['token'],
                    "username": result['username'],
                    "expires_in": result['expires_in']
                })
            else:
                self._send_json(401, {"error": result['error']})
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
            pull_kwargs = {
                "repository": image_name,
                "tag": tag,
                "stream": True,
                "decode": True,
            }
            if auth_config:
                pull_kwargs["auth_config"] = auth_config
            pull_stream = client.api.pull(**pull_kwargs)
            for chunk in pull_stream:
                if "error" in chunk:
                    raise RuntimeError(chunk["error"])

            client.images.get(full_tag)  # 确认镜像存在

            os.makedirs(EXPORT_DIR, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            safe_base = get_safe_filename(image_name.replace("/", "_") or "image")
            tar_filename = f"{safe_base}-{tag}-{timestamp}.tar"
            tar_path = os.path.join(EXPORT_DIR, tar_filename)

            image_stream = client.api.get_image(full_tag)
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

            config = load_config()
            docker_config = config.get("docker", {})
            # 获取属性registry_prefix
            base_name = docker_config.get("registry_prefix", "")
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
            }

            if "docker" not in config:
                config["docker"] = {}
            config["docker"].update(new_docker_config)

            save_config(config)

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
            if not re.match(r'^[a-z0-9_-]+$', project_type):
                self._send_json(400, {"error": "项目类型只能包含小写字母、数字、下划线和连字符"})
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
            if target_project_type and not re.match(r'^[a-z0-9_-]+$', target_project_type):
                self._send_json(400, {"error": "项目类型只能包含小写字母、数字、下划线和连字符"})
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
                        {
                            "error": "内置模板的项目类型不可修改"
                        },
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
                        "filename": os.path.basename(dst_path)
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
        self.logs = defaultdict(deque)  # build_id -> deque[str]
        self.lock = threading.Lock()
        self.tasks = {}  # build_id -> Thread

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
    ):
        build_id = str(uuid.uuid4())
        thread = threading.Thread(
            target=self._build_task,
            args=(
                build_id,
                file_data,
                image_name,
                tag,
                should_push,
                selected_template,
                original_filename,
                project_type,
                template_params or {},
            ),
            daemon=True,
        )
        thread.start()
        with self.lock:
            self.tasks[build_id] = thread
        return build_id

    def _build_task(
        self,
        build_id: str,
        file_data: bytes,
        image_name: str,
        tag: str,
        should_push: bool,
        selected_template: str,
        original_filename: str,
        project_type: str = "jar",
        template_params: dict = None,
    ):
        full_tag = f"{image_name}:{tag}"
        build_context = os.path.join(BUILD_DIR, image_name.replace("/", "_"))

        def log(msg: str):
            with self.lock:
                self.logs[build_id].append(msg)

        def extract_archive(file_path: str, extract_to: str):
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
                return True
            except Exception as e:
                log(f"❌ 解压失败: {str(e)}\n")
                return False

        try:
            log(f"📦 开始处理上传: {original_filename}")
            log(f"🏷️ 镜像名: {full_tag}")
            log(f"🧱 模板: {selected_template}")
            log(f"📂 项目类型: {project_type}")

            # === 模拟模式 ===
            if not DOCKER_AVAILABLE:
                config = load_config()
                os.makedirs(build_context, exist_ok=True)

                # 保存文件
                if project_type == "jar" and original_filename.endswith(".jar"):
                    with open(os.path.join(build_context, "app.jar"), "wb") as f:
                        f.write(file_data)
                    log("🧪 模拟模式：已保存 JAR")
                else:
                    # 保存并解压
                    temp_file = os.path.join(build_context, original_filename)
                    with open(temp_file, "wb") as f:
                        f.write(file_data)
                    if not extract_archive(temp_file, build_context):
                        log("⚠️ 模拟模式：文件未解压（可能是 JAR 或不支持的格式）")
                    else:
                        os.remove(temp_file)

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
                    log("🚀 开始模拟推送...\n")
                    username = config.get("docker", {}).get("username", None)
                    log(f"🚀 账号: {username}\n")
                    for i in range(1, 4):
                        log(f"📡 Pushing layer {i}/3...\n")
                    log("✅ 模拟推送完成\n")
                else:
                    log("🚀 模拟推送跳过（未启用推送）\n")

                log("\n✅✅✅ 所有操作已完成（模拟）✅✅✅\n")
                return

            # === 真实构建 ===
            os.makedirs(build_context, exist_ok=True)

            # 根据项目类型处理文件
            if project_type == "jar" and original_filename.endswith(".jar"):
                # JAR 文件直接保存
                jar_path = os.path.join(build_context, "app.jar")
                with open(jar_path, "wb") as f:
                    f.write(file_data)
                log("✅ JAR 文件已保存\n")
            else:
                # 压缩包需要解压
                temp_file = os.path.join(build_context, original_filename)
                with open(temp_file, "wb") as f:
                    f.write(file_data)

                if not extract_archive(temp_file, build_context):
                    # 如果不是压缩包，可能是 JAR 文件
                    if original_filename.endswith(".jar"):
                        os.rename(temp_file, os.path.join(build_context, "app.jar"))
                        log("✅ JAR 文件已保存\n")
                    else:
                        log(f"❌ 不支持的文件格式: {original_filename}\n")
                        return
                else:
                    # 解压成功，删除临时文件
                    try:
                        os.remove(temp_file)
                    except:
                        pass

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
            
            # 如果没有传入 EXPOSE_PORT，使用配置中的默认值
            if "EXPOSE_PORT" not in template_vars:
                template_vars["EXPOSE_PORT"] = str(config.get("docker", {}).get("expose_port", 8080))
            
            # 替换所有变量
            from backend.template_parser import replace_template_variables
            try:
                dockerfile_content = replace_template_variables(dockerfile_content, template_vars)
            except ValueError as e:
                log(f"❌ 模板变量替换失败: {e}\n")
                return

            with open(
                os.path.join(build_context, "Dockerfile"), "w", encoding="utf-8"
            ) as f:
                f.write(dockerfile_content)

            log(f"\n🚀 开始构建镜像: {full_tag}\n")

            build_stream = client.api.build(
                path=build_context, tag=full_tag, rm=True, decode=True
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
                log(f"\n📤 开始推送镜像: {full_tag}\n")
                username = config.get("docker", {}).get("username", None)
                password = config.get("docker", {}).get("password", None)
                auth_config = {"username": username, "password": password}
                try:
                    push_stream = client.images.push(
                        full_tag, auth_config=auth_config, stream=True, decode=True
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
                            log(f"\n❌ 推送失败: {chunk['error']}\n")
                            return
                    log(f"\n✅ 推送完成: {full_tag}\n")
                except Exception as e:
                    log(f"\n❌ 推送异常: {e}\n")

            log("\n🎉🎉🎉 所有操作已完成！🎉🎉🎉\n")

        except Exception as e:
            clean_msg = re.sub(r"[\x00-\x1F\x7F]", " ", str(e)).strip()
            log(f"\n❌ 构建异常: {clean_msg}\n")
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

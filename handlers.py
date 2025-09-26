# handlers.py
import json
import os
import re
import shutil
import threading
import urllib
import uuid
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler
from urllib import parse

from config import load_config, save_config
from utils import generate_image_name

UPLOAD_DIR = "uploads"
BUILD_DIR = "docker_build"
TEMPLATES_DIR = "templates"
INDEX_FILE = "index.html"

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
except (ImportError, ModuleNotFoundError) as e:
    print(f"⚠️ 未安装 docker SDK 模块: {e}")
    print("🔧 启用模拟构建模式（仅输出日志，不真实构建）")
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
    DOCKER_AVAILABLE = False  # 明确标记为不可用

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

class Jar2DockerHandler(BaseHTTPRequestHandler):
    server_version = "Jar2Docker/1.0"

    def _send_json(self, code, data):
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))
        except Exception as e:
            print(f"❌ 发送 JSON 响应失败: {e}")

    def _send_html(self, content):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            if isinstance(content, str):
                content = content.encode('utf-8')
            self.wfile.write(content)
        except Exception as e:
            print(f"❌ 发送 HTML 响应失败: {e}")

    def _send_file(self, filepath, content_type='application/octet-stream'):
        try:
            if not os.path.exists(filepath):
                self.send_error(404, "File not found")
                return False

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(os.path.getsize(filepath)))
            self.end_headers()

            with open(filepath, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
            return True
        except Exception as e:
            print(f"❌ 发送文件 {filepath} 失败: {e}")
            return False

    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/get-config':
            self.handle_get_config()
        elif path == '/get-logs':
            # 在 do_GET 中：
            parsed_url = parse.urlparse(self.path)
            query_params = parse.parse_qs(parsed_url.query)  # 返回 dict，值是 list
            build_id = query_params.get('build_id', [None])[0]
            if build_id:
                self.handle_get_logs(build_id)
            else:
                self.send_error(400, "缺少 build_id 参数")
        elif path == '/list-templates':
            self.handle_list_templates()
        elif path == '/' or path == '/index.html':
            self.serve_index()
        elif path.startswith('/static/') or path.endswith(('.png', '.css', '.js')):
            filepath = path.lstrip('/')
            if os.path.exists(filepath):
                content_type = 'image/png' if filepath.endswith('.png') else 'text/css'
                self._send_file(filepath, content_type)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    # === 新增：获取日志 ===
    def handle_get_logs(self, build_id):
        try:
            manager = BuildManager()
            logs = manager.get_logs(build_id)  # 假设返回 list[str] 或 str
            log_text = ''.join(logs) if isinstance(logs, list) else str(logs)

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(log_text.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"获取日志失败: {e}")

    def serve_index(self):
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            self._send_html(content)
        else:
            self.send_error(404, "index.html not found")

    def handle_get_config(self):
        try:
            config = load_config()
            docker_config = config.get('docker', {})
            self._send_json(200, {"docker": docker_config})
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": f"获取配置失败: {str(e)}"})

    def handle_list_templates(self):
        try:
            if not os.path.exists(TEMPLATES_DIR):
                templates = []
            else:
                templates = [
                    f.replace('.Dockerfile', '')
                    for f in os.listdir(TEMPLATES_DIR)
                    if f.endswith('.Dockerfile')
                ]
                templates = sorted(templates, key=natural_sort_key)
            self._send_json(200, {"templates": templates})
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": "获取模板列表失败"})

    def do_POST(self):
        if self.path == '/upload':
            self.handle_upload()
        elif self.path == '/save-config':
            self.handle_save_config()
        elif self.path == '/suggest-image-name':
            self.handle_suggest_image_name()
        else:
            self.send_error(404)

    def handle_suggest_image_name(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)

            boundary = self.headers['Content-Type'].split("boundary=")[1].encode()
            parts = body.split(b'--' + boundary)

            jar_filename = None
            for part in parts[1:-1]:
                if b'\r\n\r\n' in part and b'name="jar_file"' in part and b'filename="' in part:
                    headers = part[:part.find(b'\r\n\r\n')].decode('utf-8', errors='ignore')
                    match = re.search(r'filename="(.+?)"', headers)
                    if match:
                        jar_filename = match.group(1)
                        break

            if not jar_filename:
                self._send_json(400, {"error": "未找到 JAR 文件"})
                return

            config = load_config()
            docker_config = config.get('docker', {})
            # 获取属性registry_prefix
            base_name = docker_config.get('registry_prefix', '')
            suggested_name = generate_image_name(base_name,jar_filename)
            self._send_json(200, {"suggested_imagename": suggested_name})

        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": f"生成镜像名失败: {str(e)}"})

    def handle_save_config(self):
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)

            boundary = self.headers['Content-Type'].split("boundary=")[1].encode()
            parts = body.split(b'--' + boundary)
            form_data = {}

            for part in parts[1:-1]:
                if b'\r\n\r\n' in part:
                    header_end = part.find(b'\r\n\r\n')
                    headers = part[:header_end].decode('utf-8', errors='ignore')
                    data = part[header_end + 4:].rstrip(b'\r\n')

                    if 'name="' in headers:
                        try:
                            field_name = headers.split('name="')[1].split('"')[0]
                            form_data[field_name] = data.decode('utf-8', errors='ignore')
                        except:
                            continue

            config = load_config()
            new_docker_config = {
                "registry": form_data.get("registry", "docker.io").strip(),
                "registry_prefix": form_data.get("registry_prefix", "").strip().rstrip('/'),
                "default_push": (form_data.get("default_push") == "on"),
                "expose_port": int(form_data.get("expose_port", "8080")) if form_data.get("expose_port", "").isdigit() else 8080
            }

            if 'docker' not in config:
                config['docker'] = {}
            config['docker'].update(new_docker_config)

            save_config(config)

            print(f"✅ 配置已更新: {config['docker']}")
            self._send_json(200, {
                "message": "Docker 配置保存成功！",
                "docker_config": config['docker']
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            clean_error_msg = re.sub(r'[\x00-\x1F\x7F]', ' ', error_msg).strip()
            self._send_json(500, {"error": f"保存配置失败: {clean_error_msg}"})

    def handle_upload(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        try:
            boundary = self.headers['Content-Type'].split("boundary=")[1].encode()
            parts = body.split(b'--' + boundary)
            form_data = {}
            jar_data = None

            for part in parts[1:-1]:
                if b'\r\n\r\n' not in part:
                    continue
                header_end = part.find(b'\r\n\r\n')
                headers = part[:header_end].decode('utf-8', errors='ignore')
                data = part[header_end + 4:].rstrip(b'\r\n')

                if 'filename=' in headers:
                    try:
                        filename = headers.split('filename=')[1].split('"')[1]
                        if filename.endswith('.jar'):
                            jar_data = data
                            form_data['original_filename'] = filename
                    except Exception as e:
                        print(f"⚠️ 解析文件名失败: {e}")
                        continue
                else:
                    try:
                        field_name = headers.split('name="')[1].split('"')[0]
                        form_data[field_name] = data.decode('utf-8', errors='ignore')
                    except Exception as e:
                        print(f"⚠️ 解析字段失败: {e}")
                        continue

            if not jar_data:
                self._send_json(400, {"error": "未上传 JAR 文件"})
                return

            jar_basename = form_data.get('original_filename', 'app.jar').replace('.jar', '')
            image_name = form_data.get('imagename') or f"myapp/{jar_basename}"
            tag = form_data.get('tag') or 'latest'
            should_push = form_data.get('push') == 'on'
            selected_template = form_data.get('template') or 'simple'

            # 👇 启动后台构建，立即返回 build_id
            build_manager = BuildManager()
            build_id = build_manager.start_build(
                jar_data=jar_data,
                image_name=image_name,
                tag=tag,
                should_push=should_push,
                selected_template=selected_template,
                original_filename=form_data.get('original_filename', 'app.jar')
            )

            self._send_json(200, {
                "build_id": build_id,
                "message": "构建任务已启动，请通过 WebSocket 订阅日志"
            })

        except Exception as e:
            clean_msg = re.sub(r'[\x00-\x1F\x7F]', ' ', str(e)).strip()
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

        def start_build(self, jar_data: bytes, image_name: str, tag: str, should_push: bool, selected_template: str,
                        original_filename: str):
            build_id = str(uuid.uuid4())
            thread = threading.Thread(
                target=self._build_task,
                args=(build_id, jar_data, image_name, tag, should_push, selected_template, original_filename),
                daemon=True
            )
            thread.start()
            with self.lock:
                self.tasks[build_id] = thread
            return build_id

        def _build_task(self, build_id: str, jar_data: bytes, image_name: str, tag: str, should_push: bool,
                        selected_template: str, original_filename: str):
            full_tag = f"{image_name}:{tag}"
            jar_basename = original_filename.replace('.jar', '') if original_filename else 'app'
            build_context = os.path.join(BUILD_DIR, image_name.replace('/', '_'))

            def log(msg: str):
                with self.lock:
                    self.logs[build_id].append(msg)

            try:
                log(f"📦 开始处理上传: {original_filename}")
                log(f"🏷️ 镜像名: {full_tag}")
                log(f"🧱 模板: {selected_template}")

                # === 模拟模式 ===
                if not DOCKER_AVAILABLE:
                    os.makedirs(build_context, exist_ok=True)
                    with open(os.path.join(build_context, 'app.jar'), 'wb') as f:
                        f.write(jar_data)
                    log("🧪 模拟模式：已保存 JAR")

                    for line in [
                        "🧪 模拟模式：Docker 服务不可用\n",
                        "Step 1/4 : FROM openjdk:17-jre-slim (模拟)\n",
                        "Step 2/4 : COPY app.jar /app.jar (模拟)\n",
                        "Step 3/4 : WORKDIR /app (模拟)\n",
                        "Step 4/4 : ENTRYPOINT [\"java\", \"-jar\", \"app.jar\"] (模拟)\n",
                        f"✅ 模拟构建成功: {full_tag}\n",
                    ]:
                        log(line)

                    if should_push:
                        log("🚀 开始模拟推送...\n")
                        for i in range(1, 4):
                            log(f"📡 Pushing layer {i}/3...\n")
                        log("✅ 模拟推送完成\n")
                    else:
                        log("🚀 模拟推送跳过（未启用推送）\n")

                    log("\n✅✅✅ 所有操作已完成（模拟）✅✅✅\n")
                    return

                # === 真实构建 ===
                os.makedirs(build_context, exist_ok=True)
                jar_path = os.path.join(build_context, 'app.jar')
                with open(jar_path, 'wb') as f:
                    f.write(jar_data)

                template_file = os.path.join(TEMPLATES_DIR, f"{selected_template}.Dockerfile")
                if not os.path.exists(template_file):
                    log(f"❌ 模板文件不存在: {template_file}\n")
                    return

                with open(template_file, 'r', encoding='utf-8') as f:
                    dockerfile_content = f.read()

                config = load_config()
                expose_port = config.get('docker', {}).get('expose_port', 8080)
                dockerfile_content = dockerfile_content.replace('{{EXPOSE_PORT}}', str(expose_port))

                with open(os.path.join(build_context, 'Dockerfile'), 'w', encoding='utf-8') as f:
                    f.write(dockerfile_content)

                log(f"\n🚀 开始构建镜像: {full_tag}\n")

                build_stream = client.api.build(path=build_context, tag=full_tag, rm=True, decode=True)
                build_succeeded = False
                last_error = None

                for chunk in build_stream:
                    if 'stream' in chunk:
                        log(f"🏗️  {chunk['stream']}")
                    elif 'error' in chunk:
                        last_error = chunk['error']
                        log(f"\n🔥 [DOCKER ERROR]: {last_error}\n")
                    elif 'errorDetail' in chunk:
                        err_msg = chunk['errorDetail'].get('message', 'Unknown')
                        last_error = err_msg
                        log(f"\n💥 [ERROR DETAIL]: {err_msg}\n")
                    elif 'aux' in chunk and 'ID' in chunk['aux']:
                        build_succeeded = True

                if not build_succeeded:
                    log(f"\n❌ 构建失败！最后错误: {last_error or '未知错误'}\n")
                    return

                log(f"\n✅ 镜像构建成功: {full_tag}\n")

                if should_push:
                    log(f"\n📤 开始推送镜像: {full_tag}\n")
                    try:
                        push_stream = client.images.push(full_tag, stream=True, decode=True)
                        for chunk in push_stream:
                            status = chunk.get('status') or chunk.get('progress') or chunk.get('id')
                            if status:
                                log(f"📡 {status}\n")
                            if 'error' in chunk:
                                log(f"\n❌ 推送失败: {chunk['error']}\n")
                                return
                        log(f"\n✅ 推送完成: {full_tag}\n")
                    except Exception as e:
                        log(f"\n❌ 推送异常: {e}\n")

                log("\n🎉🎉🎉 所有操作已完成！🎉🎉🎉\n")

            except Exception as e:
                clean_msg = re.sub(r'[\x00-\x1F\x7F]', ' ', str(e)).strip()
                log(f"\n❌ 构建异常: {clean_msg}\n")
                import traceback
                traceback.print_exc()
            finally:
                if os.getenv('KEEP_BUILD_CONTEXT', '0') != '1':
                    try:
                        shutil.rmtree(build_context, ignore_errors=True)
                    except Exception as e:
                        print(f"⚠️ 清理失败: {e}")

        def get_logs(self, build_id: str):
            with self.lock:
                return list(self.logs[build_id])
# jar2docker.py

import http.server
import socketserver
import os
import json
import yaml
import base64


# --- 模拟 Docker 模块 ---
try:
    import docker

    DOCKER_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    print(f"⚠️ 未安装 docker 模块: {e}")
    print("🔧 启用模拟模式（仅用于调试）")
    DOCKER_AVAILABLE = False

try:
    client = docker.from_env() if DOCKER_AVAILABLE else None
except Exception as e:
    print(f"⚠️ Docker 服务未运行: {e}")
    print("🔧 启用模拟模式")
    DOCKER_AVAILABLE = False
    client = None

# --- 其他配置 ---
UPLOAD_DIR = "uploads"
DOCKER_BUILD_DIR = "docker_build"
CONFIG_FILE = "config.yml"
STATIC_FILE = "index.html"

for d in [UPLOAD_DIR, DOCKER_BUILD_DIR]:
    os.makedirs(d, exist_ok=True)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        # 如果没有配置文件，创建一个默认的
        default_config = {
            "docker": {
                "registry": "localhost:5000",
                "default_push": False,
                "expose_port": 8080
            },
            "server": {
                "default_image_format": "myapp/{jar_basename}"
            }
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True)
        print(f"📄 已创建默认配置文件: {CONFIG_FILE}")
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


CONFIG = load_config()

import base64

def require_auth(handler):
    """装饰器：检查 Basic Auth"""
    config = CONFIG['server']
    username = config['username']
    password = config['password']
    expected_auth = base64.b64encode(f"{username}:{password}".encode()).decode()

    auth_header = handler.headers.get('Authorization')
    if not auth_header:
        return False

    if not auth_header.startswith('Basic '):
        return False

    encoded = auth_header.split(' ')[1]
    return encoded == expected_auth

def auth_required(func):
    """装饰器：用于 do_GET/do_POST"""
    def wrapper(self, *args, **kwargs):
        if not require_auth(self):
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="jar2docker"')
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>401 Unauthorized</h1><p>Authentication required.</p>')
            return
        return func(self, *args, **kwargs)
    return wrapper

# --- HTTP 处理器 ---
class UploadHandler(http.server.BaseHTTPRequestHandler):

    @auth_required
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self._serve_file(STATIC_FILE, 'text/html')
        elif self.path == '/list_templates':
            self._list_templates()
        elif self.path.startswith('/get_default_image'):
            self._get_default_image()
        else:
            self.send_error(404)

    @auth_required
    def _serve_file(self, path, ctype):
        if os.path.exists(path):
            self.send_response(200)
            self.send_header('Content-type', ctype)
            self.end_headers()
            with open(path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

    @auth_required
    def _get_default_image(self):
        """根据上传的 jar 文件名，生成推荐的镜像名"""
        from urllib.parse import parse_qs, urlparse
        query = urlparse(self.path).query
        jarname = parse_qs(query).get('jarname', ['app'])[0]

        # 清理文件名
        if '.' in jarname:
            basename = jarname.rsplit('.', 1)[0]  # 去掉扩展名
        else:
            basename = jarname

        # 简单清洗：转小写，替换非法字符
        import re
        clean_name = re.sub(r'[^a-z0-9\-_.]+', '-', basename.lower())
        clean_name = clean_name.strip('.-_')

        # 构造默认镜像名（可从配置读取前缀）
        registry_prefix = CONFIG['docker'].get('registry_prefix', 'myapp')
        default_image = f"{registry_prefix}/{clean_name}"

        self._send_json(200, {
            "default_image": default_image,
            "default_tag": "latest"
        })

    @auth_required
    def _list_templates(self):
        """列出 templates 目录下的所有模板文件（基于文件名）"""
        template_dir = CONFIG['templates']['directory']
        templates = {}

        if not os.path.exists(template_dir):
            os.makedirs(template_dir, exist_ok=True)
            # 可选：创建一个默认模板
            default_template = """FROM openjdk:11-jre
    COPY app.jar app.jar
    CMD ["java", "-jar", "app.jar"]
    """
            with open(os.path.join(template_dir, "dragonwell8.Dockerfile"), "w", encoding="utf-8") as f:
                f.write(default_template)
            print(f"✅ 已创建默认模板: {template_dir}/dragonwell8.Dockerfile")

        try:
            for filename in os.listdir(template_dir):
                if filename.startswith(".") or not filename.endswith(".Dockerfile"):
                    continue  # 跳过隐藏文件和非 Dockerfile

                template_id = os.path.splitext(filename)[0]  # 去掉 .Dockerfile
                filepath = os.path.join(template_dir, filename)

                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                templates[template_id] = {
                    "name": template_id.capitalize(),  # 可在前端自定义
                    "description": f"使用模板: {filename}",
                    "content": content.strip()
                }

            # 返回第一个作为默认（可自定义逻辑）
            default_template_id = next(iter(templates)) if templates else None

            self._send_json(200, {
                "templates": templates,
                "default": default_template_id,
                "count": len(templates)
            })

        except Exception as e:
            print(f"❌ 读取模板失败: {e}")
            self._send_json(500, {"error": f"读取模板目录失败: {str(e)}"})

    def do_POST(self):
        if self.path != '/upload':
            return self.send_error(404)

        # 简化表单解析（实际中可用 cgi 或 multipart）
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        # 这里省略复杂解析，仅做演示

        # 模拟接收数据
        import tempfile
        import shutil
        from io import BytesIO

        # 模拟提取 jarfile 和字段
        try:
            boundary = self.headers['Content-Type'].split("boundary=")[1].encode()
            parts = body.split(b'--' + boundary)
            form_data = {}
            jar_data = None

            for part in parts[1:-1]:
                if b'\r\n\r\n' in part:
                    header_end = part.find(b'\r\n\r\n')
                    headers = part[:header_end].decode()
                    data = part[header_end + 4:].rstrip(b'\r\n')

                    if 'filename=' in headers:
                        filename = headers.split('filename=')[1].split('"')[1]
                        if filename.endswith('.jar'):
                            jar_data = data
                            form_data['original_filename'] = filename
                    else:
                        field_name = headers.split('name="')[1].split('"')[0]
                        form_data[field_name] = data.decode()

            if not jar_data:
                return self._send_json(400, {"error": "未上传 JAR 文件"})

            jar_basename = form_data.get('original_filename', 'app.jar').replace('.jar', '')
            image_name = form_data.get('imagename') or f"myapp/{jar_basename}"
            tag = form_data.get('tag') or 'latest'
            full_tag = f"{image_name}:{tag}"
            should_push = form_data.get('push') == 'on'

            # 模拟构建过程
            build_context = os.path.join(DOCKER_BUILD_DIR, image_name.replace('/', '_'))
            os.makedirs(build_context, exist_ok=True)

            with open(os.path.join(build_context, 'app.jar'), 'wb') as f:
                f.write(jar_data)

            # ✅ 核心：如果没有 Docker，就模拟成功
            if not DOCKER_AVAILABLE:
                print(f"🧪 模拟模式：已保存 JAR 到 {build_context}")
                return self._send_json(200, {
                    "message": "✅ 模拟成功：JAR 已接收（Docker 不可用）",
                    "image_name": full_tag,
                    "pushed": False,
                    "build_log": "Mock build: Success\nStep 1: COPY app.jar\nStep 2: CMD java -jar"
                })

            # --- 真实 Docker 构建（仅当可用时）---
            # （保留你原来的 docker 构建逻辑）
            # ...

            self._send_json(200, {
                "message": "构建成功！",
                "image_name": full_tag,
                "pushed": should_push,
                "pushed_to": full_tag if should_push else ""
            })

        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


if __name__ == "__main__":

    # server.port指定端口
    PORT = int(os.environ.get('server.port', 8000))
    print(f"🌐 调试模式启动: http://localhost:{PORT}/")
    print(f"📁 上传目录: {os.path.abspath(UPLOAD_DIR)}")
    print(f"🛠️  DOCKER_AVAILABLE = {DOCKER_AVAILABLE}")

    with socketserver.TCPServer(("", PORT), UploadHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 已停止")
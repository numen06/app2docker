# jar2docker.py

import http.server
import json
import os
import socketserver
import re
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
    """加载 config.yml，不存在则返回带默认 docker 配置的空结构"""
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "docker": {
                "registry": "docker.io",
                "registry_prefix": "",
                "default_push": False,
                "expose_port": 8080
            }
        }
        # 创建默认配置文件（只包含 docker，不影响未来扩展）
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"🆕 配置文件 {CONFIG_FILE} 不存在，已创建默认配置")
        return default_config

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}

    # 确保 docker 配置存在
    if 'docker' not in config:
        config['docker'] = {
            "registry": "docker.io",
            "registry_prefix": "",
            "default_push": False,
            "expose_port": 8080
        }
        # 保存回去（可选，确保下次不用再补）
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return config

CONFIG = load_config()



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
    def handle_save_config(self):
        """保存全局配置到 config.yml，只更新 docker 部分，保留其他配置"""
        try:
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)

            # 解析表单（和上传逻辑一致）
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

            # 构造新的 docker 配置
            new_docker_config = {
                "registry": form_data.get("registry", "docker.io").strip(),
                "registry_prefix": form_data.get("registry_prefix", "").strip().rstrip('/'),
                "default_push": (form_data.get("default_push") == "on"),
                "expose_port": int(form_data.get("expose_port", "8080")) if form_data.get("expose_port",
                                                                                          "").isdigit() else 8080
            }

            # 🆕 读取现有完整配置（如果存在）
            full_config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f) or {}
                print(f"📄 读取现有配置: {full_config}")

            # 🆕 只更新 docker 部分，保留其他部分
            if 'docker' not in full_config:
                full_config['docker'] = {}
            full_config['docker'].update(new_docker_config)

            # 🆕 写回完整配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(full_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

            print(f"✅ 配置已更新到 {CONFIG_FILE}: {full_config}")

            self._send_json(200, {
                "message": "Docker 配置保存成功！",
                "docker_config": full_config.get('docker')
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            clean_error_msg = re.sub(r'[\x00-\x1F\x7F]', ' ', error_msg).strip()
            self._send_json(500, {"error": f"保存配置失败: {clean_error_msg}"})

    def handle_get_config(self):
        """返回当前 config.yml 中的配置"""
        try:
            config = load_config()  # 复用你已有的 load_config 方法
            docker_config = config.get('docker', {})

            self._send_json(200, {
                "docker": docker_config
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            clean_error_msg = re.sub(r'[\x00-\x1F\x7F]', ' ', error_msg).strip()
            self._send_json(500, {"error": f"获取配置失败: {clean_error_msg}"})

    @auth_required
    def do_GET(self):

        if self.path == '/' or self.path == '/index.html':
            self._serve_file(STATIC_FILE, 'text/html')
        elif self.path == '/list_templates':
            self._list_templates()
        elif self.path.startswith('/get_default_image'):
            self._get_default_image()
        if self.path == '/get-config':
            return self.handle_get_config()
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

    def handle_upload(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        try:
            boundary = self.headers['Content-Type'].split("boundary=")[1].encode()
            parts = body.split(b'--' + boundary)
            form_data = {}
            jar_data = None

            for part in parts[1:-1]:  # 跳过首尾空部分
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
                        print(f"⚠️ 解析字段 {headers} 失败: {e}")
                        continue

            if not jar_data:
                self._send_json(400, {"error": "未上传 JAR 文件"})
                return  # 👈 必须 return

            # 获取表单字段
            jar_basename = form_data.get('original_filename', 'app.jar').replace('.jar', '')
            image_name = form_data.get('imagename') or f"myapp/{jar_basename}"
            tag = form_data.get('tag') or 'latest'
            full_tag = f"{image_name}:{tag}"
            should_push = form_data.get('push') == 'on'
            selected_template = form_data.get('template') or 'simple'  # 👈 你漏了这行！

            print(f"📦 接收到上传: {form_data.get('original_filename')}")
            print(f"🏷️  镜像名: {full_tag}")
            print(f"🧱 模板: {selected_template}")

            # 模拟模式（Docker 不可用）
            if not DOCKER_AVAILABLE:
                build_context = os.path.join(DOCKER_BUILD_DIR, image_name.replace('/', '_'))
                os.makedirs(build_context, exist_ok=True)
                with open(os.path.join(build_context, 'app.jar'), 'wb') as f:
                    f.write(jar_data)
                print(f"🧪 模拟模式：已保存 JAR 到 {build_context}")
                self._send_json(200, {
                    "message": "✅ 模拟成功：JAR 已接收（Docker 不可用）",
                    "image_name": full_tag,
                    "pushed": False,
                    "build_log": "Mock build: Success\nStep 1: COPY app.jar\nStep 2: CMD java -jar"
                })
                return  # 👈 必须 return

            # === 真实 Docker 构建 ===
            elif DOCKER_AVAILABLE and client:
                try:
                    # --- 1. 准备构建上下文 ---
                    build_context = os.path.join(DOCKER_BUILD_DIR, image_name.replace('/', '_'))
                    print(f"📁 创建构建目录: {build_context}")
                    os.makedirs(build_context, exist_ok=True)

                    # --- 2. 保存 JAR 文件 ---
                    jar_path = os.path.join(build_context, 'app.jar')
                    print(f"📄 保存 JAR 文件: {jar_path} ({len(jar_data)} 字节)")
                    with open(jar_path, 'wb') as f:
                        f.write(jar_data)

                    # --- 3. 读取 Dockerfile 模板 ---
                    template_dir = CONFIG['templates']['directory']
                    template_file = os.path.join(template_dir, f"{selected_template}.Dockerfile")
                    print(f"📜 读取模板: {template_file}")

                    if not os.path.exists(template_file):
                        raise FileNotFoundError(f"模板文件不存在: {template_file}")

                    with open(template_file, 'r', encoding='utf-8') as f:
                        dockerfile_content = f.read()

                    # --- 4. 写入 Dockerfile ---
                    dockerfile_path = os.path.join(build_context, 'Dockerfile')
                    with open(dockerfile_path, 'w', encoding='utf-8') as f:
                        f.write(dockerfile_content)
                    print(f"✅ Dockerfile 已写入，内容预览:\n{dockerfile_content[:150]}...")

                    # --- 5. 构建镜像 ---
                    print(f"\n" + "=" * 60)
                    print(f"🚀 开始构建镜像: {full_tag}")
                    print("=" * 60)

                    build_log = []
                    build_stream = client.api.build(
                        path=build_context,
                        tag=full_tag,
                        rm=True,
                        decode=True,
                    )

                    build_succeeded = False
                    last_error = None

                    for chunk in build_stream:
                        if 'stream' in chunk:
                            line = chunk['stream']
                            build_log.append(line)
                            print("🏗️  ", line.rstrip())

                        if 'error' in chunk:
                            error_detail = chunk['error']
                            last_error = error_detail
                            print(f"\n🔥 [DOCKER ERROR]: {error_detail}\n")

                        if 'errorDetail' in chunk:
                            error_detail = chunk.get('errorDetail', {}).get('message', 'Unknown error')
                            last_error = error_detail
                            print(f"\n💥 [ERROR DETAIL]: {error_detail}\n")

                        if 'aux' in chunk and 'ID' in chunk['aux']:
                            build_succeeded = True

                    if not build_succeeded:
                        full_log = "".join(build_log)
                        print(f"\n" + "❌" * 50)
                        print("❌ DOCKER 构建失败！完整日志如下：")
                        print(full_log)
                        print("❌" * 50)
                        raise Exception(f"Docker 构建失败！最后错误: {last_error or '未知错误'}")

                    print(f"\n✅ 镜像构建成功: {full_tag}\n")

                    # --- 6. 推送（可选）---
                    push_log = []
                    if should_push:
                        print(f"📤 开始推送镜像: {full_tag}")
                        push_stream = client.images.push(full_tag, stream=True, decode=True)
                        for chunk in push_stream:
                            if 'status' in chunk:
                                line = chunk['status']
                                push_log.append(line)
                                print("📡 ", line)
                            if 'error' in chunk:
                                raise Exception(f"推送失败: {chunk['error']}")

                    # --- 7. 返回成功 ---
                    self._send_json(200, {
                        "message": "构建成功！",
                        "image_name": full_tag,
                        "pushed": should_push,
                        "pushed_to": full_tag if should_push else "",
                        "build_log": "".join(build_log),
                        "push_log": "\n".join(push_log) if should_push else ""
                    })
                    return  # 👈 必须 return

                except Exception as e:
                    error_msg = str(e)
                    clean_error_msg = re.sub(r'[\x00-\x1F\x7F]', ' ', error_msg).strip()
                    print(f"❌ 构建或推送失败: {clean_error_msg}")
                    # 打印完整堆栈
                    import traceback
                    traceback.print_exc()
                    self._send_json(500, {"error": f"构建失败: {clean_error_msg}"})
                    return  # 👈 必须 return

            # 正常情况不应该走到这里
            self._send_json(500, {"error": "未知错误：未进入任何构建分支"})
            return

        except Exception as e:
            error_msg = str(e)
            clean_error_msg = re.sub(r'[\x00-\x1F\x7F]', ' ', error_msg).strip()
            print(f"❌ 请求处理失败: {clean_error_msg}")
            import traceback
            traceback.print_exc()
            self._send_json(500, {"error": f"服务器内部错误: {clean_error_msg}"})
            return  # 👈 必须 return

    def do_POST(self):
        if self.path == '/upload':
            return self.handle_upload()
        elif self.path == '/save-config':
            return self.handle_save_config()
        else:
            self.send_error(404)


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
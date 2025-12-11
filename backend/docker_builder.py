# docker_builder.py
"""
Docker 构建器抽象类和实现类
支持本地和远程 Docker 构建
参考: https://github.com/docker/build-push-action
"""
import os
import subprocess
import json
import shutil
import threading
import queue
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Iterator, List, Union


class DockerBuilder(ABC):
    """Docker 构建器抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化构建器
        Args:
            config: Docker 配置字典
        """
        self.config = config
        self.client = None
        self.available = False
        self._initialize()

    @abstractmethod
    def _initialize(self):
        """初始化 Docker 客户端（由子类实现）"""
        pass

    @abstractmethod
    def ping(self) -> bool:
        """测试 Docker 连接"""
        pass

    @abstractmethod
    def build_image(self, path: str, tag: str, **kwargs) -> Iterator[Dict]:
        """
        构建 Docker 镜像
        Args:
            path: 构建上下文路径
            tag: 镜像标签
            **kwargs: 其他构建参数
        Returns:
            构建日志流
        """
        pass

    @abstractmethod
    def push_image(
        self, repository: str, tag: str = "latest", auth_config: Optional[Dict] = None
    ) -> Iterator[Dict]:
        """
        推送镜像到仓库
        Args:
            repository: 仓库名称
            tag: 镜像标签
            auth_config: 认证配置
        Returns:
            推送日志流
        """
        pass

    @abstractmethod
    def get_image(self, name: str):
        """获取镜像对象"""
        pass

    @abstractmethod
    def pull_image(
        self, repository: str, tag: str = "latest", auth_config: Optional[Dict] = None
    ) -> Iterator[Dict]:
        """
        拉取镜像
        Args:
            repository: 仓库名称
            tag: 镜像标签
            auth_config: 认证配置
        Returns:
            拉取日志流
        """
        pass

    @abstractmethod
    def export_image(self, name: str) -> Iterator[bytes]:
        """
        导出镜像为 tar 文件
        Args:
            name: 镜像名称
        Returns:
            镜像数据流
        """
        pass

    def is_available(self) -> bool:
        """检查 Docker 是否可用"""
        return self.available

    def get_connection_info(self) -> str:
        """获取连接信息（用于日志显示）"""
        return "Unknown"

    def _ensure_buildx_builder(self, docker_path: str) -> str:
        """
        确保 buildx builder 存在并可用
        参考: https://github.com/docker/build-push-action
        Returns:
            builder 名称
        """
        # 检查默认 builder 是否存在
        try:
            result = subprocess.run(
                [docker_path, "buildx", "ls"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                # 查找默认的 builder（标记为 * 的）
                for line in result.stdout.splitlines():
                    # 跳过标题行
                    if "NAME" in line or "BUILDER" in line or not line.strip():
                        continue

                    # 查找包含 * 的行（默认 builder）
                    if "*" in line:
                        # 分割行，第一个字段是 builder 名称
                        parts = line.split()
                        if parts:
                            builder_name = parts[0].strip()
                            # 确保 builder 名称不包含 * 符号
                            if "*" in builder_name:
                                # 如果名称中包含 *，尝试移除或使用默认值
                                builder_name = builder_name.replace("*", "").strip()
                                if not builder_name:
                                    continue

                            # 优先选择 docker-container driver 的 builder
                            if "docker-container" in line:
                                return builder_name
                            # 否则返回第一个找到的默认 builder
                            return builder_name
        except Exception as e:
            print(f"⚠️ 检查 buildx builder 失败: {e}")

        # 如果没有找到合适的 builder，尝试创建默认的
        try:
            # 尝试创建默认的 docker-container builder
            result = subprocess.run(
                [
                    docker_path,
                    "buildx",
                    "create",
                    "--name",
                    "default",
                    "--driver",
                    "docker-container",
                    "--use",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return "default"
        except Exception as e:
            print(f"⚠️ 创建 buildx builder 失败: {e}")

        # 如果创建失败，尝试使用默认的 builder（不指定 --builder）
        # 返回空字符串表示使用默认 builder
        return ""

    def _build_with_buildx(
        self,
        path: str,
        tag: str,
        dockerfile: Optional[str] = None,
        target: Optional[str] = None,
        platform: Optional[str] = None,
        platforms: Optional[list] = None,
        build_args: Optional[Dict[str, str]] = None,
        cache_from: Optional[list] = None,
        cache_to: Optional[str] = None,
        load: bool = False,
        push: bool = False,
        outputs: Optional[list] = None,
        **kwargs,
    ) -> Iterator[Dict]:
        """
        使用 docker buildx build 命令构建镜像
        参考: https://github.com/docker/build-push-action

        Args:
            path: 构建上下文路径
            tag: 镜像标签（可以是列表，支持多标签）
            dockerfile: Dockerfile 路径（相对于构建上下文）
            target: 多阶段构建的目标阶段
            platform: 目标平台（如 linux/amd64, linux/arm64），已废弃，使用 platforms
            platforms: 目标平台列表（支持多平台构建）
            build_args: 构建参数
            cache_from: 缓存源列表（如 ["type=local,src=path/to/cache"]）
            cache_to: 缓存目标（如 "type=local,dest=path/to/cache"）
            load: 是否加载到本地 Docker（多平台构建时不能使用）
            push: 是否推送到仓库
            outputs: 输出选项列表（如 ["type=docker,dest=image.tar"]）
            **kwargs: 其他参数（用于兼容性）
        Returns:
            构建日志流（格式与 Docker API 兼容）
        """
        # 查找 docker 命令路径
        # 参考: https://github.com/docker/build-push-action
        docker_path = shutil.which("docker")

        # 如果找不到，尝试常见路径
        if not docker_path:
            common_paths = [
                "/usr/bin/docker",
                "/usr/local/bin/docker",
                "/bin/docker",
            ]
            for path in common_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    docker_path = path
                    break

        if not docker_path:
            # 检查 PATH 环境变量
            path_env = os.environ.get("PATH", "")
            error_msg = f"未找到 docker 命令\n"
            error_msg += f"PATH 环境变量: {path_env}\n"
            error_msg += f"请确保 docker 已安装并在 PATH 中"
            raise RuntimeError(error_msg)

        # 检查 buildx 是否可用
        try:
            result = subprocess.run(
                [docker_path, "buildx", "version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise RuntimeError("docker buildx 不可用")
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            raise RuntimeError(f"docker buildx 不可用: {e}")

        # 确保 builder 存在
        builder_name = self._ensure_buildx_builder(docker_path)

        # 构建 buildx 命令
        cmd = [docker_path, "buildx", "build"]

        # 使用指定的 builder（如果提供了名称）
        if builder_name and builder_name.strip():
            cmd.extend(["--builder", builder_name])

        # 处理标签（支持多标签）
        tags = tag if isinstance(tag, list) else [tag]
        for t in tags:
            cmd.extend(["--tag", t])

        # 构建上下文路径应该是绝对路径
        build_context = os.path.abspath(path)

        # 添加 Dockerfile 路径
        # 注意：由于 handlers.py 中已经将自定义文件名的 Dockerfile 统一复制为 "Dockerfile"
        # 所以这里传入的 dockerfile 参数应该总是 "Dockerfile" 或相对路径
        if dockerfile:
            # dockerfile 路径应该是相对于构建上下文的
            if os.path.isabs(dockerfile):
                dockerfile_rel = os.path.relpath(dockerfile, build_context)
            else:
                dockerfile_rel = dockerfile

            # 验证 Dockerfile 文件是否存在
            dockerfile_full_path = os.path.join(build_context, dockerfile_rel)
            if not os.path.exists(dockerfile_full_path):
                raise RuntimeError(
                    f"Dockerfile 不存在: {dockerfile_rel} (完整路径: {dockerfile_full_path})"
                )
            # 如果文件名不是默认的 "Dockerfile"，使用 --file 参数指定
            # 如果文件名是 "Dockerfile"，也可以明确指定，避免 buildx 静默失败
            if dockerfile_rel != "Dockerfile":
                cmd.extend(["--file", dockerfile_rel])
            else:
                # 即使是默认文件名，也明确指定，确保 buildx 使用正确的文件
                cmd.extend(["--file", dockerfile_rel])

        # 添加目标阶段（多阶段构建）
        if target:
            cmd.extend(["--target", target])

        # 添加平台（支持多平台构建）
        if platforms:
            # 多平台构建
            for p in platforms:
                cmd.extend(["--platform", p])
        elif platform:
            # 单平台构建（向后兼容）
            cmd.extend(["--platform", platform])

        # 添加构建参数
        if build_args:
            for key, value in build_args.items():
                if value is not None:
                    cmd.extend(["--build-arg", f"{key}={value}"])

        # 添加缓存选项
        if cache_from:
            for cache in cache_from:
                cmd.extend(["--cache-from", cache])

        if cache_to:
            cmd.extend(["--cache-to", cache_to])

        # 添加输出选项
        if outputs:
            for output in outputs:
                cmd.extend(["--output", output])
        elif push:
            # 如果指定了 push，使用 registry 输出
            cmd.append("--push")
        elif load:
            # 如果指定了 load，且没有多平台构建，则加载到本地
            # 注意：多平台构建不能使用 --load，必须使用 --push 或 --output
            if platforms and len(platforms) > 1:
                raise RuntimeError(
                    "多平台构建不能使用 --load，请使用 --push 或 --output"
                )
            if platform:
                # 单平台构建可以使用 --load
                cmd.append("--load")
            else:
                # 没有指定平台，默认加载到本地
                cmd.append("--load")

        # 添加其他常用参数
        if kwargs.get("pull", False):
            cmd.append("--pull")

        if kwargs.get("no_cache", False):
            cmd.append("--no-cache")

        # 添加进度输出格式（plain 格式，与 Docker API 兼容）
        # 使用 plain 格式以便更好地解析输出
        cmd.extend(["--progress", "plain"])

        # 添加构建上下文路径（使用绝对路径）
        cmd.append(build_context)

        # 打印完整的构建命令，方便排查问题
        cmd_str = " ".join(
            (
                f'"{arg}"'
                if " " in str(arg)
                or any(c in str(arg) for c in ["&", "|", ";", "<", ">", "(", ")"])
                else str(arg)
            )
            for arg in cmd
        )
        print(f"🔧 执行 Docker 构建命令:")
        print(f"   {cmd_str}")
        print(f"   工作目录: {build_context}")
        print(f"   构建上下文: {build_context}")

        # 启动构建进程
        try:
            # 准备环境变量（继承当前环境，包括 DOCKER_HOST）
            # 参考: https://github.com/docker/build-push-action
            # buildx 会读取 DOCKER_HOST 环境变量来连接远程 Docker
            env = os.environ.copy()

            # 使用 PIPE 分别捕获 stdout 和 stderr，以便更好地处理错误
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=build_context,
                env=env,  # 传递环境变量，确保 DOCKER_HOST 被使用
            )

            # 使用线程同时读取 stdout 和 stderr
            output_queue = queue.Queue()
            error_lines = []

            def read_stdout():
                try:
                    for line in process.stdout:
                        if line:
                            output_queue.put(("stdout", line))
                except Exception:
                    pass
                output_queue.put(("stdout", None))

            def read_stderr():
                try:
                    for line in process.stderr:
                        if line:
                            error_lines.append(line)
                            output_queue.put(("stderr", line))
                except Exception:
                    pass
                output_queue.put(("stderr", None))

            # 启动读取线程
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stdout_thread.start()
            stderr_thread.start()

            # 流式读取输出
            stdout_done = False
            stderr_done = False

            while not (stdout_done and stderr_done):
                try:
                    source, line = output_queue.get(timeout=0.1)
                    if line is None:
                        if source == "stdout":
                            stdout_done = True
                        else:
                            stderr_done = True
                    else:
                        # 将输出转换为与 Docker API 兼容的格式
                        yield {"stream": line}
                except queue.Empty:
                    # 检查进程是否已经结束
                    if process.poll() is not None:
                        # 进程已结束，读取剩余输出
                        break

            # 等待进程完成
            return_code = process.wait()

            # 读取剩余输出
            while not output_queue.empty():
                try:
                    source, line = output_queue.get_nowait()
                    if line is not None:
                        yield {"stream": line}
                except queue.Empty:
                    break

            if return_code != 0:
                error_msg = f"docker buildx build 失败，退出码: {return_code}"
                if error_lines:
                    error_msg += f"\n错误信息:\n{''.join(error_lines[-10:])}"  # 只显示最后10行错误
                raise RuntimeError(error_msg)

            # 构建成功，返回最终结果
            yield {"stream": f"Successfully built and tagged {', '.join(tags)}\n"}

        except Exception as e:
            raise RuntimeError(f"执行 docker buildx build 失败: {e}")


class LocalDockerBuilder(DockerBuilder):
    """本地 Docker 构建器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化时保存认证信息"""
        self.auth_config = None
        # 从配置中获取认证信息
        if config.get("username") and config.get("password"):
            self.auth_config = {
                "username": config.get("username"),
                "password": config.get("password"),
            }
            if config.get("registry"):
                self.auth_config["serveraddress"] = config.get("registry")
        super().__init__(config)

    def _initialize(self):
        """初始化本地 Docker 客户端"""
        try:
            try:
                import docker
            except ImportError as e:
                if "distutils" in str(e).lower():
                    print(
                        "⚠️ Docker 库导入失败: distutils 模块不可用（Python 3.12+ 已移除 distutils）"
                    )
                    print("   请安装 setuptools: pip install setuptools")
                else:
                    print(f"⚠️ Docker 库导入失败: {e}")
                self.available = False
                self.client = None
                return

            # 尝试连接本地 Docker
            self.client = docker.from_env()
            self.client.ping()
            self.available = True
            print("✅ 本地 Docker 连接成功")
        except Exception as e:
            print(f"⚠️ 本地 Docker 连接失败: {e}")
            self.available = False
            self.client = None

    def ping(self) -> bool:
        """测试 Docker 连接"""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False

    def build_image(
        self, path: str, tag: Union[str, List[str]], **kwargs
    ) -> Iterator[Dict]:
        """
        构建 Docker 镜像（使用 buildx）
        参考: https://github.com/docker/build-push-action
        """
        if not self.available:
            raise RuntimeError("本地 Docker 不可用")

        # 如果有认证信息，先尝试登录
        if hasattr(self, "auth_config") and self.auth_config:
            try:
                # 尝试登录到仓库
                self.client.login(
                    username=self.auth_config["username"],
                    password=self.auth_config["password"],
                    registry=self.auth_config.get("serveraddress", "docker.io"),
                )
                print(
                    f"✅ 已登录到仓库: {self.auth_config.get('serveraddress', 'docker.io')}"
                )
            except Exception as e:
                print(f"⚠️ 仓库登录失败: {e}")

        # 提取 buildx 相关参数
        dockerfile = kwargs.pop("dockerfile", None)
        target = kwargs.pop("target", None)
        platform = kwargs.pop("platform", None)
        platforms = kwargs.pop("platforms", None)
        build_args = kwargs.pop("buildargs", None) or kwargs.pop("build_args", None)
        cache_from = kwargs.pop("cache_from", None)
        cache_to = kwargs.pop("cache_to", None)
        load = kwargs.pop("load", False)
        push = kwargs.pop("push", False)
        outputs = kwargs.pop("outputs", None)

        # 使用 buildx 构建
        return self._build_with_buildx(
            path=path,
            tag=tag,
            dockerfile=dockerfile,
            target=target,
            platform=platform,
            platforms=platforms,
            build_args=build_args,
            cache_from=cache_from,
            cache_to=cache_to,
            load=load,
            push=push,
            outputs=outputs,
            **kwargs,  # 剩余的 kwargs（如 pull, no_cache 等）
        )

    def push_image(
        self, repository: str, tag: str = "latest", auth_config: Optional[Dict] = None
    ) -> Iterator[Dict]:
        """推送镜像到仓库"""
        if not self.available:
            raise RuntimeError("本地 Docker 不可用")

        # 使用低级 API 推送，支持完整的 repository 路径
        return self.client.api.push(
            repository=repository,
            tag=tag,
            auth_config=auth_config,
            stream=True,
            decode=True,
        )

    def get_image(self, name: str):
        """获取镜像对象"""
        if not self.available:
            raise RuntimeError("本地 Docker 不可用")
        return self.client.images.get(name)

    def pull_image(
        self, repository: str, tag: str = "latest", auth_config: Optional[Dict] = None
    ) -> Iterator[Dict]:
        """拉取镜像"""
        if not self.available:
            raise RuntimeError("本地 Docker 不可用")

        pull_kwargs = {
            "repository": repository,
            "tag": tag,
            "stream": True,
            "decode": True,
        }
        if auth_config:
            pull_kwargs["auth_config"] = auth_config

        return self.client.api.pull(**pull_kwargs)

    def export_image(self, name: str) -> Iterator[bytes]:
        """导出镜像为 tar 文件"""
        if not self.available:
            raise RuntimeError("本地 Docker 不可用")

        return self.client.api.get_image(name)

    def get_connection_info(self) -> str:
        """获取连接信息"""
        return "本地 Docker (unix:///var/run/docker.sock)"


class RemoteDockerBuilder(DockerBuilder):
    """远程 Docker 构建器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化时保存认证信息"""
        self.auth_config = None
        # 从配置中获取认证信息
        if config.get("username") and config.get("password"):
            self.auth_config = {
                "username": config.get("username"),
                "password": config.get("password"),
            }
            if config.get("registry"):
                self.auth_config["serveraddress"] = config.get("registry")
        super().__init__(config)

    def _initialize(self):
        """初始化远程 Docker 客户端"""
        try:
            try:
                import docker
            except ImportError as e:
                if "distutils" in str(e).lower():
                    error_msg = "Docker 库导入失败: distutils 模块不可用（Python 3.12+ 已移除 distutils）。请安装 setuptools: pip install setuptools"
                    print(f"⚠️ {error_msg}")
                else:
                    error_msg = f"Docker 库导入失败: {e}"
                    print(f"⚠️ {error_msg}")
                self.available = False
                self.client = None
                self._connection_info = "远程 Docker (导入失败)"
                self._connection_error = error_msg
                return

            import warnings
        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            print(f"⚠️ {error_msg}")
            self.available = False
            self.client = None
            self._connection_info = "远程 Docker (初始化失败)"
            self._connection_error = error_msg
            return

        try:
            # 忽略凭证助手警告
            warnings.filterwarnings("ignore", message=".*docker-credential.*")

            # 从配置中获取远程 Docker 信息
            remote_config = self.config.get("remote", {})
            host = remote_config.get("host", "")
            port = remote_config.get("port", 2375)
            use_tls = remote_config.get("use_tls", False)

            if not host:
                print("⚠️ 未配置远程 Docker 主机地址")
                self.available = False
                self.client = None
                return

            # 构建连接 URL
            if use_tls:
                base_url = f"https://{host}:{port}"
                # TLS 配置
                tls_config = None
                cert_path = remote_config.get("cert_path")
                if cert_path:
                    tls_config = docker.tls.TLSConfig(
                        client_cert=(
                            os.path.join(cert_path, "cert.pem"),
                            os.path.join(cert_path, "key.pem"),
                        ),
                        ca_cert=os.path.join(cert_path, "ca.pem"),
                        verify=remote_config.get("verify_tls", True),
                    )
                self.client = docker.DockerClient(
                    base_url=base_url,
                    tls=tls_config,
                    use_ssh_client=False,
                    credstore_env={},  # 禁用凭证存储
                )
            else:
                base_url = f"tcp://{host}:{port}"
                self.client = docker.DockerClient(
                    base_url=base_url,
                    use_ssh_client=False,
                    credstore_env={},  # 禁用凭证存储
                )

            # 测试连接
            self.client.ping()
            self.available = True
            self._connection_info = f"远程 Docker ({host}:{port})"
            print(f"✅ 远程 Docker 连接成功: {host}:{port}")

        except docker.errors.DockerException as e:
            error_msg = f"远程 Docker 连接失败: {str(e)}"
            print(f"⚠️ {error_msg}")
            self.available = False
            self.client = None
            self._connection_info = f"远程 Docker (连接失败: {str(e)})"
            self._connection_error = error_msg
        except Exception as e:
            error_msg = f"远程 Docker 连接异常: {str(e)}"
            print(f"⚠️ {error_msg}")
            import traceback

            traceback.print_exc()
            self.available = False
            self.client = None
            self._connection_info = f"远程 Docker (连接异常: {str(e)})"
            self._connection_error = error_msg

    def ping(self) -> bool:
        """测试 Docker 连接"""
        if not self.client:
            self._connection_error = "Docker 客户端未初始化"
            return False
        try:
            self.client.ping()
            self._connection_error = None  # 清除之前的错误
            return True
        except Exception as e:
            # 保存连接错误信息
            self._connection_error = f"Docker ping 失败: {str(e)}"
            return False

    def get_connection_error(self) -> str:
        """获取连接错误信息"""
        return getattr(self, "_connection_error", None) or "未知错误"

    def build_image(
        self, path: str, tag: Union[str, List[str]], **kwargs
    ) -> Iterator[Dict]:
        """
        构建 Docker 镜像（直接使用远程 Docker API，不依赖本地 docker 命令）
        参考: https://github.com/docker/build-push-action
        """
        if not self.available:
            error_msg = "远程 Docker 不可用"
            if hasattr(self, "_connection_error") and self._connection_error:
                error_msg += f": {self._connection_error}"
            raise RuntimeError(error_msg)

        # 如果有认证信息，先尝试登录
        if hasattr(self, "auth_config") and self.auth_config:
            try:
                # 尝试登录到仓库
                self.client.login(
                    username=self.auth_config["username"],
                    password=self.auth_config["password"],
                    registry=self.auth_config.get("serveraddress", "docker.io"),
                )
                print(
                    f"✅ 已登录到仓库: {self.auth_config.get('serveraddress', 'docker.io')}"
                )
            except Exception as e:
                print(f"⚠️ 仓库登录失败: {e}")

        # 提取构建参数
        dockerfile = kwargs.pop("dockerfile", None)
        target = kwargs.pop("target", None)
        platform = kwargs.pop("platform", None)
        platforms = kwargs.pop("platforms", None)
        build_args = kwargs.pop("buildargs", None) or kwargs.pop("build_args", None)
        pull = kwargs.pop("pull", False)
        no_cache = kwargs.pop("no_cache", False)
        load = kwargs.pop("load", True)  # 远程 Docker 构建后默认加载到远程
        push = kwargs.pop("push", False)

        # 处理标签（支持多标签）
        tags = tag if isinstance(tag, list) else [tag]

        # 构建上下文路径（必须是绝对路径）
        build_context = os.path.abspath(path)

        # 准备 Dockerfile 路径
        dockerfile_path = None
        if dockerfile:
            if os.path.isabs(dockerfile):
                dockerfile_path = dockerfile
            else:
                dockerfile_path = os.path.join(build_context, dockerfile)
        else:
            dockerfile_path = os.path.join(build_context, "Dockerfile")

        # 检查 Dockerfile 是否存在
        if not os.path.exists(dockerfile_path):
            raise RuntimeError(f"Dockerfile 不存在: {dockerfile_path}")

        # 使用 Docker API 直接构建（不需要本地 docker 命令）
        # 参考: https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build
        try:
            print(f"🔗 使用远程 Docker API 构建镜像: {', '.join(tags)}")
            print(f"   构建上下文: {build_context}")
            print(f"   Dockerfile: {dockerfile_path}")

            # 准备构建参数（Docker API 只支持单个标签）
            primary_tag = tags[0]
            build_kwargs = {
                "path": build_context,
                "tag": primary_tag,  # Docker API 只接受单个标签字符串
                "dockerfile": os.path.relpath(dockerfile_path, build_context),
                "decode": True,  # 解码 JSON 响应
                "pull": pull,
                "nocache": no_cache,
            }

            # 添加目标阶段（多阶段构建）
            if target:
                build_kwargs["target"] = target

            # 添加平台（注意：Docker API 的 build 方法不支持多平台构建，需要使用 buildx）
            if platform:
                build_kwargs["platform"] = platform
            elif platforms and len(platforms) == 1:
                build_kwargs["platform"] = platforms[0]
            elif platforms and len(platforms) > 1:
                # 多平台构建需要使用 buildx，回退到 buildx 方法
                print("⚠️ 多平台构建需要使用 buildx，尝试使用 buildx...")
                return self._build_with_buildx_via_remote(
                    path=build_context,
                    tag=tags,
                    dockerfile=os.path.relpath(dockerfile_path, build_context),
                    target=target,
                    platforms=platforms,
                    build_args=build_args,
                    load=load,
                    push=push,
                    **kwargs,
                )

            # 添加构建参数
            if build_args:
                build_kwargs["buildargs"] = build_args

            # 打印构建参数，方便排查问题
            print(f"🔧 使用 Docker API 构建镜像:")
            print(f"   镜像标签: {primary_tag}")
            print(f"   构建上下文: {build_context}")
            print(f"   Dockerfile: {build_kwargs['dockerfile']}")
            if target:
                print(f"   目标阶段: {target}")
            if platform or (platforms and len(platforms) == 1):
                print(f"   平台: {build_kwargs.get('platform', 'default')}")
            if build_args:
                print(f"   构建参数: {build_args}")
            print(f"   完整参数: {build_kwargs}")

            # 使用 Docker API 构建（默认返回生成器，流式返回日志）
            build_logs = self.client.api.build(**build_kwargs)

            # 流式返回构建日志
            try:
                for chunk in build_logs:
                    if isinstance(chunk, dict):
                        # Docker API 返回的格式
                        if "stream" in chunk:
                            yield {"stream": chunk["stream"]}
                        elif "error" in chunk:
                            yield {"error": chunk["error"]}
                        elif "status" in chunk:
                            yield {"status": chunk["status"]}
                        elif "aux" in chunk:
                            yield {"aux": chunk["aux"]}
                    else:
                        # 字符串格式
                        yield {"stream": str(chunk)}
            except GeneratorExit:
                # 生成器被关闭时，清理资源
                if build_logs:
                    try:
                        build_logs.close()
                    except:
                        pass
                raise

            # 构建成功后，如果需要多标签，为其他标签打标签
            if len(tags) > 1:
                base_image = primary_tag
                for tag_name in tags[1:]:
                    try:
                        image = self.client.images.get(base_image)
                        # 解析标签（格式：repository:tag）
                        if ":" in tag_name:
                            repo, tag = tag_name.rsplit(":", 1)
                        else:
                            repo, tag = tag_name, "latest"
                        image.tag(repo, tag)
                        yield {"stream": f"Successfully tagged {tag_name}\n"}
                    except Exception as e:
                        yield {"error": f"Failed to tag {tag_name}: {str(e)}\n"}

            # 如果需要推送
            if push:
                for tag_name in tags:
                    # 解析标签（格式：repository:tag）
                    if ":" in tag_name:
                        repo, tag = tag_name.rsplit(":", 1)
                    else:
                        repo, tag = tag_name, "latest"
                    yield from self.push_image(repository=repo, tag=tag)

        except Exception as e:
            import traceback

            error_msg = f"远程 Docker 构建失败: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()
            yield {"error": error_msg}
            raise RuntimeError(error_msg)

    def _build_with_buildx_via_remote(
        self,
        path: str,
        tag: Union[str, List[str]],
        dockerfile: Optional[str] = None,
        target: Optional[str] = None,
        platforms: Optional[list] = None,
        build_args: Optional[Dict[str, str]] = None,
        load: bool = True,
        push: bool = False,
        **kwargs,
    ) -> Iterator[Dict]:
        """
        通过远程 Docker 使用 buildx 构建（需要远程 Docker 支持 buildx）
        如果本地没有 docker 命令，尝试通过远程 Docker API 执行 buildx
        """
        # 检查本地是否有 docker 命令
        docker_path = shutil.which("docker")
        if not docker_path:
            # 如果没有本地 docker 命令，尝试使用远程 Docker API
            # 但 buildx 的高级功能（多平台构建）需要通过命令行
            raise RuntimeError(
                "多平台构建需要本地 docker buildx 命令，或者使用单平台构建。\n"
                "请安装 docker 客户端，或使用单平台构建。"
            )

        # 使用本地 docker 命令，但通过 DOCKER_HOST 连接到远程 Docker
        remote_config = self.config.get("remote", {})
        original_docker_host = os.environ.get("DOCKER_HOST")

        try:
            if remote_config.get("host"):
                host = remote_config.get("host")
                port = remote_config.get("port", 2375)
                use_tls = remote_config.get("use_tls", False)

                if use_tls:
                    docker_host = f"https://{host}:{port}"
                else:
                    docker_host = f"tcp://{host}:{port}"

                os.environ["DOCKER_HOST"] = docker_host
                print(f"🔗 设置 DOCKER_HOST={docker_host} 用于 buildx 构建")

            return self._build_with_buildx(
                path=path,
                tag=tag,
                dockerfile=dockerfile,
                target=target,
                platforms=platforms,
                build_args=build_args,
                load=load,
                push=push,
                **kwargs,
            )
        finally:
            if original_docker_host is not None:
                os.environ["DOCKER_HOST"] = original_docker_host
            elif "DOCKER_HOST" in os.environ:
                del os.environ["DOCKER_HOST"]

    def push_image(
        self, repository: str, tag: str = "latest", auth_config: Optional[Dict] = None
    ) -> Iterator[Dict]:
        """推送镜像到仓库"""
        if not self.available:
            raise RuntimeError("远程 Docker 不可用")

        # 使用低级 API 推送，支持完整的 repository 路径
        return self.client.api.push(
            repository=repository,
            tag=tag,
            auth_config=auth_config,
            stream=True,
            decode=True,
        )

    def get_image(self, name: str):
        """获取镜像对象"""
        if not self.available:
            raise RuntimeError("远程 Docker 不可用")
        return self.client.images.get(name)

    def pull_image(
        self, repository: str, tag: str = "latest", auth_config: Optional[Dict] = None
    ) -> Iterator[Dict]:
        """拉取镜像"""
        if not self.available:
            raise RuntimeError("远程 Docker 不可用")

        pull_kwargs = {
            "repository": repository,
            "tag": tag,
            "stream": True,
            "decode": True,
        }
        if auth_config:
            pull_kwargs["auth_config"] = auth_config

        return self.client.api.pull(**pull_kwargs)

    def export_image(self, name: str) -> Iterator[bytes]:
        """导出镜像为 tar 文件"""
        if not self.available:
            error_msg = "远程 Docker 不可用"
            if hasattr(self, "_connection_error") and self._connection_error:
                error_msg += f": {self._connection_error}"
            raise RuntimeError(error_msg)

        return self.client.api.get_image(name)

    def get_connection_info(self) -> str:
        """获取连接信息"""
        return getattr(self, "_connection_info", "远程 Docker (未知)")


class MockDockerBuilder(DockerBuilder):
    """模拟 Docker 构建器（用于测试和演示）"""

    def _initialize(self):
        """初始化模拟客户端"""
        self.available = True
        print("⚠️ 使用模拟 Docker 构建器（仅用于测试）")

    def ping(self) -> bool:
        """测试 Docker 连接"""
        return True

    def build_image(self, path: str, tag: str, **kwargs) -> Iterator[Dict]:
        """模拟构建 Docker 镜像"""
        yield {"stream": "🧪 模拟模式：Docker 服务不可用\n"}
        yield {"stream": "Step 1/6 : FROM nginx:alpine (模拟)\n"}
        yield {"stream": "Step 2/6 : ENV TZ=Asia/Shanghai (模拟)\n"}
        yield {"stream": "Step 3/6 : COPY . /usr/share/nginx/html/ (模拟)\n"}
        yield {"stream": "Step 4/6 : EXPOSE 9999 (模拟)\n"}
        yield {"stream": 'Step 5/6 : CMD ["nginx", "-g", "daemon off;"] (模拟)\n'}
        yield {"stream": "Successfully built 模拟镜像ID12345\n"}
        yield {"stream": f"Successfully tagged {tag}\n"}
        yield {"aux": {"ID": "sha256:mock_image_id_12345"}}

    def push_image(
        self, repository: str, tag: str = "latest", auth_config: Optional[Dict] = None
    ) -> Iterator[Dict]:
        """模拟推送镜像"""
        full_tag = f"{repository}:{tag}"
        yield {"status": f"模拟推送：推送镜像 {full_tag} (未真实推送)"}
        yield {"status": "模拟推送完成，耗时 0.01 秒"}

    def get_image(self, name: str):
        """模拟获取镜像"""
        return {"Id": "mock_image_id", "Tags": [name]}

    def pull_image(
        self, repository: str, tag: str = "latest", auth_config: Optional[Dict] = None
    ) -> Iterator[Dict]:
        """模拟拉取镜像"""
        yield {"status": f"模拟拉取：{repository}:{tag}"}
        yield {"status": "模拟拉取完成"}

    def export_image(self, name: str) -> Iterator[bytes]:
        """模拟导出镜像"""
        yield b"mock_tar_data"

    def get_connection_info(self) -> str:
        """获取连接信息"""
        return "模拟 Docker (测试模式)"


def create_docker_builder(config: Dict[str, Any]) -> DockerBuilder:
    """
    工厂函数：根据配置创建合适的 Docker 构建器
    Args:
        config: Docker 配置字典
    Returns:
        DockerBuilder 实例
    """
    # 检查是否配置了远程 Docker
    use_remote = config.get("use_remote", False)

    if use_remote:
        # 使用远程 Docker
        builder = RemoteDockerBuilder(config)
        if builder.is_available():
            return builder
        else:
            print("⚠️ 远程 Docker 不可用，尝试使用本地 Docker")

    # 尝试使用本地 Docker
    builder = LocalDockerBuilder(config)
    if builder.is_available():
        return builder

    # 都不可用，使用模拟构建器
    print("⚠️ Docker 不可用，使用模拟构建器")
    return MockDockerBuilder(config)

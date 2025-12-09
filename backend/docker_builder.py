# docker_builder.py
"""
Docker 构建器抽象类和实现类
支持本地和远程 Docker 构建
"""
import os
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Iterator


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

    def build_image(self, path: str, tag: str, **kwargs) -> Iterator[Dict]:
        """构建 Docker 镜像（强制启用 BuildKit）"""
        if not self.available:
            raise RuntimeError("本地 Docker 不可用")

        # 强制启用 BuildKit（方法一：通过环境变量）
        original_buildkit = os.environ.get("DOCKER_BUILDKIT")
        os.environ["DOCKER_BUILDKIT"] = "1"
        # 同时设置 COMPOSE_DOCKER_CLI_BUILD 以支持 docker-compose
        original_compose_buildkit = os.environ.get("COMPOSE_DOCKER_CLI_BUILD")
        os.environ["COMPOSE_DOCKER_CLI_BUILD"] = "1"

        try:
            # 准备构建参数，包含认证信息
            build_kwargs = {
                "path": path,
                "tag": tag,
                "rm": True,
                "decode": True,
            }

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

            build_kwargs.update(kwargs)

            # 使用低级 API 获取流式输出（BuildKit 会自动启用）
            return self.client.api.build(**build_kwargs)
        finally:
            # 恢复原始环境变量
            if original_buildkit is not None:
                os.environ["DOCKER_BUILDKIT"] = original_buildkit
            elif "DOCKER_BUILDKIT" in os.environ:
                del os.environ["DOCKER_BUILDKIT"]

            if original_compose_buildkit is not None:
                os.environ["COMPOSE_DOCKER_CLI_BUILD"] = original_compose_buildkit
            elif "COMPOSE_DOCKER_CLI_BUILD" in os.environ:
                del os.environ["COMPOSE_DOCKER_CLI_BUILD"]

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

    def build_image(self, path: str, tag: str, **kwargs) -> Iterator[Dict]:
        """构建 Docker 镜像（强制启用 BuildKit）"""
        if not self.available:
            error_msg = "远程 Docker 不可用"
            if hasattr(self, "_connection_error") and self._connection_error:
                error_msg += f": {self._connection_error}"
            raise RuntimeError(error_msg)

        # 强制启用 BuildKit（方法一：通过环境变量）
        original_buildkit = os.environ.get("DOCKER_BUILDKIT")
        os.environ["DOCKER_BUILDKIT"] = "1"
        # 同时设置 COMPOSE_DOCKER_CLI_BUILD 以支持 docker-compose
        original_compose_buildkit = os.environ.get("COMPOSE_DOCKER_CLI_BUILD")
        os.environ["COMPOSE_DOCKER_CLI_BUILD"] = "1"

        try:
            # 准备构建参数，包含认证信息
            build_kwargs = {
                "path": path,
                "tag": tag,
                "rm": True,
                "decode": True,
            }

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

            build_kwargs.update(kwargs)

            # 使用低级 API 获取流式输出（BuildKit 会自动启用）
            return self.client.api.build(**build_kwargs)
        finally:
            # 恢复原始环境变量
            if original_buildkit is not None:
                os.environ["DOCKER_BUILDKIT"] = original_buildkit
            elif "DOCKER_BUILDKIT" in os.environ:
                del os.environ["DOCKER_BUILDKIT"]

            if original_compose_buildkit is not None:
                os.environ["COMPOSE_DOCKER_CLI_BUILD"] = original_compose_buildkit
            elif "COMPOSE_DOCKER_CLI_BUILD" in os.environ:
                del os.environ["COMPOSE_DOCKER_CLI_BUILD"]

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

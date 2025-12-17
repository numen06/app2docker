# backend/host_manager.py
"""
主机资源管理模块（基于数据库）
用于管理远程主机SSH连接和Docker编译支持配置
"""
import os
import uuid
import paramiko
from datetime import datetime
from typing import List, Dict, Optional
from backend.database import get_db_session, init_db
from backend.models import Host

# 确保数据库已初始化
try:
    init_db()
except:
    pass


class HostManager:
    """主机资源管理器（基于数据库）"""

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            import threading

            cls._instance = super().__new__(cls)
            cls._lock = threading.Lock()
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化主机管理器"""
        pass

    def _to_dict(self, host: Host, include_secrets: bool = False) -> Optional[Dict]:
        """将数据库模型转换为字典"""
        if not host:
            return None

        result = {
            "host_id": host.host_id,
            "name": host.name,
            "host": host.host,
            "port": host.port,
            "username": host.username,
            "docker_enabled": host.docker_enabled,
            "docker_version": host.docker_version,
            "description": host.description,
            "created_at": host.created_at.isoformat() if host.created_at else None,
            "updated_at": host.updated_at.isoformat() if host.updated_at else None,
        }

        if include_secrets:
            result["password"] = host.password
            result["private_key"] = host.private_key
            result["key_password"] = host.key_password
        else:
            result["has_password"] = bool(host.password)
            result["has_private_key"] = bool(host.private_key)
            if host.password:
                result["password"] = "***"
            if host.private_key:
                result["private_key"] = "***"
            if host.key_password:
                result["key_password"] = "***"
            result["docker_available"] = bool(host.docker_version)

        return result

    def test_ssh_connection(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        key_password: Optional[str] = None,
        timeout: int = 10,
    ) -> Dict:
        """测试SSH连接"""
        ssh_client = None
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            auth_methods = []

            if private_key:
                try:
                    import io

                    key_file = io.StringIO(private_key)
                    for key_class in [
                        paramiko.RSAKey,
                        paramiko.Ed25519Key,
                        paramiko.ECDSAKey,
                        paramiko.DSSKey,
                    ]:
                        try:
                            key_file.seek(0)
                            if key_password:
                                pkey = key_class.from_private_key(
                                    key_file, password=key_password
                                )
                            else:
                                pkey = key_class.from_private_key(key_file)
                            auth_methods.append(pkey)
                            break
                        except:
                            continue
                    key_file.close()
                except Exception as e:
                    print(f"⚠️ 解析SSH私钥失败: {e}")

            if password:
                auth_methods.append(password)

            if not auth_methods:
                return {
                    "success": False,
                    "message": "请提供密码或SSH私钥",
                    "docker_available": False,
                }

            connect_kwargs = {
                "hostname": host,
                "port": port,
                "username": username,
                "timeout": timeout,
            }

            if isinstance(
                auth_methods[0],
                (
                    paramiko.RSAKey,
                    paramiko.Ed25519Key,
                    paramiko.ECDSAKey,
                    paramiko.DSSKey,
                ),
            ):
                connect_kwargs["pkey"] = auth_methods[0]
            else:
                connect_kwargs["password"] = auth_methods[0]

            ssh_client.connect(**connect_kwargs)

            docker_available = False
            docker_version = None
            try:
                stdin, stdout, stderr = ssh_client.exec_command(
                    "docker --version", timeout=5
                )
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    docker_version = stdout.read().decode("utf-8").strip()
                    docker_available = True
            except Exception as e:
                print(f"⚠️ 检查Docker失败: {e}")

            # 检测 Docker Compose 模式支持
            compose_supported = False
            stack_supported = False
            compose_version = None
            swarm_mode = None

            if docker_available:
                try:
                    # 检测 docker-compose
                    stdin, stdout, stderr = ssh_client.exec_command(
                        "docker-compose --version", timeout=5
                    )
                    exit_status = stdout.channel.recv_exit_status()
                    if exit_status == 0:
                        compose_supported = True
                        compose_version = stdout.read().decode("utf-8").strip()
                except Exception as e:
                    print(f"⚠️ 检查docker-compose失败: {e}")

                try:
                    # 检测 Swarm 模式
                    stdin, stdout, stderr = ssh_client.exec_command(
                        "docker info --format '{{.Swarm.LocalNodeState}}'", timeout=5
                    )
                    exit_status = stdout.channel.recv_exit_status()
                    if exit_status == 0:
                        swarm_mode = stdout.read().decode("utf-8").strip()
                        stack_supported = swarm_mode == "active"
                except Exception as e:
                    print(f"⚠️ 检查Swarm模式失败: {e}")

            return {
                "success": True,
                "message": "SSH连接成功",
                "docker_available": docker_available,
                "docker_version": docker_version,
                "compose_supported": compose_supported,
                "stack_supported": stack_supported,
                "compose_version": compose_version,
                "swarm_mode": swarm_mode,
            }

        except paramiko.AuthenticationException:
            return {
                "success": False,
                "message": "SSH认证失败，请检查用户名和密码/密钥",
                "docker_available": False,
            }
        except paramiko.SSHException as e:
            return {
                "success": False,
                "message": f"SSH连接错误: {str(e)}",
                "docker_available": False,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
                "docker_available": False,
            }
        finally:
            if ssh_client:
                try:
                    ssh_client.close()
                except:
                    pass

    def add_host(
        self,
        name: str,
        host: str,
        port: int = 22,
        username: str = "",
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        key_password: Optional[str] = None,
        docker_enabled: bool = False,
        description: str = "",
    ) -> Dict:
        """添加主机"""
        with self._lock:
            db = get_db_session()
            try:
                # 检查名称是否已存在
                existing = db.query(Host).filter(Host.name == name).first()
                if existing:
                    raise ValueError(f"主机名称 '{name}' 已存在")

                host_id = str(uuid.uuid4())

                host_obj = Host(
                    host_id=host_id,
                    name=name,
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    private_key=private_key,
                    key_password=key_password,
                    docker_enabled=docker_enabled,
                    docker_version=None,
                    description=description,
                )

                db.add(host_obj)
                db.commit()

                print(f"✅ 主机添加成功: {host_id} ({name})")
                return self._to_dict(host_obj)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()

    def update_host(
        self,
        host_id: str,
        name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        key_password: Optional[str] = None,
        docker_enabled: Optional[bool] = None,
        docker_version: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Dict]:
        """更新主机信息"""
        with self._lock:
            db = get_db_session()
            try:
                host_obj = db.query(Host).filter(Host.host_id == host_id).first()
                if not host_obj:
                    return None

                if name and name != host_obj.name:
                    existing = (
                        db.query(Host)
                        .filter(Host.name == name, Host.host_id != host_id)
                        .first()
                    )
                    if existing:
                        raise ValueError(f"主机名称 '{name}' 已存在")
                    host_obj.name = name

                if host is not None:
                    host_obj.host = host
                if port is not None:
                    host_obj.port = port
                if username is not None:
                    host_obj.username = username
                if password is not None:
                    host_obj.password = password if password else None
                if private_key is not None:
                    host_obj.private_key = private_key if private_key else None
                    if not private_key:
                        host_obj.key_password = None
                if key_password is not None:
                    host_obj.key_password = key_password if key_password else None
                if docker_enabled is not None:
                    host_obj.docker_enabled = docker_enabled
                if docker_version is not None:
                    host_obj.docker_version = docker_version
                if description is not None:
                    host_obj.description = description

                host_obj.updated_at = datetime.now()
                db.commit()

                print(f"✅ 主机更新成功: {host_id}")
                return self._to_dict(host_obj)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()

    def list_hosts(self) -> List[Dict]:
        """列出所有主机"""
        db = get_db_session()
        try:
            hosts = db.query(Host).order_by(Host.created_at.desc()).all()
            return [self._to_dict(h) for h in hosts]
        finally:
            db.close()

    def get_host(self, host_id: str) -> Optional[Dict]:
        """获取主机信息"""
        db = get_db_session()
        try:
            host = db.query(Host).filter(Host.host_id == host_id).first()
            return self._to_dict(host)
        finally:
            db.close()

    def get_host_full(self, host_id: str) -> Optional[Dict]:
        """获取主机完整信息（包含密码和私钥，用于连接）"""
        db = get_db_session()
        try:
            host = db.query(Host).filter(Host.host_id == host_id).first()
            return self._to_dict(host, include_secrets=True)
        finally:
            db.close()

    def delete_host(self, host_id: str) -> bool:
        """删除主机"""
        with self._lock:
            db = get_db_session()
            try:
                host = db.query(Host).filter(Host.host_id == host_id).first()
                if not host:
                    return False

                db.delete(host)
                db.commit()

                print(f"✅ 主机已删除: {host_id}")
                return True
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()

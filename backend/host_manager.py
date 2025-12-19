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
from backend.crypto_utils import (
    encrypt_password,
    decrypt_password,
    migrate_old_password,
)

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
            # 解密密码和密钥
            if host.password:
                try:
                    result["password"] = decrypt_password(host.password)
                except (ValueError, Exception):
                    # 如果解密失败，尝试迁移旧格式（明文或base64）
                    try:
                        # migrate_old_password 会返回加密后的密码，但我们需要明文
                        # 所以先尝试获取明文
                        import base64

                        try:
                            # 尝试base64解码
                            decoded = base64.b64decode(host.password.encode("utf-8"))
                            plaintext = decoded.decode("utf-8")
                            # 如果能解码，说明是base64编码的明文，加密后更新数据库
                            encrypted = encrypt_password(plaintext)
                            db = get_db_session()
                            try:
                                host_obj = (
                                    db.query(Host)
                                    .filter(Host.host_id == host.host_id)
                                    .first()
                                )
                                if host_obj:
                                    host_obj.password = encrypted
                                    db.commit()
                            finally:
                                db.close()
                            result["password"] = plaintext
                        except Exception:
                            # 如果base64解码失败，当作明文处理
                            plaintext = host.password
                            encrypted = encrypt_password(plaintext)
                            db = get_db_session()
                            try:
                                host_obj = (
                                    db.query(Host)
                                    .filter(Host.host_id == host.host_id)
                                    .first()
                                )
                                if host_obj:
                                    host_obj.password = encrypted
                                    db.commit()
                            finally:
                                db.close()
                            result["password"] = plaintext
                    except Exception as e:
                        print(f"⚠️ 解密Host密码失败: {e}")
                        result["password"] = None
            else:
                result["password"] = None

            if host.private_key:
                try:
                    result["private_key"] = decrypt_password(host.private_key)
                except (ValueError, Exception):
                    try:
                        # 尝试迁移旧格式
                        import base64

                        try:
                            decoded = base64.b64decode(host.private_key.encode("utf-8"))
                            plaintext = decoded.decode("utf-8")
                            encrypted = encrypt_password(plaintext)
                            db = get_db_session()
                            try:
                                host_obj = (
                                    db.query(Host)
                                    .filter(Host.host_id == host.host_id)
                                    .first()
                                )
                                if host_obj:
                                    host_obj.private_key = encrypted
                                    db.commit()
                            finally:
                                db.close()
                            result["private_key"] = plaintext
                        except Exception:
                            plaintext = host.private_key
                            encrypted = encrypt_password(plaintext)
                            db = get_db_session()
                            try:
                                host_obj = (
                                    db.query(Host)
                                    .filter(Host.host_id == host.host_id)
                                    .first()
                                )
                                if host_obj:
                                    host_obj.private_key = encrypted
                                    db.commit()
                            finally:
                                db.close()
                            result["private_key"] = plaintext
                    except Exception as e:
                        print(f"⚠️ 解密Host私钥失败: {e}")
                        result["private_key"] = None
            else:
                result["private_key"] = None

            if host.key_password:
                try:
                    result["key_password"] = decrypt_password(host.key_password)
                except (ValueError, Exception):
                    try:
                        # 尝试迁移旧格式
                        import base64

                        try:
                            decoded = base64.b64decode(
                                host.key_password.encode("utf-8")
                            )
                            plaintext = decoded.decode("utf-8")
                            encrypted = encrypt_password(plaintext)
                            db = get_db_session()
                            try:
                                host_obj = (
                                    db.query(Host)
                                    .filter(Host.host_id == host.host_id)
                                    .first()
                                )
                                if host_obj:
                                    host_obj.key_password = encrypted
                                    db.commit()
                            finally:
                                db.close()
                            result["key_password"] = plaintext
                        except Exception:
                            plaintext = host.key_password
                            encrypted = encrypt_password(plaintext)
                            db = get_db_session()
                            try:
                                host_obj = (
                                    db.query(Host)
                                    .filter(Host.host_id == host.host_id)
                                    .first()
                                )
                                if host_obj:
                                    host_obj.key_password = encrypted
                                    db.commit()
                            finally:
                                db.close()
                            result["key_password"] = plaintext
                    except Exception as e:
                        print(f"⚠️ 解密Host密钥密码失败: {e}")
                        result["key_password"] = None
            else:
                result["key_password"] = None
        else:
            result["has_password"] = bool(host.password)
            result["has_private_key"] = bool(host.private_key)
            result["has_key_password"] = bool(host.key_password)
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

                # 加密敏感信息
                encrypted_password = encrypt_password(password) if password else None
                encrypted_private_key = (
                    encrypt_password(private_key) if private_key else None
                )
                encrypted_key_password = (
                    encrypt_password(key_password) if key_password else None
                )

                host_obj = Host(
                    host_id=host_id,
                    name=name,
                    host=host,
                    port=port,
                    username=username,
                    password=encrypted_password,
                    private_key=encrypted_private_key,
                    key_password=encrypted_key_password,
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
                    # 加密密码后存储
                    host_obj.password = encrypt_password(password) if password else None
                if private_key is not None:
                    # 加密私钥后存储
                    host_obj.private_key = (
                        encrypt_password(private_key) if private_key else None
                    )
                    if not private_key:
                        host_obj.key_password = None
                if key_password is not None:
                    # 加密密钥密码后存储
                    host_obj.key_password = (
                        encrypt_password(key_password) if key_password else None
                    )
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

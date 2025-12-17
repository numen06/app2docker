# backend/agent_secret_manager.py
"""
Agent密钥管理器
用于管理Agent连接的密钥
"""
import os
import uuid
import hashlib
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any
from backend.database import get_db_session, init_db
from backend.models import AgentSecret

# 确保数据库已初始化
try:
    init_db()
except:
    pass


class AgentSecretManager:
    """Agent密钥管理器"""

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = threading.Lock()
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化密钥管理器"""
        pass

    def _generate_secret_key(self) -> str:
        """生成唯一密钥（32位小写字母和数字）"""
        # 使用UUID + 时间戳 + 随机数生成唯一密钥
        secret_data = (
            f"{uuid.uuid4()}{datetime.now().timestamp()}{os.urandom(16).hex()}"
        )
        secret_hash = hashlib.sha256(secret_data.encode()).hexdigest()[:32]
        return secret_hash

    def _to_dict(self, secret: AgentSecret) -> Optional[Dict]:
        """将数据库模型转换为字典"""
        if not secret:
            return None

        return {
            "secret_id": secret.secret_id,
            "secret_key": secret.secret_key,
            "name": secret.name or "",
            "enabled": secret.enabled,
            "created_at": secret.created_at.isoformat() if secret.created_at else None,
            "updated_at": secret.updated_at.isoformat() if secret.updated_at else None,
        }

    def generate_secret(self, name: str = "") -> Dict:
        """
        生成新密钥

        Args:
            name: 密钥名称/描述

        Returns:
            密钥信息字典
        """
        with self._lock:
            db = get_db_session()
            try:
                secret_id = str(uuid.uuid4())
                secret_key = self._generate_secret_key()

                # 确保密钥唯一
                while (
                    db.query(AgentSecret)
                    .filter(AgentSecret.secret_key == secret_key)
                    .first()
                ):
                    secret_key = self._generate_secret_key()

                secret_obj = AgentSecret(
                    secret_id=secret_id,
                    secret_key=secret_key,
                    name=name,
                    enabled=True,
                )

                db.add(secret_obj)
                db.commit()

                print(f"✅ 密钥生成成功: {secret_id} ({name or '未命名'})")
                return self._to_dict(secret_obj)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()

    def list_secrets(self) -> List[Dict]:
        """列出所有密钥"""
        db = get_db_session()
        try:
            secrets = (
                db.query(AgentSecret).order_by(AgentSecret.created_at.desc()).all()
            )
            return [self._to_dict(s) for s in secrets]
        finally:
            db.close()

    def get_secret(self, secret_key: str) -> Optional[Dict]:
        """
        根据密钥值获取密钥信息

        Args:
            secret_key: 密钥值

        Returns:
            密钥信息字典，如果不存在返回None
        """
        db = get_db_session()
        try:
            secret = (
                db.query(AgentSecret)
                .filter(AgentSecret.secret_key == secret_key)
                .first()
            )
            return self._to_dict(secret) if secret else None
        finally:
            db.close()

    def get_secret_by_id(self, secret_id: str) -> Optional[Dict]:
        """
        根据密钥ID获取密钥信息

        Args:
            secret_id: 密钥ID

        Returns:
            密钥信息字典，如果不存在返回None
        """
        db = get_db_session()
        try:
            secret = (
                db.query(AgentSecret).filter(AgentSecret.secret_id == secret_id).first()
            )
            return self._to_dict(secret) if secret else None
        finally:
            db.close()

    def validate_secret(self, secret_key: str) -> bool:
        """
        验证密钥是否有效且启用

        Args:
            secret_key: 密钥值

        Returns:
            是否有效且启用
        """
        secret = self.get_secret(secret_key)
        return secret is not None and secret.get("enabled", False)

    def enable_secret(self, secret_id: str) -> Optional[Dict]:
        """
        启用密钥

        Args:
            secret_id: 密钥ID

        Returns:
            更新后的密钥信息，如果不存在返回None
        """
        with self._lock:
            db = get_db_session()
            try:
                secret = (
                    db.query(AgentSecret)
                    .filter(AgentSecret.secret_id == secret_id)
                    .first()
                )
                if not secret:
                    return None

                secret.enabled = True
                secret.updated_at = datetime.now()
                db.commit()

                return self._to_dict(secret)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()

    def disable_secret(self, secret_id: str) -> Optional[Dict]:
        """
        禁用密钥

        Args:
            secret_id: 密钥ID

        Returns:
            更新后的密钥信息，如果不存在返回None
        """
        with self._lock:
            db = get_db_session()
            try:
                secret = (
                    db.query(AgentSecret)
                    .filter(AgentSecret.secret_id == secret_id)
                    .first()
                )
                if not secret:
                    return None

                secret.enabled = False
                secret.updated_at = datetime.now()
                db.commit()

                return self._to_dict(secret)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()

    def delete_secret(self, secret_id: str) -> bool:
        """
        删除密钥

        Args:
            secret_id: 密钥ID

        Returns:
            是否成功删除
        """
        with self._lock:
            db = get_db_session()
            try:
                secret = (
                    db.query(AgentSecret)
                    .filter(AgentSecret.secret_id == secret_id)
                    .first()
                )
                if not secret:
                    return False

                db.delete(secret)
                db.commit()

                print(f"✅ 密钥已删除: {secret_id}")
                return True
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()

    def update_secret(
        self, secret_id: str, name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        更新密钥信息

        Args:
            secret_id: 密钥ID
            name: 密钥名称（可选）

        Returns:
            更新后的密钥信息，如果不存在返回None
        """
        with self._lock:
            db = get_db_session()
            try:
                secret = (
                    db.query(AgentSecret)
                    .filter(AgentSecret.secret_id == secret_id)
                    .first()
                )
                if not secret:
                    return None

                if name is not None:
                    secret.name = name
                secret.updated_at = datetime.now()
                db.commit()

                return self._to_dict(secret)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()

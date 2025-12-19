# backend/crypto_utils.py
"""
密码加密工具模块
使用 AES-256-GCM 加密算法对敏感数据进行加密存储
"""
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from backend.auth import SECRET_KEY


def _get_encryption_key() -> bytes:
    """从 SECRET_KEY 生成加密密钥（32字节）"""
    # 使用 SHA256 哈希确保密钥长度为 32 字节
    key_hash = hashlib.sha256(SECRET_KEY.encode()).digest()
    return key_hash


def encrypt_password(plaintext: str) -> str:
    """
    加密密码

    Args:
        plaintext: 明文密码

    Returns:
        加密后的字符串（base64编码）
    """
    if not plaintext:
        return ""

    try:
        # 生成加密密钥
        key = _get_encryption_key()

        # 创建 AESGCM 实例
        aesgcm = AESGCM(key)

        # 生成随机 nonce（12字节，GCM推荐）
        import os

        nonce = os.urandom(12)

        # 加密数据
        plaintext_bytes = plaintext.encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)

        # 将 nonce 和 ciphertext 组合，然后 base64 编码
        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode("utf-8")
    except Exception as e:
        print(f"⚠️ 加密密码失败: {e}")
        raise


def decrypt_password(encrypted: str) -> str:
    """
    解密密码

    Args:
        encrypted: 加密后的字符串（base64编码）

    Returns:
        解密后的明文密码

    Raises:
        ValueError: 如果解密失败
    """
    if not encrypted:
        return ""

    try:
        # 生成加密密钥
        key = _get_encryption_key()

        # 创建 AESGCM 实例
        aesgcm = AESGCM(key)

        # base64 解码
        encrypted_data = base64.b64decode(encrypted.encode("utf-8"))

        # 提取 nonce（前12字节）和 ciphertext（剩余部分）
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # 解密数据
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")
    except Exception as e:
        # 如果解密失败，可能是旧格式的数据，返回 None 让调用者处理
        print(f"⚠️ 解密密码失败: {e}")
        raise ValueError(f"解密失败: {str(e)}")


def is_encrypted(value: str) -> bool:
    """
    判断字符串是否是加密后的格式

    Args:
        value: 待检查的字符串

    Returns:
        如果是加密格式返回 True，否则返回 False
    """
    if not value:
        return False

    try:
        # 尝试 base64 解码
        decoded = base64.b64decode(value.encode("utf-8"))
        # 加密后的数据应该至少包含 nonce（12字节）+ 一些密文
        return len(decoded) > 12
    except Exception:
        return False


def migrate_old_password(old_value: str) -> str:
    """
    迁移旧格式的密码（明文或base64编码）到加密格式

    Args:
        old_value: 旧格式的密码（可能是明文或base64编码）

    Returns:
        加密后的密码
    """
    if not old_value:
        return ""

    # 如果已经是加密格式，直接返回
    if is_encrypted(old_value):
        return old_value

    # 尝试判断是否是 base64 编码的明文
    try:
        # 尝试 base64 解码
        decoded = base64.b64decode(old_value.encode("utf-8"))
        # 如果能解码且长度合理，可能是 base64 编码的明文
        if len(decoded) < 1000:  # 假设密码不会超过1000字节
            try:
                plaintext = decoded.decode("utf-8")
                # 如果能解码为UTF-8，说明是base64编码的明文，加密它
                return encrypt_password(plaintext)
            except UnicodeDecodeError:
                # 解码失败，可能是其他格式，当作明文处理
                pass
    except Exception:
        # base64 解码失败，当作明文处理
        pass

    # 当作明文处理，加密它
    return encrypt_password(old_value)

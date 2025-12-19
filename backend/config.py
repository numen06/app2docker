# config.py
import os
import yaml
import base64
from typing import Optional
from backend.crypto_utils import encrypt_password, decrypt_password

# 将配置文件放在data目录中，方便Docker映射
CONFIG_FILE = "data/config.yml"

# 默认配置
DEFAULT_CONFIG = {
    "docker": {
        # 多仓库配置（新格式）
        "registries": [
            {
                "name": "Docker Hub",
                "registry": "docker.io",
                "registry_prefix": "",
                "username": "",
                "password": "",
                "active": True,  # 激活状态，推送时使用此仓库
            }
        ],
        "default_push": False,
        "expose_port": 8080,
        # 远程构建配置
        "use_remote": False,  # 是否使用远程 Docker
        "remote": {
            "host": "",  # 远程 Docker 主机地址（如：192.168.1.100）
            "port": 2375,  # 远程 Docker 端口（默认 2375 for HTTP, 2376 for HTTPS）
            "use_tls": False,  # 是否使用 TLS
            "cert_path": "",  # TLS 证书路径（如果使用 TLS）
            "verify_tls": True,  # 是否验证 TLS 证书
        },
    },
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "username": "admin",
        "password": "admin",
    },
    "git": {
        "username": "",  # Git 用户名
        "password": "",  # Git 密码（或 token）
        "ssh_key_path": "",  # SSH 私钥路径（可选）
        "ssh_key_password": "",  # SSH 私钥密码（可选）
    },
}


def ensure_config_exists():
    """确保配置文件存在，如果不存在则创建默认配置"""
    # 确保 data 目录存在
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    if not os.path.exists(CONFIG_FILE) or os.path.getsize(CONFIG_FILE) == 0:
        print(f"⚠️  配置文件不存在或为空，创建默认配置: {CONFIG_FILE}")
        save_config(DEFAULT_CONFIG)
        print(f"✅ 默认配置已创建")
        return True
    return False


def load_config():
    """加载配置文件"""
    # 确保配置文件存在
    ensure_config_exists()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 如果配置为空，使用默认配置
        if config is None or not isinstance(config, dict):
            print(f"⚠️  配置文件为空或格式错误，使用默认配置")
            config = DEFAULT_CONFIG.copy()
            save_config(config)
            return config

        # 兼容旧配置格式：将单一仓库配置转换为多仓库格式
        if "docker" in config:
            docker = config["docker"]
            # 检查是否为旧格式（有 registry 字段但没有 registries）
            if "registry" in docker and "registries" not in docker:
                print(f"⚠️  检测到旧配置格式，正在转换为多仓库格式...")
                old_registry = {
                    "name": "默认仓库",
                    "registry": docker.get("registry", "docker.io"),
                    "registry_prefix": docker.get("registry_prefix", ""),
                    "username": docker.get("username", ""),
                    "password": docker.get("password", ""),
                    "active": True,
                }
                docker["registries"] = [old_registry]
                # 移除旧字段
                for old_field in [
                    "registry",
                    "registry_prefix",
                    "username",
                    "password",
                ]:
                    docker.pop(old_field, None)
                print(f"✅ 配置已转换为新格式")
                save_config(config)

        # 合并默认配置（补充缺失的字段）
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in config[key]:
                        config[key][sub_key] = sub_value

        # 确保至少有一个仓库
        if "docker" in config and "registries" in config["docker"]:
            if not config["docker"]["registries"] or not isinstance(
                config["docker"]["registries"], list
            ):
                config["docker"]["registries"] = DEFAULT_CONFIG["docker"]["registries"]

        return config
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        print(f"📝 使用默认配置")
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置文件（使用临时文件确保原子性）"""
    # 确保目录存在
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    # 使用临时文件，然后原子性替换
    temp_file = f"{CONFIG_FILE}.tmp"
    try:
        # 先写入临时文件
        with open(temp_file, "w", encoding="utf-8") as f:
            yaml.dump(
                config, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )

        # 原子性替换
        if os.path.exists(CONFIG_FILE):
            os.replace(temp_file, CONFIG_FILE)
        else:
            os.rename(temp_file, CONFIG_FILE)
    except Exception as e:
        # 清理临时文件
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        print(f"❌ 保存配置文件失败: {e}")
        raise


def get_active_registry():
    """获取当前激活的仓库配置（用于推送，返回解密后的密码）"""
    config = load_config()
    registries = config.get("docker", {}).get("registries", [])

    # 查找激活的仓库
    for registry in registries:
        if registry.get("active", False):
            # 解密密码
            registry_copy = registry.copy()
            password = registry.get("password")
            if password:
                try:
                    registry_copy["password"] = decrypt_password(password)
                except (ValueError, Exception):
                    # 如果解密失败，尝试迁移旧格式
                    try:
                        try:
                            decoded = base64.b64decode(password.encode("utf-8"))
                            plaintext = decoded.decode("utf-8")
                        except Exception:
                            plaintext = password

                        # 加密后更新配置
                        encrypted = encrypt_password(plaintext)
                        registry["password"] = encrypted
                        save_config(config)
                        registry_copy["password"] = plaintext
                    except Exception as e:
                        print(f"⚠️ 解密Registry密码失败: {e}")
                        registry_copy["password"] = ""
            else:
                registry_copy["password"] = ""
            return registry_copy

    # 如果没有激活的仓库，返回第一个
    if registries:
        registry = registries[0].copy()
        password = registries[0].get("password")
        if password:
            try:
                registry["password"] = decrypt_password(password)
            except (ValueError, Exception):
                try:
                    try:
                        decoded = base64.b64decode(password.encode("utf-8"))
                        plaintext = decoded.decode("utf-8")
                    except Exception:
                        plaintext = password
                    encrypted = encrypt_password(plaintext)
                    registries[0]["password"] = encrypted
                    save_config(config)
                    registry["password"] = plaintext
                except Exception as e:
                    print(f"⚠️ 解密Registry密码失败: {e}")
                    registry["password"] = ""
        else:
            registry["password"] = ""
        return registry

    # 如果没有任何仓库，返回默认值
    return {
        "name": "Docker Hub",
        "registry": "docker.io",
        "registry_prefix": "",
        "username": "",
        "password": "",
        "active": True,
    }


def get_registry_by_name(name):
    """根据名称获取仓库配置"""
    config = load_config()
    registries = config.get("docker", {}).get("registries", [])

    for registry in registries:
        if registry.get("name") == name:
            return registry

    return None


def get_all_registries():
    """获取所有仓库配置（不返回密码，只返回 has_password 标志）"""
    config = load_config()
    registries = config.get("docker", {}).get("registries", [])

    # 移除密码字段，添加 has_password 标志
    safe_registries = []
    for registry in registries:
        safe_registry = registry.copy()
        safe_registry["has_password"] = bool(registry.get("password"))
        # 移除密码字段
        if "password" in safe_registry:
            del safe_registry["password"]
        safe_registries.append(safe_registry)

    return safe_registries


def get_registry_password(registry_name: str) -> Optional[str]:
    """获取指定仓库的解密后的密码（用于Docker推送等操作）"""
    config = load_config()
    registries = config.get("docker", {}).get("registries", [])

    for registry in registries:
        if registry.get("name") == registry_name:
            password = registry.get("password")
            if not password:
                return None

            try:
                # 尝试解密（AES加密格式）
                return decrypt_password(password)
            except (ValueError, Exception):
                # 如果解密失败，尝试迁移旧格式（明文或base64）
                try:
                    # 尝试base64解码
                    try:
                        decoded = base64.b64decode(password.encode("utf-8"))
                        plaintext = decoded.decode("utf-8")
                    except Exception:
                        # base64解码失败，当作明文处理
                        plaintext = password

                    # 加密后更新配置
                    encrypted = encrypt_password(plaintext)
                    registry["password"] = encrypted
                    save_config(config)
                    return plaintext
                except Exception as e:
                    print(f"⚠️ 解密Registry密码失败: {e}")
                    return None

    return None


def encrypt_registry_passwords(registries: list) -> list:
    """加密仓库配置中的密码"""
    encrypted_registries = []
    for registry in registries:
        encrypted_registry = registry.copy()
        password = registry.get("password")
        if password:
            # 如果密码不是加密格式，则加密它
            try:
                # 尝试解密，如果成功说明已经是加密格式
                decrypt_password(password)
                # 已经是加密格式，保持不变
                encrypted_registry["password"] = password
            except (ValueError, Exception):
                # 不是加密格式，需要加密
                # 如果密码是占位符，不更新
                if password and password not in ["******", "***", ""]:
                    encrypted_registry["password"] = encrypt_password(password)
                elif password == "":
                    encrypted_registry["password"] = ""
        encrypted_registries.append(encrypted_registry)
    return encrypted_registries


def get_git_config():
    """获取 Git 配置"""
    config = load_config()
    return config.get("git", {})


def save_git_config(git_config: dict):
    """保存 Git 配置"""
    config = load_config()
    config["git"] = git_config
    save_config(config)

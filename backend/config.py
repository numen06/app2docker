# config.py
import os
import yaml

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
    """保存配置文件"""
    # 确保目录存在
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(
                config, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        raise


def get_active_registry():
    """获取当前激活的仓库配置（用于推送）"""
    config = load_config()
    registries = config.get("docker", {}).get("registries", [])

    # 查找激活的仓库
    for registry in registries:
        if registry.get("active", False):
            return registry

    # 如果没有激活的仓库，返回第一个
    if registries:
        return registries[0]

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
    """获取所有仓库配置"""
    config = load_config()
    return config.get("docker", {}).get("registries", [])

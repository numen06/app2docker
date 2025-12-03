# config.py
import os
import yaml

# 将配置文件放在data目录中，方便Docker映射
CONFIG_FILE = "data/config.yml"

# 默认配置
DEFAULT_CONFIG = {
    "docker": {
        "registry": "docker.io",
        "registry_prefix": "",
        "default_push": False,
        "username": "",
        "password": "",
        "expose_port": 8080,
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
        
        # 合并默认配置（补充缺失的字段）
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in config[key]:
                        config[key][sub_key] = sub_value
        
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
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        raise

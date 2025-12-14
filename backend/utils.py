# utils.py
import os
import re


def get_safe_filename(filename):
    """生成安全文件名，防止路径注入"""
    name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    return name[:255]


def generate_image_name(base_name, file_input):
    """根据文件名智能生成镜像名（支持 JAR、ZIP、TAR 等）"""
    if os.sep in file_input or '/' in file_input:
        file_name = os.path.basename(file_input)
    else:
        file_name = file_input

    # 移除常见的文件扩展名
    for ext in ['.jar', '.zip', '.tar.gz', '.tgz', '.tar']:
        if file_name.endswith(ext):
            file_name = file_name[:-len(ext)]
            break
    
    return f"{base_name}/{file_name.lower()}"

def ensure_dirs():
    """确保必要目录存在（放在data目录中，方便Docker映射）"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/uploads", exist_ok=True)
    os.makedirs("data/docker_build", exist_ok=True)
    os.makedirs("data/templates", exist_ok=True)  # 用户自定义模板目录
    os.makedirs("data/exports", exist_ok=True)
    os.makedirs("data/deploy_tasks", exist_ok=True)  # 部署任务目录
    # 注意：templates/ 为内置模板目录，已打包在镜像中，无需创建
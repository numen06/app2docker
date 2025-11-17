# utils.py
import os
import re


def get_safe_filename(filename):
    """生成安全文件名，防止路径注入"""
    name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    return name[:255]


def generate_image_name(base_name,jar_input):
    """根据 JAR 文件名智能生成镜像名"""
    if os.sep in jar_input or '/' in jar_input:
        jar_name = os.path.basename(jar_input)
    else:
        jar_name = jar_input

    if jar_name.endswith('.jar'):
        jar_name = jar_name[:-4]
    return f"{base_name}/{jar_name.lower()}"

def ensure_dirs():
    """确保必要目录存在"""
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("docker_build", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("exports", exist_ok=True)
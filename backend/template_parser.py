# template_parser.py
"""Dockerfile 模板参数解析器"""
import re
from typing import Dict, List


def parse_template_variables(content: str) -> List[Dict[str, str]]:
    """
    解析 Dockerfile 模板中的变量
    
    格式支持：
    - {{VAR_NAME}} - 必填变量（构建前替换）
    - {{VAR_NAME:default_value}} - 带默认值的变量（构建前替换）
    - ${VAR_NAME} - Docker ARG 变量（构建时由 Docker 处理，不解析）
    
    返回：
    [
        {
            "name": "EXPOSE_PORT",
            "default": "8080",
            "required": False,
            "description": "",
            "type": "template"  # template 或 docker_arg
        },
        ...
    ]
    """
    variables = {}
    
    # 1. 匹配 {{VAR_NAME}} 或 {{VAR_NAME:default_value}} - 我们的模板变量
    template_pattern = r'\{\{([A-Z_][A-Z0-9_]*?)(?::([^}]+))?\}\}'
    for match in re.finditer(template_pattern, content):
        var_name = match.group(1)
        default_value = match.group(2) or ""
        
        if var_name not in variables:
            variables[var_name] = {
                "name": var_name,
                "default": default_value.strip(),
                "required": not bool(default_value),
                "description": _get_var_description(var_name),
                "type": "template"
            }
    
    # 注意：${VAR} 格式的变量是 Docker 原生 ARG，不需要解析
    # 它们应该在 Dockerfile 中使用 ARG 声明，由 Docker 在构建时处理
    
    return list(variables.values())


def _get_var_description(var_name: str) -> str:
    """获取变量的中文描述"""
    descriptions = {
        "EXPOSE_PORT": "暴露端口",
        "APP_NAME": "应用名称",
        "APP_PORT": "应用端口",
        "JAVA_OPTS": "Java 启动参数",
        "JAVA_VERSION": "Java 版本",
        "NODE_ENV": "Node.js 运行环境",
        "NODE_VERSION": "Node.js 版本",
        "NGINX_VERSION": "Nginx 版本",
        "WORKDIR": "工作目录",
        "BASE_IMAGE": "基础镜像",
        "VERSION": "应用版本号",
        "MAINTAINER": "维护者",
        "BUILD_ARGS": "构建参数",
        "SERVER_NAME": "服务器名称",
        "GZIP_MIN_LENGTH": "Gzip 最小压缩大小",
        "CACHE_DURATION": "缓存时长",
        "JAR_FILE": "JAR 文件名",
        "APP_FILE": "应用文件名",
    }
    return descriptions.get(var_name, var_name.replace("_", " ").title())


def replace_template_variables(content: str, variables: Dict[str, str]) -> str:
    """
    替换模板中的变量
    
    Args:
        content: Dockerfile 模板内容
        variables: 变量值字典 {"VAR_NAME": "value", ...}
    
    Returns:
        替换后的内容
    """
    result = content
    
    # 替换所有变量
    for var_name, value in variables.items():
        # 匹配 {{VAR_NAME}} 或 {{VAR_NAME:default}}
        pattern = r'\{\{' + re.escape(var_name) + r'(?::[^}]+)?\}\}'
        result = re.sub(pattern, str(value), result)
    
    # 检查是否还有未替换的必填变量
    remaining = re.findall(r'\{\{([A-Z_][A-Z0-9_]*?)\}\}', result)
    if remaining:
        raise ValueError(f"缺少必填参数: {', '.join(remaining)}")
    
    # 替换带默认值的变量（使用默认值）
    def replace_with_default(match):
        var_name = match.group(1)
        default_value = match.group(2) or ""
        return default_value
    
    result = re.sub(r'\{\{[A-Z_][A-Z0-9_]*?:([^}]+)\}\}', replace_with_default, result)
    
    return result


# 示例用法
if __name__ == "__main__":
    # 测试模板
    template = """
FROM openjdk:17-jre-slim
WORKDIR /app
COPY app.jar /app/app.jar
EXPOSE {{EXPOSE_PORT:8080}}
ENV JAVA_OPTS="{{JAVA_OPTS:-Xmx512m}}"
CMD ["java", {{JAVA_OPTS}}, "-jar", "app.jar"]
"""
    
    # 解析变量
    variables = parse_template_variables(template)
    print("解析到的变量:")
    for var in variables:
        print(f"  - {var['name']}: {var['default']} (必填: {var['required']})")
    
    # 替换变量
    values = {
        "EXPOSE_PORT": "9090",
        "JAVA_OPTS": "-Xmx1024m -Xms512m"
    }
    result = replace_template_variables(template, values)
    print("\n替换后的内容:")
    print(result)


"""
项目类型统一字典定义
前端和后端都使用此字典，确保一致性
"""

# 项目类型字典列表
PROJECT_TYPES = [
    {
        'value': 'jar',
        'label': 'Java 应用（JAR）',
        'icon': 'fab fa-java',
        'badgeClass': 'bg-danger',
        'order': 1
    },
    {
        'value': 'nodejs',
        'label': 'Node.js 应用',
        'icon': 'fab fa-node-js',
        'badgeClass': 'bg-success',
        'order': 2
    },
    {
        'value': 'python',
        'label': 'Python 应用',
        'icon': 'fab fa-python',
        'badgeClass': 'bg-info',
        'order': 3
    },
    {
        'value': 'go',
        'label': 'Go 应用',
        'icon': 'fas fa-code',
        'badgeClass': 'bg-primary',
        'order': 4
    },
    {
        'value': 'web',
        'label': '静态网站',
        'icon': 'fas fa-globe',
        'badgeClass': 'bg-secondary',
        'order': 5
    },
]


def get_project_types():
    """
    获取项目类型列表，按order排序
    
    Returns:
        list: 排序后的项目类型列表
    """
    return sorted(PROJECT_TYPES, key=lambda x: x['order'])


def get_project_type_dict():
    """
    获取项目类型字典，以value为key
    
    Returns:
        dict: 以value为key的项目类型字典
    """
    return {pt['value']: pt for pt in PROJECT_TYPES}


def get_project_type_info(project_type):
    """
    根据项目类型值获取项目类型信息
    
    Args:
        project_type (str): 项目类型值
        
    Returns:
        dict: 项目类型信息，如果不存在则返回None
    """
    return get_project_type_dict().get(project_type)


def get_project_type_label(project_type):
    """
    获取项目类型的标签
    
    Args:
        project_type (str): 项目类型值
        
    Returns:
        str: 项目类型标签，如果不存在则返回原值
    """
    info = get_project_type_info(project_type)
    return info['label'] if info else project_type


def is_valid_project_type(project_type):
    """
    验证项目类型是否有效
    
    Args:
        project_type (str): 项目类型值
        
    Returns:
        bool: 是否为有效的项目类型
    """
    return project_type in get_project_type_dict()


def get_project_type_values():
    """
    获取所有项目类型的值列表
    
    Returns:
        list: 项目类型值列表
    """
    return [pt['value'] for pt in PROJECT_TYPES]


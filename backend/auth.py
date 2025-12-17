"""
认证模块 - 基于 JWT 的 API 认证
"""
import jwt
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import List, Set, Optional

# 配置
TOKEN_EXPIRE_HOURS = 24

# SECRET_KEY 文件路径
SECRET_KEY_FILE = "data/secret_key.txt"


def get_or_create_secret_key() -> str:
    """获取或创建 SECRET_KEY（持久化到文件，确保重启后密钥一致）"""
    # 确保目录存在
    os.makedirs(os.path.dirname(SECRET_KEY_FILE), exist_ok=True)
    
    # 如果文件存在，读取密钥
    if os.path.exists(SECRET_KEY_FILE):
        try:
            with open(SECRET_KEY_FILE, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key and len(key) >= 32:  # 确保密钥长度足够
                    return key
        except Exception as e:
            print(f"⚠️ 读取 SECRET_KEY 失败: {e}，将生成新密钥")
    
    # 生成新密钥并保存
    key = secrets.token_hex(32)
    try:
        with open(SECRET_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(key)
        print(f"✅ 已生成并保存新的 SECRET_KEY")
    except Exception as e:
        print(f"⚠️ 保存 SECRET_KEY 失败: {e}，使用临时密钥（重启后会失效）")
    
    return key


# 初始化 SECRET_KEY（从文件加载或生成）
SECRET_KEY = get_or_create_secret_key()

# 默认用户（应该从配置文件读取或数据库）
DEFAULT_USERS = {
    "admin": hashlib.sha256("admin".encode()).hexdigest()  # 默认密码：admin
}


def hash_password(password: str) -> str:
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed


def create_token(username: str) -> str:
    """创建 JWT token"""
    payload = {
        'username': username,
        'exp': datetime.now() + timedelta(hours=TOKEN_EXPIRE_HOURS),
        'iat': datetime.now()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def verify_token(token: str) -> dict:
    """验证 JWT token"""
    try:
        # 使用 options 参数，不验证 iat（issued at）时间，避免时间不匹配问题
        # JWT 库默认使用 UTC 时间，但我们的系统使用本地时间
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'], options={'verify_iat': False})
        return {'valid': True, 'username': payload['username']}
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token 已过期'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Token 无效'}


def authenticate(username: str, password: str) -> dict:
    """用户认证"""
    # 从数据库获取用户
    user = get_user_from_db(username)
    
    if not user:
        # 向后兼容：尝试从配置文件加载
        users = load_users()
        if username not in users:
            return {'success': False, 'error': '用户名或密码错误'}
        
        if not verify_password(password, users[username]):
            return {'success': False, 'error': '用户名或密码错误'}
        
        # 检查是否使用默认密码
        default_password_hash = hash_password("admin")
        is_default_password = verify_password("admin", users[username])
    else:
        # 检查用户是否启用
        if not user.enabled:
            return {'success': False, 'error': '用户已被禁用'}
        
        # 验证密码
        if not verify_password(password, user.password_hash):
            return {'success': False, 'error': '用户名或密码错误'}
        
        # 检查是否使用默认密码
        default_password_hash = hash_password("admin")
        is_default_password = verify_password("admin", user.password_hash)
    
    token = create_token(username)
    return {
        'success': True,
        'token': token,
        'username': username,
        'expires_in': TOKEN_EXPIRE_HOURS * 3600,
        'require_password_change': is_default_password  # 需要修改密码
    }


def load_users():
    """从数据库加载用户（兼容旧代码，返回字典格式）"""
    try:
        from backend.database import get_db_session
        from backend.models import User
        
        db = get_db_session()
        try:
            users = {}
            db_users = db.query(User).filter(User.enabled == True).all()
            for user in db_users:
                users[user.username] = user.password_hash
            
            # 如果数据库中没有用户，尝试从配置文件加载（向后兼容）
            if not users:
                from backend.config import load_config
                config = load_config()
                users = config.get('users', {})
                
                # 如果配置中也没有用户，使用默认用户
                if not users:
                    users = DEFAULT_USERS
            
            return users
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ 从数据库加载用户失败: {e}，尝试从配置文件加载")
        try:
            from backend.config import load_config
            config = load_config()
            users = config.get('users', {})
            if not users:
                users = DEFAULT_USERS
            return users
        except Exception:
            return DEFAULT_USERS


def get_user_from_db(username: str):
    """从数据库获取用户对象"""
    try:
        from backend.database import get_db_session
        from backend.models import User
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.username == username).first()
            return user
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ 从数据库获取用户失败: {e}")
        return None


def get_user_permissions(username: str) -> Set[str]:
    """获取用户的所有权限代码集合"""
    try:
        from backend.database import get_db_session
        from backend.models import User, UserRole, RolePermission
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.username == username, User.enabled == True).first()
            if not user:
                return set()
            
            # 获取用户的所有角色
            user_roles = db.query(UserRole).filter(UserRole.user_id == user.user_id).all()
            role_ids = [ur.role_id for ur in user_roles]
            
            if not role_ids:
                return set()
            
            # 获取角色对应的所有权限
            role_permissions = db.query(RolePermission).filter(
                RolePermission.role_id.in_(role_ids)
            ).all()
            
            permission_ids = [rp.permission_id for rp in role_permissions]
            
            if not permission_ids:
                return set()
            
            # 获取权限代码
            from backend.models import Permission
            permissions = db.query(Permission).filter(
                Permission.permission_id.in_(permission_ids)
            ).all()
            
            return {perm.code for perm in permissions}
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ 获取用户权限失败: {e}")
        return set()


def check_permission(username: str, permission_code: str) -> bool:
    """检查用户是否有指定权限"""
    user_permissions = get_user_permissions(username)
    return permission_code in user_permissions


def check_role(username: str, role_name: str) -> bool:
    """检查用户是否有指定角色"""
    try:
        from backend.database import get_db_session
        from backend.models import User, UserRole, Role
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.username == username, User.enabled == True).first()
            if not user:
                return False
            
            # 获取用户的所有角色
            user_roles = db.query(UserRole).join(Role).filter(
                UserRole.user_id == user.user_id,
                Role.name == role_name
            ).first()
            
            return user_roles is not None
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ 检查用户角色失败: {e}")
        return False


def require_permission(permission_code: str):
    """装饰器：要求指定权限"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs或args中获取request对象
            request = None
            for arg in args:
                if hasattr(arg, 'headers'):
                    request = arg
                    break
            if not request:
                for key, value in kwargs.items():
                    if hasattr(value, 'headers'):
                        request = value
                        break
            
            if not request:
                from fastapi import HTTPException
                raise HTTPException(status_code=500, detail="无法获取请求对象")
            
            # 获取当前用户名
            from backend.routes import require_auth
            username = require_auth(request)
            
            # 检查权限
            if not check_permission(username, permission_code):
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail=f"权限不足：需要 {permission_code} 权限")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role_name: str):
    """装饰器：要求指定角色"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs或args中获取request对象
            request = None
            for arg in args:
                if hasattr(arg, 'headers'):
                    request = arg
                    break
            if not request:
                for key, value in kwargs.items():
                    if hasattr(value, 'headers'):
                        request = value
                        break
            
            if not request:
                from fastapi import HTTPException
                raise HTTPException(status_code=500, detail="无法获取请求对象")
            
            # 获取当前用户名
            from backend.routes import require_auth
            username = require_auth(request)
            
            # 检查角色
            if not check_role(username, role_name):
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail=f"权限不足：需要 {role_name} 角色")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_auth(handler_method):
    """装饰器：要求认证"""
    @wraps(handler_method)
    def wrapper(self, *args, **kwargs):
        # 从请求头获取 token
        auth_header = self.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Unauthorized"}')
            return
        
        token = auth_header[7:]  # 移除 "Bearer " 前缀
        result = verify_token(token)
        
        if not result['valid']:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_msg = result.get('error', 'Unauthorized')
            self.wfile.write(f'{{"error": "{error_msg}"}}'.encode())
            return
        
        # Token 有效，继续处理请求
        self.current_user = result['username']
        return handler_method(self, *args, **kwargs)
    
    return wrapper


"""
认证模块 - 基于 JWT 的 API 认证
"""
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

# 配置
SECRET_KEY = secrets.token_hex(32)  # 生成随机密钥（生产环境应该从配置文件读取）
TOKEN_EXPIRE_HOURS = 24

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
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return {'valid': True, 'username': payload['username']}
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token 已过期'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Token 无效'}


def authenticate(username: str, password: str) -> dict:
    """用户认证"""
    # 从配置或数据库获取用户（这里简化为硬编码）
    users = load_users()
    
    if username not in users:
        return {'success': False, 'error': '用户名或密码错误'}
    
    if not verify_password(password, users[username]):
        return {'success': False, 'error': '用户名或密码错误'}
    
    token = create_token(username)
    return {
        'success': True,
        'token': token,
        'username': username,
        'expires_in': TOKEN_EXPIRE_HOURS * 3600
    }


def load_users():
    """从配置加载用户（简化版）"""
    try:
        from backend.config import load_config
        config = load_config()
        users = config.get('users', {})
        
        # 如果配置中没有用户，使用默认用户
        if not users:
            users = DEFAULT_USERS
        
        return users
    except Exception:
        return DEFAULT_USERS


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


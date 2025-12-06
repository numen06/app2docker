"""
认证模块 - 基于 JWT 的 API 认证
"""
import jwt
import hashlib
import secrets
import os
from datetime import datetime, timedelta
from functools import wraps

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
    
    # 检查是否使用默认密码
    default_password_hash = hash_password("admin")
    is_default_password = verify_password("admin", users[username])
    
    token = create_token(username)
    return {
        'success': True,
        'token': token,
        'username': username,
        'expires_in': TOKEN_EXPIRE_HOURS * 3600,
        'require_password_change': is_default_password  # 需要修改密码
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


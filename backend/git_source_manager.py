# backend/git_source_manager.py
"""Git 数据源管理器 - 用于管理验证过的 Git 仓库（基于数据库）"""
import base64
import uuid
import threading
from datetime import datetime
from typing import Optional, Dict, List
from backend.database import get_db_session, init_db
from backend.models import GitSource

# 确保数据库已初始化
try:
    init_db()
except:
    pass


class GitSourceManager:
    """Git 数据源管理器（基于数据库）"""
    
    def __init__(self):
        self.lock = threading.RLock()
    
    def _to_dict(self, source: GitSource, include_password: bool = False) -> Optional[Dict]:
        """将数据库模型转换为字典"""
        if not source:
            return None
        
        result = {
            "source_id": source.source_id,
            "name": source.name,
            "description": source.description,
            "git_url": source.git_url,
            "branches": source.branches or [],
            "tags": source.tags or [],
            "default_branch": source.default_branch,
            "username": source.username,
            "dockerfiles": source.dockerfiles or {},
            "created_at": source.created_at.isoformat() if source.created_at else None,
            "updated_at": source.updated_at.isoformat() if source.updated_at else None,
        }
        
        if include_password:
            result["password"] = source.password
        else:
            result["has_password"] = bool(source.password)
        
        return result
    
    def create_source(
        self,
        name: str,
        git_url: str,
        description: str = "",
        branches: List[str] = None,
        tags: List[str] = None,
        default_branch: str = None,
        username: str = None,
        password: str = None,
        dockerfiles: Dict[str, str] = None,
    ) -> str:
        """创建 Git 数据源"""
        source_id = str(uuid.uuid4())
        
        # 加密密码（使用 base64 编码，仅用于基本保护）
        encrypted_password = None
        if password:
            encrypted_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
        
        db = get_db_session()
        try:
            source = GitSource(
                source_id=source_id,
                name=name,
                description=description,
                git_url=git_url,
                branches=branches or [],
                tags=tags or [],
                default_branch=default_branch,
                username=username or "",
                password=encrypted_password,
                dockerfiles=dockerfiles or {},
            )
            
            db.add(source)
            db.commit()
            return source_id
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_source(self, source_id: str, include_password: bool = False) -> Optional[Dict]:
        """获取数据源配置"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
            return self._to_dict(source, include_password)
        finally:
            db.close()
    
    def list_sources(self, include_password: bool = False) -> List[Dict]:
        """列出所有数据源配置"""
        db = get_db_session()
        try:
            sources = db.query(GitSource).order_by(GitSource.created_at.desc()).all()
            return [self._to_dict(s, include_password) for s in sources]
        finally:
            db.close()
    
    def update_source(
        self,
        source_id: str,
        name: str = None,
        git_url: str = None,
        description: str = None,
        branches: List[str] = None,
        tags: List[str] = None,
        default_branch: str = None,
        username: str = None,
        password: str = None,
    ) -> bool:
        """更新数据源配置"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
            if not source:
                return False
            
            if name is not None:
                source.name = name
            if git_url is not None:
                source.git_url = git_url
            if description is not None:
                source.description = description
            if branches is not None:
                source.branches = branches
            if tags is not None:
                source.tags = tags
            if default_branch is not None:
                source.default_branch = default_branch
            if username is not None:
                source.username = username
            if password is not None:
                if password:
                    source.password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
                else:
                    source.password = None
            
            if source.dockerfiles is None:
                source.dockerfiles = {}
            
            source.updated_at = datetime.now()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def delete_source(self, source_id: str) -> bool:
        """删除数据源配置"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
            if not source:
                return False
            
            db.delete(source)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_source_by_url(self, git_url: str) -> Optional[Dict]:
        """通过 Git URL 获取数据源配置"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.git_url == git_url).first()
            return self._to_dict(source)
        finally:
            db.close()
    
    def get_decrypted_password(self, source_id: str) -> Optional[str]:
        """获取解密后的密码"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
            if not source or not source.password:
                return None
            try:
                return base64.b64decode(source.password).decode('utf-8')
            except Exception:
                return None
        finally:
            db.close()
    
    def get_auth_config(self, source_id: str) -> Dict[str, str]:
        """获取数据源的认证配置"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
            if not source:
                return {}
            
            auth_config = {}
            if source.username:
                auth_config["username"] = source.username
            
            password = self.get_decrypted_password(source_id)
            if password:
                auth_config["password"] = password
            
            return auth_config
        finally:
            db.close()
    
    def update_dockerfile(self, source_id: str, dockerfile_path: str, content: str) -> bool:
        """更新或创建 Dockerfile"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
            if not source:
                return False
            
            if not source.dockerfiles:
                source.dockerfiles = {}
            
            source.dockerfiles[dockerfile_path] = content
            source.updated_at = datetime.now()
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def delete_dockerfile(self, source_id: str, dockerfile_path: str) -> bool:
        """删除 Dockerfile"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
            if not source or not source.dockerfiles:
                return False
            
            if dockerfile_path in source.dockerfiles:
                del source.dockerfiles[dockerfile_path]
                source.updated_at = datetime.now()
                db.commit()
                return True
            
            return False
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_dockerfile(self, source_id: str, dockerfile_path: str) -> Optional[str]:
        """获取 Dockerfile 内容"""
        db = get_db_session()
        try:
            source = db.query(GitSource).filter(GitSource.source_id == source_id).first()
            if not source or not source.dockerfiles:
                return None
            
            return source.dockerfiles.get(dockerfile_path)
        finally:
            db.close()

# backend/git_source_manager.py
"""Git 数据源管理器 - 用于管理验证过的 Git 仓库"""
import json
import os
import uuid
import threading
import base64
from datetime import datetime
from typing import Optional, Dict, List

# 数据源配置文件
GIT_SOURCES_FILE = "data/git_sources.json"


class GitSourceManager:
    """Git 数据源管理器"""
    
    def __init__(self):
        self.lock = threading.RLock()
        self.sources = {}
        self._load_sources()
    
    def _load_sources(self):
        """从文件加载数据源配置"""
        if not os.path.exists(GIT_SOURCES_FILE):
            return
        
        try:
            with open(GIT_SOURCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.sources = data.get('sources', {})
                print(f"✅ 加载了 {len(self.sources)} 个 Git 数据源")
        except Exception as e:
            print(f"⚠️ 加载 Git 数据源配置失败: {e}")
            self.sources = {}
    
    def _save_sources(self):
        """保存数据源配置到文件"""
        try:
            os.makedirs(os.path.dirname(GIT_SOURCES_FILE), exist_ok=True)
            with open(GIT_SOURCES_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'sources': self.sources,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存 Git 数据源配置失败: {e}")
            raise
    
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
    ) -> str:
        """
        创建 Git 数据源
        
        Args:
            name: 数据源名称
            git_url: Git 仓库地址
            description: 描述
            branches: 分支列表
            tags: 标签列表
            default_branch: 默认分支
            username: Git 用户名（可选）
            password: Git 密码或 token（可选，将加密存储）
        
        Returns:
            source_id: 数据源 ID
        """
        source_id = str(uuid.uuid4())
        
        # 加密密码（使用 base64 编码，仅用于基本保护）
        encrypted_password = None
        if password:
            encrypted_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')
        
        source = {
            "source_id": source_id,
            "name": name,
            "description": description,
            "git_url": git_url,
            "branches": branches or [],
            "tags": tags or [],
            "default_branch": default_branch,
            "username": username or "",  # Git 用户名
            "password": encrypted_password,  # 加密后的密码
            # 元数据
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        with self.lock:
            self.sources[source_id] = source
            self._save_sources()
        
        return source_id
    
    def get_source(self, source_id: str, include_password: bool = False) -> Optional[Dict]:
        """获取数据源配置"""
        with self.lock:
            source = self.sources.get(source_id)
            if not source:
                return None
            
            # 如果不包含密码，移除密码字段
            if not include_password and source:
                source = source.copy()
                if "password" in source:
                    source["has_password"] = bool(source["password"])
                    del source["password"]
            
            return source
    
    def list_sources(self, include_password: bool = False) -> List[Dict]:
        """
        列出所有数据源配置
        
        Args:
            include_password: 是否包含密码（用于内部使用，前端不应包含密码）
        
        Returns:
            数据源列表
        """
        with self.lock:
            sources = list(self.sources.values())
            # 按创建时间倒序排列
            sources.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            # 如果不包含密码，移除密码字段
            if not include_password:
                for source in sources:
                    if "password" in source:
                        # 只返回是否有密码的标识，不返回实际密码
                        source["has_password"] = bool(source["password"])
                        del source["password"]
            
            return sources
    
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
        """
        更新数据源配置
        
        Returns:
            True 表示更新成功，False 表示数据源不存在
        """
        with self.lock:
            if source_id not in self.sources:
                return False
            
            source = self.sources[source_id]
            
            # 更新字段
            if name is not None:
                source["name"] = name
            if git_url is not None:
                source["git_url"] = git_url
            if description is not None:
                source["description"] = description
            if branches is not None:
                source["branches"] = branches
            if tags is not None:
                source["tags"] = tags
            if default_branch is not None:
                source["default_branch"] = default_branch
            if username is not None:
                source["username"] = username
            if password is not None:
                # 如果提供了新密码，加密存储
                if password:
                    source["password"] = base64.b64encode(password.encode('utf-8')).decode('utf-8')
                else:
                    source["password"] = None
            
            # 更新时间
            source["updated_at"] = datetime.now().isoformat()
            
            self._save_sources()
            return True
    
    def delete_source(self, source_id: str) -> bool:
        """
        删除数据源配置
        
        Returns:
            True 表示删除成功，False 表示数据源不存在
        """
        with self.lock:
            if source_id not in self.sources:
                return False
            
            del self.sources[source_id]
            self._save_sources()
            return True
    
    def get_source_by_url(self, git_url: str) -> Optional[Dict]:
        """通过 Git URL 获取数据源配置"""
        with self.lock:
            for source in self.sources.values():
                if source.get("git_url") == git_url:
                    return source
            return None
    
    def get_decrypted_password(self, source_id: str) -> Optional[str]:
        """获取解密后的密码"""
        with self.lock:
            source = self.sources.get(source_id)
            if not source or not source.get("password"):
                return None
            try:
                return base64.b64decode(source["password"]).decode('utf-8')
            except Exception:
                return None
    
    def get_auth_config(self, source_id: str) -> Dict[str, str]:
        """获取数据源的认证配置"""
        with self.lock:
            source = self.sources.get(source_id)
            if not source:
                return {}
            
            auth_config = {}
            if source.get("username"):
                auth_config["username"] = source["username"]
            
            password = self.get_decrypted_password(source_id)
            if password:
                auth_config["password"] = password
            
            return auth_config


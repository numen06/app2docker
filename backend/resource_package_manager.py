# backend/resource_package_manager.py
"""
资源包管理模块（基于数据库）
用于管理不能公开的配置信息，在构建时一同打包到镜像中
"""
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from backend.database import get_db_session, init_db
from backend.models import ResourcePackage

# 资源包存储目录
RESOURCE_PACKAGE_DIR = "data/resource_packages"

# 确保数据库已初始化
try:
    init_db()
except:
    pass


class ResourcePackageManager:
    """资源包管理器（基于数据库）"""
    
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            import threading
            cls._instance = super().__new__(cls)
            cls._lock = threading.Lock()
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化资源包管理器"""
        os.makedirs(RESOURCE_PACKAGE_DIR, exist_ok=True)
    
    def _to_dict(self, package: ResourcePackage) -> Optional[Dict]:
        """将数据库模型转换为字典"""
        if not package:
            return None
        
        return {
            "package_id": package.package_id,
            "name": package.name,
            "description": package.description,
            "filename": package.filename,
            "size": package.size,
            "extracted": package.extracted,
            "team_id": getattr(package, "team_id", None),
            "created_by": getattr(package, "created_by", None),
            "created_at": package.created_at.isoformat() if package.created_at else None,
            "updated_at": package.updated_at.isoformat() if package.updated_at else None,
        }
    
    def upload_package(
        self,
        file_data: bytes,
        filename: str,
        description: str = "",
        extract: bool = True,
        team_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Dict:
        """上传资源包"""
        with self._lock:
            package_id = str(uuid.uuid4())
            
            package_dir = os.path.join(RESOURCE_PACKAGE_DIR, package_id)
            os.makedirs(package_dir, exist_ok=True)
            
            original_file_path = os.path.join(package_dir, filename)
            with open(original_file_path, 'wb') as f:
                f.write(file_data)
            
            extracted_path = None
            if extract:
                filename_lower = filename.lower()
                if filename_lower.endswith(('.zip', '.tar.gz', '.tgz', '.tar')):
                    extracted_path = os.path.join(package_dir, "extracted")
                    os.makedirs(extracted_path, exist_ok=True)
                    
                    try:
                        if filename_lower.endswith('.zip'):
                            import zipfile
                            with zipfile.ZipFile(original_file_path, 'r') as zip_ref:
                                zip_ref.extractall(extracted_path)
                        elif filename_lower.endswith(('.tar.gz', '.tgz')):
                            import tarfile
                            with tarfile.open(original_file_path, 'r:gz') as tar_ref:
                                tar_ref.extractall(extracted_path)
                        elif filename_lower.endswith('.tar'):
                            import tarfile
                            with tarfile.open(original_file_path, 'r') as tar_ref:
                                tar_ref.extractall(extracted_path)
                    except Exception as e:
                        print(f"⚠️ 解压资源包失败: {e}")
                        extract = False
                else:
                    extract = False
            
            file_size = len(file_data)
            
            db = get_db_session()
            try:
                package = ResourcePackage(
                    package_id=package_id,
                    name=filename,
                    description=description,
                    filename=filename,
                    size=file_size,
                    extracted=extract and extracted_path is not None,
                    team_id=team_id,
                    created_by=created_by,
                )
                
                db.add(package)
                db.commit()
                
                print(f"✅ 资源包上传成功: {package_id} ({filename})")
                return self._to_dict(package)
            except Exception as e:
                db.rollback()
                # 如果数据库保存失败，删除已创建的文件
                if os.path.exists(package_dir):
                    shutil.rmtree(package_dir)
                raise
            finally:
                db.close()
    
    def list_packages(self, team_id: Optional[str] = None) -> List[Dict]:
        """列出所有资源包（可选按团队过滤）"""
        db = get_db_session()
        try:
            query = db.query(ResourcePackage)
            if team_id:
                query = query.filter(ResourcePackage.team_id == team_id)
            packages = query.order_by(ResourcePackage.created_at.desc()).all()
            result = []
            packages_to_delete = []
            
            for package in packages:
                # 检查文件是否存在
                package_dir = os.path.join(RESOURCE_PACKAGE_DIR, package.package_id)
                if os.path.exists(package_dir):
                    result.append(self._to_dict(package))
                else:
                    # 文件不存在，标记为删除
                    print(f"⚠️ 资源包文件不存在，清理元数据: {package.package_id}")
                    packages_to_delete.append(package)
            
            # 批量删除不存在的资源包
            if packages_to_delete:
                for package in packages_to_delete:
                    db.delete(package)
                db.commit()
            
            return result
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_package(self, package_id: str) -> Optional[Dict]:
        """获取资源包信息"""
        db = get_db_session()
        try:
            package = db.query(ResourcePackage).filter(ResourcePackage.package_id == package_id).first()
            return self._to_dict(package)
        finally:
            db.close()
    
    def delete_package(self, package_id: str) -> bool:
        """删除资源包"""
        with self._lock:
            db = get_db_session()
            try:
                package = db.query(ResourcePackage).filter(ResourcePackage.package_id == package_id).first()
                if not package:
                    return False
                
                # 删除文件目录
                package_dir = os.path.join(RESOURCE_PACKAGE_DIR, package_id)
                if os.path.exists(package_dir):
                    try:
                        shutil.rmtree(package_dir)
                    except Exception as e:
                        print(f"❌ 删除资源包目录失败: {e}")
                        return False
                
                # 从数据库中删除
                db.delete(package)
                db.commit()
                
                print(f"✅ 资源包已删除: {package_id}")
                return True
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()
    
    def copy_packages_to_build_context(
        self,
        package_configs: List[Dict],
        build_context: str
    ) -> List[str]:
        """将资源包复制到构建上下文"""
        if not package_configs:
            return []
        
        db = get_db_session()
        try:
            copied_packages = []
            
            for config in package_configs:
                package_id = config.get('package_id')
                target_path_rel = config.get('target_path') or config.get('target_dir', 'resources')
                
                if not package_id:
                    continue
                
                package = db.query(ResourcePackage).filter(ResourcePackage.package_id == package_id).first()
                if not package:
                    print(f"⚠️ 资源包不存在: {package_id}")
                    continue
                
                package_dir = os.path.join(RESOURCE_PACKAGE_DIR, package_id)
                if not os.path.exists(package_dir):
                    print(f"⚠️ 资源包目录不存在: {package_dir}")
                    continue
                
                try:
                    target_path_rel = target_path_rel.replace('\\', '/')
                    path_parts = target_path_rel.split('/')
                    last_part = path_parts[-1]
                    has_extension = '.' in last_part and not last_part.startswith('.')
                    
                    if len(path_parts) == 1 and has_extension:
                        target_dir_rel = '.'
                        target_filename = last_part
                    elif len(path_parts) > 1 and has_extension:
                        target_dir_rel = '/'.join(path_parts[:-1])
                        target_filename = last_part
                    else:
                        target_dir_rel = target_path_rel
                        target_filename = None
                    
                    if target_dir_rel == '.':
                        target_dir_abs = build_context
                    else:
                        target_dir_abs = os.path.join(build_context, target_dir_rel)
                    os.makedirs(target_dir_abs, exist_ok=True)
                    
                    if package.extracted:
                        extracted_path = os.path.join(package_dir, "extracted")
                        if os.path.exists(extracted_path):
                            for item in os.listdir(extracted_path):
                                src = os.path.join(extracted_path, item)
                                if target_filename and os.path.isfile(src):
                                    dst = os.path.join(target_dir_abs, target_filename)
                                    shutil.copy2(src, dst)
                                    break
                                else:
                                    dst = os.path.join(target_dir_abs, item)
                                    if os.path.isdir(src):
                                        shutil.copytree(src, dst, dirs_exist_ok=True)
                                    else:
                                        shutil.copy2(src, dst)
                        else:
                            original_file = os.path.join(package_dir, package.filename)
                            if os.path.exists(original_file):
                                dst_filename = target_filename or package.filename
                                shutil.copy2(original_file, os.path.join(target_dir_abs, dst_filename))
                    else:
                        original_file = os.path.join(package_dir, package.filename)
                        if os.path.exists(original_file):
                            dst_filename = target_filename or package.filename
                            shutil.copy2(original_file, os.path.join(target_dir_abs, dst_filename))
                    
                    copied_packages.append(package_id)
                    final_path = os.path.join(target_dir_rel, dst_filename or package.filename).replace('\\', '/')
                    if final_path.startswith('./'):
                        final_path = final_path[2:]
                    print(f"✅ 资源包已复制到构建上下文: {package_id} ({package.filename}) -> {final_path}")
                except Exception as e:
                    print(f"❌ 复制资源包失败 {package_id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            return copied_packages
        finally:
            db.close()

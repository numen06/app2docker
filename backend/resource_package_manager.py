# resource_package_manager.py
"""
资源包管理模块
用于管理不能公开的配置信息，在构建时一同打包到镜像中
"""
import os
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 资源包存储目录
RESOURCE_PACKAGE_DIR = "data/resource_packages"
# 资源包元数据文件
METADATA_FILE = os.path.join(RESOURCE_PACKAGE_DIR, "metadata.json")


class ResourcePackageManager:
    """资源包管理器"""
    
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
        # 确保目录存在
        os.makedirs(RESOURCE_PACKAGE_DIR, exist_ok=True)
        # 加载元数据
        self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        """加载资源包元数据"""
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 加载资源包元数据失败: {e}")
                return {}
        return {}
    
    def _save_metadata(self, metadata: Dict):
        """保存资源包元数据"""
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存资源包元数据失败: {e}")
            raise
    
    def upload_package(
        self,
        file_data: bytes,
        filename: str,
        description: str = "",
        extract: bool = True
    ) -> Dict:
        """
        上传资源包
        
        Args:
            file_data: 文件数据
            filename: 原始文件名
            description: 描述信息
            extract: 是否解压（如果是压缩包）
        
        Returns:
            资源包信息字典
        """
        with self._lock:
            # 生成唯一ID
            package_id = str(uuid.uuid4())
            
            # 创建资源包目录
            package_dir = os.path.join(RESOURCE_PACKAGE_DIR, package_id)
            os.makedirs(package_dir, exist_ok=True)
            
            # 保存原始文件
            original_file_path = os.path.join(package_dir, filename)
            with open(original_file_path, 'wb') as f:
                f.write(file_data)
            
            # 如果启用解压且是压缩包，则解压
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
                        # 解压失败不影响，继续使用原始文件
                else:
                    # 不是压缩包格式，即使选择了解压也不处理
                    extract = False
            
            # 计算文件大小
            file_size = len(file_data)
            
            # 创建资源包信息
            package_info = {
                "package_id": package_id,
                "name": filename,
                "description": description,
                "filename": filename,
                "size": file_size,
                "extracted": extract and extracted_path is not None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            
            # 保存元数据
            metadata = self._load_metadata()
            metadata[package_id] = package_info
            self._save_metadata(metadata)
            
            print(f"✅ 资源包上传成功: {package_id} ({filename})")
            return package_info
    
    def list_packages(self) -> List[Dict]:
        """列出所有资源包"""
        metadata = self._load_metadata()
        packages = []
        
        for package_id, package_info in metadata.items():
            # 检查文件是否存在
            package_dir = os.path.join(RESOURCE_PACKAGE_DIR, package_id)
            if os.path.exists(package_dir):
                packages.append(package_info)
            else:
                # 文件不存在，从元数据中移除
                print(f"⚠️ 资源包文件不存在，清理元数据: {package_id}")
                del metadata[package_id]
                self._save_metadata(metadata)
        
        # 按创建时间倒序排列
        packages.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return packages
    
    def get_package(self, package_id: str) -> Optional[Dict]:
        """获取资源包信息"""
        metadata = self._load_metadata()
        return metadata.get(package_id)
    
    def delete_package(self, package_id: str) -> bool:
        """删除资源包"""
        with self._lock:
            metadata = self._load_metadata()
            
            if package_id not in metadata:
                return False
            
            # 删除文件目录
            package_dir = os.path.join(RESOURCE_PACKAGE_DIR, package_id)
            if os.path.exists(package_dir):
                try:
                    shutil.rmtree(package_dir)
                except Exception as e:
                    print(f"❌ 删除资源包目录失败: {e}")
                    return False
            
            # 从元数据中移除
            del metadata[package_id]
            self._save_metadata(metadata)
            
            print(f"✅ 资源包已删除: {package_id}")
            return True
    
    def copy_packages_to_build_context(
        self,
        package_configs: List[Dict],
        build_context: str
    ) -> List[str]:
        """
        将资源包复制到构建上下文
        
        Args:
            package_configs: 资源包配置列表，每个配置包含 package_id 和 target_path（或 target_dir）
                target_path: 完整相对路径，如 "test/b.txt" 或 "config/app.conf"
                target_dir: 目录路径（向后兼容），如 "resources"
            build_context: 构建上下文目录
        
        Returns:
            已复制的资源包ID列表
        """
        if not package_configs:
            return []
        
        metadata = self._load_metadata()
        copied_packages = []
        
        for config in package_configs:
            package_id = config.get('package_id')
            # 优先使用 target_path，如果没有则使用 target_dir（向后兼容）
            target_path_rel = config.get('target_path') or config.get('target_dir', 'resources')
            
            if not package_id:
                continue
            if package_id not in metadata:
                print(f"⚠️ 资源包不存在: {package_id}")
                continue
            
            package_info = metadata[package_id]
            package_dir = os.path.join(RESOURCE_PACKAGE_DIR, package_id)
            
            if not os.path.exists(package_dir):
                print(f"⚠️ 资源包目录不存在: {package_dir}")
                continue
            
            try:
                # 解析目标路径：分离目录和文件名
                # 例如 "test/b.txt" -> dir="test", filename="b.txt"
                # 例如 "resources" -> dir="resources", filename=None（使用原文件名）
                target_path_rel = target_path_rel.replace('\\', '/')  # 统一使用正斜杠
                path_parts = target_path_rel.split('/')
                
                # 判断最后一部分是文件名还是目录名
                # 如果包含扩展名或没有斜杠，可能是文件名
                last_part = path_parts[-1]
                has_extension = '.' in last_part and not last_part.startswith('.')
                
                if len(path_parts) > 1 and has_extension:
                    # 有目录和文件名：如 "test/b.txt"
                    target_dir_rel = '/'.join(path_parts[:-1])
                    target_filename = last_part
                else:
                    # 只有目录：如 "resources" 或 "test"
                    target_dir_rel = target_path_rel
                    target_filename = None  # 使用原文件名
                
                # 构建完整目标路径
                target_dir_abs = os.path.join(build_context, target_dir_rel)
                os.makedirs(target_dir_abs, exist_ok=True)
                
                # 如果已解压，复制解压后的目录；否则复制原始文件
                if package_info.get('extracted'):
                    extracted_path = os.path.join(package_dir, "extracted")
                    if os.path.exists(extracted_path):
                        # 解压包：复制整个解压目录的内容
                        for item in os.listdir(extracted_path):
                            src = os.path.join(extracted_path, item)
                            # 如果指定了文件名，只复制第一个文件并使用指定名称
                            if target_filename and os.path.isfile(src):
                                dst = os.path.join(target_dir_abs, target_filename)
                                shutil.copy2(src, dst)
                                break  # 只复制第一个文件
                            else:
                                dst = os.path.join(target_dir_abs, item)
                                if os.path.isdir(src):
                                    shutil.copytree(src, dst, dirs_exist_ok=True)
                                else:
                                    shutil.copy2(src, dst)
                    else:
                        # 解压目录不存在，复制原始文件
                        original_file = os.path.join(package_dir, package_info['filename'])
                        if os.path.exists(original_file):
                            dst_filename = target_filename or package_info['filename']
                            shutil.copy2(original_file, os.path.join(target_dir_abs, dst_filename))
                else:
                    # 复制原始文件
                    original_file = os.path.join(package_dir, package_info['filename'])
                    if os.path.exists(original_file):
                        dst_filename = target_filename or package_info['filename']
                        shutil.copy2(original_file, os.path.join(target_dir_abs, dst_filename))
                
                copied_packages.append(package_id)
                print(f"✅ 资源包已复制到构建上下文: {package_id} -> {target_path_rel}")
            except Exception as e:
                print(f"❌ 复制资源包失败 {package_id}: {e}")
                import traceback
                traceback.print_exc()
        
        return copied_packages


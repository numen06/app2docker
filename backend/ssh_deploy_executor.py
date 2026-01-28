# backend/ssh_deploy_executor.py
"""
SSH 部署执行器
通过 SSH 连接执行 Docker 部署
"""
import paramiko
import logging
from typing import Dict, Any, Optional
from io import StringIO

logger = logging.getLogger(__name__)


class SSHDeployExecutor:
    """SSH 部署执行器"""
    
    def __init__(self):
        """初始化 SSH 部署执行器"""
        pass
    
    def _clean_compose_content(self, compose_content: str) -> str:
        """
        清理 docker-compose.yml 内容，移除不支持的 version 字段
        
        Args:
            compose_content: 原始的 compose 内容
            
        Returns:
            清理后的 compose 内容
        """
        # #region agent log
        try:
            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                import json, time
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"ssh_deploy_executor.py:_clean_compose_content:ENTRY","message":"清理函数被调用","data":{"content_length":len(compose_content),"has_version":("version:" in compose_content or "version:" in compose_content)},"timestamp":int(time.time()*1000)}) + "\n")
        except: pass
        # #endregion
        try:
            import yaml
            
            # 解析 YAML
            compose_config = yaml.safe_load(compose_content)
            # #region agent log
            try:
                with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                    import json, time
                    # 记录解析后的原始配置结构
                    if isinstance(compose_config, dict):
                        services = compose_config.get('services', {})
                        service_keys = list(services.keys()) if services else []
                        first_service_config = services.get(service_keys[0], {}) if service_keys else {}
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"ssh_deploy_executor.py:_clean_compose_content:AFTER_PARSE","message":"解析后的原始配置","data":{"is_dict":True,"has_services":"services" in compose_config,"service_count":len(services) if services else 0,"service_names":service_keys,"first_service_keys":list(first_service_config.keys()) if first_service_config else []},"timestamp":int(time.time()*1000)}) + "\n")
                    else:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"ssh_deploy_executor.py:_clean_compose_content:AFTER_PARSE","message":"解析失败：不是字典","data":{"type":str(type(compose_config))},"timestamp":int(time.time()*1000)}) + "\n")
            except: pass
            # #endregion
            if not isinstance(compose_config, dict):
                # 如果不是字典，返回原内容（使用简单替换）
                logger.warning("compose 文件不是有效的字典格式，使用简单替换清理")
                return self._simple_clean_compose(compose_content)
            
            # 验证结构：确保有 services 字段，且 services 是字典
            if "services" not in compose_config:
                logger.warning("compose 文件缺少 services 字段，返回原内容")
                return compose_content
            
            if not isinstance(compose_config.get("services"), dict):
                logger.warning("compose 文件的 services 字段不是字典格式，返回原内容")
                return compose_content
            
            # 移除 version 字段（Docker Compose v2 不再需要）
            # #region agent log
            try:
                with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                    import json, time
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"ssh_deploy_executor.py:_clean_compose_content:BEFORE_DELETE","message":"准备移除version字段","data":{"has_version_in_dict":"version" in compose_config},"timestamp":int(time.time()*1000)}) + "\n")
            except: pass
            # #endregion
            if "version" in compose_config:
                del compose_config["version"]
                logger.info(f"✅ 已移除 docker-compose.yml 中的 version 字段（Docker Compose v2 不再需要）")
                # #region agent log
                try:
                    with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                        import json, time
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"ssh_deploy_executor.py:_clean_compose_content:AFTER_DELETE","message":"已移除version字段","data":{},"timestamp":int(time.time()*1000)}) + "\n")
                except: pass
                # #endregion
            
            # 重新序列化为 YAML，强制使用 block style（多行格式）
            try:
                # 必须使用 default_flow_style=False 强制 block style
                # 这样服务配置会以多行格式输出，而不是单行 {key: value} 格式
                cleaned_content = yaml.dump(
                    compose_config, 
                    default_flow_style=False,  # 强制使用 block style（多行格式）
                    allow_unicode=True,
                    sort_keys=False,  # 保持原始键的顺序
                    width=1000,  # 增加行宽，避免长行被截断
                    indent=2,  # 确保缩进一致
                    default_style=None,  # 不使用引号样式
                    explicit_start=False,  # 不添加 ---
                    explicit_end=False,  # 不添加 ...
                    Dumper=yaml.SafeDumper  # 使用 SafeDumper
                )
                # 确保以换行符结尾
                if not cleaned_content.endswith('\n'):
                    cleaned_content += '\n'
                
                # 验证序列化后的内容可以正确解析
                test_parse = yaml.safe_load(cleaned_content)
                if not isinstance(test_parse, dict) or "services" not in test_parse:
                    logger.error("序列化后的内容无法正确解析，使用简单替换方法")
                    return self._simple_clean_compose(compose_content)
                
                # 检查缩进和格式 - 确保 services 下的服务配置是字典格式
                services = test_parse.get("services", {})
                for service_name, service_config in services.items():
                    if not isinstance(service_config, dict):
                        logger.error(f"服务 {service_name} 的配置不是字典格式，使用简单替换方法")
                        return self._simple_clean_compose(compose_content)
                    # 确保服务配置至少有一个有效字段（如 image）
                    if not service_config:
                        logger.error(f"服务 {service_name} 的配置为空，使用简单替换方法")
                        return self._simple_clean_compose(compose_content)
                
                # #region agent log
                try:
                    with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                        import json, time
                        # 记录序列化后的完整内容和服务配置
                        services = test_parse.get('services', {})
                        service_keys = list(services.keys()) if services else []
                        first_service_config = services.get(service_keys[0], {}) if service_keys else {}
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"ssh_deploy_executor.py:_clean_compose_content:AFTER_SERIALIZE","message":"序列化后的内容检查","data":{"cleaned_content":cleaned_content,"service_count":len(services),"service_names":service_keys,"first_service_keys":list(first_service_config.keys())},"timestamp":int(time.time()*1000)}) + "\n")
                except: pass
                # #endregion
                    
            except Exception as dump_error:
                logger.error(f"YAML 序列化失败: {dump_error}，使用简单替换方法")
                import traceback
                logger.error(traceback.format_exc())
                return self._simple_clean_compose(compose_content)
            
            # 验证清理后的内容
            try:
                verify_config = yaml.safe_load(cleaned_content)
                if not isinstance(verify_config, dict):
                    logger.error("清理后的 compose 文件不是字典格式，返回原内容")
                    return compose_content
                if "services" not in verify_config:
                    logger.error("清理后的 compose 文件缺少 services 字段，返回原内容")
                    return compose_content
                if not isinstance(verify_config.get("services"), dict):
                    logger.error("清理后的 compose 文件的 services 字段不是字典格式，返回原内容")
                    return compose_content
                
                # 验证 services 下的每个服务都是字典
                for service_name, service_config in verify_config["services"].items():
                    if not isinstance(service_config, dict):
                        logger.error(f"服务 {service_name} 的配置不是字典格式，返回原内容")
                        return compose_content
                
                logger.debug(f"清理后的 compose 文件验证通过，包含 {len(verify_config['services'])} 个服务")
                # #region agent log
                try:
                    with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                        import json, time
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"ssh_deploy_executor.py:_clean_compose_content:SUCCESS","message":"清理成功","data":{"cleaned_length":len(cleaned_content),"has_version_in_result":("version:" in cleaned_content or "version:" in cleaned_content),"service_count":len(verify_config.get('services',{}))},"timestamp":int(time.time()*1000)}) + "\n")
                except: pass
                # #endregion
            except Exception as verify_error:
                logger.error(f"验证清理后的 compose 文件失败: {verify_error}，返回原内容")
                import traceback
                logger.error(traceback.format_exc())
                # #region agent log
                try:
                    with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                        import json, time
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"ssh_deploy_executor.py:_clean_compose_content:VERIFY_FAILED","message":"验证失败","data":{"error":str(verify_error)},"timestamp":int(time.time()*1000)}) + "\n")
                except: pass
                # #endregion
                return compose_content
            
            return cleaned_content
        except Exception as e:
            # 如果解析失败，尝试简单的字符串替换
            logger.warning(f"清理 compose_content 失败，使用简单替换: {e}")
            # #region agent log
            try:
                with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                    import json, time
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"ssh_deploy_executor.py:_clean_compose_content:EXCEPTION","message":"清理失败，使用简单替换","data":{"error":str(e)},"timestamp":int(time.time()*1000)}) + "\n")
            except: pass
            # #endregion
            return self._simple_clean_compose(compose_content)
    
    def _simple_clean_compose(self, compose_content: str) -> str:
        """
        简单的 compose 内容清理（字符串替换方式）
        这个方法更可靠，不会改变文件的其他格式
        
        Args:
            compose_content: 原始的 compose 内容
            
        Returns:
            清理后的 compose 内容
        """
        lines = compose_content.split("\n")
        cleaned_lines = []
        skip_next = False
        
        for line in lines:
            # 跳过 version 行（支持多种格式）
            stripped = line.strip()
            # 匹配 version: 'x.x' 或 version: "x.x" 或 version: x.x
            if (stripped.startswith("version:") or 
                stripped.startswith('version:') or
                (stripped.startswith('version') and ':' in stripped)):
                skip_next = True
                continue
            # 跳过空行（如果上一行是 version）
            if skip_next and stripped == "":
                skip_next = False
                continue
            skip_next = False
            cleaned_lines.append(line)
        
        result = "\n".join(cleaned_lines)
        
        # 确保以换行符结尾
        if not result.endswith('\n'):
            result += '\n'
        
        # 验证清理结果
        if "version:" in result or "version:" in result:
            logger.warning("简单替换方法未能完全移除 version 字段，尝试更严格的清理")
            # 更严格的清理：移除所有包含 version 的行
            strict_lines = [line for line in lines if not line.strip().startswith('version')]
            result = "\n".join(strict_lines)
            if not result.endswith('\n'):
                result += '\n'
        
        return result
    
    def _create_ssh_client(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        key_password: Optional[str] = None
    ) -> paramiko.SSHClient:
        """
        创建 SSH 客户端
        
        Args:
            host: 主机地址
            port: SSH 端口
            username: 用户名
            password: 密码（可选）
            private_key: SSH 私钥（可选）
            key_password: 私钥密码（可选）
        
        Returns:
            SSH 客户端
        """
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if private_key:
                # 使用私钥认证
                key_obj = None
                try:
                    # 尝试解析私钥
                    key_obj = paramiko.RSAKey.from_private_key(
                        StringIO(private_key),
                        password=key_password if key_password else None
                    )
                except:
                    try:
                        key_obj = paramiko.Ed25519Key.from_private_key(
                            StringIO(private_key),
                            password=key_password if key_password else None
                        )
                    except:
                        key_obj = paramiko.ECDSAKey.from_private_key(
                            StringIO(private_key),
                            password=key_password if key_password else None
                        )
                
                ssh_client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    pkey=key_obj,
                    timeout=10
                )
            elif password:
                # 使用密码认证
                ssh_client.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=10
                )
            else:
                raise ValueError("请提供密码或SSH私钥")
            
            return ssh_client
        
        except Exception as e:
            ssh_client.close()
            raise
    
    def execute_deploy(
        self,
        host_config: Dict[str, Any],
        docker_config: Dict[str, Any],
        deploy_mode: str = "docker_run"
    ) -> Dict[str, Any]:
        """
        通过 SSH 执行部署
        
        Args:
            host_config: SSH 主机配置（host, port, username, password/private_key等）
            docker_config: Docker 配置
            deploy_mode: 部署模式（docker_run 或 docker_compose）
        
        Returns:
            执行结果字典
        """
        try:
            # 创建 SSH 客户端
            ssh_client = self._create_ssh_client(
                host=host_config.get("host"),
                port=host_config.get("port", 22),
                username=host_config.get("username"),
                password=host_config.get("password"),
                private_key=host_config.get("private_key"),
                key_password=host_config.get("key_password")
            )
            
            try:
                if deploy_mode == "docker_compose":
                    # Docker Compose 模式
                    compose_content = docker_config.get("compose_content", "")
                    if not compose_content:
                        return {
                            "success": False,
                            "message": "Docker Compose 模式需要提供 compose_content"
                        }
                    
                    # 获取 Compose 模式（docker-compose 或 docker-stack）
                    compose_mode = docker_config.get("compose_mode", "docker-compose")
                    redeploy_strategy = docker_config.get("redeploy_strategy", "update_existing")
                    redeploy = docker_config.get("redeploy", False)
                    
                    # 生成 Stack/项目名称（优先使用应用名称，否则使用配置的 stack_name）
                    app_name = docker_config.get("app_name") or docker_config.get("stack_name", "app")
                    # 确保名称符合 Docker 命名规范（小写字母、数字、连字符）
                    import re
                    project_name = re.sub(r'[^a-z0-9-]', '-', app_name.lower())
                    
                    # 对于 docker-compose，使用 project_name；对于 docker-stack，使用 project_name 作为 stack_name
                    stack_name = project_name
                    
                    # 根据 redeploy_strategy 处理重新发布
                    if redeploy and redeploy_strategy == "remove_and_redeploy":
                        if compose_mode == "docker-stack":
                            # Docker Stack 模式：删除 Stack
                            logger.info(f"删除已有 Stack: {stack_name}")
                            stdin, stdout, stderr = ssh_client.exec_command(
                                f"docker stack rm {stack_name} || true"
                            )
                            stdout.channel.recv_exit_status()
                            # 等待 Stack 完全删除
                            import time
                            time.sleep(2)
                        else:
                            # Docker Compose 模式：停止并删除
                            logger.info(f"停止并删除已有 Compose Stack: {stack_name}")
                            stdin, stdout, stderr = ssh_client.exec_command(
                                f"docker-compose -f /tmp/{stack_name}/docker-compose.yml down -v || true"
                            )
                            stdout.channel.recv_exit_status()
                    
                    # 创建临时目录
                    stdin, stdout, stderr = ssh_client.exec_command(
                        f"mkdir -p /tmp/{stack_name}"
                    )
                    stdout.channel.recv_exit_status()
                    
                    # 清理 compose_content：移除不支持的 version 字段
                    logger.info(f"🔍 开始清理 compose 内容，原始内容长度: {len(compose_content)} 字节")
                    logger.info(f"原始内容（前10行）:\n{chr(10).join(compose_content.split(chr(10))[:10])}")
                    # #region agent log
                    try:
                        with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                            import json, time
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"F","location":"ssh_deploy_executor.py:execute_deploy:BEFORE_CLEAN","message":"原始compose内容完整检查","data":{"original_length":len(compose_content),"original_full_content":compose_content,"original_has_version":("version:" in compose_content or "version:" in compose_content)},"timestamp":int(time.time()*1000)}) + "\n")
                    except: pass
                    # #endregion
                    
                    # 直接使用简单替换方法，避免 YAML 解析/序列化可能的问题
                    # 简单替换方法更可靠，不会改变文件格式
                    cleaned_compose_content = self._simple_clean_compose(compose_content)
                    logger.info("使用简单替换方法清理 compose 内容（更可靠）")
                    
                    # #region agent log
                    try:
                        with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                            import json, time
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"ssh_deploy_executor.py:execute_deploy:AFTER_CLEAN","message":"清理完成","data":{"cleaned_length":len(cleaned_compose_content),"cleaned_has_version":("version:" in cleaned_compose_content or "version:" in cleaned_compose_content),"is_same":(cleaned_compose_content == compose_content)},"timestamp":int(time.time()*1000)}) + "\n")
                    except: pass
                    # #endregion
                    
                    # 检查是否真的清理了 version
                    if "version:" in cleaned_compose_content or "version:" in cleaned_compose_content:
                        logger.warning("⚠️ 清理后仍然包含 version 字段，使用简单替换方法强制清理")
                        cleaned_compose_content = self._simple_clean_compose(compose_content)
                        # 再次检查
                        if "version:" in cleaned_compose_content or "version:" in cleaned_compose_content:
                            logger.error("❌ 简单替换方法也失败，version 字段仍然存在")
                        else:
                            logger.info("✅ 简单替换方法成功移除了 version 字段")
                    
                    # 记录清理后的内容（用于调试）
                    logger.info(f"清理后的 compose 内容（前30行）:\n{chr(10).join(cleaned_compose_content.split(chr(10))[:30])}")
                    logger.info(f"清理后的内容长度: {len(cleaned_compose_content)} 字节")
                    
                    # 验证清理后的内容是否有效（再次验证）
                    try:
                        import yaml
                        test_config = yaml.safe_load(cleaned_compose_content)
                        if not isinstance(test_config, dict) or "services" not in test_config:
                            logger.error("清理后的 compose 文件结构无效，使用简单替换方法")
                            cleaned_compose_content = self._simple_clean_compose(compose_content)
                        else:
                            # 验证 services 结构
                            services = test_config.get("services", {})
                            if not isinstance(services, dict):
                                logger.error("清理后的 compose 文件的 services 不是字典，使用简单替换方法")
                                cleaned_compose_content = self._simple_clean_compose(compose_content)
                            else:
                                logger.info(f"清理后的 compose 文件验证通过，包含 {len(services)} 个服务: {list(services.keys())}")
                    except Exception as e:
                        logger.error(f"验证清理后的 compose 文件失败: {e}，使用简单替换方法")
                        import traceback
                        logger.error(traceback.format_exc())
                        cleaned_compose_content = self._simple_clean_compose(compose_content)
                    
                    # 最终验证：确保 version 字段已移除
                    if "version:" in cleaned_compose_content or "version:" in cleaned_compose_content:
                        logger.error("❌ 清理失败，version 字段仍然存在，强制使用简单替换方法")
                        cleaned_compose_content = self._simple_clean_compose(compose_content)
                        # 再次强制检查
                        if "version:" in cleaned_compose_content or "version:" in cleaned_compose_content:
                            logger.error("❌ 简单替换方法也失败，尝试手动移除")
                            # 手动移除所有包含 version 的行
                            lines = cleaned_compose_content.split('\n')
                            cleaned_lines = [line for line in lines if not line.strip().startswith('version')]
                            cleaned_compose_content = '\n'.join(cleaned_lines)
                            if not cleaned_compose_content.endswith('\n'):
                                cleaned_compose_content += '\n'
                    
                    # 写入 docker-compose.yml
                    sftp = ssh_client.open_sftp()
                    compose_file = f"/tmp/{stack_name}/docker-compose.yml"
                    
                    # 确保内容以 UTF-8 编码写入
                    file_content_bytes = cleaned_compose_content.encode('utf-8')
                    # #region agent log
                    try:
                        with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                            import json, time
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ssh_deploy_executor.py:execute_deploy:BEFORE_WRITE","message":"准备写入文件","data":{"file_path":compose_file,"content_length":len(file_content_bytes),"bytes_length":len(file_content_bytes),"has_version":("version:" in cleaned_compose_content or "version:" in cleaned_compose_content)},"timestamp":int(time.time()*1000)}) + "\n")
                    except: pass
                    # #endregion
                    
                    # 使用二进制模式写入，确保换行符正确
                    remote_file = sftp.file(compose_file, "wb")  # 使用二进制模式
                    remote_file.write(file_content_bytes)
                    remote_file.flush()  # 确保数据写入
                    remote_file.close()
                    sftp.close()
                    
                    # 验证文件权限
                    try:
                        stdin, stdout, stderr = ssh_client.exec_command(f"chmod 644 /tmp/{stack_name}/docker-compose.yml")
                        stdout.channel.recv_exit_status()
                    except:
                        pass
                    
                    logger.info(f"✅ 已写入 docker-compose.yml 到 {compose_file} (大小: {len(file_content_bytes)} 字节)")
                    # #region agent log
                    try:
                        with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                            import json, time
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ssh_deploy_executor.py:execute_deploy:AFTER_WRITE","message":"文件写入完成","data":{"file_path":compose_file,"bytes_written":len(file_content_bytes)},"timestamp":int(time.time()*1000)}) + "\n")
                    except: pass
                    # #endregion
                    
                    # 强制验证文件是否写入成功（使用 SSH 命令检查文件是否存在）
                    logger.info(f"🔍 验证文件是否成功写入到远程主机...")
                    check_file_cmd = f"test -f {compose_file} && echo 'FILE_EXISTS' && ls -lh {compose_file} && wc -l {compose_file}"
                    stdin, stdout, stderr = ssh_client.exec_command(check_file_cmd)
                    check_output = stdout.read().decode("utf-8", errors='ignore')
                    check_error = stderr.read().decode("utf-8", errors='ignore')
                    exit_status = stdout.channel.recv_exit_status()
                    
                    if exit_status == 0 and "FILE_EXISTS" in check_output:
                        logger.info(f"✅ 文件验证成功：文件已存在于远程主机")
                        logger.info(f"文件信息:\n{check_output}")
                        # #region agent log
                        try:
                            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                import json, time
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ssh_deploy_executor.py:execute_deploy:FILE_EXISTS","message":"文件存在验证成功","data":{"file_path":compose_file,"check_output":check_output},"timestamp":int(time.time()*1000)}) + "\n")
                        except: pass
                        # #endregion
                    else:
                        logger.error(f"❌ 文件验证失败：文件不存在于远程主机")
                        logger.error(f"检查命令输出: {check_output}")
                        logger.error(f"检查命令错误: {check_error}")
                        logger.error(f"退出状态: {exit_status}")
                        # #region agent log
                        try:
                            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                import json, time
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ssh_deploy_executor.py:execute_deploy:FILE_NOT_EXISTS","message":"文件不存在验证失败","data":{"file_path":compose_file,"check_output":check_output,"check_error":check_error,"exit_status":exit_status},"timestamp":int(time.time()*1000)}) + "\n")
                        except: pass
                        # #endregion
                        return {
                            "success": False,
                            "message": f"文件写入失败：无法在远程主机找到文件 {compose_file}"
                        }
                    
                    # 验证文件内容（读取完整内容）
                    try:
                        sftp = ssh_client.open_sftp()
                        verify_file = sftp.file(compose_file, "r")
                        verify_content = verify_file.read().decode('utf-8', errors='ignore')
                        verify_file.close()
                        sftp.close()
                        
                        # 检查是否还有 version
                        # #region agent log
                        try:
                            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                import json, time
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ssh_deploy_executor.py:execute_deploy:VERIFY_FILE","message":"验证写入的文件内容","data":{"verify_content_length":len(verify_content),"verify_has_version":("version:" in verify_content or "version:" in verify_content),"first_100_chars":verify_content[:100]},"timestamp":int(time.time()*1000)}) + "\n")
                        except: pass
                        # #endregion
                        if "version:" in verify_content or "version:" in verify_content:
                            logger.error(f"❌ 写入的文件仍然包含 version 字段！")
                            logger.error(f"文件内容:\n{verify_content}")
                            # #region agent log
                            try:
                                with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                    import json, time
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"ssh_deploy_executor.py:execute_deploy:VERIFY_FAILED","message":"验证失败：文件仍包含version","data":{"full_content":verify_content},"timestamp":int(time.time()*1000)}) + "\n")
                            except: pass
                            # #endregion
                        else:
                            logger.info(f"✅ 验证通过：文件不包含 version 字段")
                            logger.info(f"写入的文件完整内容:\n{verify_content}")
                            # #region agent log
                            try:
                                with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                    import json, time
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ssh_deploy_executor.py:execute_deploy:VERIFY_SUCCESS","message":"验证成功：文件不包含version","data":{"full_content":verify_content},"timestamp":int(time.time()*1000)}) + "\n")
                            except: pass
                            # #endregion
                    except Exception as verify_error:
                        logger.warning(f"无法验证写入的文件内容: {verify_error}")
                        import traceback
                        logger.warning(traceback.format_exc())
                    
                    # 验证 compose 文件（使用 docker-compose config 命令）
                    if compose_mode == "docker-compose":
                        logger.info("验证 docker-compose.yml 文件...")
                        # 先尝试读取并显示文件内容
                        try:
                            sftp = ssh_client.open_sftp()
                            verify_file = sftp.file(compose_file, "r")
                            verify_content = verify_file.read().decode('utf-8', errors='ignore')
                            verify_file.close()
                            sftp.close()
                            logger.info(f"远程文件完整内容:\n{verify_content}")
                            # #region agent log
                            try:
                                with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                    import json, time
                                    # 检查文件内容的详细信息
                                    import yaml as yaml_check
                                    try:
                                        parsed_check = yaml_check.safe_load(verify_content)
                                        services_check = parsed_check.get('services', {}) if isinstance(parsed_check, dict) else {}
                                        first_service_check = list(services_check.values())[0] if services_check else {}
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"ssh_deploy_executor.py:execute_deploy:READ_REMOTE","message":"读取远程文件并解析检查","data":{"content":verify_content,"length":len(verify_content),"can_parse":isinstance(parsed_check, dict),"has_services":"services" in parsed_check if isinstance(parsed_check, dict) else False,"service_count":len(services_check),"first_service_keys":list(first_service_check.keys()) if isinstance(first_service_check, dict) else []},"timestamp":int(time.time()*1000)}) + "\n")
                                    except Exception as parse_err:
                                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"J","location":"ssh_deploy_executor.py:execute_deploy:READ_REMOTE_PARSE_ERROR","message":"解析远程文件失败","data":{"content":verify_content,"error":str(parse_err)},"timestamp":int(time.time()*1000)}) + "\n")
                            except: pass
                            # #endregion
                        except Exception as read_error:
                            logger.warning(f"无法读取远程文件进行调试: {read_error}")
                        
                        # 检查文件是否存在和可读
                        check_cmd = f"test -f /tmp/{stack_name}/docker-compose.yml && ls -la /tmp/{stack_name}/docker-compose.yml && file /tmp/{stack_name}/docker-compose.yml && cat -A /tmp/{stack_name}/docker-compose.yml"
                        stdin, stdout, stderr = ssh_client.exec_command(check_cmd)
                        check_output = stdout.read().decode("utf-8", errors='ignore')
                        check_error = stderr.read().decode("utf-8", errors='ignore')
                        logger.info(f"文件检查结果:\n{check_output}")
                        # #region agent log
                        try:
                            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                import json, time
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"K","location":"ssh_deploy_executor.py:execute_deploy:FILE_CHECK","message":"文件检查结果（包含cat -A输出）","data":{"check_output":check_output,"check_error":check_error},"timestamp":int(time.time()*1000)}) + "\n")
                        except: pass
                        # #endregion
                        
                        # 检查 docker compose 版本，优先使用 v2
                        check_v2_cmd = "docker compose version 2>&1"
                        stdin, stdout, stderr = ssh_client.exec_command(check_v2_cmd)
                        v2_exit = stdout.channel.recv_exit_status()
                        use_docker_compose_v2 = (v2_exit == 0)
                        compose_cmd = "docker compose" if use_docker_compose_v2 else "docker-compose"
                        
                        # 先尝试使用绝对路径验证
                        validate_cmd = f"cd /tmp/{stack_name} && {compose_cmd} -f {compose_file} config 2>&1"
                        stdin, stdout, stderr = ssh_client.exec_command(validate_cmd)
                        validate_output = stdout.read().decode("utf-8", errors='ignore')
                        validate_error = stderr.read().decode("utf-8", errors='ignore')
                        exit_status = stdout.channel.recv_exit_status()
                        
                        # 记录验证命令的完整输出
                        logger.info(f"docker-compose config 验证输出:\nstdout: {validate_output}\nstderr: {validate_error}\nexit_status: {exit_status}")
                        # #region agent log
                        try:
                            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                import json, time
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"ssh_deploy_executor.py:execute_deploy:VALIDATE_FULL","message":"docker-compose config 完整输出","data":{"exit_status":exit_status,"stdout":validate_output,"stderr":validate_error,"command":validate_cmd},"timestamp":int(time.time()*1000)}) + "\n")
                        except: pass
                        # #endregion
                        if exit_status != 0:
                            # 错误信息已经在上面记录了，这里不再重复获取
                            # 但是继续执行部署，让 docker-compose 自己报告错误
                            logger.warning(f"docker-compose.yml 文件验证失败，但继续执行部署")
                            # #region agent log
                            try:
                                with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                    import json, time
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"ssh_deploy_executor.py:execute_deploy:VALIDATE_ERROR","message":"docker-compose config 验证失败","data":{"error":error_output},"timestamp":int(time.time()*1000)}) + "\n")
                            except: pass
                            # #endregion
                            
                            # 不阻止部署，让 docker-compose 自己报告错误
                    
                    # 如果是 docker-stack 模式，检查 compose 文件中是否有不兼容的选项
                    if compose_mode == "docker-stack":
                        # docker stack deploy 不支持 container_name，会显示警告
                        if "container_name" in compose_content:
                            logger.warning("docker stack deploy 不支持 container_name 选项，该选项将被忽略")
                    
                    # 根据 compose_mode 执行不同的命令
                    if compose_mode == "docker-stack":
                        # Docker Stack 模式：使用 docker stack deploy
                        command = docker_config.get("command", "")
                        # 构建 docker stack deploy 命令
                        # 命令格式：docker stack deploy -c <compose-file> <stack-name> [OPTIONS]
                        if command:
                            # 如果命令中包含 -c 或 --compose-file，需要替换文件路径
                            import shlex
                            cmd_parts = shlex.split(command)
                            
                            # 检查并替换 -c 或 --compose-file 参数
                            has_compose_file = False
                            for i, part in enumerate(cmd_parts):
                                if part == "-c" and i + 1 < len(cmd_parts):
                                    cmd_parts[i + 1] = compose_file
                                    has_compose_file = True
                                    break
                                elif part == "--compose-file" and i + 1 < len(cmd_parts):
                                    cmd_parts[i + 1] = compose_file
                                    has_compose_file = True
                                    break
                            
                            if has_compose_file:
                                # 已经有 -c 或 --compose-file，直接使用（stack_name 必须在最后）
                                stack_command = f"docker stack deploy {' '.join(cmd_parts)} {stack_name}"
                            else:
                                # 没有 -c 或 --compose-file，添加它（stack_name 必须在最后）
                                stack_command = f"docker stack deploy -c {compose_file} {' '.join(cmd_parts)} {stack_name}"
                        else:
                            # 默认命令：使用 -c 参数（stack_name 必须在最后）
                            import shlex
                            stack_command = f"docker stack deploy -c {shlex.quote(compose_file)} {shlex.quote(stack_name)}"
                        
                        logger.info(f"执行 SSH Stack 命令: {stack_command}")
                        stdin, stdout, stderr = ssh_client.exec_command(stack_command)
                    else:
                        # Docker Compose 模式：优先使用 docker compose (v2)，如果不存在则使用 docker-compose (v1)
                        # 先检查 docker compose 版本
                        check_v2_cmd = "docker compose version 2>&1"
                        stdin, stdout, stderr = ssh_client.exec_command(check_v2_cmd)
                        v2_output = stdout.read().decode("utf-8", errors='ignore')
                        v2_exit = stdout.channel.recv_exit_status()
                        
                        # 检查 docker-compose (v1) 版本
                        check_v1_cmd = "docker-compose --version 2>&1"
                        stdin, stdout, stderr = ssh_client.exec_command(check_v1_cmd)
                        v1_output = stdout.read().decode("utf-8", errors='ignore')
                        v1_exit = stdout.channel.recv_exit_status()
                        
                        # 决定使用哪个命令
                        use_docker_compose_v2 = (v2_exit == 0)
                        compose_cmd = "docker compose" if use_docker_compose_v2 else "docker-compose"
                        
                        logger.info(f"检测到的 docker compose 版本: v2={use_docker_compose_v2}, v2_output={v2_output}, v1_output={v1_output}")
                        # #region agent log
                        try:
                            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                import json, time
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"L","location":"ssh_deploy_executor.py:execute_deploy:CHECK_VERSION","message":"检查docker compose版本","data":{"use_v2":use_docker_compose_v2,"v2_exit":v2_exit,"v2_output":v2_output,"v1_exit":v1_exit,"v1_output":v1_output},"timestamp":int(time.time()*1000)}) + "\n")
                        except: pass
                        # #endregion
                        
                        command = docker_config.get("command", "up -d")
                        # 确保文件存在后再执行命令
                        # 使用绝对路径，并确保工作目录正确
                        import shlex
                        cmd_parts = shlex.split(command)
                        if "-p" not in cmd_parts and "--project-name" not in cmd_parts:
                            # 添加项目名称参数
                            # docker compose v2 使用 --project-name，docker-compose v1 使用 -p
                            project_flag = "--project-name" if use_docker_compose_v2 else "-p"
                            # 使用绝对路径 -f 指定 compose 文件路径，确保能找到文件
                            compose_command = f"cd /tmp/{stack_name} && pwd && ls -la docker-compose.yml && {compose_cmd} -f {compose_file} {project_flag} {shlex.quote(project_name)} {command}"
                        else:
                            # 使用绝对路径 -f 指定 compose 文件路径
                            compose_command = f"cd /tmp/{stack_name} && pwd && ls -la docker-compose.yml && {compose_cmd} -f {compose_file} {command}"
                        logger.info(f"执行 SSH Compose 命令: {compose_command}")
                        logger.info(f"使用项目名称: {project_name}")
                        logger.info(f"使用 compose 文件: {compose_file}")
                        logger.info(f"使用 compose 命令: {compose_cmd}")
                        # #region agent log
                        try:
                            with open('/Users/wesley/wokerspacs/jar2docker/.cursor/debug.log', 'a') as f:
                                import json, time
                                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"ssh_deploy_executor.py:execute_deploy:BEFORE_EXECUTE","message":"准备执行docker-compose命令","data":{"compose_command":compose_command,"compose_file":compose_file,"stack_name":stack_name,"compose_cmd":compose_cmd},"timestamp":int(time.time()*1000)}) + "\n")
                        except: pass
                        # #endregion
                        stdin, stdout, stderr = ssh_client.exec_command(compose_command)
                        stack_command = compose_command
                    
                    exit_status = stdout.channel.recv_exit_status()
                    stdout_text = stdout.read().decode("utf-8", errors='ignore')
                    stderr_text = stderr.read().decode("utf-8", errors='ignore')
                    
                    # 记录详细的执行结果
                    logger.info(f"SSH {compose_mode} 命令执行完成: exit_status={exit_status}")
                    if stdout_text:
                        logger.info(f"SSH {compose_mode} stdout: {stdout_text[:500]}")
                    if stderr_text:
                        logger.warning(f"SSH {compose_mode} stderr: {stderr_text[:500]}")
                    
                    if exit_status == 0:
                        return {
                            "success": True,
                            "message": f"{'Stack' if compose_mode == 'docker-stack' else 'Compose'} 部署成功",
                            "output": stdout_text,
                            "command": stack_command
                        }
                    else:
                        # 构建详细的错误消息
                        error_message = f"{'Stack' if compose_mode == 'docker-stack' else 'Compose'} 部署失败"
                        if stderr_text:
                            error_message = f"{error_message}: {stderr_text.strip()}"
                        elif stdout_text:
                            error_message = f"{error_message}: {stdout_text.strip()}"
                        
                        logger.error(f"SSH {compose_mode} 部署失败: exit_status={exit_status}, error={stderr_text}, output={stdout_text}")
                        return {
                            "success": False,
                            "message": error_message,
                            "error": stderr_text,
                            "output": stdout_text,
                            "exit_status": exit_status,
                            "command": stack_command
                        }
                else:
                    # Docker Run 模式
                    command_str = docker_config.get("command", "").strip()
                    
                    # 如果命令包含"docker run"前缀，保留它（SSH需要完整命令）
                    # 如果命令不包含"docker run"前缀，添加它
                    if command_str and not command_str.startswith("docker"):
                        command_str = f"docker run {command_str}"
                    elif command_str.startswith("docker run"):
                        # 已经是完整命令，保持不变
                        pass
                    elif command_str.startswith("docker"):
                        # 可能是"docker"开头但后面不是"run"，检查一下
                        parts = command_str.split(None, 1)
                        if len(parts) == 1 or parts[1].startswith("-"):
                            # 只有"docker"或"docker"后面直接跟参数，添加"run"
                            command_str = f"docker run {parts[1] if len(parts) > 1 else ''}"
                    
                    # 如果没有 command，尝试从配置构建命令
                    if not command_str:
                        # 从配置构建 docker run 命令
                        image_template = docker_config.get("image_template", "")
                        container_name = docker_config.get("container_name", "")
                        ports = docker_config.get("ports", [])
                        env = docker_config.get("env", [])
                        volumes = docker_config.get("volumes", [])
                        restart_policy = docker_config.get("restart_policy", "always")
                        
                        if not image_template:
                            return {
                                "success": False,
                                "message": "Docker Run 模式需要提供 command 或 image_template"
                            }
                        
                        # 构建 docker run 命令
                        cmd_parts = ["docker", "run", "-d"]
                        
                        if container_name:
                            cmd_parts.extend(["--name", container_name])
                        
                        if restart_policy:
                            cmd_parts.extend(["--restart", restart_policy])
                        
                        for port in ports:
                            cmd_parts.extend(["-p", port])
                        
                        for env_var in env:
                            cmd_parts.extend(["-e", env_var])
                        
                        for volume in volumes:
                            cmd_parts.extend(["-v", volume])
                        
                        cmd_parts.append(image_template)
                        
                        command_str = " ".join(cmd_parts)
                    
                    # 处理多行命令和反斜杠续行符
                    import re
                    command_str = re.sub(r'\\\s*\n\s*', ' ', command_str)
                    command_str = re.sub(r'\\\\\s*\n\s*', ' ', command_str)
                    command_str = re.sub(r'\s+', ' ', command_str).strip()
                    
                    # 检查是否需要重新发布
                    redeploy = docker_config.get("redeploy", False)
                    
                    # 从命令中提取容器名
                    import shlex
                    cmd_parts = shlex.split(command_str)
                    container_name = None
                    
                    # 跳过"docker"和"run"（如果存在）
                    start_idx = 0
                    if len(cmd_parts) >= 2 and cmd_parts[0] == "docker" and cmd_parts[1] == "run":
                        start_idx = 2
                    
                    # 在剩余部分查找--name
                    if "--name" in cmd_parts[start_idx:]:
                        name_idx = cmd_parts.index("--name", start_idx)
                        if name_idx + 1 < len(cmd_parts):
                            container_name = cmd_parts[name_idx + 1]
                    
                    # 如果还没找到，尝试从 docker_config 获取
                    if not container_name:
                        container_name = docker_config.get("container_name")
                    
                    # 如果redeploy为true但没找到容器名，尝试从命令中提取（使用正则表达式）
                    if redeploy and not container_name:
                        # 尝试使用正则表达式提取 --name=value 或 --name value 格式
                        name_match = re.search(r'--name[=\s]+([^\s]+)', command_str)
                        if name_match:
                            container_name = name_match.group(1)
                    
                    if redeploy and container_name:
                        # 停止并删除已有容器
                        logger.info(f"清理已有容器: {container_name}")
                        stdin, stdout, stderr = ssh_client.exec_command(
                            f"docker stop {container_name} || true"
                        )
                        stdout.channel.recv_exit_status()
                        stdin, stdout, stderr = ssh_client.exec_command(
                            f"docker rm -f {container_name} || true"
                        )
                        stdout.channel.recv_exit_status()
                    
                    # 执行 docker run 命令
                    logger.info(f"执行 SSH 命令: {command_str}")
                    stdin, stdout, stderr = ssh_client.exec_command(
                        command_str
                    )
                    
                    exit_status = stdout.channel.recv_exit_status()
                    stdout_text = stdout.read().decode("utf-8", errors='ignore')
                    stderr_text = stderr.read().decode("utf-8", errors='ignore')
                    
                    # 记录详细的执行结果
                    logger.info(f"SSH 命令执行完成: exit_status={exit_status}")
                    if stdout_text:
                        logger.info(f"SSH 命令 stdout: {stdout_text[:500]}")  # 限制长度
                    if stderr_text:
                        logger.warning(f"SSH 命令 stderr: {stderr_text[:500]}")  # 限制长度
                    
                    if exit_status == 0:
                        return {
                            "success": True,
                            "message": "容器部署成功",
                            "output": stdout_text,
                            "command": command_str
                        }
                    else:
                        # 构建详细的错误消息
                        error_message = "容器部署失败"
                        if stderr_text:
                            error_message = f"容器部署失败: {stderr_text.strip()}"
                        elif stdout_text:
                            error_message = f"容器部署失败: {stdout_text.strip()}"
                        
                        logger.error(f"SSH 部署失败: exit_status={exit_status}, error={stderr_text}, output={stdout_text}")
                        return {
                            "success": False,
                            "message": error_message,
                            "error": stderr_text,
                            "output": stdout_text,
                            "exit_status": exit_status,
                            "command": command_str
                        }
            
            finally:
                ssh_client.close()
        
        except Exception as e:
            import traceback
            logger.exception("SSH 部署执行异常")
            return {
                "success": False,
                "message": f"SSH 部署失败: {str(e)}",
                "error": traceback.format_exc()
            }


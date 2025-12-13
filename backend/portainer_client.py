# backend/portainer_client.py
"""
Portainer API 客户端
用于连接 Portainer 和 Portainer Agent，执行部署操作
"""
import requests
import logging
from typing import Dict, Any, Optional, List
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class PortainerClient:
    """Portainer API 客户端"""
    
    def __init__(self, url: str, api_key: str, endpoint_id: int):
        """
        初始化 Portainer 客户端
        
        Args:
            url: Portainer API URL（如：http://portainer.example.com:9000/api）
            api_key: Portainer API Key
            endpoint_id: Portainer Endpoint ID
        """
        self.url = url.rstrip('/')
        # 确保 URL 以 /api 结尾
        if not self.url.endswith('/api'):
            if self.url.endswith('/'):
                self.url = f"{self.url}api"
            else:
                self.url = f"{self.url}/api"
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
        logger.info(f"PortainerClient 初始化: URL={self.url}, EndpointID={endpoint_id}")
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送请求到 Portainer API
        
        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 其他请求参数
        
        Returns:
            响应数据
        """
        url = f"{self.url}{endpoint}"
        try:
            # 设置默认超时时间（10秒）
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 10
            logger.debug(f"Portainer API 请求: {method} {url}")
            response = self.session.request(method, url, **kwargs)
            
            # 记录响应状态
            logger.debug(f"Portainer API 响应状态: {response.status_code}")
            
            # 如果状态码不是 2xx，尝试获取错误信息
            if not response.ok:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('details', response.text))
                    logger.error(f"Portainer API 错误响应: {response.status_code} - {error_msg}")
                    raise Exception(f"API 错误 ({response.status_code}): {error_msg}")
                except:
                    logger.error(f"Portainer API 错误响应: {response.status_code} - {response.text}")
                    raise Exception(f"API 错误 ({response.status_code}): {response.text}")
            
            response.raise_for_status()
            if response.content:
                return response.json()
            return {}
        except requests.exceptions.Timeout:
            logger.error(f"Portainer API 请求超时: {url}")
            raise Exception("连接超时，请检查 Portainer URL 是否正确")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Portainer API 连接失败: {e}")
            error_str = str(e)
            # 提供更友好的错误信息
            if "Connection reset" in error_str or "Connection aborted" in error_str:
                raise Exception("连接被重置，可能是 Portainer 服务器不稳定或网络问题，请稍后重试")
            elif "Name or service not known" in error_str:
                raise Exception("无法解析 Portainer 服务器地址，请检查 URL 是否正确")
            elif "Connection refused" in error_str:
                raise Exception("连接被拒绝，请检查 Portainer 服务器是否运行以及端口是否正确")
            else:
                raise Exception(f"无法连接到 Portainer 服务器: {error_str}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Portainer API HTTP 错误: {e}")
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', error_data.get('details', str(e)))
                    raise Exception(f"HTTP 错误 ({e.response.status_code}): {error_msg}")
                except:
                    raise Exception(f"HTTP 错误 ({e.response.status_code}): {e.response.text}")
            raise Exception(f"HTTP 错误: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Portainer API 请求失败: {e}")
            raise Exception(f"请求失败: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接
        
        Returns:
            连接测试结果
        """
        try:
            logger.info(f"开始测试 Portainer 连接: URL={self.url}, EndpointID={self.endpoint_id}")
            
            # 首先测试 API 是否可访问（尝试获取状态）
            try:
                status = self._request('GET', '/status', timeout=5)
                logger.info(f"Portainer 状态检查成功: {status}")
            except Exception as status_e:
                logger.warning(f"状态检查失败（可能正常）: {status_e}")
                # 继续尝试获取 endpoint
            
            # 先获取所有 endpoints，以便提供更好的错误提示
            try:
                all_endpoints = self._request('GET', '/endpoints', timeout=5)
                available_ids = [ep.get('Id') for ep in all_endpoints]
                logger.info(f"找到 {len(all_endpoints)} 个 endpoints: {available_ids}")
                
                # 检查指定的 endpoint_id 是否存在
                if self.endpoint_id not in available_ids:
                    endpoint_names = {ep.get('Id'): ep.get('Name') for ep in all_endpoints}
                    return {
                        "success": False,
                        "message": f"Endpoint ID {self.endpoint_id} 不存在。可用的 Endpoint IDs: {', '.join(map(str, available_ids))}",
                        "available_endpoints": [
                            {"id": ep.get('Id'), "name": ep.get('Name')} 
                            for ep in all_endpoints
                        ]
                    }
            except Exception as list_e:
                logger.warning(f"获取 endpoints 列表失败: {list_e}")
                # 继续尝试直接获取指定的 endpoint
            
            # 获取 endpoint 信息（设置5秒超时）
            endpoint = self._request('GET', f'/endpoints/{self.endpoint_id}', timeout=5)
            logger.info(f"Endpoint 信息获取成功: {endpoint.get('Name', 'Unknown')}")
            
            return {
                "success": True,
                "message": "连接成功",
                "endpoint": endpoint
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Portainer 连接测试失败: {error_msg}")
            
            # 尝试更详细的错误信息
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = error_detail.get('message', error_detail.get('details', error_msg))
                except:
                    error_msg = e.response.text or error_msg
            
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                return {
                    "success": False,
                    "message": "连接超时，请检查 Portainer URL 是否正确且可访问"
                }
            elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
                return {
                    "success": False,
                    "message": f"无法连接到 Portainer 服务器: {error_msg}"
                }
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                return {
                    "success": False,
                    "message": "API Key 无效或已过期，请检查 Portainer API Key"
                }
            elif "404" in error_msg or "not found" in error_msg.lower():
                # 尝试获取可用的 endpoints
                try:
                    all_endpoints = self._request('GET', '/endpoints', timeout=3)
                    available_ids = [ep.get('Id') for ep in all_endpoints]
                    endpoint_names = {ep.get('Id'): ep.get('Name') for ep in all_endpoints}
                    return {
                        "success": False,
                        "message": f"Endpoint ID {self.endpoint_id} 不存在。可用的 Endpoint IDs: {', '.join(map(str, available_ids))}",
                        "available_endpoints": [
                            {"id": ep.get('Id'), "name": ep.get('Name')} 
                            for ep in all_endpoints
                        ]
                    }
                except:
                    return {
                        "success": False,
                        "message": f"Endpoint ID {self.endpoint_id} 不存在，请检查 Endpoint ID"
                    }
            else:
                return {
                    "success": False,
                    "message": f"连接失败: {error_msg}"
                }
    
    def get_endpoint_info(self) -> Dict[str, Any]:
        """
        获取 Endpoint 信息
        
        Returns:
            Endpoint 信息
        """
        return self._request('GET', f'/endpoints/{self.endpoint_id}')
    
    def get_docker_info(self) -> Dict[str, Any]:
        """
        获取 Docker 信息
        
        Returns:
            Docker 信息
        """
        return self._request('GET', f'/endpoints/{self.endpoint_id}/docker/info')
    
    def deploy_container(
        self,
        name: str,
        image: str,
        command: Optional[str] = None,
        ports: Optional[List[str]] = None,
        env: Optional[List[str]] = None,
        volumes: Optional[List[str]] = None,
        restart_policy: str = "always"
    ) -> Dict[str, Any]:
        """
        部署容器（Docker Run）
        
        Args:
            name: 容器名称
            image: 镜像名称
            command: 命令（docker run 的参数，不包含 docker run）
            ports: 端口映射列表（如：["8000:8000"]）
            env: 环境变量列表（如：["KEY=value"]）
            volumes: 卷映射列表（如：["/host:/container"]）
            restart_policy: 重启策略
        
        Returns:
            部署结果
        """
        try:
            # 如果提供了 command，需要解析 docker run 命令参数
            if command:
                # 处理多行命令和反斜杠续行符
                import re
                command = re.sub(r'\\\s*\n\s*', ' ', command)
                command = re.sub(r'\\\\\s*\n\s*', ' ', command)
                command = re.sub(r'\s+', ' ', command).strip()
                
                # 解析命令参数
                import shlex
                cmd_parts = shlex.split(command)
                
                # 解析 docker run 参数
                parsed_env = env or []
                parsed_volumes = volumes or []
                parsed_ports = ports or []
                parsed_restart = restart_policy
                container_cmd = []  # 容器启动后的命令（如果有）
                
                i = 0
                while i < len(cmd_parts):
                    arg = cmd_parts[i]
                    
                    if arg == '-d' or arg == '--detach':
                        # 后台运行，Portainer API 中不需要
                        i += 1
                    elif arg == '--name':
                        # 容器名称，已经在 name 参数中传递，忽略
                        i += 2
                    elif arg == '-e' or arg == '--env':
                        # 环境变量
                        if i + 1 < len(cmd_parts):
                            parsed_env.append(cmd_parts[i + 1])
                            i += 2
                        else:
                            i += 1
                    elif arg == '--env-file':
                        # 环境变量文件，暂不支持
                        i += 2
                    elif arg == '-v' or arg == '--volume':
                        # 卷映射
                        if i + 1 < len(cmd_parts):
                            parsed_volumes.append(cmd_parts[i + 1])
                            i += 2
                        else:
                            i += 1
                    elif arg == '-p' or arg == '--publish':
                        # 端口映射
                        if i + 1 < len(cmd_parts):
                            parsed_ports.append(cmd_parts[i + 1])
                            i += 2
                        else:
                            i += 1
                    elif arg == '--restart':
                        # 重启策略
                        if i + 1 < len(cmd_parts):
                            parsed_restart = cmd_parts[i + 1]
                            i += 2
                        else:
                            i += 1
                    elif arg.startswith('-'):
                        # 其他参数，跳过
                        i += 1
                    else:
                        # 可能是镜像名称或容器命令
                        # 如果还没有设置镜像，且这不是最后一个参数，可能是镜像
                        # 最后一个参数通常是镜像名称，但我们已经从参数中获取了
                        # 这里可能是容器启动后的命令
                        if i == len(cmd_parts) - 1:
                            # 最后一个参数，应该是镜像名称，但我们已经有了
                            # 如果和传入的 image 不一致，可能是命令
                            if arg != image:
                                container_cmd.append(arg)
                        else:
                            container_cmd.append(arg)
                        i += 1
                
                # 构建容器创建配置
                container_config = {
                    "Image": image,
                    "Env": parsed_env,
                    "ExposedPorts": {},
                    "HostConfig": {
                        "RestartPolicy": {"Name": parsed_restart},
                        "Binds": parsed_volumes,
                        "PortBindings": {}
                    }
                }
                
                # 如果有容器命令，添加它
                if container_cmd:
                    container_config["Cmd"] = container_cmd
                
                # 处理端口映射
                if parsed_ports:
                    for port_mapping in parsed_ports:
                        if ':' in port_mapping:
                            host_port, container_port = port_mapping.split(':')
                            container_port_proto = f"{container_port}/tcp"
                            container_config["ExposedPorts"][container_port_proto] = {}
                            container_config["HostConfig"]["PortBindings"][container_port_proto] = [
                                {"HostPort": host_port}
                            ]
                
                # 创建容器（使用更长的超时时间，因为创建容器可能需要较长时间）
                try:
                    create_response = self._request(
                        'POST',
                        f'/endpoints/{self.endpoint_id}/docker/containers/create',
                        params={"name": name},
                        json=container_config,
                        timeout=60  # 创建容器可能需要更长时间
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "Connection reset" in error_msg or "Connection aborted" in error_msg:
                        raise Exception("创建容器时连接被重置，可能是 Portainer 服务器不稳定或网络问题，请稍后重试")
                    raise
                
                container_id = create_response.get("Id")
                if not container_id:
                    raise Exception("创建容器失败：未返回容器 ID")
                
                # 启动容器（使用更长的超时时间）
                try:
                    self._request(
                        'POST',
                        f'/endpoints/{self.endpoint_id}/docker/containers/{container_id}/start',
                        timeout=30  # 启动容器也需要一些时间
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "Connection reset" in error_msg or "Connection aborted" in error_msg:
                        raise Exception("启动容器时连接被重置，容器可能已创建但未启动，请检查 Portainer 中的容器状态")
                    raise
                
                return {
                    "success": True,
                    "message": "容器部署成功",
                    "container_id": container_id
                }
            else:
                # 使用配置构建容器
                container_config = {
                    "Image": image,
                    "Env": env or [],
                    "ExposedPorts": {},
                    "HostConfig": {
                        "RestartPolicy": {"Name": restart_policy},
                        "Binds": volumes or [],
                        "PortBindings": {}
                    }
                }
                
                # 处理端口映射
                if ports:
                    for port_mapping in ports:
                        if ':' in port_mapping:
                            host_port, container_port = port_mapping.split(':')
                            container_port_proto = f"{container_port}/tcp"
                            container_config["ExposedPorts"][container_port_proto] = {}
                            container_config["HostConfig"]["PortBindings"][container_port_proto] = [
                                {"HostPort": host_port}
                            ]
                
                # 创建容器（使用更长的超时时间，因为创建容器可能需要较长时间）
                try:
                    create_response = self._request(
                        'POST',
                        f'/endpoints/{self.endpoint_id}/docker/containers/create',
                        params={"name": name},
                        json=container_config,
                        timeout=60  # 创建容器可能需要更长时间
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "Connection reset" in error_msg or "Connection aborted" in error_msg:
                        raise Exception("创建容器时连接被重置，可能是 Portainer 服务器不稳定或网络问题，请稍后重试")
                    raise
                
                container_id = create_response.get("Id")
                if not container_id:
                    raise Exception("创建容器失败：未返回容器 ID")
                
                # 启动容器（使用更长的超时时间）
                try:
                    self._request(
                        'POST',
                        f'/endpoints/{self.endpoint_id}/docker/containers/{container_id}/start',
                        timeout=30  # 启动容器也需要一些时间
                    )
                except Exception as e:
                    error_msg = str(e)
                    if "Connection reset" in error_msg or "Connection aborted" in error_msg:
                        raise Exception("启动容器时连接被重置，容器可能已创建但未启动，请检查 Portainer 中的容器状态")
                    raise
                
                return {
                    "success": True,
                    "message": "容器部署成功",
                    "container_id": container_id
                }
        
        except Exception as e:
            logger.exception("Portainer 容器部署失败")
            return {
                "success": False,
                "message": f"部署失败: {str(e)}"
            }
    
    def deploy_stack(
        self,
        name: str,
        compose_content: str,
        command: str = "up -d"
    ) -> Dict[str, Any]:
        """
        部署 Docker Compose Stack
        
        Args:
            name: Stack 名称
            compose_content: docker-compose.yml 内容
            command: docker-compose 命令（默认：up -d）
        
        Returns:
            部署结果
        """
        try:
            # Portainer 使用 stacks API
            stack_config = {
                "Name": name,
                "StackFileContent": compose_content,
                "EndpointID": self.endpoint_id
            }
            
            # 检查 Stack 是否已存在
            stacks = self._request('GET', '/stacks')
            existing_stack = None
            for stack in stacks:
                if stack.get("Name") == name and stack.get("EndpointID") == self.endpoint_id:
                    existing_stack = stack
                    break
            
            if existing_stack:
                # 更新现有 Stack
                stack_id = existing_stack["Id"]
                update_response = self._request(
                    'PUT',
                    f'/stacks/{stack_id}',
                    params={"endpointId": self.endpoint_id},
                    json=stack_config
                )
                return {
                    "success": True,
                    "message": "Stack 更新成功",
                    "stack_id": stack_id
                }
            else:
                # 创建新 Stack
                create_response = self._request(
                    'POST',
                    '/stacks',
                    params={"endpointId": self.endpoint_id, "method": "string"},
                    json=stack_config
                )
                return {
                    "success": True,
                    "message": "Stack 部署成功",
                    "stack_id": create_response.get("Id")
                }
        
        except Exception as e:
            logger.exception("Portainer Stack 部署失败")
            return {
                "success": False,
                "message": f"部署失败: {str(e)}"
            }
    
    def stop_container(self, container_name: str) -> Dict[str, Any]:
        """
        停止容器
        
        Args:
            container_name: 容器名称
        
        Returns:
            操作结果
        """
        try:
            # 查找容器
            containers = self._request('GET', f'/endpoints/{self.endpoint_id}/docker/containers/json', params={"all": True})
            container_id = None
            for container in containers:
                names = container.get("Names", [])
                if any(f"/{container_name}" in name for name in names):
                    container_id = container["Id"]
                    break
            
            if not container_id:
                return {
                    "success": False,
                    "message": f"容器不存在: {container_name}"
                }
            
            # 停止容器
            self._request('POST', f'/endpoints/{self.endpoint_id}/docker/containers/{container_id}/stop')
            
            return {
                "success": True,
                "message": "容器已停止"
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"停止失败: {str(e)}"
            }
    
    def remove_container(self, container_name: str, force: bool = True) -> Dict[str, Any]:
        """
        删除容器
        
        Args:
            container_name: 容器名称
            force: 是否强制删除
        
        Returns:
            操作结果
        """
        try:
            # 查找容器
            containers = self._request('GET', f'/endpoints/{self.endpoint_id}/docker/containers/json', params={"all": True})
            container_id = None
            for container in containers:
                names = container.get("Names", [])
                if any(f"/{container_name}" in name for name in names):
                    container_id = container["Id"]
                    break
            
            if not container_id:
                return {
                    "success": False,
                    "message": f"容器不存在: {container_name}"
                }
            
            # 删除容器
            self._request('DELETE', f'/endpoints/{self.endpoint_id}/docker/containers/{container_id}', params={"force": force})
            
            return {
                "success": True,
                "message": "容器已删除"
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }

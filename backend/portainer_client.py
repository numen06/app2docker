# backend/portainer_client.py
"""
Portainer API 客户端
用于连接 Portainer 和 Portainer Agent，执行部署操作
"""
import requests
import logging
from typing import Dict, Any, Optional, List
import yaml

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
        self.session.headers.update({"Content-Type": "application/json"})
        logger.info(f"PortainerClient 初始化: URL={self.url}, EndpointID={endpoint_id}")

    def _build_auth_headers(self, force_mode: Optional[str] = None) -> Dict[str, str]:
        """根据凭据格式构建鉴权头。"""
        auth_headers: Dict[str, str] = {}
        mode = force_mode
        if not mode:
            if self.api_key.startswith("ptc_"):
                mode = "x_api_key"
            elif self.api_key.count(".") == 2:
                mode = "bearer"
            else:
                mode = "x_api_key"

        if mode == "bearer":
            auth_headers["Authorization"] = f"Bearer {self.api_key}"
        else:
            auth_headers["X-API-Key"] = self.api_key
        return auth_headers
    
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
            request_headers = kwargs.pop("headers", {})
            headers = {
                **self._build_auth_headers(),
                **request_headers,
            }
            response = self.session.request(method, url, headers=headers, **kwargs)
            if (
                response.status_code == 401
                and self.api_key
                and self.api_key.count(".") == 2
            ):
                alt_headers = {
                    **self._build_auth_headers(force_mode="x_api_key"),
                    **request_headers,
                }
                response = self.session.request(
                    method, url, headers=alt_headers, **kwargs
                )
            
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
        部署容器（Portainer 模式下转换为单容器 Stack）
        
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
        return self.deploy_container_as_stack(
            container_name=name,
            image=image,
            command=command,
            ports=ports,
            env=env,
            volumes=volumes,
            restart_policy=restart_policy,
        )

    def _split_env_pairs(self, env: Optional[List[str]]) -> List[Dict[str, str]]:
        if not env:
            return []
        result = []
        for item in env:
            if "=" in item:
                key, value = item.split("=", 1)
                result.append({"name": key, "value": value})
        return result

    def list_stacks(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/stacks", params={"endpointId": self.endpoint_id})

    def get_stack(self, stack_id: int) -> Dict[str, Any]:
        return self._request(
            "GET", f"/stacks/{stack_id}", params={"endpointId": self.endpoint_id}
        )

    def get_stack_by_name(self, stack_name: str) -> Optional[Dict[str, Any]]:
        stacks = self.list_stacks()
        for stack in stacks:
            if (
                stack.get("Name") == stack_name
                and int(stack.get("EndpointId", stack.get("EndpointID", 0)))
                == int(self.endpoint_id)
            ):
                return stack
        return None

    def update_stack(
        self, stack_id: int, compose_content: str, env: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        # 读取更新前的 Stack 文件，便于判断“调用成功但内容未变化”的情况
        before_content = ""
        try:
            stack_file = self._request(
                "GET",
                f"/stacks/{stack_id}/file",
                params={"endpointId": self.endpoint_id},
            )
            before_content = stack_file.get("StackFileContent", "") or ""
        except Exception as read_err:
            logger.warning("读取更新前 Stack 文件失败 (stack_id=%s): %s", stack_id, read_err)

        payload = {
            "StackFileContent": compose_content,
            "Env": self._split_env_pairs(env),
            "Prune": False,
            # 即使镜像 tag 不变（如 latest），也尝试拉取新镜像，避免“更新成功但运行态未变化”
            "PullImage": True,
        }
        self._request(
            "PUT",
            f"/stacks/{stack_id}",
            params={"endpointId": self.endpoint_id},
            json=payload,
        )

        changed = (before_content or "").strip() != (compose_content or "").strip()
        if changed:
            message = "Stack 更新成功（Compose 内容已变更）"
        else:
            message = "Stack 更新成功（Compose 内容未变化，可能仅执行了重部署/拉镜像）"
            logger.info(
                "Stack 更新调用成功但 Compose 内容未变化: stack_id=%s, endpoint_id=%s",
                stack_id,
                self.endpoint_id,
            )
        return {
            "success": True,
            "message": message,
            "stack_id": stack_id,
            "compose_changed": changed,
        }

    def deploy_container_as_stack(
        self,
        container_name: str,
        image: str,
        command: Optional[str] = None,
        ports: Optional[List[str]] = None,
        env: Optional[List[str]] = None,
        volumes: Optional[List[str]] = None,
        restart_policy: str = "always",
    ) -> Dict[str, Any]:
        service: Dict[str, Any] = {"image": image, "restart": restart_policy}
        if ports:
            service["ports"] = ports
        if env:
            service["environment"] = env
        if volumes:
            service["volumes"] = volumes
        if command:
            service["command"] = command

        compose = {
            "version": "3.8",
            "services": {container_name: service},
        }
        compose_content = yaml.safe_dump(compose, allow_unicode=True, sort_keys=False)
        return self.deploy_stack(container_name, compose_content, env=env)
    
    def deploy_stack(
        self,
        name: str,
        compose_content: str,
        command: str = "up -d",
        env: Optional[List[str]] = None,
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
            existing_stack = self.get_stack_by_name(name)
            if existing_stack:
                stack_id = existing_stack["Id"]
                return self.update_stack(stack_id, compose_content, env=env)
            else:
                payload = {
                    "Name": name,
                    "StackFileContent": compose_content,
                    "Env": self._split_env_pairs(env),
                }
                try:
                    create_response = self._request(
                        "POST",
                        "/stacks",
                        params={
                            "endpointId": self.endpoint_id,
                            "type": 2,
                            "method": "string",
                        },
                        json=payload,
                    )
                except Exception as create_err:
                    err_msg = str(create_err)
                    # 某些 Portainer 版本 /api/stacks 创建会返回 405，回退到 standalone 端点。
                    if "405" in err_msg:
                        logger.warning(
                            "创建 Stack 走 /stacks 失败，尝试 standalone 回退: %s",
                            err_msg,
                        )
                        fallback_payload = {
                            **payload,
                            "FromAppTemplate": False,
                        }
                        try:
                            create_response = self._request(
                                "POST",
                                "/stacks/create/standalone/string",
                                params={"endpointId": self.endpoint_id},
                                json=fallback_payload,
                            )
                        except Exception:
                            # 部分环境会返回 500 但实际已创建，二次查询确认。
                            created = self.get_stack_by_name(name)
                            if created:
                                create_response = {"Id": created.get("Id")}
                            else:
                                raise
                    else:
                        raise
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

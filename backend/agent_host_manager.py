# backend/agent_host_manager.py
"""
Agent主机资源管理模块
用于管理通过WebSocket连接的Agent主机
"""
import os
import uuid
import hashlib
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from backend.database import get_db_session, init_db
from backend.models import AgentHost
from backend.config import load_config
from backend.portainer_client import PortainerClient

# 确保数据库已初始化
try:
    init_db()
except:
    pass


class AgentHostManager:
    """Agent主机资源管理器"""
    
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = threading.Lock()
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化Agent主机管理器"""
        pass
    
    def _generate_token(self) -> str:
        """生成唯一token"""
        # 使用UUID + 时间戳 + 随机数生成唯一token
        token_data = f"{uuid.uuid4()}{datetime.now().timestamp()}{os.urandom(16).hex()}"
        token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        return token
    
    def _to_dict(self, host: AgentHost) -> Optional[Dict]:
        """将数据库模型转换为字典"""
        if not host:
            return None
        
        return {
            "host_id": host.host_id,
            "name": host.name,
            "host_type": host.host_type or "agent",
            "token": host.token,
            "portainer_url": host.portainer_url,
            "portainer_endpoint_id": host.portainer_endpoint_id,
            "status": host.status,
            "last_heartbeat": host.last_heartbeat.isoformat() if host.last_heartbeat else None,
            "host_info": host.host_info or {},
            "docker_info": host.docker_info or {},
            "description": host.description,
            "created_at": host.created_at.isoformat() if host.created_at else None,
            "updated_at": host.updated_at.isoformat() if host.updated_at else None,
        }
    
    def add_agent_host(
        self,
        name: str,
        host_type: str = "agent",
        description: str = "",
        portainer_url: str = None,
        portainer_api_key: str = None,
        portainer_endpoint_id: int = None
    ) -> Dict:
        """
        添加主机（支持 Agent 和 Portainer 类型）
        
        Args:
            name: 主机名称
            host_type: 主机类型（agent 或 portainer）
            description: 描述
            portainer_url: Portainer API URL（Portainer 类型必需）
            portainer_api_key: Portainer API Key（Portainer 类型必需）
            portainer_endpoint_id: Portainer Endpoint ID（Portainer 类型必需）
        """
        with self._lock:
            db = get_db_session()
            try:
                # 检查名称是否已存在
                existing = db.query(AgentHost).filter(AgentHost.name == name).first()
                if existing:
                    raise ValueError(f"主机名称 '{name}' 已存在")
                
                host_id = str(uuid.uuid4())
                token = None
                
                if host_type == "agent":
                    # Agent 类型：生成 token
                    token = self._generate_token()
                    # 确保token唯一
                    while db.query(AgentHost).filter(AgentHost.token == token).first():
                        token = self._generate_token()
                elif host_type == "portainer":
                    # Portainer 类型：验证必需字段
                    if not portainer_url or not portainer_api_key or portainer_endpoint_id is None:
                        raise ValueError("Portainer 类型主机需要提供 portainer_url、portainer_api_key 和 portainer_endpoint_id")
                    # Portainer 类型不需要 token，明确设置为 None
                    token = None
                
                # 构建创建参数，对于 Portainer 类型，token 为 None
                create_params = {
                    "host_id": host_id,
                    "name": name,
                    "host_type": host_type,
                    "status": "offline",
                    "host_info": {},
                    "docker_info": {},
                    "description": description,
                }
                
                # 根据主机类型设置不同的字段
                if host_type == "agent":
                    create_params["token"] = token
                elif host_type == "portainer":
                    create_params["token"] = None  # Portainer 类型明确设置为 None
                    create_params["portainer_url"] = portainer_url
                    create_params["portainer_api_key"] = portainer_api_key
                    create_params["portainer_endpoint_id"] = portainer_endpoint_id
                
                host_obj = AgentHost(**create_params)
                
                db.add(host_obj)
                db.commit()
                
                print(f"✅ 主机添加成功: {host_id} ({name}, 类型: {host_type})")
                return self._to_dict(host_obj)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()
    
    def get_agent_host_by_token(self, token: str) -> Optional[Dict]:
        """根据token查找主机"""
        db = get_db_session()
        try:
            host = db.query(AgentHost).filter(AgentHost.token == token).first()
            return self._to_dict(host) if host else None
        finally:
            db.close()
    
    def update_host_status(
        self,
        host_id: str,
        status: str,
        host_info: Optional[Dict] = None,
        docker_info: Optional[Dict] = None
    ) -> Optional[Dict]:
        """更新主机状态和信息"""
        with self._lock:
            db = get_db_session()
            try:
                host_obj = db.query(AgentHost).filter(AgentHost.host_id == host_id).first()
                if not host_obj:
                    return None
                
                host_obj.status = status
                host_obj.last_heartbeat = datetime.now()
                
                if host_info is not None:
                    # 合并更新host_info
                    current_info = host_obj.host_info or {}
                    current_info.update(host_info)
                    host_obj.host_info = current_info
                
                if docker_info is not None:
                    # 合并更新docker_info
                    current_docker = host_obj.docker_info or {}
                    current_docker.update(docker_info)
                    host_obj.docker_info = current_docker
                
                host_obj.updated_at = datetime.now()
                db.commit()
                
                return self._to_dict(host_obj)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()
    
    def update_host_info(
        self,
        host_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        portainer_url: Optional[str] = None,
        portainer_api_key: Optional[str] = None,
        portainer_endpoint_id: Optional[int] = None
    ) -> Optional[Dict]:
        """更新主机基本信息"""
        with self._lock:
            db = get_db_session()
            try:
                host_obj = db.query(AgentHost).filter(AgentHost.host_id == host_id).first()
                if not host_obj:
                    return None
                
                if name and name != host_obj.name:
                    existing = db.query(AgentHost).filter(
                        AgentHost.name == name,
                        AgentHost.host_id != host_id
                    ).first()
                    if existing:
                        raise ValueError(f"Agent主机名称 '{name}' 已存在")
                    host_obj.name = name
                
                if description is not None:
                    host_obj.description = description
                
                # 更新 Portainer 相关字段（如果是 Portainer 类型）
                if host_obj.host_type == "portainer":
                    if portainer_url is not None:
                        host_obj.portainer_url = portainer_url
                    if portainer_api_key is not None:
                        host_obj.portainer_api_key = portainer_api_key
                    if portainer_endpoint_id is not None:
                        host_obj.portainer_endpoint_id = portainer_endpoint_id
                
                host_obj.updated_at = datetime.now()
                db.commit()
                
                return self._to_dict(host_obj)
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()
    
    def test_portainer_connection(
        self,
        portainer_url: str,
        api_key: str,
        endpoint_id: int
    ) -> Dict[str, Any]:
        """
        测试 Portainer 连接
        
        Args:
            portainer_url: Portainer API URL
            api_key: Portainer API Key
            endpoint_id: Portainer Endpoint ID
        
        Returns:
            测试结果
        """
        try:
            client = PortainerClient(portainer_url, api_key, endpoint_id)
            result = client.test_connection()
            
            if result.get("success"):
                # 获取 Docker 信息
                try:
                    docker_info = client.get_docker_info()
                    result["docker_info"] = docker_info
                except:
                    pass
            
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}"
            }
    
    def update_portainer_host_status(self, host_id: str, retry_count: int = 3) -> Optional[Dict]:
        """
        更新 Portainer 主机状态（通过 API 获取最新信息）
        使用重试机制，避免网络波动导致的误判
        
        Args:
            host_id: 主机ID
            retry_count: 重试次数（默认3次）
        
        Returns:
            更新后的主机信息
        """
        db = get_db_session()
        try:
            host_obj = db.query(AgentHost).filter(AgentHost.host_id == host_id).first()
            if not host_obj or host_obj.host_type != "portainer":
                return None
            
            if not host_obj.portainer_url or not host_obj.portainer_api_key or host_obj.portainer_endpoint_id is None:
                return None
            
            # 重试机制：只有在多次失败后才标记为离线
            last_error = None
            success = False
            
            for attempt in range(retry_count):
                try:
                    client = PortainerClient(
                        host_obj.portainer_url,
                        host_obj.portainer_api_key,
                        host_obj.portainer_endpoint_id
                    )
                    
                    # 测试连接（使用较短的超时时间，避免长时间等待）
                    test_result = client.test_connection()
                    if test_result.get("success"):
                        success = True
                        host_obj.status = "online"
                        
                        # 获取 Docker 信息
                        try:
                            docker_info = client.get_docker_info()
                            host_obj.docker_info = {
                                "version": docker_info.get("ServerVersion", ""),
                                "containers": docker_info.get("Containers", 0),
                                "images": docker_info.get("Images", 0)
                            }
                        except Exception as docker_e:
                            # Docker 信息获取失败不影响在线状态
                            logger.warning(f"获取 Docker 信息失败: {docker_e}")
                        
                        host_obj.last_heartbeat = datetime.now()
                        db.commit()
                        
                        if attempt > 0:
                            logger.info(f"Portainer 主机 {host_obj.name} 在第 {attempt + 1} 次尝试后成功连接")
                        
                        return self._to_dict(host_obj)
                    else:
                        last_error = test_result.get("message", "连接测试失败")
                        if attempt < retry_count - 1:
                            # 等待后重试（指数退避）
                            import time
                            wait_time = (attempt + 1) * 0.5  # 0.5秒, 1秒, 1.5秒
                            time.sleep(wait_time)
                            logger.debug(f"Portainer 主机 {host_obj.name} 连接失败，{wait_time}秒后重试 ({attempt + 1}/{retry_count})")
                
                except Exception as e:
                    last_error = str(e)
                    if attempt < retry_count - 1:
                        # 等待后重试（指数退避）
                        import time
                        wait_time = (attempt + 1) * 0.5
                        time.sleep(wait_time)
                        logger.debug(f"Portainer 主机 {host_obj.name} 连接异常，{wait_time}秒后重试 ({attempt + 1}/{retry_count}): {e}")
            
            # 所有重试都失败，但只有在之前是在线状态时才标记为离线
            # 如果之前就是离线状态，保持离线（避免频繁切换）
            if host_obj.status == "online":
                logger.warning(f"Portainer 主机 {host_obj.name} 连接失败（{retry_count}次重试），标记为离线: {last_error}")
                host_obj.status = "offline"
            else:
                # 如果之前就是离线，不更新状态，避免频繁检测
                logger.debug(f"Portainer 主机 {host_obj.name} 仍然离线: {last_error}")
            
            host_obj.last_heartbeat = datetime.now()
            db.commit()
            
            return self._to_dict(host_obj)
            
        except Exception as e:
            logger.exception(f"更新 Portainer 主机状态失败: {e}")
            # 发生异常时，不改变状态，避免误判
            return self._to_dict(host_obj) if host_obj else None
        finally:
            db.close()
    
    def list_agent_hosts(self) -> List[Dict]:
        """列出所有Agent主机"""
        db = get_db_session()
        try:
            hosts = db.query(AgentHost).order_by(AgentHost.created_at.desc()).all()
            return [self._to_dict(h) for h in hosts]
        finally:
            db.close()
    
    def get_agent_host(self, host_id: str) -> Optional[Dict]:
        """获取Agent主机信息"""
        db = get_db_session()
        try:
            host = db.query(AgentHost).filter(AgentHost.host_id == host_id).first()
            return self._to_dict(host) if host else None
        finally:
            db.close()
    
    def delete_agent_host(self, host_id: str) -> bool:
        """删除Agent主机"""
        with self._lock:
            db = get_db_session()
            try:
                host = db.query(AgentHost).filter(AgentHost.host_id == host_id).first()
                if not host:
                    return False
                
                db.delete(host)
                db.commit()
                
                print(f"✅ Agent主机已删除: {host_id}")
                return True
            except Exception as e:
                db.rollback()
                raise
            finally:
                db.close()
    
    def generate_deploy_command(
        self,
        host_id: str,
        deploy_type: str = "run",
        agent_image: str = "registry.cn-hangzhou.aliyuncs.com/51jbm/app2docker-agent:latest",
        server_url: Optional[str] = None
    ) -> Dict:
        """生成部署命令
        
        Args:
            host_id: 主机ID
            deploy_type: 部署类型，'run' 或 'stack'
            agent_image: Agent镜像名称
            server_url: 服务器URL（如果为None，则从配置中获取）
        
        Returns:
            包含部署命令的字典
        """
        host = self.get_agent_host(host_id)
        if not host:
            raise ValueError(f"Agent主机不存在: {host_id}")
        
        token = host["token"]
        
        # 获取服务器URL
        if server_url is None:
            config = load_config()
            server_config = config.get("server", {})
            host_addr = server_config.get("host", "0.0.0.0")
            port = server_config.get("port", 8000)
            
            # 如果是0.0.0.0，尝试获取实际IP
            if host_addr == "0.0.0.0":
                import socket
                try:
                    # 连接到外部地址以获取本机IP
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(("8.8.8.8", 80))
                    host_addr = s.getsockname()[0]
                    s.close()
                except:
                    host_addr = "localhost"
            
            # 构建WebSocket URL
            ws_protocol = "ws"
            if port == 443:
                ws_protocol = "wss"
            server_url = f"{ws_protocol}://{host_addr}:{port}"
        
        if deploy_type == "run":
            # Docker Run方式
            command = f"""docker run -d \\
  --name app2docker-agent \\
  --restart=always \\
  -e AGENT_TOKEN={token} \\
  -e SERVER_URL={server_url} \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -v /proc:/host/proc:ro \\
  -v /sys:/host/sys:ro \\
  {agent_image}"""
            
            return {
                "type": "run",
                "command": command,
                "description": "使用docker run命令部署Agent"
            }
        
        elif deploy_type == "stack":
            # Docker Stack方式
            compose_content = f"""version: '3.8'

services:
  agent:
    image: {agent_image}
    container_name: app2docker-agent
    restart: always
    environment:
      - AGENT_TOKEN={token}
      - SERVER_URL={server_url}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge"""
            
            deploy_command = f"""# 1. 创建docker-compose.yml文件
cat > docker-compose.yml << 'EOF'
{compose_content}
EOF

# 2. 部署stack
docker stack deploy -c docker-compose.yml app2docker-agent

# 或者使用docker-compose（如果使用docker-compose而不是swarm）
# docker-compose up -d"""
            
            return {
                "type": "stack",
                "command": deploy_command,
                "compose_content": compose_content,
                "description": "使用docker stack deploy命令部署Agent"
            }
        
        else:
            raise ValueError(f"不支持的部署类型: {deploy_type}")
    
    def check_offline_hosts(self, timeout_seconds: int = 60):
        """
        检查并更新离线主机（心跳超时）
        注意：只检查 Agent 类型的主机，Portainer 类型的主机通过 API 检测，不依赖心跳
        """
        db = get_db_session()
        try:
            timeout_threshold = datetime.now() - timedelta(seconds=timeout_seconds)
            # 只检查 Agent 类型的主机（Portainer 类型不依赖心跳）
            hosts = db.query(AgentHost).filter(
                AgentHost.host_type == "agent",  # 只检查 Agent 类型
                AgentHost.status == "online",
                AgentHost.last_heartbeat < timeout_threshold
            ).all()
            
            for host in hosts:
                host.status = "offline"
                host.updated_at = datetime.now()
            
            if hosts:
                db.commit()
                print(f"✅ 更新了 {len(hosts)} 个离线 Agent 主机")
        except Exception as e:
            db.rollback()
            print(f"⚠️ 检查离线主机失败: {e}")
        finally:
            db.close()
    
    def check_portainer_hosts_status(self):
        """
        定期检查 Portainer 主机状态
        使用重试机制，避免网络波动导致的误判
        """
        db = get_db_session()
        try:
            # 获取所有 Portainer 类型的主机
            portainer_hosts = db.query(AgentHost).filter(
                AgentHost.host_type == "portainer"
            ).all()
            
            for host in portainer_hosts:
                try:
                    # 更新状态（内部有重试机制）
                    self.update_portainer_host_status(host.host_id, retry_count=2)  # 定期检测使用较少重试次数
                except Exception as e:
                    logger.warning(f"检查 Portainer 主机 {host.name} 状态失败: {e}")
        finally:
            db.close()


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
from typing import List, Dict, Optional
from backend.database import get_db_session, init_db
from backend.models import AgentHost
from backend.config import load_config

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
            "token": host.token,
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
        description: str = ""
    ) -> Dict:
        """添加Agent主机"""
        with self._lock:
            db = get_db_session()
            try:
                # 检查名称是否已存在
                existing = db.query(AgentHost).filter(AgentHost.name == name).first()
                if existing:
                    raise ValueError(f"Agent主机名称 '{name}' 已存在")
                
                host_id = str(uuid.uuid4())
                token = self._generate_token()
                
                # 确保token唯一
                while db.query(AgentHost).filter(AgentHost.token == token).first():
                    token = self._generate_token()
                
                host_obj = AgentHost(
                    host_id=host_id,
                    name=name,
                    token=token,
                    status="offline",
                    host_info={},
                    docker_info={},
                    description=description,
                )
                
                db.add(host_obj)
                db.commit()
                
                print(f"✅ Agent主机添加成功: {host_id} ({name})")
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
        description: Optional[str] = None
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
                
                host_obj.updated_at = datetime.now()
                db.commit()
                
                return self._to_dict(host_obj)
            except Exception as e:
                db.rollback()
                raise
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
  --name jar2docker-agent \\
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
    container_name: jar2docker-agent
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
docker stack deploy -c docker-compose.yml jar2docker-agent

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
        """检查并更新离线主机（心跳超时）"""
        db = get_db_session()
        try:
            timeout_threshold = datetime.now() - timedelta(seconds=timeout_seconds)
            hosts = db.query(AgentHost).filter(
                AgentHost.status == "online",
                AgentHost.last_heartbeat < timeout_threshold
            ).all()
            
            for host in hosts:
                host.status = "offline"
                host.updated_at = datetime.now()
            
            if hosts:
                db.commit()
                print(f"✅ 更新了 {len(hosts)} 个离线主机")
        except Exception as e:
            db.rollback()
            print(f"⚠️ 检查离线主机失败: {e}")
        finally:
            db.close()


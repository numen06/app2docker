# backend/pending_host_manager.py
"""
待加入主机管理器
管理通过WebSocket连接但尚未正式加入系统的Agent主机
"""
import threading
from datetime import datetime
from typing import Dict, Optional, Any, List
from fastapi import WebSocket


class PendingHostManager:
    """待加入主机管理器（内存存储）"""

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = threading.Lock()
            cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化待加入主机管理器"""
        # agent_token (唯一标识) -> 主机信息字典
        self._pending_hosts: Dict[str, Dict[str, Any]] = {}
        # agent_token -> WebSocket连接
        self._pending_connections: Dict[str, WebSocket] = {}
        # WebSocket -> agent_token (反向查找)
        self._websocket_to_token: Dict[WebSocket, str] = {}

    def add_pending_host(
        self,
        agent_token: Optional[str] = None,
        websocket: Optional[WebSocket] = None,
        host_info: Optional[Dict] = None,
        docker_info: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        添加待加入主机

        Args:
            agent_token: Agent唯一标识（可选，如果没有则使用临时ID）
            websocket: WebSocket连接（可选）
            host_info: 主机信息
            docker_info: Docker信息

        Returns:
            待加入主机信息字典
        """
        with self._lock:
            # 如果没有提供agent_token，生成临时ID
            if not agent_token:
                import uuid

                agent_token = f"temp_{uuid.uuid4().hex[:16]}"

            # 如果该唯一标识已存在，更新信息
            if agent_token in self._pending_hosts:
                existing = self._pending_hosts[agent_token]
                if host_info:
                    existing["host_info"].update(host_info or {})
                if docker_info:
                    existing["docker_info"].update(docker_info or {})
                if websocket:
                    # 如果已有旧连接，标记需要关闭（由调用方异步关闭）
                    old_websocket = self._pending_connections.get(agent_token)
                    if old_websocket and old_websocket != websocket:
                        # 从反向映射中删除旧连接
                        if old_websocket in self._websocket_to_token:
                            del self._websocket_to_token[old_websocket]
                        # 将旧连接保存到 existing 中，供调用方关闭
                        existing["_old_websocket"] = old_websocket
                    # 更新为新连接
                    self._pending_connections[agent_token] = websocket
                    self._websocket_to_token[websocket] = agent_token
                existing["last_heartbeat"] = datetime.now()
                return existing

            pending_host = {
                "agent_token": agent_token,
                "host_info": host_info or {},
                "docker_info": docker_info or {},
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
            }

            self._pending_hosts[agent_token] = pending_host
            if websocket:
                self._pending_connections[agent_token] = websocket
                self._websocket_to_token[websocket] = agent_token

            print(
                f"✅ 待加入主机已记录: agent_token={agent_token[:16] if agent_token else 'None'}..."
            )
            return pending_host

    def get_pending_host(self, agent_token: str) -> Optional[Dict[str, Any]]:
        """
        获取待加入主机信息

        Args:
            agent_token: Agent唯一标识

        Returns:
            待加入主机信息字典，如果不存在返回None
        """
        with self._lock:
            return self._pending_hosts.get(agent_token)

    def get_pending_host_by_agent_token(
        self, agent_token: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        根据agent_token获取待加入主机（兼容None）

        Args:
            agent_token: Agent唯一标识（可为None）

        Returns:
            待加入主机信息字典，如果不存在返回None
        """
        if not agent_token:
            return None
        return self.get_pending_host(agent_token)

    def get_pending_host_by_websocket(
        self, websocket: WebSocket
    ) -> Optional[Dict[str, Any]]:
        """
        根据WebSocket连接获取待加入主机

        Args:
            websocket: WebSocket连接

        Returns:
            待加入主机信息字典，如果不存在返回None
        """
        with self._lock:
            agent_token = self._websocket_to_token.get(websocket)
            if agent_token:
                return self._pending_hosts.get(agent_token)
            return None

    def get_pending_connection(self, agent_token: str) -> Optional[WebSocket]:
        """
        获取待加入主机的WebSocket连接

        Args:
            agent_token: Agent唯一标识

        Returns:
            WebSocket连接，如果不存在返回None
        """
        with self._lock:
            return self._pending_connections.get(agent_token)

    def list_pending_hosts(self) -> List[Dict[str, Any]]:
        """
        列出所有待加入主机

        Returns:
            待加入主机列表（不包含WebSocket对象，datetime已转换为字符串）
        """
        with self._lock:
            # 返回副本，不包含WebSocket对象
            result = []
            for agent_token, host_info in self._pending_hosts.items():
                host_copy = host_info.copy()
                # 确保不包含WebSocket对象
                if "websocket" in host_copy:
                    del host_copy["websocket"]
                # 转换datetime对象为字符串
                if "connected_at" in host_copy and host_copy["connected_at"]:
                    if isinstance(host_copy["connected_at"], datetime):
                        host_copy["connected_at"] = host_copy[
                            "connected_at"
                        ].isoformat()
                if "last_heartbeat" in host_copy and host_copy["last_heartbeat"]:
                    if isinstance(host_copy["last_heartbeat"], datetime):
                        host_copy["last_heartbeat"] = host_copy[
                            "last_heartbeat"
                        ].isoformat()
                result.append(host_copy)
            return result

    def update_pending_host_heartbeat(
        self,
        agent_token: str,
        host_info: Optional[Dict] = None,
        docker_info: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        更新待加入主机心跳和信息

        Args:
            agent_token: Agent唯一标识
            host_info: 主机信息（可选，用于更新）
            docker_info: Docker信息（可选，用于更新）

        Returns:
            更新后的待加入主机信息，如果不存在返回None
        """
        with self._lock:
            if agent_token not in self._pending_hosts:
                return None

            pending_host = self._pending_hosts[agent_token]
            pending_host["last_heartbeat"] = datetime.now()

            if host_info is not None:
                # 合并更新host_info
                current_info = pending_host.get("host_info", {})
                current_info.update(host_info)
                pending_host["host_info"] = current_info

            if docker_info is not None:
                # 合并更新docker_info
                current_docker = pending_host.get("docker_info", {})
                current_docker.update(docker_info)
                pending_host["docker_info"] = current_docker

            return pending_host

    def remove_pending_host(self, agent_token: str) -> bool:
        """
        移除待加入主机

        Args:
            agent_token: Agent唯一标识

        Returns:
            是否成功移除
        """
        with self._lock:
            removed = False
            if agent_token in self._pending_hosts:
                del self._pending_hosts[agent_token]
                removed = True
            if agent_token in self._pending_connections:
                websocket = self._pending_connections[agent_token]
                del self._pending_connections[agent_token]
                if websocket in self._websocket_to_token:
                    del self._websocket_to_token[websocket]
            return removed

    def remove_pending_host_by_websocket(self, websocket: WebSocket) -> bool:
        """
        通过WebSocket连接移除待加入主机

        Args:
            websocket: WebSocket连接

        Returns:
            是否成功移除
        """
        with self._lock:
            agent_token = self._websocket_to_token.get(websocket)
            if agent_token:
                return self.remove_pending_host(agent_token)
            return False

    def transfer_connection_to_host(
        self, agent_token: str, host_id: str
    ) -> Optional[WebSocket]:
        """
        将待加入主机的连接转移到正式主机

        Args:
            agent_token: Agent唯一标识
            host_id: 正式主机的host_id

        Returns:
            WebSocket连接，如果不存在返回None
        """
        with self._lock:
            websocket = self._pending_connections.get(agent_token)
            if websocket:
                # 从待加入列表中移除
                self.remove_pending_host(agent_token)
                print(
                    f"✅ 待加入主机连接已转移: agent_token={agent_token[:16] if agent_token else 'None'}... -> host_id={host_id}"
                )
            return websocket

    def cleanup_stale_hosts(self, timeout_seconds: int = 300):
        """
        清理长时间未心跳的待加入主机

        Args:
            timeout_seconds: 超时时间（秒），默认5分钟
        """
        from datetime import timedelta

        with self._lock:
            now = datetime.now()
            timeout_threshold = now - timedelta(seconds=timeout_seconds)

            stale_tokens = []
            for agent_token, host_info in self._pending_hosts.items():
                last_heartbeat = host_info.get("last_heartbeat")
                if last_heartbeat and last_heartbeat < timeout_threshold:
                    stale_tokens.append(agent_token)

            for agent_token in stale_tokens:
                self.remove_pending_host(agent_token)
                print(
                    f"🧹 清理超时待加入主机: agent_token={agent_token[:16] if agent_token else 'None'}..."
                )

            if stale_tokens:
                print(f"✅ 清理了 {len(stale_tokens)} 个超时待加入主机")


# 全局单例实例
pending_host_manager = PendingHostManager()

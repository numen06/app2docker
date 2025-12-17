# backend/agent/websocket_client.py
"""
WebSocket 客户端封装
负责连接管理、消息发送和接收、自动重连机制
"""
import asyncio
import json
import logging
import os
from typing import Optional, Callable, Dict, Any
from websockets.client import connect, WebSocketClientProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket 客户端"""

    def __init__(
        self,
        server_url: str,
        token: Optional[str] = None,
        secret_key: Optional[str] = None,
        agent_token: Optional[str] = None,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        reconnect_interval: int = 5,
        heartbeat_interval: int = 30,
        heartbeat_data_callback: Optional[Callable[[], Dict[str, Any]]] = None,
    ):
        """
        初始化 WebSocket 客户端

        Args:
            server_url: 服务器 WebSocket URL (ws://host:port 或 wss://host:port)
            token: Agent 认证 token（旧方式，向后兼容）
            secret_key: Agent 认证密钥（新方式）
            agent_token: Agent 唯一标识（新方式，可选）
            on_message: 消息处理回调函数
            on_connect: 连接成功回调函数
            on_disconnect: 断开连接回调函数
            reconnect_interval: 重连间隔（秒）
            heartbeat_interval: 心跳间隔（秒）
            heartbeat_data_callback: 心跳数据回调函数，返回要包含在心跳消息中的额外数据
        """
        self.server_url = server_url.rstrip("/")
        # 确保 URL 是 WebSocket 协议
        if not self.server_url.startswith(("ws://", "wss://")):
            # 如果是 http/https，转换为 ws/wss
            self.server_url = self.server_url.replace("http://", "ws://").replace(
                "https://", "wss://"
            )

        # 构建完整的 WebSocket URL
        if secret_key:
            # 新方式：使用 secret_key 和 agent_token
            import urllib.parse

            params = {"secret_key": secret_key}
            if agent_token:
                params["agent_token"] = agent_token
            query_string = urllib.parse.urlencode(params)
            ws_path = f"/api/ws/agent?{query_string}"
        else:
            # 旧方式：使用 token（向后兼容）
            ws_path = f"/api/ws/agent?token={token}"

        if self.server_url.endswith("/"):
            self.ws_url = f"{self.server_url}{ws_path.lstrip('/')}"
        else:
            self.ws_url = f"{self.server_url}{ws_path}"

        self.token = token
        self.secret_key = secret_key
        self.agent_token = agent_token
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.reconnect_interval = reconnect_interval
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_data_callback = heartbeat_data_callback

        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected = False
        self.running = False
        self._reconnect_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """连接到服务器"""
        try:
            logger.info(f"正在连接到服务器: {self.ws_url}")
            # 使用 asyncio.wait_for 设置连接超时
            self.websocket = await asyncio.wait_for(
                connect(self.ws_url, ping_interval=None, ping_timeout=None),
                timeout=10.0,  # 10秒连接超时
            )
            self.connected = True

            if self.on_connect:
                self.on_connect()

            logger.info("✅ WebSocket 连接成功")
            return True
        except asyncio.TimeoutError:
            logger.error(f"❌ WebSocket 连接超时（10秒）")
            logger.error(f"   请检查：")
            logger.error(f"   1. 主程序是否正在运行")
            logger.error(f"   2. SERVER_URL 是否正确（在 Docker 中不能使用 localhost）")
            logger.error(f"   3. 网络是否可达")
            logger.error(f"   连接 URL: {self.ws_url}")
            self.connected = False
            return False
        except ConnectionRefusedError as e:
            logger.error(f"❌ WebSocket 连接被拒绝: {e}")
            logger.error(f"   请检查：")
            logger.error(f"   1. 主程序是否正在运行")
            logger.error(f"   2. SERVER_URL 是否正确（在 Docker 中不能使用 localhost）")
            logger.error(f"   3. 端口是否正确")
            logger.error(f"   连接 URL: {self.ws_url}")
            self.connected = False
            return False
        except Exception as e:
            logger.error(f"❌ WebSocket 连接失败: {type(e).__name__}: {e}")
            logger.error(f"   连接 URL: {self.ws_url}")
            self.connected = False
            return False

    async def disconnect(self):
        """断开连接"""
        self.running = False
        self.connected = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass

        if self.on_disconnect:
            self.on_disconnect()

        logger.info("WebSocket 已断开连接")

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """发送消息（带重试机制）"""
        if not self.connected or not self.websocket:
            logger.warning(
                f"WebSocket 未连接，无法发送消息: type={message.get('type')}, "
                f"connected={self.connected}, websocket={self.websocket is not None}"
            )
            return False

        # 重试机制：最多重试2次
        max_retries = 2
        last_error = None

        for attempt in range(max_retries):
            try:
                # 发送前再次检查连接状态
                if not self.connected or not self.websocket:
                    logger.debug(f"连接已断开，取消发送: type={message.get('type')}")
                    return False

                message_str = json.dumps(message)
                await self.websocket.send(message_str)
                if attempt > 0:
                    logger.info(
                        f"✅ 消息已发送（重试 {attempt} 次后成功）: type={message.get('type')}"
                    )
                # 正常发送成功时不记录日志（减少日志量）
                return True
            except ConnectionClosed as e:
                # 远端关闭连接（包括 no close frame 等情况），视为正常断连，走统一重连逻辑
                logger.debug(
                    f"WebSocket 已关闭，发送失败: type={message.get('type')}, code={getattr(e, 'code', None)}, reason={getattr(e, 'reason', '')}"
                )
                last_error = e
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # 短暂等待后重试
                    await asyncio.sleep(0.1)
                    # 检查连接状态
                    if not self.connected or not self.websocket:
                        logger.debug(
                            f"连接已断开，停止重试: type={message.get('type')}"
                        )
                        break
                else:
                    logger.error(
                        f"❌ 发送消息失败（{max_retries}次尝试后）: type={message.get('type')}, error={e}"
                    )

        # 所有重试都失败或连接已关闭
        # 如果连接已关闭，不重复触发重连（重连循环已经在运行）
        if last_error is not None:
            if isinstance(last_error, ConnectionClosed):
                # ConnectionClosed 说明连接已断开，_receive_loop 或重连循环会处理
                logger.debug(
                    f"连接已关闭，发送失败: type={message.get('type')}（重连循环将处理）"
                )
            else:
                logger.warning(
                    f"发送消息失败: type={message.get('type')}, error={last_error}"
                )

        # 只有在连接状态还是 True 时才标记为 False，避免重复操作
        if self.connected:
            self.connected = False
            # 确保重连任务正在运行（但避免重复创建）
            if self.running and (
                not self._reconnect_task or self._reconnect_task.done()
            ):
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        return False

    async def _receive_loop(self):
        """接收消息循环"""
        # 给连接一点时间稳定，避免立即检测到关闭
        await asyncio.sleep(0.1)

        while self.running and self.connected:
            try:
                if not self.websocket:
                    logger.debug("WebSocket 对象不存在，退出接收循环")
                    break

                message = await self.websocket.recv()

                try:
                    data = json.loads(message)
                    if self.on_message:
                        self.on_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"收到无效的 JSON 消息: {message}")

            except ConnectionClosed as e:
                # 连接已关闭，记录日志但不重复触发重连（重连循环已在运行）
                logger.debug(
                    f"WebSocket 连接已关闭: code={getattr(e, 'code', None)}, reason={getattr(e, 'reason', '')}"
                )
                # 只有在连接状态还是 True 时才标记为 False
                if self.connected:
                    self.connected = False
                # 重连任务应该已经在运行，不需要重复创建
                break
            except Exception as e:
                logger.error(f"接收消息时出错: {e}")
                # 只有在连接状态还是 True 时才标记为 False
                if self.connected:
                    self.connected = False
                # 确保重连任务正在运行（但避免重复创建）
                if self.running and (
                    not self._reconnect_task or self._reconnect_task.done()
                ):
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())
                break

    async def _heartbeat_loop(self):
        """心跳循环"""
        import time

        while self.running and self.connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.connected:
                    heartbeat_message = {"type": "heartbeat", "timestamp": time.time()}

                    # 如果使用新方式且有agent_token，添加到心跳消息中
                    if self.agent_token:
                        heartbeat_message["agent_token"] = self.agent_token

                    # 如果提供了心跳数据回调，获取额外数据并添加到心跳消息中
                    if self.heartbeat_data_callback:
                        try:
                            extra_data = self.heartbeat_data_callback()
                            if extra_data:
                                heartbeat_message.update(extra_data)
                        except Exception as e:
                            logger.warning(f"获取心跳数据失败: {e}")

                    await self.send_message(heartbeat_message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳发送失败: {e}")
                self.connected = False
                # 确保重连任务正在运行
                if not self._reconnect_task or self._reconnect_task.done():
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        """自动重连循环"""
        while self.running:
            if not self.connected:
                logger.info(f"尝试重连... ({self.reconnect_interval}秒后)")
                await asyncio.sleep(self.reconnect_interval)

                # 如果已经停止，退出循环
                if not self.running:
                    break

                # 再次检查连接状态（可能在等待期间已经连接成功）
                if self.connected:
                    logger.debug("连接已恢复，跳过重连")
                    continue

                if await self.connect():
                    # 重新启动接收和心跳任务
                    # 先取消旧的心跳任务（如果存在）
                    if self._heartbeat_task and not self._heartbeat_task.done():
                        self._heartbeat_task.cancel()
                        try:
                            await self._heartbeat_task
                        except asyncio.CancelledError:
                            pass

                    # 启动新的接收和心跳任务
                    asyncio.create_task(self._receive_loop())
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                    logger.info("✅ 重连成功，已恢复接收和心跳")
            else:
                # 连接正常，等待一段时间后再检查
                await asyncio.sleep(1)

    async def start(self):
        """启动客户端"""
        self.running = True

        # 先尝试初始连接
        if await self.connect():
            # 连接成功，启动接收和心跳任务
            asyncio.create_task(self._receive_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            # 连接成功后，再启动重连任务（作为保底机制，正常情况下不会触发）
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        else:
            # 初始连接失败，立即启动重连任务
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def stop(self):
        """停止客户端"""
        await self.disconnect()
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

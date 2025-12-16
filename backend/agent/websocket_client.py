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
        token: str,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
        reconnect_interval: int = 5,
        heartbeat_interval: int = 30,
    ):
        """
        初始化 WebSocket 客户端

        Args:
            server_url: 服务器 WebSocket URL (ws://host:port 或 wss://host:port)
            token: Agent 认证 token
            on_message: 消息处理回调函数
            on_connect: 连接成功回调函数
            on_disconnect: 断开连接回调函数
            reconnect_interval: 重连间隔（秒）
            heartbeat_interval: 心跳间隔（秒）
        """
        self.server_url = server_url.rstrip("/")
        # 确保 URL 是 WebSocket 协议
        if not self.server_url.startswith(("ws://", "wss://")):
            # 如果是 http/https，转换为 ws/wss
            self.server_url = self.server_url.replace("http://", "ws://").replace(
                "https://", "wss://"
            )

        # 构建完整的 WebSocket URL（包含 token 作为查询参数）
        ws_path = f"/api/ws/agent?token={token}"
        if self.server_url.endswith("/"):
            self.ws_url = f"{self.server_url}{ws_path.lstrip('/')}"
        else:
            self.ws_url = f"{self.server_url}{ws_path}"

        self.token = token
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.reconnect_interval = reconnect_interval
        self.heartbeat_interval = heartbeat_interval

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
                message_str = json.dumps(message)
                await self.websocket.send(message_str)
                if attempt > 0:
                    logger.info(
                        f"✅ 消息已发送（重试 {attempt} 次后成功）: type={message.get('type')}"
                    )
                # 正常发送成功时不记录日志（减少日志量）
                return True
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # 短暂等待后重试
                    await asyncio.sleep(0.1)
                    # 检查连接状态
                    if not self.connected or not self.websocket:
                        logger.warning(
                            f"连接已断开，停止重试: type={message.get('type')}"
                        )
                        break
                else:
                    logger.error(
                        f"❌ 发送消息失败（{max_retries}次尝试后）: type={message.get('type')}, error={e}"
                    )
        
        # 所有重试都失败
        logger.error(
            f"❌ 发送消息最终失败: type={message.get('type')}, error={last_error}"
        )
        self.connected = False
        # 确保重连任务正在运行
        if self.running and (
            not self._reconnect_task or self._reconnect_task.done()
        ):
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        return False

    async def _receive_loop(self):
        """接收消息循环"""
        while self.running and self.connected:
            try:
                if not self.websocket:
                    break

                message = await self.websocket.recv()

                try:
                    data = json.loads(message)
                    if self.on_message:
                        self.on_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"收到无效的 JSON 消息: {message}")

            except ConnectionClosed:
                logger.warning("WebSocket 连接已关闭")
                self.connected = False
                # 确保重连任务正在运行
                if not self._reconnect_task or self._reconnect_task.done():
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())
                break
            except Exception as e:
                logger.error(f"接收消息时出错: {e}")
                self.connected = False
                # 确保重连任务正在运行
                if not self._reconnect_task or self._reconnect_task.done():
                    self._reconnect_task = asyncio.create_task(self._reconnect_loop())
                break

    async def _heartbeat_loop(self):
        """心跳循环"""
        import time

        while self.running and self.connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.connected:
                    await self.send_message(
                        {"type": "heartbeat", "timestamp": time.time()}
                    )
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
                await asyncio.sleep(1)

    async def start(self):
        """启动客户端"""
        self.running = True

        # 启动重连任务（无论初始连接是否成功，都需要重连机制）
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

        # 初始连接
        if await self.connect():
            # 启动接收和心跳任务
            asyncio.create_task(self._receive_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        """停止客户端"""
        await self.disconnect()
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

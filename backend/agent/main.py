# backend/agent/main.py
"""
Agent 主程序入口
负责连接主程序的 WebSocket，接收部署任务，执行部署操作，发送执行结果和心跳
"""
# 立即输出，确保 Docker 容器能看到启动信息
import sys
print("=" * 60, file=sys.stdout, flush=True)
print("Agent 程序开始启动...", file=sys.stdout, flush=True)
print(f"Python 版本: {sys.version}", file=sys.stdout, flush=True)
print("=" * 60, file=sys.stdout, flush=True)

import os
import asyncio
import logging
import signal
from typing import Dict, Any, Optional

# 先配置日志，确保启动错误能被看到
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 明确输出到 stdout
    ],
    force=True  # 强制重新配置，避免重复配置问题
)
logger = logging.getLogger(__name__)
logger.info("日志系统已初始化")

# 添加项目根目录到 Python 路径
try:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, project_root)
    logger.info(f"项目根目录: {project_root}")
    logger.info(f"Python 路径: {sys.path[:3]}")
except Exception as e:
    logger.error(f"设置 Python 路径失败: {e}", exc_info=True)
    sys.exit(1)

# 导入模块
try:
    from backend.agent.websocket_client import WebSocketClient
    from backend.agent.deploy_executor import DeployExecutor
    logger.info("✅ 模块导入成功")
except ImportError as e:
    logger.error(f"❌ 模块导入失败: {e}", exc_info=True)
    sys.exit(1)

# 设置其他模块的日志级别
logging.getLogger("backend.agent").setLevel(logging.INFO)
logging.getLogger("websockets").setLevel(logging.WARNING)  # 减少 websockets 库的噪音

# 全局变量
websocket_client: Optional[WebSocketClient] = None
deploy_executor: Optional[DeployExecutor] = None
running = True


def get_host_info() -> Dict[str, Any]:
    """获取主机信息"""
    import platform
    
    info = {
        "hostname": platform.node(),
        "os": platform.system(),
        "os_version": platform.release(),
        "arch": platform.machine(),
    }
    
    # 尝试获取详细的系统信息（需要 psutil）
    try:
        import psutil
        info.update({
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "memory_percent": psutil.virtual_memory().percent,
            "disk_total": psutil.disk_usage('/').total,
            "disk_free": psutil.disk_usage('/').free,
            "disk_percent": psutil.disk_usage('/').percent,
        })
    except ImportError:
        logger.warning("psutil 未安装，无法获取详细的系统信息")
    except Exception as e:
        logger.error(f"获取主机信息失败: {e}")
    
    return info


def get_docker_info() -> Dict[str, Any]:
    """获取 Docker 信息"""
    import subprocess
    
    info = {}
    
    try:
        # Docker 版本
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info["version"] = result.stdout.strip()
    except:
        pass
    
    try:
        # 容器数量
        result = subprocess.run(
            ["docker", "ps", "-q"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            containers = [c for c in result.stdout.strip().split('\n') if c]
            info["container_count"] = len(containers)
    except:
        pass
    
    try:
        # 镜像数量
        result = subprocess.run(
            ["docker", "images", "-q"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            images = [i for i in result.stdout.strip().split('\n') if i]
            info["image_count"] = len(images)
    except:
        pass
    
    return info


def on_connect():
    """连接成功回调"""
    logger.info("✅ 已连接到主程序")
    
    # 发送主机信息
    if websocket_client:
        asyncio.create_task(websocket_client.send_message({
            "type": "host_info",
            "host_info": get_host_info(),
            "docker_info": get_docker_info()
        }))


def on_disconnect():
    """断开连接回调"""
    logger.warning("⚠️ 与主程序断开连接")


def on_message(message: Dict[str, Any]):
    """消息处理回调"""
    message_type = message.get("type")
    
    if message_type == "welcome":
        logger.info(f"收到欢迎消息: {message.get('message')}")
    
    elif message_type == "deploy":
        # 部署任务
        logger.info("收到部署任务")
        asyncio.create_task(handle_deploy_task(message))
    
    elif message_type == "heartbeat_ack":
        # 心跳确认
        pass
    
    elif message_type == "error":
        logger.error(f"收到错误消息: {message.get('message')}")
    
    else:
        logger.warning(f"未知消息类型: {message_type}")


async def handle_deploy_task(message: Dict[str, Any]):
    """处理部署任务"""
    task_id = message.get("task_id")
    deploy_config = message.get("deploy_config", {})
    context = message.get("context", {})
    
    logger.info(f"开始执行部署任务: {task_id}")
    
    if not websocket_client:
        logger.error("WebSocket 客户端未初始化")
        return
    
    # 发送任务开始消息
    await websocket_client.send_message({
        "type": "deploy_result",
        "task_id": task_id,
        "status": "running",
        "message": "部署任务已开始"
    })
    
    try:
        # 获取部署模式（如果有）
        deploy_mode = deploy_config.get("deploy_mode")
        logger.info(f"部署模式: {deploy_mode or '从配置中获取'}")
        logger.info(f"部署配置: {deploy_config}")
        
        # 执行部署
        logger.info(f"开始执行部署操作...")
        result = deploy_executor.execute_deploy(
            deploy_config,
            context,
            deploy_mode=deploy_mode
        )
        
        logger.info(f"部署执行完成，结果: {result}")
        
        # 发送执行结果
        await websocket_client.send_message({
            "type": "deploy_result",
            "task_id": task_id,
            "status": "completed" if result.get("success") else "failed",
            "message": result.get("message"),
            "result": result
        })
        
        logger.info(f"部署任务完成: {task_id}, 成功: {result.get('success')}, 消息: {result.get('message')}")
    
    except Exception as e:
        logger.exception(f"部署任务异常: {task_id}")
        await websocket_client.send_message({
            "type": "deploy_result",
            "task_id": task_id,
            "status": "failed",
            "message": f"部署异常: {str(e)}",
            "error": str(e)
        })


def signal_handler(signum, frame):
    """信号处理器"""
    global running
    logger.info("收到停止信号，正在关闭...")
    running = False


async def main():
    """主函数"""
    global websocket_client, deploy_executor, running
    
    logger.info("=" * 60)
    logger.info("Agent 启动中...")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"Python 版本: {sys.version}")
    logger.info(f"Python 路径: {sys.path[:3]}")
    logger.info("=" * 60)
    
    # 从环境变量获取配置
    agent_token = os.getenv("AGENT_TOKEN")
    server_url = os.getenv("SERVER_URL", "http://localhost:8000")
    
    if not agent_token:
        logger.error("❌ 未设置 AGENT_TOKEN 环境变量")
        logger.error("请设置环境变量: export AGENT_TOKEN=your-token")
        sys.exit(1)
    
    logger.info(f"服务器地址: {server_url}")
    logger.info(f"Token: {agent_token[:8]}...")
    
    # 初始化部署执行器
    deploy_executor = DeployExecutor()
    
    # 初始化 WebSocket 客户端
    websocket_client = WebSocketClient(
        server_url=server_url,
        token=agent_token,
        on_message=on_message,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        reconnect_interval=5,
        heartbeat_interval=30,
    )
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动 WebSocket 客户端
        await websocket_client.start()
        
        # 保持运行
        while running:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
    except Exception as e:
        logger.exception("主程序异常")
    finally:
        # 清理资源
        if websocket_client:
            await websocket_client.stop()
        logger.info("Agent 已停止")


if __name__ == "__main__":
    try:
        logger.info("开始运行 Agent 主程序...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agent 已停止（键盘中断）")
    except Exception as e:
        logger.exception("启动失败")
        print(f"致命错误: {e}", file=sys.stderr)
        sys.exit(1)


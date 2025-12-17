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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],  # 明确输出到 stdout
    force=True,  # 强制重新配置，避免重复配置问题
)
logger = logging.getLogger(__name__)
logger.info("日志系统已初始化")

# 添加项目根目录到 Python 路径
try:
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
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


def generate_agent_unique_id() -> Optional[str]:
    """生成Agent唯一标识
    优先使用Docker的SystemID，如果不可用则使用/etc/machine-id
    """
    import subprocess
    import hashlib

    try:
        # 方法1: 尝试从Docker获取SystemID
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ID}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            system_id = result.stdout.strip()
            if system_id:
                # 使用SHA256生成固定长度的唯一标识
                unique_id = hashlib.sha256(system_id.encode()).hexdigest()[:32]
                logger.info(f"从Docker SystemID生成唯一标识")
                return unique_id
    except Exception as e:
        logger.debug(f"无法从Docker获取SystemID: {e}")

    try:
        # 方法2: 使用/etc/machine-id
        machine_id_path = "/etc/machine-id"
        if os.path.exists(machine_id_path):
            with open(machine_id_path, "r") as f:
                machine_id = f.read().strip()
                if machine_id:
                    # 使用SHA256生成固定长度的唯一标识
                    unique_id = hashlib.sha256(machine_id.encode()).hexdigest()[:32]
                    logger.info(f"从/etc/machine-id生成唯一标识")
                    return unique_id
    except Exception as e:
        logger.debug(f"无法读取/etc/machine-id: {e}")

    logger.warning("无法生成唯一标识，将使用临时标识")
    return None


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

        info.update(
            {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_total": psutil.disk_usage("/").total,
                "disk_free": psutil.disk_usage("/").free,
                "disk_percent": psutil.disk_usage("/").percent,
            }
        )
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
            ["docker", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["version"] = result.stdout.strip()
    except:
        pass

    try:
        # 容器数量
        result = subprocess.run(
            ["docker", "ps", "-q"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            containers = [c for c in result.stdout.strip().split("\n") if c]
            info["container_count"] = len(containers)
    except:
        pass

    try:
        # 镜像数量
        result = subprocess.run(
            ["docker", "images", "-q"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            images = [i for i in result.stdout.strip().split("\n") if i]
            info["image_count"] = len(images)
    except:
        pass

    # 检测 docker-compose 支持
    try:
        result = subprocess.run(
            ["docker-compose", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["compose_supported"] = True
            info["compose_version"] = result.stdout.strip()
        else:
            info["compose_supported"] = False
    except:
        info["compose_supported"] = False

    # 检测 docker stack 支持（需要 Swarm 模式）
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Swarm.LocalNodeState}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            swarm_state = result.stdout.strip()
            info["swarm_mode"] = swarm_state
            info["stack_supported"] = swarm_state == "active"
        else:
            info["stack_supported"] = False
            info["swarm_mode"] = "unknown"
    except:
        info["stack_supported"] = False
        info["swarm_mode"] = "unknown"

    return info


def on_connect():
    """连接成功回调"""
    logger.info("✅ 已连接到主程序")

    # 发送主机信息
    if websocket_client:
        host_info_message = {
            "type": "host_info",
            "host_info": get_host_info(),
            "docker_info": get_docker_info(),
        }
        # 如果使用新方式且有agent_token，添加到消息中
        if websocket_client.agent_token:
            host_info_message["agent_token"] = websocket_client.agent_token
        asyncio.create_task(websocket_client.send_message(host_info_message))


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

    elif message_type == "host_info_ack":
        # 主机信息确认
        logger.debug(f"收到主机信息确认: {message.get('message')}")

    elif message_type == "deploy_result_ack":
        # 部署结果确认
        logger.debug(f"收到部署结果确认: {message.get('message')}")

    elif message_type == "error":
        logger.error(f"收到错误消息: {message.get('message')}")

    else:
        logger.warning(f"未知消息类型: {message_type}")


async def handle_deploy_task(message: Dict[str, Any]):
    """处理部署任务"""
    task_id = message.get("task_id")  # 任务ID（用于匹配）
    target_name = message.get("target_name", "")  # 目标名称
    deploy_config = message.get("deploy_config", {})
    context = message.get("context", {})

    logger.info(f"开始执行部署任务: task_id={task_id}, target={target_name}")

    if not websocket_client:
        logger.error("WebSocket 客户端未初始化")
        return

    # 发送任务开始消息（使用 task_id 匹配）
    running_message = {
        "type": "deploy_result",
        "task_id": task_id,  # 任务ID（用于匹配）
        "target_name": target_name,  # 目标名称（用于区分同一任务的多个目标）
        "status": "running",
        "message": "部署任务已开始",
    }
    logger.info(
        f"准备发送任务开始消息: task_id={task_id}, target={target_name}, message={running_message}"
    )
    send_success = await websocket_client.send_message(running_message)
    if send_success:
        logger.info(f"✅ 任务开始消息已发送: task_id={task_id}, target={target_name}")
    else:
        logger.error(
            f"❌ 任务开始消息发送失败: task_id={task_id}, target={target_name}"
        )

    try:
        # 获取部署模式（如果有）
        deploy_mode = deploy_config.get("deploy_mode")
        logger.info(f"部署模式: {deploy_mode or '从配置中获取'}")
        logger.info(f"部署配置: {deploy_config}")

        # 执行部署
        logger.info(f"开始执行部署操作...")

        # 推送开始执行日志
        async def send_running_log(message: str):
            """发送running状态的日志消息（带重试）"""
            log_message = {
                "type": "deploy_result",
                "task_id": task_id,
                "target_name": target_name,
                "status": "running",
                "message": message,
            }
            max_retries = 2
            for attempt in range(max_retries):
                success = await websocket_client.send_message(log_message)
                if success:
                    return True
                elif attempt < max_retries - 1:
                    await asyncio.sleep(0.1)  # 短暂等待后重试
            logger.warning(f"发送running日志失败: {message[:50]}")
            return False

        await send_running_log("开始执行部署操作...")
        # 短暂延迟，确保消息发送完成
        await asyncio.sleep(0.2)

        result = deploy_executor.execute_deploy(
            deploy_config, context, deploy_mode=deploy_mode
        )

        logger.info(f"部署执行完成，结果: {result}")
        logger.info(
            f"部署结果详情: success={result.get('success')}, message={result.get('message')}, returncode={result.get('returncode', 'N/A')}"
        )

        # 推送执行完成日志（包含命令输出）
        if result.get("success"):
            output = result.get("output", "").strip()
            if output:
                await send_running_log(f"命令执行成功，输出: {output[:200]}")
                # 短暂延迟，确保消息发送完成
                await asyncio.sleep(0.2)
        else:
            error = result.get("error", "").strip()
            if error:
                await send_running_log(f"命令执行失败: {error[:200]}")
                # 短暂延迟，确保消息发送完成
                await asyncio.sleep(0.2)

        # 发送执行结果（使用 task_id 匹配）
        deploy_status = "completed" if result.get("success") else "failed"
        deploy_message = {
            "type": "deploy_result",
            "task_id": task_id,  # 任务ID（用于匹配）
            "target_name": target_name,  # 目标名称（用于区分同一任务的多个目标）
            "status": deploy_status,
            "message": result.get("message"),
            "result": result,
        }

        # 如果失败，添加error字段到消息顶层（方便主程序处理）
        if deploy_status == "failed":
            deploy_message["error"] = result.get(
                "error", result.get("message", "部署失败")
            )

        logger.info(
            f"准备发送部署结果: task_id={task_id}, target={target_name}, status={deploy_status}"
        )
        logger.info(
            f"部署结果消息内容: type={deploy_message.get('type')}, task_id={deploy_message.get('task_id')}, "
            f"target_name={deploy_message.get('target_name')}, status={deploy_message.get('status')}"
        )
        logger.info(f"部署结果消息完整内容: {deploy_message}")
        # 计算future_key，用于调试
        future_key_for_debug = f"{task_id}:{target_name}"
        logger.info(f"预期的future_key应该是: {future_key_for_debug}")

        # 尝试发送消息，最多重试3次
        max_retries = 3
        send_success = False
        for attempt in range(max_retries):
            send_success = await websocket_client.send_message(deploy_message)
            if send_success:
                logger.info(
                    f"✅ 部署结果消息已发送: task_id={task_id}, target={target_name}, status={deploy_status}"
                )
                # 短暂延迟，确保消息发送完成
                await asyncio.sleep(0.2)
                break
            else:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 0.5  # 0.5秒, 1秒
                    logger.warning(
                        f"⚠️ 部署结果消息发送失败（尝试 {attempt + 1}/{max_retries}），"
                        f"{wait_time}秒后重试: task_id={task_id}, target={target_name}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"❌ 部署结果消息发送失败（{max_retries}次尝试后）: "
                        f"task_id={task_id}, target={target_name}, status={deploy_status}"
                    )
                    # 即使发送失败，也记录到本地日志，确保不会丢失
                    logger.error(f"最终部署结果（未发送）: {deploy_message}")

        logger.info(
            f"部署任务完成: task_id={task_id}, target={target_name}, 成功: {result.get('success')}, 消息: {result.get('message')}"
        )

    except Exception as e:
        logger.exception(f"部署任务异常: task_id={task_id}, target={target_name}")
        await websocket_client.send_message(
            {
                "type": "deploy_result",
                "task_id": task_id,  # 任务ID（用于匹配）
                "target_name": target_name,  # 目标名称
                "status": "failed",
                "message": f"部署异常: {str(e)}",
                "error": str(e),
            }
        )


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
    # 新方式：使用 AGENT_SECRET_KEY（必需）和可选的 AGENT_TOKEN（用于标识已知主机）
    # 旧方式：使用 AGENT_TOKEN（向后兼容）
    secret_key = os.getenv("AGENT_SECRET_KEY")
    agent_token = os.getenv("AGENT_TOKEN")  # 可选，用于标识已知主机
    server_url = os.getenv("SERVER_URL", "http://localhost:8000")

    # 如果没有设置新方式的密钥，检查旧方式的token
    if not secret_key and not agent_token:
        logger.error("❌ 未设置认证信息")
        logger.error("新方式：请设置环境变量: export AGENT_SECRET_KEY=your-secret-key")
        logger.error(
            "旧方式（向后兼容）：请设置环境变量: export AGENT_TOKEN=your-token"
        )
        sys.exit(1)

    # 如果使用新方式但没有设置token，尝试生成唯一标识
    if secret_key and not agent_token:
        agent_token = generate_agent_unique_id()
        if agent_token:
            logger.info(f"已生成唯一标识: {agent_token[:16]}...")
        else:
            logger.warning("⚠️  无法生成唯一标识，将使用临时标识")

    logger.info(f"服务器地址: {server_url}")
    if secret_key:
        logger.info(f"密钥: {secret_key[:8]}...")
    if agent_token:
        logger.info(f"标识: {agent_token[:16]}...")

    # 初始化部署执行器
    deploy_executor = DeployExecutor()

    # 初始化 WebSocket 客户端
    def get_heartbeat_data():
        """获取心跳数据（包含host_info和docker_info）"""
        try:
            return {
                "host_info": get_host_info(),
                "docker_info": get_docker_info(),
            }
        except Exception as e:
            logger.warning(f"获取心跳数据失败: {e}")
            return {}

    # 根据认证方式初始化WebSocket客户端
    if secret_key:
        # 新方式：使用secret_key和agent_token
        websocket_client = WebSocketClient(
            server_url=server_url,
            secret_key=secret_key,
            agent_token=agent_token,
            on_message=on_message,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            reconnect_interval=5,
            heartbeat_interval=30,
            heartbeat_data_callback=get_heartbeat_data,
        )
    else:
        # 旧方式：使用token（向后兼容）
        websocket_client = WebSocketClient(
            server_url=server_url,
            token=agent_token,
            on_message=on_message,
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            reconnect_interval=5,
            heartbeat_interval=30,
            heartbeat_data_callback=get_heartbeat_data,
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
        sys.exit(0)
    except SystemExit as e:
        # 重新抛出 SystemExit，让 shell 脚本能看到退出码
        raise
    except Exception as e:
        # 确保错误输出到 stderr
        import traceback

        print("=" * 60, file=sys.stderr)
        print("致命错误:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        logger.exception("启动失败")
        sys.exit(1)

# backend/app.py
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from backend.routes import router
from backend.utils import ensure_dirs

# 创建 FastAPI 应用
app = FastAPI(
    title="App2Docker API",
    description="一键将应用打包成 Docker 镜像的可视化平台 - 支持 Java、Node.js、静态网站等多种应用类型",
    version="2.0.0",
)

# CORS 配置（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发环境）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（添加 /api 前缀）
app.include_router(router, prefix="/api")

# 静态文件服务（前端构建产物）
if os.path.exists("dist/assets"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")


# 前端页面路由
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """提供前端页面"""
    index_file = "dist/index.html"
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse(
        content="<h1>前端未构建</h1><p>请先运行前端开发服务器或构建前端</p>",
        status_code=404,
    )


@app.get("/favicon.ico")
async def serve_favicon():
    """提供 favicon（优先使用前端构建产物中的 favicon）"""
    # 优先使用前端构建产物中的 favicon
    dist_favicon = "dist/favicon.ico"
    if os.path.exists(dist_favicon):
        return FileResponse(dist_favicon, media_type="image/x-icon")

    # 回退到 public 目录的 favicon（开发模式）
    public_favicon = "frontend/public/favicon.ico"
    if os.path.exists(public_favicon):
        return FileResponse(public_favicon, media_type="image/x-icon")

    # 回退到根目录的 favicon
    root_favicon = "favicon.ico"
    if os.path.exists(root_favicon):
        return FileResponse(root_favicon, media_type="image/x-icon")

    # 最后使用 vite 默认图标
    vite_svg = "frontend/public/vite.svg"
    if os.path.exists(vite_svg):
        return FileResponse(vite_svg, media_type="image/svg+xml")

    # 如果都不存在，返回 404
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="Favicon not found")


# 健康检查端点（在 /api 之外）
@app.get("/health")
async def health_check_root():
    """健康检查（根路径）"""
    return {"status": "healthy", "service": "app2docker"}


# 也在 /api/health 提供
@app.get("/api/health")
async def health_check_api():
    """健康检查（API 路径）"""
    return {"status": "healthy", "service": "app2docker"}


# 全局变量：本地 Agent WebSocket 客户端
_local_agent_client = None


def get_local_host_info():
    """获取本地主机信息（复用agent/main.py的逻辑）"""
    import platform
    from typing import Dict, Any

    info: Dict[str, Any] = {
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
        print("⚠️ psutil 未安装，无法获取详细的系统信息")
    except Exception as e:
        print(f"⚠️ 获取主机信息失败: {e}")

    return info


def get_local_docker_info():
    """获取本地 Docker 信息（复用agent/main.py的逻辑）"""
    import subprocess
    from typing import Dict, Any

    info: Dict[str, Any] = {}

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
            info["containers"] = len(containers)
    except:
        pass

    try:
        # 镜像数量
        result = subprocess.run(
            ["docker", "images", "-q"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            images = [i for i in result.stdout.strip().split("\n") if i]
            info["images"] = len(images)
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


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    import asyncio
    from backend.config import ensure_config_exists, load_config
    from backend.scheduler import start_scheduler
    from backend.agent_host_manager import AgentHostManager
    from backend.agent.websocket_client import WebSocketClient
    import platform

    # 确保配置文件存在
    ensure_config_exists()

    # 确保必要的目录存在
    ensure_dirs()

    # 初始化数据库（包括迁移）
    from backend.database import init_db

    init_db()

    # 启动流水线调度器
    start_scheduler()

    # 自动注册主程序为 Agent 并连接
    global _local_agent_client
    try:
        agent_manager = AgentHostManager()
        agent_hosts = agent_manager.list_agent_hosts()

        # 检查是否已存在名为"本地主机"的 Agent
        local_agent = None
        for host in agent_hosts:
            if host.get("name") == "本地主机":
                local_agent = host
                print(f"✅ 本地 Agent 已存在: {host.get('host_id')}")
                break

        # 如果不存在，创建本地 Agent
        if not local_agent:
            local_agent = agent_manager.add_agent_host(
                name="本地主机", description="主程序自动注册的本地 Agent"
            )
            print(f"✅ 已自动注册本地 Agent: {local_agent.get('host_id')}")
            print(f"   Token: {local_agent.get('token')}")

        # 立即获取并更新本地主机的host_info和docker_info
        try:
            host_info = get_local_host_info()
            docker_info = get_local_docker_info()

            # 更新主机状态和信息（设置为online，因为本地agent是直接连接的）
            agent_manager.update_host_status(
                local_agent.get("host_id"),
                "online",
                host_info=host_info,
                docker_info=docker_info,
            )
            print(
                f"✅ 已更新本地 Agent 主机信息: host_info={len(host_info)}项, docker_info={len(docker_info)}项"
            )
        except Exception as e:
            print(f"⚠️ 更新本地 Agent 主机信息失败: {e}")
            import traceback

            traceback.print_exc()

        # 启动本地 Agent WebSocket 客户端连接到自身
        try:
            config = load_config()
            server_config = config.get("server", {})
            host_addr = os.getenv("APP_HOST", server_config.get("host", "0.0.0.0"))
            port = int(os.getenv("APP_PORT", server_config.get("port", 8000)))

            # 构建服务器 URL
            # 如果是 0.0.0.0，使用 localhost 或 127.0.0.1
            if host_addr == "0.0.0.0":
                server_url = f"http://127.0.0.1:{port}"
            else:
                server_url = f"http://{host_addr}:{port}"

            # 创建 WebSocket 客户端
            def on_connect():
                """连接成功回调 - 立即发送主机信息"""
                print("✅ 本地 Agent 已连接到主程序")

                # 验证连接是否已注册到active_connections
                from backend.websocket_handler import active_connections

                host_id = local_agent.get("host_id")
                if host_id in active_connections:
                    print(f"✅ 本地 Agent 连接已注册到 active_connections: {host_id}")
                else:
                    print(f"⚠️ 本地 Agent 连接未注册到 active_connections: {host_id}")
                    print(
                        f"   当前 active_connections keys: {list(active_connections.keys())}"
                    )

                # 连接成功后，立即发送主机信息
                if _local_agent_client:
                    # 获取最新的主机信息
                    try:
                        host_info = get_local_host_info()
                        docker_info = get_local_docker_info()

                        # 发送host_info消息
                        asyncio.create_task(
                            _local_agent_client.send_message(
                                {
                                    "type": "host_info",
                                    "host_info": host_info,
                                    "docker_info": docker_info,
                                }
                            )
                        )
                        print("✅ 已发送本地 Agent 主机信息")

                        # 同时更新数据库中的主机信息
                        try:
                            agent_manager.update_host_status(
                                local_agent.get("host_id"),
                                "online",
                                host_info=host_info,
                                docker_info=docker_info,
                            )
                            print("✅ 已更新本地 Agent 主机状态为 online")
                        except Exception as update_error:
                            print(f"⚠️ 更新本地 Agent 主机状态失败: {update_error}")
                    except Exception as e:
                        print(f"⚠️ 发送本地 Agent 主机信息失败: {e}")
                        print(f"   错误类型: {type(e).__name__}")
                        import traceback

                        traceback.print_exc()

            def on_disconnect():
                """断开连接回调"""
                print("⚠️ 本地 Agent 与主程序断开连接")
                # 更新主机状态为offline
                try:
                    agent_manager.update_host_status(
                        local_agent.get("host_id"), "offline"
                    )
                    print("✅ 已更新本地 Agent 主机状态为 offline")
                except Exception as e:
                    print(f"⚠️ 更新本地 Agent 状态失败: {e}")
                    print(f"   错误类型: {type(e).__name__}")
                    import traceback

                    traceback.print_exc()

            def on_message(message):
                """消息处理回调"""
                # 处理来自主程序的消息（部署任务等）
                message_type = message.get("type")
                if message_type == "deploy":
                    # 部署任务 - 本地agent需要处理部署任务
                    print(
                        f"📥 本地 Agent 收到部署任务: task_id={message.get('task_id')}, target={message.get('target_name')}"
                    )
                    # 在后台任务中处理部署任务
                    asyncio.create_task(handle_local_deploy_task(message))
                elif message_type == "welcome":
                    print(f"✅ 收到欢迎消息: {message.get('message')}")
                elif message_type == "heartbeat_ack":
                    # 心跳确认
                    pass
                elif message_type == "host_info_ack":
                    print(f"✅ 收到主机信息确认: {message.get('message')}")
                elif message_type == "error":
                    print(f"❌ 收到错误消息: {message.get('message')}")

            async def handle_local_deploy_task(message: Dict[str, Any]):
                """处理本地agent的部署任务"""
                try:
                    from backend.agent.deploy_executor import DeployExecutor
                    import logging

                    logger = logging.getLogger(__name__)

                    task_id = message.get("task_id")
                    target_name = message.get("target_name", "")
                    deploy_config = message.get("deploy_config", {})
                    context = message.get("context", {})
                    deploy_task_id = message.get("deploy_task_id", task_id)

                    logger.info(
                        f"[本地Agent] 开始执行部署任务: task_id={task_id}, target={target_name}"
                    )
                    print(
                        f"[本地Agent] 开始执行部署任务: task_id={task_id}, target={target_name}"
                    )

                    # 初始化部署执行器
                    deploy_executor = DeployExecutor()

                    # 发送任务开始消息
                    if _local_agent_client:
                        await _local_agent_client.send_message(
                            {
                                "type": "deploy_result",
                                "task_id": task_id,
                                "deploy_task_id": deploy_task_id,
                                "target_name": target_name,
                                "status": "running",
                                "message": "部署任务已开始",
                            }
                        )

                    # 执行部署
                    deploy_mode = deploy_config.get("deploy_mode")
                    result = deploy_executor.execute_deploy(
                        deploy_config, context, deploy_mode=deploy_mode
                    )

                    logger.info(
                        f"[本地Agent] 部署执行完成: task_id={task_id}, success={result.get('success')}"
                    )
                    print(
                        f"[本地Agent] 部署执行完成: task_id={task_id}, success={result.get('success')}"
                    )

                    # 发送执行结果
                    deploy_status = "completed" if result.get("success") else "failed"
                    if _local_agent_client:
                        await _local_agent_client.send_message(
                            {
                                "type": "deploy_result",
                                "task_id": task_id,
                                "deploy_task_id": deploy_task_id,
                                "target_name": target_name,
                                "status": deploy_status,
                                "message": result.get("message", ""),
                                "result": result,
                                "error": result.get("error"),
                            }
                        )
                        logger.info(
                            f"[本地Agent] 部署结果已发送: task_id={task_id}, status={deploy_status}"
                        )
                        print(
                            f"[本地Agent] 部署结果已发送: task_id={task_id}, status={deploy_status}"
                        )

                except Exception as e:
                    import traceback

                    logger.exception(f"[本地Agent] 部署任务异常: task_id={task_id}")
                    print(f"❌ [本地Agent] 部署任务异常: {e}")
                    traceback.print_exc()

                    # 发送失败消息
                    if _local_agent_client:
                        try:
                            await _local_agent_client.send_message(
                                {
                                    "type": "deploy_result",
                                    "task_id": message.get("task_id"),
                                    "deploy_task_id": message.get(
                                        "deploy_task_id", message.get("task_id")
                                    ),
                                    "target_name": message.get("target_name", ""),
                                    "status": "failed",
                                    "message": f"部署异常: {str(e)}",
                                    "error": str(e),
                                }
                            )
                        except:
                            pass

            def get_heartbeat_data():
                """获取心跳数据（包含host_info和docker_info）"""
                try:
                    return {
                        "host_info": get_local_host_info(),
                        "docker_info": get_local_docker_info(),
                    }
                except Exception as e:
                    print(f"⚠️ 获取心跳数据失败: {e}")
                    return {}

            _local_agent_client = WebSocketClient(
                server_url=server_url,
                token=local_agent.get("token"),
                on_message=on_message,
                on_connect=on_connect,
                on_disconnect=on_disconnect,
                reconnect_interval=5,
                heartbeat_interval=30,
                heartbeat_data_callback=get_heartbeat_data,
            )

            # 在后台任务中启动 WebSocket 客户端
            asyncio.create_task(_local_agent_client.start())
            print(f"✅ 本地 Agent WebSocket 客户端已启动，连接到: {server_url}")
            print(f"   本地 Agent host_id: {local_agent.get('host_id')}")
            print(f"   本地 Agent token: {local_agent.get('token')[:8]}...")

            # 等待一小段时间，让连接有机会建立
            await asyncio.sleep(1)

            # 检查连接状态
            from backend.websocket_handler import active_connections

            host_id = local_agent.get("host_id")
            if host_id in active_connections:
                print(f"✅ 本地 Agent 连接已建立并注册: {host_id}")
            else:
                print(f"⚠️ 本地 Agent 连接尚未建立: {host_id}")
                print(
                    f"   当前 active_connections keys: {list(active_connections.keys())}"
                )
                print(f"   提示: 连接可能在后台建立中，请稍候...")

        except Exception as e:
            print(f"⚠️ 启动本地 Agent WebSocket 客户端失败: {e}")
            print(f"   错误类型: {type(e).__name__}")
            print(f"   错误详情: {str(e)}")
            import traceback

            traceback.print_exc()

            # 如果WebSocket连接失败，至少确保主机信息已更新
            try:
                # 再次尝试更新主机信息（即使连接失败，信息也应该可用）
                host_info = get_local_host_info()
                docker_info = get_local_docker_info()
                agent_manager.update_host_status(
                    local_agent.get("host_id"),
                    "offline",  # 连接失败，状态为offline
                    host_info=host_info,
                    docker_info=docker_info,
                )
                print(f"✅ 本地 Agent 连接失败，但已保存主机信息（状态: offline）")
                print(f"   提示: 本地 Agent 主机信息已保存，但 WebSocket 连接失败")
                print(f"   可能原因:")
                print(f"   1. 服务器 URL 配置错误")
                print(f"   2. 端口被占用或防火墙阻止")
                print(f"   3. WebSocket 服务未正确启动")
                print(f"   建议: 检查服务器配置和网络连接")
            except Exception as update_error:
                print(f"❌ 更新本地 Agent 主机信息失败: {update_error}")
                print(f"   错误类型: {type(update_error).__name__}")
                import traceback

                traceback.print_exc()

    except Exception as e:
        print(f"❌ 自动注册本地 Agent 失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误详情: {str(e)}")
        print(f"   提示: 本地 Agent 主机可能无法正常使用")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("🚀 App2Docker 服务已启动")
    print("=" * 60)
    print("📍 后端 API: http://localhost:8000")
    print("📍 API 文档: http://localhost:8000/docs")
    print("📍 前端开发: http://localhost:3000 (需单独启动)")
    print("")
    print("📁 目录结构:")
    print("  ├── 上传: data/uploads/")
    print("  ├── 构建: data/docker_build/")
    print("  ├── 导出: data/exports/")
    print("  ├── 内置模板: templates/jar, templates/nodejs (只读)")
    print("  └── 用户模板: data/templates/jar, data/templates/nodejs (可读写)")
    print("")
    print("⚙️  配置文件: data/config.yml")
    print("⏰ 流水线调度器: 已启动")
    print("=" * 60)


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    global _local_agent_client
    from backend.scheduler import stop_scheduler

    # 停止本地 Agent WebSocket 客户端
    if _local_agent_client:
        try:
            await _local_agent_client.stop()
            print("✅ 本地 Agent WebSocket 客户端已停止")
        except Exception as e:
            print(f"⚠️ 停止本地 Agent WebSocket 客户端失败: {e}")

    # 停止流水线调度器
    stop_scheduler()

    print("\n👋 服务已停止")


# 命令行启动入口
if __name__ == "__main__":
    import uvicorn
    from backend.config import load_config

    # 从配置文件或环境变量读取端口
    config = load_config()
    server_config = config.get("server", {})
    host = os.getenv("APP_HOST", server_config.get("host", "0.0.0.0"))
    port = int(os.getenv("APP_PORT", server_config.get("port", 8000)))

    print(f"🌐 服务监听: {host}:{port}")

    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )

# backend/app.py
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

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
                name="本地主机",
                description="主程序自动注册的本地 Agent"
            )
            print(f"✅ 已自动注册本地 Agent: {local_agent.get('host_id')}")
            print(f"   Token: {local_agent.get('token')}")
        
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
                print("✅ 本地 Agent 已连接到主程序")
            
            def on_disconnect():
                print("⚠️ 本地 Agent 与主程序断开连接")
            
            def on_message(message):
                # 处理来自主程序的消息（部署任务等）
                message_type = message.get("type")
                if message_type == "deploy":
                    # 部署任务会在主程序中处理，这里只是接收
                    pass
            
            _local_agent_client = WebSocketClient(
                server_url=server_url,
                token=local_agent.get("token"),
                on_message=on_message,
                on_connect=on_connect,
                on_disconnect=on_disconnect,
                reconnect_interval=5,
                heartbeat_interval=30,
            )
            
            # 在后台任务中启动 WebSocket 客户端
            asyncio.create_task(_local_agent_client.start())
            print(f"✅ 本地 Agent WebSocket 客户端已启动，连接到: {server_url}")
            
        except Exception as e:
            print(f"⚠️ 启动本地 Agent WebSocket 客户端失败: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"⚠️ 自动注册本地 Agent 失败: {e}")
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

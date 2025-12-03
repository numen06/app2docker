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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "null",
    ],  # Vite 默认端口 + file:// 协议
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（添加 /api 前缀）
app.include_router(router, prefix="/api")

# 静态文件服务（前端构建产物）
if os.path.exists("dist"):
    app.mount("/static", StaticFiles(directory="dist/static"), name="static")


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
        return FileResponse(dist_favicon)

    # 回退到根目录的 favicon（开发模式）
    root_favicon = "favicon.ico"
    if os.path.exists(root_favicon):
        return FileResponse(root_favicon)

    # 最后使用 vite 默认图标
    return FileResponse("frontend/public/vite.svg")


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


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    from backend.config import ensure_config_exists

    # 确保配置文件存在
    ensure_config_exists()

    # 确保必要的目录存在
    ensure_dirs()

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
    print("=" * 60)


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
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

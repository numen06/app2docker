@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🚀 启动 App2Docker 开发环境
echo ================================
echo.

REM 检查 Python 是否安装
where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo ❌ 未找到 Python，请先安装 Python
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

REM 检查后端虚拟环境
if not exist ".venv" (
    echo 📦 创建 Python 虚拟环境...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo ❌ 创建虚拟环境失败，请确保已安装 Python
        exit /b 1
    )
    if not exist ".venv\Scripts\activate.bat" (
        echo ❌ 虚拟环境创建不完整
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    if errorlevel 1 (
        echo ❌ 激活虚拟环境失败
        exit /b 1
    )
    echo 📦 安装 Python 依赖...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 安装依赖失败
        exit /b 1
    )
) else (
    if not exist ".venv\Scripts\activate.bat" (
        echo ⚠️  虚拟环境目录存在但无效，正在重新创建...
        rmdir /s /q .venv
        %PYTHON_CMD% -m venv .venv
        if errorlevel 1 (
            echo ❌ 重新创建虚拟环境失败
            exit /b 1
        )
        call .venv\Scripts\activate.bat
        if errorlevel 1 (
            echo ❌ 激活虚拟环境失败
            exit /b 1
        )
        echo 📦 安装 Python 依赖...
        python -m pip install --upgrade pip >nul 2>&1
        python -m pip install -r requirements.txt
        if errorlevel 1 (
            echo ❌ 安装依赖失败
            exit /b 1
        )
    ) else (
        call .venv\Scripts\activate.bat
        if errorlevel 1 (
            echo ❌ 激活虚拟环境失败
            exit /b 1
        )
        REM 检查关键依赖是否已安装
        python -c "import uvicorn" >nul 2>&1
        if errorlevel 1 (
            echo ⚠️  检测到缺少依赖，正在安装...
            python -m pip install --upgrade pip >nul 2>&1
            python -m pip install -r requirements.txt
            if errorlevel 1 (
                echo ❌ 安装依赖失败
                exit /b 1
            )
        )
    )
)

REM 检查前端依赖
echo.
echo 📦 检查前端依赖...
if not exist "frontend\node_modules" (
    echo    ⚠️  node_modules 不存在，正在安装前端依赖...
    cd frontend
    npm install
    if errorlevel 1 (
        echo ❌ 安装前端依赖失败
        cd ..
        exit /b 1
    )
    cd ..
    echo    ✓ 前端依赖安装完成
) else (
    REM 检查 npm 是否可用
    where npm >nul 2>&1
    if errorlevel 1 (
        echo    ⚠️  未找到 npm，请先安装 Node.js
    ) else (
        REM 检查 package-lock.json 是否比 node_modules 新（简单检查）
        cd frontend
        if exist "package-lock.json" (
            REM 检查是否需要更新（通过比较时间戳，简单方式）
            echo    ✓ 前端依赖已存在
        ) else (
            echo    ⚠️  检测到 package-lock.json 缺失，正在重新安装...
            npm install
            if errorlevel 1 (
                echo ❌ 安装前端依赖失败
                cd ..
                exit /b 1
            )
            echo    ✓ 前端依赖安装完成
        )
        cd ..
    )
)

REM 初始化环境（创建目录和配置文件）
echo.
echo 🔧 初始化环境...
python -c "from backend.utils import ensure_dirs; from backend.config import ensure_config_exists; ensure_dirs(); ensure_config_exists(); print('✅ 环境初始化完成')"
if errorlevel 1 (
    echo ⚠️  环境初始化失败，将在应用启动时自动初始化
) else (
    echo    ✓ 目录结构已创建
    echo    ✓ 配置文件已初始化
)

echo.
echo ✅ 准备就绪！
echo.
echo 📍 后端服务: http://localhost:8000
echo 📍 前端服务: http://localhost:3000
echo.
echo 请在两个 CMD 窗口分别运行：
echo   窗口1: call .venv\Scripts\activate.bat ^&^& python backend/app.py
echo   窗口2: cd frontend ^&^& npm run dev
echo.
echo 提示: 确保在运行后端服务前先激活虚拟环境
echo.

endlocal


#!/bin/bash

echo "📦 安装前端依赖"
echo "================================"
echo ""

# 检查 Node.js 是否安装
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装 Node.js"
    echo "   下载地址: https://nodejs.org/"
    exit 1
fi

# 检查 npm 是否可用
if ! command -v npm &> /dev/null; then
    echo "❌ 未找到 npm，请先安装 Node.js"
    exit 1
fi

# 检查前端目录是否存在
if [ ! -d "frontend" ]; then
    echo "❌ 前端目录不存在"
    exit 1
fi

# 检查 package.json 是否存在
if [ ! -f "frontend/package.json" ]; then
    echo "❌ frontend/package.json 不存在"
    exit 1
fi

echo "📍 切换到前端目录..."
cd frontend

echo ""
echo "🔍 检查当前依赖状态..."
if [ -d "node_modules" ]; then
    echo "   ✓ node_modules 已存在"
    echo ""
    echo "💡 提示: 如果需要重新安装，请先删除 node_modules 目录"
    echo "   或运行: npm install --force"
    echo ""
    read -p "是否重新安装依赖? (y/N): " REINSTALL
    if [[ "$REINSTALL" =~ ^[Yy]$ ]]; then
        echo ""
        echo "🗑️  删除旧的 node_modules..."
        rm -rf node_modules
    else
        echo ""
        echo "📦 更新依赖..."
        npm install
        if [ $? -ne 0 ]; then
            echo "❌ 更新依赖失败"
            cd ..
            exit 1
        fi
        echo ""
        echo "✅ 依赖更新完成"
        cd ..
        exit 0
    fi
fi

echo ""
echo "📦 正在安装前端依赖..."
echo "   这可能需要几分钟时间，请耐心等待..."
echo ""

npm install

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 安装前端依赖失败"
    echo ""
    echo "💡 常见问题排查:"
    echo "   1. 检查网络连接是否正常"
    echo "   2. 尝试使用国内镜像: npm config set registry https://registry.npmmirror.com"
    echo "   3. 清除 npm 缓存: npm cache clean --force"
    echo "   4. 删除 node_modules 和 package-lock.json 后重试"
    cd ..
    exit 1
fi

echo ""
echo "✅ 前端依赖安装完成！"
echo ""
echo "📍 下一步:"
echo "   运行开发服务器: npm run dev"
echo "   构建生产版本: npm run build"
echo ""

cd ..

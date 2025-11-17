#!/bin/bash
# 快速下载 Font Awesome 字体文件

set -e

BASE_DIR="static/fontawesome"
mkdir -p "$BASE_DIR/webfonts"

echo "下载 Font Awesome 字体文件..."

# 下载所有字体格式以确保兼容性
FONTS=("fa-solid-900" "fa-regular-400" "fa-brands-400" "fa-v4compatibility")
FORMATS=("woff2" "woff" "ttf")

for font in "${FONTS[@]}"; do
    for format in "${FORMATS[@]}"; do
        echo "  下载 $font.$format..."
        curl -L -o "$BASE_DIR/webfonts/$font.$format" "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/$font.$format" 2>/dev/null || echo "    ⚠️  $font.$format 下载失败（可能不存在）"
    done
done

# 修改 Font Awesome CSS 中的字体路径（如果 CSS 文件存在）
if [ -f "$BASE_DIR/all.min.css" ]; then
    echo "修改 Font Awesome CSS 字体路径..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        # 先替换 CDN 路径为相对路径
        sed -i '' 's|https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/|webfonts/|g' "$BASE_DIR/all.min.css"
        # 如果还有 ../webfonts/ 路径，也替换为 webfonts/
        sed -i '' 's|url(../webfonts/|url(webfonts/|g' "$BASE_DIR/all.min.css"
    else
        # Linux
        sed -i 's|https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/|webfonts/|g' "$BASE_DIR/all.min.css"
        sed -i 's|url(../webfonts/|url(webfonts/|g' "$BASE_DIR/all.min.css"
    fi
    echo "✅ 字体文件下载完成，CSS 路径已更新！"
else
    echo "⚠️  CSS 文件不存在，请先运行 download_static.sh"
fi


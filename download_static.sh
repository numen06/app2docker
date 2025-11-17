#!/bin/bash
# 下载静态资源文件脚本

set -e

BASE_DIR="static"
mkdir -p "$BASE_DIR"/{bootstrap,css,js,codemirror/{css,js,mode/yaml},fontawesome}

echo "开始下载静态资源..."

# Bootstrap
echo "下载 Bootstrap..."
curl -L -o "$BASE_DIR/bootstrap/bootstrap.min.css" https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css
curl -L -o "$BASE_DIR/bootstrap/bootstrap.bundle.min.js" https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js

# jQuery
echo "下载 jQuery..."
curl -L -o "$BASE_DIR/js/jquery-3.7.1.min.js" https://code.jquery.com/jquery-3.7.1.min.js

# Font Awesome
echo "下载 Font Awesome..."
curl -L -o "$BASE_DIR/fontawesome/all.min.css" https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css
# Font Awesome 需要字体文件，这里只下载 CSS，字体文件需要单独下载或使用 CDN
# 如果需要完全离线，需要下载 webfonts 目录

# CodeMirror
echo "下载 CodeMirror..."
curl -L -o "$BASE_DIR/codemirror/css/codemirror.min.css" https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.css
curl -L -o "$BASE_DIR/codemirror/css/monokai.min.css" https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/theme/monokai.min.css
curl -L -o "$BASE_DIR/codemirror/js/codemirror.min.js" https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/codemirror.min.js
curl -L -o "$BASE_DIR/codemirror/mode/yaml/yaml.min.js" https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.2/mode/yaml/yaml.min.js

echo "✅ 所有静态资源下载完成！"
echo ""
echo "注意：Font Awesome 的字体文件需要单独下载。"
echo "如果需要完全离线使用，请访问 https://fontawesome.com/download 下载完整包。"


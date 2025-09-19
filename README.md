# jar2docker - JAR 包一键转 Docker 镜像工具

一个轻量级 Web 工具，将上传的 Java JAR 文件通过 Web 界面一键构建成 Docker 镜像。适合开发、测试环境快速打包部署，支持模板化构建与基本认证。

![](img.png) <!-- 可选：添加截图 -->

## 🚀 功能特性

- ✅ **Web 图形化操作**：无需命令行，拖拽上传 JAR 文件
- ✅ **自动镜像命名**：根据 JAR 文件名智能生成推荐镜像名（如 `myapp/demo-service`）
- ✅ **刷新按钮**：一键重新生成推荐名称
- ✅ **模板化构建**：`templates/` 目录下 `.Dockerfile` 文件自动加载为模板
- ✅ **HTTP Basic 认证**：全局保护，防止未授权访问
- ✅ **容器化部署**：自身可运行在 Docker 容器中，调用宿主机 Docker API
- ✅ **零依赖配置**：首次运行自动生成 `config.yml` 和默认模板

## 📦 项目结构
```
jar2docker/
├── jar2docker.py            # 主程序（Python HTTP 服务）
├── templates/               # Dockerfile 模板目录（自动加载）
│   ├── simple.Dockerfile
│   ├── springboot.Dockerfile
│   └── ...
├── uploads/                 # 临时存储上传的 JAR 文件
├── docker_build/            # 构建上下文目录
├── config.yml               # 配置文件（首次运行自动生成）
├── index.html               # 前端页面
├── requirements.txt         # Python 依赖
├── Dockerfile               # 容器化部署文件
└── README.md                # 本文件
```


## ⚙️ 快速开始（本地运行）

### 1. 准备环境

确保已安装：
- Python 3.8+（推荐使用 [python.org](https://www.python.org/) 官方安装包，避免 `distutils` 缺失）
- Docker（用于构建镜像）
- `pip`

### 2. 安装依赖

```bash
pip install -r requirements.txt

python jar2docker.py

```
### 2. 构建容器
```bash
docker build -t jar2docker .

docker run -d \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./config.yml:/app/config.yml \
  --name jar2docker \
  jar2docker
```
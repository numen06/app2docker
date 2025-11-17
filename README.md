# jar2docker - JAR 包一键转 Docker 镜像工具

一个轻量级 Web 工具，将上传的 Java JAR 文件通过 Web 界面一键构建成 Docker 镜像。适合开发、测试环境快速打包部署，支持模板化构建与基本认证。

![](img.png) <!-- 可选：添加截图 -->

## 🚀 功能特性

- ✅ **Web 图形化操作**：无需命令行，拖拽上传 JAR 文件
- ✅ **自动镜像命名**：根据 JAR 文件名智能生成推荐镜像名（如 `myapp/demo-service`）
- ✅ **刷新按钮**：一键重新生成推荐名称
- ✅ **模板化构建**：`templates/` 目录下 `.Dockerfile` 文件自动加载为模板
- ✅ **模板管理**：Web 端可视化增删改查 Dockerfile 模板
- ✅ **Compose 镜像导出**：上传 docker-compose.yml 批量下载所有镜像
- ✅ **HTTP Basic 认证**：全局保护，防止未授权访问
- ✅ **容器化部署**：自身可运行在 Docker 容器中，调用宿主机 Docker API
- ✅ **零依赖配置**：首次运行自动生成 `config.yml` 和默认模板
- ✅ **镜像导出**：一键拉取最新镜像并导出为 `.tar` 或 `.tar.gz`

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

```

### 3. 直接使用
```bash
docker run -d \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --name jar2docker \
  registry.cn-shanghai.aliyuncs.com/51jbm/jar2docker
#默认账号密码:admin/admin
```

## 🧩 模板管理

- 在 Web 页面中，`模板管理` 卡片会列出 `templates/` 目录下的所有 `.Dockerfile` 模板，并展示文件名、大小与最近更新时间。
- 点击 **新增模板** 可通过表单或上传现有 Dockerfile 创建模板，系统会自动保存为 `templates/<名称>.Dockerfile`。
- 通过 **预览 / 编辑 / 删除** 按钮即可在线维护模板内容，无需每次构建时重新上传。
- 构建表单中的模板下拉框会同步模板列表，选择后即可直接复用，进一步提升重复构建效率。

## 🧾 Compose 镜像导出

- 点击“上传 JAR 并构建”卡片右上方的 **Docker Compose 镜像导出** 区块，上传 `docker-compose.yml` 或任意 YAML 文本即可自动解析所有 `services.*.image`。
- 解析结果会列表展示并支持全选/单选，单个镜像可以立即下载，勾选多条后可一键批量下载（前端会依次触发下载，免去逐个操作）。
- 下载时可选择 `.tar` 或 `.tar.gz` 两种格式，适配不同的传输与存储需求。

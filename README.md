# App2Docker

🚀 **一键将应用打包成 Docker 镜像的可视化平台**

支持 Java（Spring Boot）、Node.js、静态网站等多种应用类型，提供可视化操作界面，内置模板参数化解析，简化 Docker 镜像构建和部署流程。

---

## ✨ 核心特性

### 🎨 现代化架构
- **Vue 3 + Vite** 现代化前端框架，快速热更新
- **FastAPI** 高性能异步 Python 后端
- **组件化设计** 9 个 Vue 组件，代码清晰易维护
- **响应式界面** Bootstrap 5，适配各种屏幕尺寸

### 🚀 强大功能
- **多语言支持** Java（Spring Boot）、Node.js、静态网站，可扩展到 Python、Go 等
- **模板参数化** 🎯 动态解析 Dockerfile 中的 `{{参数}}`，支持默认值
- **在线编辑器** 可视化创建和编辑模板，支持语法高亮
- **国内加速** 所有基础镜像使用阿里云源，下载飞快
- **实时日志** 构建过程实时显示，支持日志查看和导出
- **镜像导出** 支持导出为 tar/tar.gz 文件

### 🔧 便捷管理
- **可视化配置** Docker 仓库、认证信息、端口等参数
- **模板分类** 按项目类型（jar/nodejs/web）自动组织
- **用户模板** 支持自定义模板并持久化到 `data/templates/`
- **Compose 解析** 自动解析 docker-compose.yml 并提取镜像
- **JWT 认证** 安全的用户认证机制

---

## 📁 项目结构

```
App2Docker/
├── backend/                    # Python FastAPI 后端
│   ├── app.py                 # 主应用入口
│   ├── routes.py              # API 路由定义
│   ├── handlers.py            # 请求处理器和构建管理
│   ├── config.py              # 配置文件管理
│   ├── auth.py                # JWT 认证
│   ├── utils.py               # 工具函数
│   └── template_parser.py    # 模板参数解析器 ✨
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── components/        # Vue 组件
│   │   │   ├── BuildPanel.vue          # 构建面板
│   │   │   ├── BuildLogModal.vue       # 构建日志
│   │   │   ├── ConfigModal.vue         # Docker 配置
│   │   │   ├── TemplatePanel.vue       # 模板管理
│   │   │   ├── TemplateEditorModal.vue # 模板编辑器
│   │   │   ├── ExportPanel.vue         # 镜像导出
│   │   │   ├── ComposePanel.vue        # Compose 解析
│   │   │   └── LoginPage.vue           # 登录页面
│   │   ├── utils/
│   │   │   ├── auth.js        # 认证工具
│   │   │   └── axios-interceptor.js  # HTTP 拦截器
│   │   ├── App.vue            # 主应用
│   │   └── main.js            # 入口文件
│   ├── public/
│   │   └── favicon.ico        # 网站图标
│   ├── package.json
│   └── vite.config.js         # Vite 配置（含代理）
├── templates/                  # 内置模板（只读）
│   ├── jar/                   # Java 应用模板
│   │   ├── dragonwell8.Dockerfile      # 龙井 JDK 8
│   │   ├── dragonwell17.Dockerfile     # 龙井 JDK 17
│   │   └── spring-boot-custom.Dockerfile  # 可配置版本 ✨
│   ├── nodejs/                # Node.js 应用模板
│   │   ├── nodejs18.Dockerfile         # Node.js 18 + Nginx
│   │   └── nodejs20.Dockerfile         # Node.js 20 + Nginx
│   └── web/                   # 静态网站模板
│       ├── nginx-simple.Dockerfile     # 简单版
│       └── nginx-advanced.Dockerfile   # 高级可配置版 ✨
├── data/                       # 数据目录（Docker 卷映射）
│   ├── config.yml             # 配置文件
│   ├── templates/             # 用户自定义模板（可读写）
│   │   ├── jar/
│   │   ├── nodejs/
│   │   └── web/
│   ├── uploads/               # 上传文件
│   ├── docker_build/          # 构建临时目录
│   └── exports/               # 导出文件
├── Dockerfile                  # 主应用镜像构建
├── .dockerignore              # Docker 忽略配置
├── .gitignore                 # Git 忽略配置
├── requirements.txt           # Python 依赖
├── dev.sh                     # 开发启动脚本
└── README.md                  # 本文件
```

---

## 🎯 内置模板说明

### Java 应用模板（jar）

| 模板名 | 基础镜像 | 参数数量 | 说明 |
|--------|---------|---------|------|
| dragonwell8 | 阿里云龙井 JDK 8 | 0 | 分层构建，优化缓存 |
| dragonwell17 | 阿里云龙井 JDK 17 | 0 | 分层构建，优化缓存 |
| spring-boot-custom | OpenJDK | **6** | 可配置 Java 版本、JVM 参数等 ✨ |

### Node.js 应用模板（nodejs）

| 模板名 | 基础镜像 | 参数数量 | 说明 |
|--------|---------|---------|------|
| nodejs18 | Node 18 + Nginx | 1 | 多阶段构建，生产优化 |
| nodejs20 | Node 20 + Nginx | 1 | 多阶段构建，生产优化 |

### 静态网站模板（web）

| 模板名 | 基础镜像 | 参数数量 | 说明 |
|--------|---------|---------|------|
| nginx-simple | Nginx Alpine | 1 | 简单部署静态文件 |
| nginx-advanced | Nginx Alpine | **6** | 支持 SPA、Gzip、缓存配置 ✨ |

**✨ 带参数的模板**: 可在构建时动态配置端口、版本、JVM 参数等，无需修改 Dockerfile

---

## 🚀 快速开始

### 方式 1：Docker 部署（推荐）

#### 1. 构建镜像
```bash
docker build -t app2docker:latest .
```

#### 2. 运行容器
```bash
docker run -d \
  --name app2docker \
  -e APP_PORT=8000 \
  -v $(pwd)/data:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 8000:8000 \
  app2docker:latest
```

#### 3. 访问应用
```
http://localhost:8000
```

**默认账号**: admin / admin

**自定义端口**:
```bash
docker run -d \
  -e APP_PORT=9000 \
  -v $(pwd)/data:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 9000:9000 \
  app2docker:latest
```

---

### 方式 2：开发模式

#### 1. 安装依赖

**Python 后端**:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**前端**:
```bash
cd frontend
npm install
cd ..
```

#### 2. 启动服务

**方式 A - 使用启动脚本（推荐）**:
```bash
./dev.sh
```

**方式 B - 手动启动**:

终端 1 - 后端:
```bash
python backend/app.py
```

终端 2 - 前端:
```bash
cd frontend
npm run dev
```

#### 3. 访问应用
- **前端开发服务器**: http://localhost:3000
- **后端 API 服务器**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

---

## 🎯 使用指南

### 1. 构建 Docker 镜像

1. 选择**项目类型**（jar/nodejs/web）
2. 选择**模板**
3. 如果模板有参数，填写**参数值**（或使用默认值）
4. 上传**应用文件**（.jar/.zip/.tar.gz）
5. 填写**镜像名称**和**标签**
6. 可选：勾选**推送镜像**
7. 点击**开始构建**
8. 实时查看**构建日志**

### 2. 导出 Docker 镜像

1. 输入要导出的**镜像名称**
2. 输入**标签**（默认 latest）
3. 可选：选择 **Gzip 压缩**
4. 点击**导出镜像**
5. 自动下载 tar 或 tar.gz 文件

### 3. 解析 Docker Compose

1. 粘贴 **docker-compose.yml** 内容
2. 点击**解析 Compose**
3. 自动提取所有镜像列表
4. 可批量导出镜像

### 4. 管理模板

1. **查看模板**: 列出所有内置和用户模板
2. **新增模板**: 输入名称、选择类型、编写 Dockerfile
3. **编辑模板**: 修改用户模板内容
4. **删除模板**: 删除用户自定义模板
5. **预览模板**: 查看模板内容和参数

**模板参数支持**:
- `{{PARAM}}` - 必填参数
- `{{PARAM:default}}` - 带默认值的参数

示例:
```dockerfile
FROM openjdk:{{JAVA_VERSION:17}}-jre-slim
EXPOSE {{EXPOSE_PORT:8080}}
ENV JAVA_OPTS="{{JAVA_OPTS:-Xmx512m}}"
```

---

## ⚙️ 配置说明

### Docker 配置

编辑配置或通过界面修改：

```yaml
docker:
  registry: docker.io           # 镜像仓库地址
  registry_prefix: myapp        # 镜像名称前缀
  default_push: false           # 是否默认推送
  username: ""                  # Docker 仓库账号
  password: ""                  # Docker 仓库密码
  expose_port: 8080            # 默认暴露端口
```

### 服务器配置

```yaml
server:
  host: 0.0.0.0                # 监听地址
  port: 8000                   # 监听端口
  username: admin              # 管理员账号
  password: admin              # 管理员密码（请修改）
```

**环境变量优先级**:
- `APP_PORT` > `config.yml server.port` > 8000
- `APP_HOST` > `config.yml server.host` > 0.0.0.0

---

## 📦 技术栈

### 后端
- **Python 3.11** - 主语言
- **FastAPI** - 现代化 Web 框架
- **Uvicorn** - ASGI 服务器
- **Docker SDK** - Docker API 客户端
- **PyYAML** - 配置文件解析
- **PyJWT** - JWT 认证

### 前端
- **Vue 3** - 渐进式框架
- **Vite** - 下一代前端构建工具
- **Bootstrap 5** - UI 组件库
- **Axios** - HTTP 客户端
- **Font Awesome** - 图标库

---

## 🔧 高级功能

### 1. 模板参数化

**功能**: 自动解析 Dockerfile 中的参数并在界面显示输入框

**支持格式**:
- `{{VAR_NAME}}` - 必填参数
- `{{VAR_NAME:default}}` - 可选参数（带默认值）

**示例模板**:
```dockerfile
FROM openjdk:{{JAVA_VERSION:17}}-jre-slim
ENV JAVA_OPTS="{{JAVA_OPTS:-Xmx512m -Xms256m}}"
EXPOSE {{EXPOSE_PORT:8080}}
```

**效果**: 
- 选择该模板后，自动显示 3 个参数输入框
- JAVA_VERSION: 默认填充 17
- JAVA_OPTS: 默认填充 -Xmx512m -Xms256m
- EXPOSE_PORT: 默认填充 8080

### 2. 多项目类型支持

**内置类型**:
- `jar` - Java 应用（Spring Boot、普通 JAR）
- `nodejs` - Node.js 应用（前端项目）
- `web` - 静态网站（HTML/CSS/JS）

**扩展新类型**: 
只需在模板管理中创建新类型的模板即可，系统自动识别。

### 3. 镜像加速

**所有模板都使用阿里云镜像源**:
- Node.js: `registry.cn-hangzhou.aliyuncs.com/library/node`
- Python: `registry.cn-hangzhou.aliyuncs.com/library/python`
- Nginx: `registry.cn-hangzhou.aliyuncs.com/library/nginx`
- OpenJDK: `registry.cn-hangzhou.aliyuncs.com/library/openjdk`
- 龙井 JDK: `registry.cn-shanghai.aliyuncs.com/51jbm/spring-boot-layer`

### 4. 时区设置

所有镜像默认设置为 **Asia/Shanghai** 时区，无需额外配置。

---

## 📚 API 文档

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/login` | POST | 用户登录 |
| `/api/logout` | POST | 用户登出 |
| `/api/get-config` | GET | 获取 Docker 配置 |
| `/api/save-config` | POST | 保存 Docker 配置 |
| `/api/templates` | GET | 获取模板列表 |
| `/api/templates` | POST | 创建模板 |
| `/api/templates` | PUT | 更新模板 |
| `/api/templates` | DELETE | 删除模板 |
| `/api/template-params` | GET | 获取模板参数 ✨ |
| `/api/upload` | POST | 上传文件并构建 |
| `/api/get-logs` | GET | 获取构建日志 |
| `/api/export-image` | GET | 导出镜像 |
| `/api/parse-compose` | POST | 解析 Compose 文件 |
| `/api/suggest-image-name` | POST | 建议镜像名称 |

**完整文档**: http://localhost:8000/docs

---

## 🐳 Docker 部署

### 构建参数

```bash
docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -t app2docker:latest .
```

### 运行参数

```bash
docker run -d \
  --name app2docker \
  --restart unless-stopped \
  -e APP_PORT=8000 \
  -e APP_HOST=0.0.0.0 \
  -v $(pwd)/data:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 8000:8000 \
  app2docker:latest
```

**重要参数说明**:

| 参数 | 说明 | 必需 |
|------|------|------|
| `-v $(pwd)/data:/app/data` | 持久化配置和模板 | ✅ |
| `-v /var/run/docker.sock:/var/run/docker.sock` | Docker 构建权限 | ✅ |
| `-p 8000:8000` | 端口映射 | ✅ |
| `-e APP_PORT=8000` | 自定义服务端口 | ❌ |
| `-e APP_HOST=0.0.0.0` | 自定义监听地址 | ❌ |

### Docker Compose 部署

创建 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app2docker:
    build: .
    container_name: app2docker
    restart: unless-stopped
    environment:
      - APP_PORT=8000
      - APP_HOST=0.0.0.0
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock
```

启动:
```bash
docker-compose up -d
```

---

## 🛠️ 开发指南

### 目录说明

- **backend/** - Python 后端代码，使用 FastAPI
- **frontend/** - Vue 3 前端代码，使用 Vite
- **templates/** - 内置 Dockerfile 模板（打包到镜像）
- **data/** - 运行时数据（需要持久化）
  - `config.yml` - 配置文件
  - `templates/` - 用户自定义模板
  - `uploads/` - 上传的应用文件
  - `docker_build/` - 构建临时目录
  - `exports/` - 导出的镜像文件

### 热更新

- **前端**: Vite 自动热更新
- **后端**: 修改代码后自动重载（开发模式）

### 添加新模板

1. 在 `templates/项目类型/` 下创建 `.Dockerfile` 文件
2. 使用参数格式: `{{PARAM:default}}`
3. 重启服务，自动识别

---

## 🔐 安全建议

### 生产环境部署

1. **修改默认密码**
   ```yaml
   server:
     username: your_admin
     password: strong_password_here
   ```

2. **使用 HTTPS**
   - 在前面加 Nginx 反向代理
   - 配置 SSL 证书

3. **限制访问**
   - 使用防火墙规则
   - 配置网络策略

4. **定期备份**
   ```bash
   tar -czf backup-$(date +%Y%m%d).tar.gz data/
   ```

---

## 🐛 故障排查

### 后端服务无法启动

**检查**:
```bash
# 查看日志
docker logs app2docker

# 检查端口占用
lsof -i :8000

# 检查 Docker
docker ps
docker info
```

### 前端无法连接后端

**检查 Vite 代理配置**: `frontend/vite.config.js`
```javascript
proxy: {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  }
}
```

### 模板参数不显示

**检查**:
1. 模板中是否使用了 `{{PARAM}}` 格式
2. 浏览器控制台是否有错误
3. `/api/template-params` 接口是否正常

---

## 📈 性能优化

### 构建优化
- ✅ 多阶段构建减少镜像体积
- ✅ 分层构建优化缓存
- ✅ 使用 .dockerignore 排除无关文件

### 前端优化
- ✅ Vite 按需编译
- ✅ 代码分割和懒加载
- ✅ 生产构建压缩优化

### 后端优化
- ✅ 异步 I/O 处理
- ✅ 后台任务构建
- ✅ 日志流式传输

---

## 📝 更新日志

### v2.0.0 (2025-12-04)

**新功能**:
- ✨ 模板参数动态解析和填写
- ✨ 支持静态网站（Nginx）模板
- ✨ 环境变量配置服务端口
- ✨ 所有镜像使用阿里云源
- ✨ 自动设置上海时区

**改进**:
- 🔧 修复配置前后端同步问题
- 🔧 修复模板增删改查功能
- 🔧 项目类型动态扩展支持
- 🔧 构建面板项目类型改为下拉

**优化**:
- 🚀 配置文件自动创建
- 🚀 模板扫描不再限制类型
- 🚀 清理测试和临时文件
- 🚀 更新项目文档

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Vite](https://vitejs.dev/) - 下一代前端构建工具
- [Docker SDK](https://docker-py.readthedocs.io/) - Docker Python SDK
- [Bootstrap](https://getbootstrap.com/) - 前端 UI 框架

---

**⭐ 如果这个项目对您有帮助，欢迎 Star！**

---

## 📞 支持

- 🐛 **问题反馈**: 提交 Issue
- 💡 **功能建议**: 提交 Feature Request
- 📧 **联系方式**: [您的联系方式]

---

**Enjoy building Docker images! 🐳**

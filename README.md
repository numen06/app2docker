# App2Docker

🚀 **一键将应用打包成 Docker 镜像的可视化平台**

支持 Java（Spring Boot）、Node.js、静态网站等多种应用类型，提供 Web 界面操作，无需编写 Dockerfile。

![输入图片说明](img.png)

---

## ⚡ 快速开始

### 使用已发布的 Docker 镜像（推荐）

```bash
docker run -d \
  --name app2docker \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  registry.cn-shanghai.aliyuncs.com/51jbm/jar2docker:latest
```

然后访问：**http://localhost:8000**

默认账号：`admin` / `admin`

---

## 📦 支持的应用类型

### Java 应用
- ✅ Spring Boot JAR 包
- ✅ 普通 Java 应用
- ✅ 支持 JDK 8、17 等多版本
- ✅ 可配置 JVM 参数

### Node.js 应用
- ✅ React、Vue、Angular 等前端项目
- ✅ 自动构建并部署到 Nginx
- ✅ 支持 Node.js 18、20

### 静态网站
- ✅ HTML/CSS/JS 静态文件
- ✅ Nginx 部署，支持 SPA 路由
- ✅ 自动 Gzip 压缩和缓存优化

---

## 🎯 使用流程

### 1️⃣ 构建镜像

1. 访问 http://localhost:8000
2. 登录（admin/admin）
3. 选择**项目类型**（Java/Node.js/静态网站）
4. 选择**模板**
5. 上传**应用文件**（.jar / .zip / .tar.gz）
6. 填写**镜像名称**和**标签**
7. 点击**开始构建**
8. 实时查看构建日志

### 2️⃣ 导出镜像

1. 切换到**导出镜像**标签
2. 输入镜像名称（如 `myapp:latest`）
3. 可选：启用 Gzip 压缩
4. 点击**导出镜像**
5. 自动下载 tar 文件

### 3️⃣ 批量导出（Compose）

1. 切换到 **Docker Compose** 标签
2. 粘贴 `docker-compose.yml` 内容
3. 点击**解析 Compose**
4. 选择要导出的镜像
5. 批量下载

---

## ⚙️ 配置说明

### 修改 Docker 配置

点击页面右上角的 **⚙️ 配置** 按钮：

- **Registry 地址**: docker.io（或私有仓库）
- **镜像前缀**: 自动添加到镜像名前（如 `mycompany/`）
- **账号/密码**: Docker 仓库认证信息
- **暴露端口**: 默认端口（8080）
- **默认推送**: 构建后自动推送到仓库

### 自定义端口

```bash
docker run -d \
  -e APP_PORT=9000 \
  -p 9000:9000 \
  -v $(pwd)/data:/app/data \
  -v /var/run/docker.sock:/var/run/docker.sock \
  registry.cn-shanghai.aliyuncs.com/51jbm/jar2docker:latest
```

访问：http://localhost:9000

---

## 🎨 模板管理

### 内置模板

**Java 应用**:
- `dragonwell8` - 龙井 JDK 8（分层构建）
- `dragonwell17` - 龙井 JDK 17（分层构建）
- `spring-boot-custom` - 可配置版本和 JVM 参数

**Node.js 应用**:
- `nodejs18` - Node.js 18 + Nginx
- `nodejs20` - Node.js 20 + Nginx

**静态网站**:
- `nginx-simple` - 简单 Nginx 部署
- `nginx-advanced` - 高级配置（支持 SPA、缓存）

### 自定义模板

1. 进入**模板管理**标签
2. 点击**新增模板**
3. 输入模板名称和选择项目类型
4. 编写 Dockerfile 内容
5. 支持参数：`{{EXPOSE_PORT:8080}}`
6. 保存后即可使用

**参数格式**:
- `{{参数名}}` - 必填参数
- `{{参数名:默认值}}` - 可选参数

示例:
```dockerfile
FROM openjdk:{{JAVA_VERSION:17}}-jre-slim
EXPOSE {{EXPOSE_PORT:8080}}
ENV JAVA_OPTS="{{JAVA_OPTS:-Xmx512m}}"
COPY app.jar /app.jar
CMD ["java", ${JAVA_OPTS}, "-jar", "/app.jar"]
```

---

## 🔒 安全建议

### ⚠️ 首次使用必须修改

1. **修改管理员密码**
   - 点击配置按钮
   - 找到服务器配置（或编辑 `data/config.yml`）

2. **配置 Docker 仓库认证**
   - 填写 Docker Hub 或私有仓库的账号密码
   - 用于推送镜像

### 生产环境建议

- 🔐 使用 HTTPS（前置 Nginx 反向代理）
- 🔒 限制访问 IP
- 💾 定期备份 `data/` 目录
- 🔄 定期更新镜像

---

## 📂 数据持久化

**重要**: 必须映射 `data/` 目录，否则配置和模板会丢失！

```bash
-v $(pwd)/data:/app/data
```

**目录内容**:
- `config.yml` - 配置文件
- `templates/` - 用户自定义模板
- `uploads/` - 上传的文件（临时）
- `exports/` - 导出的镜像

---

## ❓ 常见问题

### Q: 构建失败怎么办？

**A**: 查看构建日志，常见原因：
- Docker 服务未运行
- 文件格式不正确
- 模板配置有误

### Q: 如何推送到私有仓库？

**A**: 
1. 在配置中填写私有仓库地址和认证信息
2. 镜像名使用完整路径（如 `registry.example.com/myapp`）
3. 勾选"推送镜像"

### Q: 支持哪些文件格式？

**A**:
- Java: `.jar` 文件
- Node.js: `.zip`、`.tar`、`.tar.gz` 压缩包
- 静态网站: `.zip`、`.tar`、`.tar.gz` 压缩包

### Q: 如何升级镜像？

**A**:
```bash
docker pull registry.cn-shanghai.aliyuncs.com/51jbm/jar2docker:latest
docker stop app2docker
docker rm app2docker
# 重新运行容器
```

---

## 🌟 特色功能

### 🎯 模板参数化

选择带参数的模板（如 `spring-boot-custom`）时，自动显示参数输入框，无需手动编辑 Dockerfile。

### 🚀 国内加速

所有基础镜像使用阿里云源，下载速度快：
- Java: 阿里云龙井 JDK
- Node.js: 阿里云 Node.js 镜像
- Nginx: 阿里云 Nginx 镜像

### 🕐 时区设置

所有构建的镜像自动设置为 **Asia/Shanghai** 时区。

### 📋 实时日志

构建过程实时显示，支持查看历史日志。

---

## 📞 获取帮助

- 📖 查看在线文档：http://localhost:8000/docs
- 🐛 问题反馈：提交 Issue
- 💬 使用问题：查看构建日志和后端日志

---

## 📄 开源协议

MIT License - 详见 [LICENSE](LICENSE)

---

**开始使用吧！** 🐳

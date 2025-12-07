# 流水线功能使用指南

## 功能概述

流水线功能允许您预先配置 Git 仓库构建任务，并通过标准的 Webhook 机制触发自动构建。支持 GitHub、GitLab、Gitee 等主流 Git 平台。

## 主要特性

- ✅ 预配置 Git 仓库构建参数
- ✅ 支持标准 Webhook 触发（GitHub/GitLab/Gitee）
- ✅ Webhook 签名验证（可选）
- ✅ 自动触发构建工作流
- ✅ 流水线启用/禁用控制
- ✅ 触发历史记录

## 快速开始

### 1. 创建流水线

在 Web 界面中：

1. 点击"流水线"标签页
2. 点击"新建流水线"
3. 填写以下信息：

   - **流水线名称**：例如"主分支自动构建"
   - **描述**：流水线用途说明（可选）
   - **Git 仓库地址**：例如 `https://github.com/user/repo.git`
   - **分支名称**：例如 `main`（留空表示使用默认分支）
   - **项目类型**：选择 Java/Node.js/Python/Go/Web
   - **镜像名称**：构建的镜像名称
   - **镜像标签**：镜像标签（默认 `latest`）
   - **Dockerfile 模板**：选择模板或使用项目中的 Dockerfile
   - **Webhook 密钥**：用于验证 Webhook 签名（可选，留空自动生成）
   - **启用流水线**：勾选以启用

4. 点击"保存"

### 2. 配置 Git 平台 Webhook

创建流水线后，点击流水线列表中的"链接"图标，复制 Webhook URL。

#### GitHub 配置

1. 进入仓库 Settings → Webhooks → Add webhook
2. Payload URL: 粘贴复制的 Webhook URL
3. Content type: 选择 `application/json`
4. Secret: 填写流水线配置的 Webhook 密钥（如果有）
5. 事件触发: 选择 "Just the push event"
6. 激活: 勾选 "Active"
7. 点击 "Add webhook"

#### GitLab 配置

1. 进入仓库 Settings → Webhooks
2. URL: 粘贴复制的 Webhook URL
3. Secret Token: 填写流水线配置的 Webhook 密钥（如果有）
4. Trigger: 勾选 "Push events"
5. 点击 "Add webhook"

#### Gitee 配置

1. 进入仓库 管理 → WebHooks → 添加 webhook
2. URL: 粘贴复制的 Webhook URL
3. 密码: 填写流水线配置的 Webhook 密钥（如果有）
4. 事件: 勾选 "Push"
5. 点击 "添加"

### 3. 测试 Webhook

提交代码到配置的分支，Webhook 将自动触发构建。您可以在"任务管理"标签页中查看构建状态和日志。

## Webhook 签名验证

为了安全性，建议启用 Webhook 签名验证：

1. 在创建/编辑流水线时，设置一个强密钥作为 Webhook 密钥
2. 在 Git 平台配置 Webhook 时，填写相同的密钥
3. 系统将使用 HMAC-SHA256 验证请求签名

**支持的签名格式：**

- **GitHub**: 使用 `X-Hub-Signature-256` 请求头（SHA256）或 `X-Hub-Signature`（SHA1）
- **GitLab**: 使用 `X-Gitlab-Token` 请求头（Token 验证）
- **Gitee**: 使用 `X-Gitee-Token` 请求头（Token 验证）

## 流水线管理

### 查看流水线

流水线列表显示：

- 流水线名称和描述
- Git 仓库地址
- 分支
- 镜像名称和标签
- 启用状态
- 触发次数
- 最后触发时间

### 编辑流水线

点击流水线的"编辑"按钮可以修改配置。注意：

- Webhook Token 不可修改
- 修改后立即生效

### 删除流水线

点击流水线的"删除"按钮可以删除流水线配置。删除后：

- Webhook 将无法触发
- 历史构建记录保留

### 启用/禁用流水线

通过编辑流水线，可以快速启用或禁用流水线。禁用后：

- Webhook 请求将被拒绝
- 不会触发新的构建

## API 接口

### 创建流水线

```bash
POST /api/pipelines
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "测试流水线",
  "git_url": "https://github.com/user/repo.git",
  "branch": "main",
  "project_type": "go",
  "template": "go1.23",
  "image_name": "myapp/demo",
  "tag": "latest",
  "push": false,
  "webhook_secret": "my-secret",
  "enabled": true
}
```

### 获取流水线列表

```bash
GET /api/pipelines
Authorization: Bearer <token>
```

### 触发 Webhook

```bash
POST /api/webhook/{webhook_token}
Content-Type: application/json
X-Hub-Signature-256: sha256=<signature>

{
  "ref": "refs/heads/main",
  "repository": {
    "clone_url": "https://github.com/user/repo.git"
  }
}
```

## 测试脚本

项目包含测试脚本 `test_pipeline.py`，可以自动测试流水线功能：

```bash
# 确保服务已启动
python3 test_pipeline.py
```

测试脚本将：

1. 登录系统
2. 创建测试流水线
3. 触发 Webhook
4. 监控构建状态
5. 显示构建日志

## 故障排查

### Webhook 没有触发

1. 检查流水线是否启用
2. 检查 Webhook URL 是否正确
3. 检查 Git 平台的 Webhook 日志
4. 检查 Webhook 密钥是否匹配

### 签名验证失败

1. 确认流水线的 Webhook 密钥与 Git 平台配置一致
2. 检查 Git 平台是否支持签名验证
3. 查看服务器日志确认错误详情

### 构建失败

1. 在"任务管理"中查看构建日志
2. 检查 Git 仓库是否可访问
3. 检查分支名称是否正确
4. 检查 Dockerfile 模板配置

## 最佳实践

1. **使用有意义的流水线名称**：便于识别和管理
2. **启用 Webhook 签名验证**：提高安全性
3. **合理设置分支**：避免不必要的构建
4. **监控触发频率**：注意资源使用
5. **及时清理无用流水线**：保持配置整洁

## 安全建议

1. **保护 Webhook 密钥**：不要将密钥提交到代码仓库
2. **限制 Webhook 来源**：如果可能，配置 IP 白名单
3. **定期轮换密钥**：提高安全性
4. **监控异常触发**：注意异常的构建请求

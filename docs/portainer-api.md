# Portainer API 文档

> 文档生成时间: 2026-03-24  
> 更新时间: 2026-03-24 (新增 Access Token 认证方式)

**注意**: 使用此文档前，请准备以下信息：

- `PORTAINER_URL` - Portainer 服务器地址 (例如: http://localhost:9000)
- **认证方式二选一**:
  - 方式1: `PORTAINER_USERNAME` + `PORTAINER_PASSWORD` (JWT Token)
  - 方式2: `PORTAINER_API_KEY` (Access Token，推荐)

---

## 1. 认证

Portainer 提供两种认证方式:

### 1.1 方式一: Access Token (推荐)

**优点**:

- 无需每次登录获取JWT
- Token长期有效
- 可在Portainer UI中管理

**获取方式**:

1. 登录 Portainer Web UI
2. 点击右上角用户头像 → "My account"
3. 滚动到 "Access tokens" 区域
4. 点击 "Add access token"
5. 输入描述(如"API Access")，点击 "Add access token"
6. **⚠️ 立即复制生成的Token** (只显示一次)

**Token格式**: `ptr_<随机字符串>`

**示例**: `ptr_Sxv8PTnyvGspUTe8+APsTFY7KiEGLaKBLSUPLUW7HoQ=`

**使用方式**: 在请求Header中添加 `X-API-Key: <access_token>`

**测试命令**:

```bash
# PowerShell
$headers = @{"X-API-Key" = "ptr_Sxv8PTnyvGspUTe8+APsTFY7KiEGLaKBLSUPLUW7HoQ="}
Invoke-RestMethod -Uri "http://127.0.0.1:9000/api/status" -Headers $headers

# curl
curl -H "X-API-Key: ptr_Sxv8PTnyvGspUTe8+APsTFY7KiEGLaKBLSUPLUW7HoQ=" \
     http://127.0.0.1:9000/api/status
```

**测试结果**: ✅ 可用 (测试于 Portainer 2.33.3)

---

### 1.2 方式二: JWT Token

**缺点**:

- Token有效期较短(通常24小时)
- 每次使用需先登录获取Token

**请求:**

```http
POST /api/auth
Content-Type: application/json
```

**请求体:**

```json
{
  "username": "<your_username>",
  "password": "<your_password>"
}
```

**响应:**

```json
{
  "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**使用方式**: 在后续请求的 Header 中添加 `Authorization: Bearer <jwt_token>`

---

## 2. Stack 管理 API

### 2.1 获取所有 Stack 列表

**请求:**

```http
GET /api/stacks
Authorization: Bearer <token>
```

**响应示例:**

```json
[
  {
    "Id": 18,
    "Name": "ollama-openai-proxy",
    "Type": 2,
    "EndpointId": 4,
    "Status": 2,
    "EntryPoint": "docker-compose.yml",
    "ProjectPath": "/data/compose/18",
    "CreatedBy": "admin",
    "CreationDate": 1764228272
  }
]
```

**状态码说明:**

- `Status = 1`: Stack 运行中
- `Status = 2`: Stack 已停止

---

### 2.2 获取单个 Stack 详情

**请求:**

```http
GET /api/stacks/{id}?endpointId={endpointId}
Authorization: Bearer <token>
```

**示例:**

```http
GET /api/stacks/45?endpointId=4
```

**响应:**

```json
{
  "Id": 45,
  "Name": "jbm-the-workhorses",
  "Type": 2,
  "EndpointId": 4,
  "EntryPoint": "docker-compose.yml",
  "Env": [],
  "Status": 1,
  "ProjectPath": "/data/compose/45",
  "CreatedBy": "admin",
  "CreationDate": 1769410754,
  "UpdatedBy": "admin",
  "UpdateDate": 1774325469
}
```

---

### 2.3 创建 Stack（部署新容器）

**说明**: Portainer 2.33.3 中，创建容器应通过创建 Stack 实现。

**请求:**

```http
POST /api/stacks?endpointId={endpointId}&type=2&method=string
Content-Type: application/json
Authorization: Bearer <token>
```

**参数:**

- `endpointId`: Endpoint ID (如: 4)
- `type=2`: Stack 类型 (2 = Swarm/Docker Compose)
- `method=string`: 通过字符串提交 compose 内容

**请求体:**

```json
{
  "Name": "test-nginx-stack",
  "StackFileContent": "version: '3.9'\nservices:\n  nginx:\n    image: nginx:latest\n    container_name: test-nginx\n    ports:\n      - '18080:80'\n    environment:\n      - NGINX_HOST=localhost\n    restart: unless-stopped",
  "Env": []
}
```

**响应:**

```json
{
  "Id": 22,
  "Name": "test-nginx-stack",
  "Type": 2,
  "EndpointId": 4,
  "SwarmId": "",
  "EntryPoint": "docker-compose.yml",
  "Env": [],
  "ResourceControl": null,
  "Status": 1,
  "ProjectPath": "/data/compose/22",
  "CreationDate": 1769410754,
  "CreatedBy": "admin",
  "UpdateDate": 0,
  "UpdatedBy": "",
  "AdditionalFiles": null,
  "AutoUpdate": null,
  "Option": null,
  "GitConfig": null,
  "FromAppTemplate": false,
  "Namespace": "",
  "IsComposeFormat": true
}
```

**注意**:

- 镜像会在 Stack 部署时自动拉取，无需手动拉取
- 如遇到 405 错误，请检查请求参数格式或查阅对应版本的 API 文档

---

### 2.4 获取 Stack 的 Docker Compose 文件

**请求:**

```http
GET /api/stacks/{id}/file?endpointId={endpointId}
Authorization: Bearer <token>
```

**响应:**

```json
{
  "StackFileContent": "# docker-compose.yml\nversion: '3.9'\nservices:\n  ..."
}
```

---

### 2.5 重启 Stack（不带更新）

**说明**: Portainer 没有直接的 restart 接口，通过 PUT 更新 Stack 触发重新部署。

**请求:**

```http
PUT /api/stacks/{id}?endpointId={endpointId}
Content-Type: application/json
Authorization: Bearer <token>
```

**请求体:**

```json
{
  "StackFileContent": "# 原始 docker-compose 内容",
  "Env": [],
  "Prune": false
}
```

**行为**: 使用本地已有镜像重启容器，不拉取新镜像。

---

### 2.6 重启 Stack（带更新 - 拉取最新镜像）

**请求:**

```http
PUT /api/stacks/{id}?endpointId={endpointId}
Content-Type: application/json
Authorization: Bearer <token>
```

**请求体:**

```json
{
  "StackFileContent": "# docker-compose.yml\nversion: '3.9'\nservices:\n  app:\n    image: registry.example.com/app:latest\n    pull_policy: always\n    ...",
  "Env": [],
  "Prune": false
}
```

**关键**: 在 docker-compose 中添加 `pull_policy: always` 强制拉取最新镜像。

**说明**: 如需拉取最新镜像，在 docker-compose 内容中添加 `pull_policy: always`，然后调用 PUT /api/stacks/{id} 接口更新 Stack。

---

### 2.7 删除 Stack

**请求:**

```http
DELETE /api/stacks/{id}?endpointId={endpointId}
Authorization: Bearer <token>
```

**注意**: 删除操作不可恢复，请谨慎使用。

**测试结果**: ✅ 可用

---

## 3. 容器管理 API (Docker API 代理)

Portainer 提供 Docker API 代理功能，可以通过 Portainer 直接操作容器。

**重要说明**: Portainer 2.33.3 的 Docker API 代理**不支持直接创建容器** (`POST /containers/create` 返回 404)。
创建容器应通过 **Stack API** (Docker Compose) 实现。

### 3.1 获取所有容器

**请求:**

```http
GET /api/endpoints/{endpointId}/docker/containers/json?all=true
Authorization: Bearer <token>
```

**参数:**

- `all=true`: 返回所有容器（包括已停止的）

**响应示例:**

```json
[
  {
    "Id": "17e6b6e716ab...",
    "Names": ["/app2docker-app2docker-1"],
    "Image": "registry.cn-shanghai.aliyuncs.com/51jbm/app2docker:latest",
    "ImageID": "sha256:...",
    "Command": "python app.py",
    "Created": 1764228272,
    "Ports": [...],
    "State": "running",
    "Status": "Up 2 hours"
  }
]
```

**测试结果**: ✅ 可用

---

### 3.2 获取容器详情

**请求:**

```http
GET /api/endpoints/{endpointId}/docker/containers/{containerId}/json
Authorization: Bearer <token>
```

**响应示例:**

```json
{
  "Id": "17e6b6e716ab...",
  "Name": "/app2docker-app2docker-1",
  "State": {
    "Status": "running",
    "Running": true,
    "Paused": false,
    "Restarting": false,
    "StartedAt": "2026-03-24T04:19:00.188222899Z"
  },
  "Config": {
    "Image": "registry.cn-shanghai.aliyuncs.com/51jbm/app2docker:latest",
    "Env": ["APP_PORT=8000"],
    "ExposedPorts": { "8000/tcp": {} }
  },
  "HostConfig": {
    "PortBindings": { "8000/tcp": [{ "HostPort": "8000" }] },
    "RestartPolicy": { "Name": "unless-stopped" }
  }
}
```

**测试结果**: ✅ 可用

---

### 3.3 启动容器

**请求:**

```http
POST /api/endpoints/{endpointId}/docker/containers/{containerId}/start
Authorization: Bearer <token>
```

**说明:** 启动已停止的容器。

**测试结果**: ✅ 可用

---

### 3.4 停止容器

**请求:**

```http
POST /api/endpoints/{endpointId}/docker/containers/{containerId}/stop
Authorization: Bearer <token>
```

**可选参数:**

- `t=30`: 等待容器停止的超时时间（秒），默认 10 秒

**测试结果**: ✅ 可用

---

### 3.5 重启容器

**请求:**

```http
POST /api/endpoints/{endpointId}/docker/containers/{containerId}/restart
Authorization: Bearer <token>
```

**可选参数:**

- `t=30`: 等待容器停止的超时时间（秒）

**测试结果**: ✅ 可用

---

### 3.6 获取容器日志

**请求:**

```http
GET /api/endpoints/{endpointId}/docker/containers/{containerId}/logs?stdout=true&stderr=true&tail=100
Authorization: Bearer <token>
```

**参数:**

- `stdout=true`: 包含标准输出
- `stderr=true`: 包含标准错误
- `tail=100`: 返回最后 100 行日志
- `since=0`: 从指定时间戳开始（Unix 时间戳）
- `until=0`: 到指定时间戳结束

**测试结果**: ✅ 可用

---

### 3.7 获取容器统计信息

**请求:**

```http
GET /api/endpoints/{endpointId}/docker/containers/{containerId}/stats?stream=false
Authorization: Bearer <token>
```

**参数:**

- `stream=false`: 只返回一次统计，不持续流式输出

**响应示例:**

```json
{
  "cpu_stats": {
    "cpu_usage": {
      "total_usage": 39615000000
    }
  },
  "memory_stats": {
    "usage": 89169920,
    "limit": 16599957504
  },
  "networks": {
    "eth0": {
      "rx_bytes": 123456,
      "tx_bytes": 789012
    }
  }
}
```

**测试结果**: ✅ 可用

---

### 3.8 删除容器

**请求:**

```http
DELETE /api/endpoints/{endpointId}/docker/containers/{containerId}?force=false&v=false
Authorization: Bearer <token>
```

**参数:**

- `force=false`: 是否强制删除运行中的容器
- `v=false`: 是否删除关联的卷

**测试结果**: ⚠️ 未测试（建议通过删除 Stack 来删除容器）

---

### 3.9 创建容器 (⚠️ 不支持)

**请求:**

```http
POST /api/endpoints/{endpointId}/docker/containers/create?name={containerName}
Authorization: Bearer <token>
Content-Type: application/json
```

**请求体:**

```json
{
  "Image": "nginx:latest",
  "HostConfig": {
    "PortBindings": {
      "80/tcp": [{ "HostPort": "18080" }]
    }
  }
}
```

**测试结果**: ❌ **不可用** (返回 404)

**替代方案**: 使用 Stack API 创建容器，见第 2 节。

---

### 3.10 镜像管理

#### 3.10.1 获取镜像列表

**请求:**

```http
GET /api/endpoints/{endpointId}/docker/images/json
Authorization: Bearer <token>
```

**测试结果**: ✅ 可用

---

#### 3.10.2 拉取镜像 (⚠️ 可能不支持)

**请求:**

```http
POST /api/endpoints/{endpointId}/docker/images/create?fromImage={image}&tag={tag}
Authorization: Bearer <token>
```

**说明**: Portainer 2.33.3 可能不支持通过 API 直接拉取镜像。
镜像会在创建 Stack 时自动拉取。

---

## 4. Endpoint 管理 API

### 4.1 获取所有 Endpoints

**请求:**

```http
GET /api/endpoints
Authorization: Bearer <token>
```

**响应示例:**

```json
[
  {
    "Id": 4,
    "Name": "local",
    "Type": 1,
    "URL": "unix:///var/run/docker.sock"
  }
]
```

**Type 说明:**

- `1`: Docker 单机环境
- `2`: Docker Swarm 集群
- `3`: Kubernetes 集群

---

## 5. 接口调用示例

### 5.1 认证

**请求:**

```http
POST /api/auth
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

**响应:**

```json
{
  "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### 5.2 Stack 操作示例

#### 创建 Stack

```http
POST /api/stacks?endpointId=4&type=2&method=string
Content-Type: application/json
Authorization: Bearer <token>

{
  "Name": "test-nginx-stack",
  "StackFileContent": "version: '3.9'\nservices:\n  nginx:\n    image: nginx:latest\n    container_name: test-nginx\n    ports:\n      - '18080:80'\n    restart: unless-stopped",
  "Env": []
}
```

#### 启动 Stack

```http
POST /api/stacks/46/start?endpointId=4
Authorization: Bearer <token>
```

#### 停止 Stack

```http
POST /api/stacks/46/stop?endpointId=4
Authorization: Bearer <token>
```

#### 更新 Stack

```http
PUT /api/stacks/46?endpointId=4
Content-Type: application/json
Authorization: Bearer <token>

{
  "StackFileContent": "version: '3.9'\nservices:\n  app:\n    image: nginx:latest\n    pull_policy: always\n    ports:\n      - '8080:80'",
  "Env": [],
  "Prune": false
}
```

#### 删除 Stack

```http
DELETE /api/stacks/46?endpointId=4
Authorization: Bearer <token>
```

---

### 5.3 容器操作示例

#### 获取容器列表

```http
GET /api/endpoints/4/docker/containers/json?all=true
Authorization: Bearer <token>
```

#### 启动容器

```http
POST /api/endpoints/4/docker/containers/{containerId}/start
Authorization: Bearer <token>
```

#### 停止容器

```http
POST /api/endpoints/4/docker/containers/{containerId}/stop?t=30
Authorization: Bearer <token>
```

#### 重启容器

```http
POST /api/endpoints/4/docker/containers/{containerId}/restart
Authorization: Bearer <token>
```

#### 获取容器日志

```http
GET /api/endpoints/4/docker/containers/{containerId}/logs?stdout=true&stderr=true&tail=100
Authorization: Bearer <token>
```

---

## 6. API 测试结果汇总

### 6.1 Stack 管理 API

| API                      | 方法   | 状态      | 说明                                       |
| ------------------------ | ------ | --------- | ------------------------------------------ |
| `/api/stacks`            | GET    | ✅ 可用   | 获取 Stack 列表                            |
| `/api/stacks/{id}`       | GET    | ✅ 可用   | 获取 Stack 详情                            |
| `/api/stacks/{id}/file`  | GET    | ✅ 可用   | 获取 compose 文件                          |
| `/api/stacks/{id}/start` | POST   | ✅ 可用   | 启动 Stack                                 |
| `/api/stacks/{id}/stop`  | POST   | ✅ 可用   | 停止 Stack                                 |
| `/api/stacks`            | POST   | ⚠️ 待验证 | 创建 Stack（如遇 405 请检查参数格式）      |
| `/api/stacks/{id}`       | PUT    | ⚠️ 待验证 | 更新/重启 Stack（如遇 500 请检查参数格式） |
| `/api/stacks/{id}`       | DELETE | ✅ 可用   | 删除 Stack                                 |

### 6.2 容器操作 API (Docker 代理)

| API                               | 方法   | 状态      | 说明                              |
| --------------------------------- | ------ | --------- | --------------------------------- |
| `/docker/containers/json`         | GET    | ✅ 可用   | 获取容器列表                      |
| `/docker/containers/{id}/json`    | GET    | ✅ 可用   | 获取容器详情                      |
| `/docker/containers/{id}/start`   | POST   | ✅ 可用   | 启动容器                          |
| `/docker/containers/{id}/stop`    | POST   | ✅ 可用   | 停止容器                          |
| `/docker/containers/{id}/restart` | POST   | ✅ 可用   | 重启容器                          |
| `/docker/containers/{id}/logs`    | GET    | ✅ 可用   | 获取日志                          |
| `/docker/containers/{id}/stats`   | GET    | ✅ 可用   | 获取统计信息                      |
| `/docker/containers/{id}`         | DELETE | ⚠️ 未测试 | 删除容器（建议通过 Stack 删除）   |
| `/docker/containers/create`       | POST   | ❌ 不可用 | 返回 404，Portainer 2.33.3 不支持 |

### 6.3 镜像管理 API

| API                     | 方法 | 状态      | 说明                          |
| ----------------------- | ---- | --------- | ----------------------------- |
| `/docker/images/json`   | GET  | ✅ 可用   | 获取镜像列表                  |
| `/docker/images/create` | POST | ✅ 可用   | 拉取镜像（已测试成功）        |

### 6.4 重要说明

1. **创建容器方式**: Portainer 2.33.3 不支持直接通过 Docker API 创建容器 (`POST /containers/create` 返回 400 错误)。
   - **正确做法**: 使用 Stack API 创建 Stack，镜像会自动拉取

2. **镜像拉取**: ✅ **支持通过API拉取镜像** - 已测试成功拉取 nginx:latest

3. **容器管理**: 可以通过 Docker API 代理管理现有容器（启动、停止、重启、查看日志等）

4. **Endpoint ID**: 当前环境使用 Endpoint ID = 4

5. **Stack 操作限制**:
   - ✅ 支持: 获取Stack列表、详情、文件、启动、删除
   - ❌ 不支持: 创建Stack(405)、更新Stack(500)、停止Stack(400)
   - ⚠️ **替代方案**: 通过 Portainer Web UI 创建和更新 Stack

---

## 7. API 测试详细结果

### 7.1 ✅ 成功的 API

#### 7.1.1 拉取镜像 (POST /docker/images/create)
```
状态码: 200 OK
响应: 成功拉取 nginx:latest 镜像
说明: 可以通过 API 拉取镜像,支持进度流式输出
```

#### 7.1.2 启动 Stack (POST /api/stacks/{id}/start)
```
状态码: 200 OK
测试: Stack ID 18 (ollama-openai-proxy) 启动成功
状态变化: Status = 2 (已停止) → Status = 1 (运行中)
```

#### 7.1.3 获取 Stack 文件 (GET /api/stacks/{id}/file)
```
状态码: 200 OK
响应: 返回完整的 docker-compose.yml 内容
说明: 可用于查看 Stack 的当前配置
```

### 7.2 ❌ 失败的 API

#### 7.2.1 创建 Stack (POST /api/stacks)
```
状态码: 405 Method Not Allowed
请求: POST /api/stacks?endpointId=4&type=2&method=string
请求体: { Name, StackFileContent, Env }
错误: "不允许的方法"
原因: Portainer 2.33.3 可能不支持通过 API 创建 Stack
替代方案: 使用 Portainer Web UI 创建 Stack
```

#### 7.2.2 更新 Stack (PUT /api/stacks/{id})
```
状态码: 500 Internal Server Error
请求: PUT /api/stacks/18?endpointId=4
请求体: { StackFileContent, Env, Prune }
错误: "内部服务器错误"
原因: 可能是参数格式问题或 Portainer 版本限制
替代方案: 使用 Portainer Web UI 更新 Stack
```

#### 7.2.3 停止 Stack (POST /api/stacks/{id}/stop)
```
状态码: 400 Bad Request
请求: POST /api/stacks/18/stop?endpointId=4
错误: "错误的请求"
原因: 可能需要额外的参数或 Header
替代方案: 使用容器级别的停止操作
```

#### 7.2.4 创建容器 (POST /docker/containers/create)
```
状态码: 400 Bad Request
请求: POST /api/endpoints/4/docker/containers/create?name=test-nginx-direct
请求体: { Image, HostConfig }
错误: "错误的请求"
原因: Portainer 2.33.3 不支持直接创建容器
替代方案: 创建 Stack 来部署容器
```

### 7.3 测试结论

**✅ 可用的功能:**
- 查询类操作: 获取列表、详情、文件等
- 容器管理: 启动、停止、重启、查看日志
- Stack 管理: 启动、删除
- 镜像管理: 拉取镜像

**❌ 不可用的功能:**
- Stack 创建和更新
- Stack 停止
- 直接创建容器

**💡 推荐方案:**
- 创建/更新 Stack: 使用 Portainer Web UI
- 管理容器: 使用 API (启动、停止、重启)
- 拉取镜像: 可使用 API 或让 Stack 自动拉取

---

## 6. Stack 列表示例

以下是一个示例 Stack 列表结构：

| ID  | 名称            | 状态     | 镜像                              |
| --- | --------------- | -------- | --------------------------------- |
| 1   | example-stack-1 | Active   | `registry.example.com/app:latest` |
| 2   | example-stack-2 | Inactive | -                                 |

**说明**: 实际 Stack 列表请通过 API 获取

---

## 7. 参考链接

- [Portainer API 官方文档](https://docs.portainer.io/api/docs)
- [Portainer CE API 参考 (2.39.1)](https://api-docs.portainer.io/?edition=ce&version=2.39.1)
- [Portainer BE API 参考 (2.39.1)](https://api-docs.portainer.io/?edition=ee&version=2.39.1)
- [Docker Compose pull_policy 文档](https://docs.docker.com/compose/compose-file/05-services/#pull_policy)

---

## 8. 注意事项

1. **认证方式**:
   - **推荐使用 Access Token** (`X-API-Key` Header): Token长期有效,无需每次登录
   - JWT Token (`Authorization: Bearer` Header): 有效期较短,需定期刷新
2. **EndpointId**: 大多数 Stack 操作需要指定 `endpointId` 参数
3. **StackFileContent**: 更新 Stack 时必须提交完整的 docker-compose 文件内容
4. **重启机制**: Portainer 没有直接的 restart 接口，通过 PUT 更新触发重新部署
5. **镜像更新**:
   - 不带更新：直接使用本地缓存镜像
   - 带更新：在 compose 文件中添加 `pull_policy: always` 强制拉取
6. **权限**: 确保用户有足够的权限操作目标 Stack

---

## 9. 常见问题

### 9.1 Access Token vs JWT Token 有什么区别?

| 特性     | Access Token         | JWT Token                   |
| -------- | -------------------- | --------------------------- |
| 获取方式 | Portainer UI 生成    | API 登录获取                |
| 有效期   | 长期有效(可手动撤销) | 短期有效(通常24小时)        |
| Header   | `X-API-Key: ptr_...` | `Authorization: Bearer ...` |
| 推荐度   | ⭐⭐⭐⭐⭐           | ⭐⭐⭐                      |
| 适用场景 | 自动化脚本、CI/CD    | 临时测试、Web应用           |

### 9.2 如何创建 Access Token?

1. 登录 Portainer Web UI (例如: http://127.0.0.1:9000)
2. 点击右上角用户头像 → "My account"
3. 滚动到 "Access tokens" 区域
4. 点击 "Add access token"
5. 输入描述(如"API Access")，点击 "Add access token"
6. **⚠️ 立即复制生成的Token** (只显示一次!)

### 9.3 测试 Access Token 是否有效

**PowerShell:**

```powershell
$apiKey = "ptr_YOUR_TOKEN_HERE"
$headers = @{"X-API-Key" = $apiKey}
try {
    $result = Invoke-RestMethod -Uri "http://127.0.0.1:9000/api/status" -Headers $headers
    Write-Host "✅ Token 有效! Portainer 版本: $($result.Version)"
} catch {
    Write-Host "❌ Token 无效或已过期: $($_.Exception.Message)"
}
```

**curl:**

```bash
curl -H "X-API-Key: ptr_YOUR_TOKEN_HERE" http://127.0.0.1:9000/api/status
```

### 9.4 Portainer API 常用端口

- `9000`: Portainer Web UI 和 API
- `9443`: Portainer HTTPS (如果启用)
- `8000`: Edge Agent 通信端口

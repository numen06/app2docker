# 主机 Docker Compose 模式检测功能

## 目标

检测主机是否支持 Docker Compose 的两种模式：

- `docker-compose`：传统 Compose 模式（独立命令）
- `docker-stack`：Docker Swarm Stack 模式（需要 Docker Swarm 环境）

并根据主机的支持情况在部署管理界面中限制可选模式。

## 检测时机（重要）

**仅在以下时机检测，不进行频繁检测：**

1. **Agent 主机**：首次连接时（`on_connect` 回调中的 `host_info` 消息）
2. **SSH 主机**：测试连接时（`test_ssh_connection` 或 `test_host_ssh_connection`）
3. **Portainer 主机**：测试连接时（`test_portainer_connection`）或手动刷新状态时（`refresh_agent_host_status`）

**不检测的时机：**

- Agent 主机的定期心跳消息（避免频繁检测）
- 定期状态检查（避免性能影响）

检测结果缓存在 `docker_info` 字段中，供后续使用。

## 实现方案

### 1. 数据模型扩展

在 `AgentHost` 和 `Host` 的 `docker_info` 字段中存储 Compose 模式支持信息：

- `compose_supported`: 布尔值，是否支持 docker-compose
- `stack_supported`: 布尔值，是否支持 docker stack
- `compose_version`: docker-compose 版本（如果支持）
- `swarm_mode`: Docker Swarm 模式状态（active/inactive）

### 2. Agent 主机检测（backend/agent/main.py）

修改 `get_docker_info()` 函数，添加 Compose 模式检测：

- 检测 `docker-compose --version` 命令是否可用
- 检测 Docker Swarm 模式（`docker info --format "{{.Swarm.LocalNodeState}}"`）
- 如果 Swarm 模式为 active，则支持 docker stack
- 将检测结果添加到返回的 `docker_info` 字典中

**注意**：只在 `on_connect()` 回调中调用 `get_docker_info()` 并发送 `host_info` 消息时进行检测，心跳消息不包含此检测。

### 3. SSH 主机检测（backend/host_manager.py）

在 `test_ssh_connection()` 函数中，SSH 连接成功后：

- 执行 `docker-compose --version` 检测传统 Compose
- 执行 `docker info --format "{{.Swarm.LocalNodeState}}"` 检测 Swarm 模式
- 如果 Swarm 模式为 active，则支持 docker stack
- 将检测结果添加到返回的字典中（后续可以扩展 Host 模型存储）

### 4. Portainer 主机检测（backend/agent_host_manager.py）

在 `test_portainer_connection()` 和 `update_portainer_host_status()` 中：

- 通过 Portainer API 获取 Docker info（`get_docker_info()` 方法）
- 从 Docker info 中提取 Swarm 状态（`Swarm.LocalNodeState`）
- 检测是否支持 docker-compose（可能需要通过 API 执行命令，如果 Portainer API 不支持，可以标记为未知）
- 更新 `docker_info` 中的 Compose 支持信息

### 5. 前端界面更新（frontend/src/components/DeployTaskManager.vue）

在部署管理界面中：

- 获取主机信息时，检查 `docker_info.compose_supported` 和 `docker_info.stack_supported`
- 在选择 Compose 模式时：
  - 如果主机不支持 `docker-compose`，禁用该选项并添加提示
  - 如果主机不支持 `docker-stack`，禁用该选项并添加提示
  - 如果都不支持，禁用整个 Compose 模式
- 在选择主机时，如果主机不支持任何 Compose 模式，给出相应提示

### 6. 部署执行验证（可选增强）

在部署执行前，可以添加验证步骤：

- 检查部署配置中的 `compose_mode` 是否与主机支持的模式匹配
- 如果不匹配，返回明确的错误提示

## 文件修改列表

1. **backend/agent/main.py**

   - 修改 `get_docker_info()` 函数，添加 Compose 模式检测
   - **不修改**心跳逻辑，确保不在心跳时检测

2. **backend/host_manager.py**

   - 修改 `test_ssh_connection()` 函数，添加 Compose 模式检测
   - 返回结果中包含 `compose_supported` 和 `stack_supported` 字段

3. **backend/agent_host_manager.py**

   - 修改 `test_portainer_connection()` 方法，添加 Compose 模式检测
   - 修改 `update_portainer_host_status()` 方法，添加 Compose 模式检测（仅在手动刷新时）

4. **frontend/src/components/DeployTaskManager.vue**
   - 在主机选择和数据加载时，处理 Compose 支持信息
   - 根据主机能力禁用不支持的 Compose 模式选项
   - 添加相应的 UI 提示和说明

## 检测逻辑示例

```python
# Agent 检测示例（backend/agent/main.py）
def get_docker_info():
    info = {}
    # ... 现有代码 ...

    # 检测 docker-compose
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            info["compose_supported"] = True
            info["compose_version"] = result.stdout.strip()
        else:
            info["compose_supported"] = False
    except:
        info["compose_supported"] = False

    # 检测 docker stack (需要 Swarm 模式)
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Swarm.LocalNodeState}}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            swarm_state = result.stdout.strip()
            info["swarm_mode"] = swarm_state
            info["stack_supported"] = (swarm_state == "active")
        else:
            info["stack_supported"] = False
    except:
        info["stack_supported"] = False
        info["swarm_mode"] = "unknown"

    return info
```

```python
# SSH 检测示例（backend/host_manager.py）
def test_ssh_connection(...):
    # ... 现有 SSH 连接代码 ...

    # 检测 Docker Compose 模式支持
    compose_supported = False
    stack_supported = False
    compose_version = None
    swarm_mode = None

    try:
        # 检测 docker-compose
        stdin, stdout, stderr = ssh_client.exec_command("docker-compose --version", timeout=5)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            compose_supported = True
            compose_version = stdout.read().decode('utf-8').strip()
    except:
        pass

    try:
        # 检测 Swarm 模式
        stdin, stdout, stderr = ssh_client.exec_command(
            "docker info --format '{{.Swarm.LocalNodeState}}'", timeout=5
        )
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            swarm_mode = stdout.read().decode('utf-8').strip()
            stack_supported = (swarm_mode == "active")
    except:
        pass

    return {
        "success": True,
        "message": "SSH连接成功",
        "docker_available": docker_available,
        "docker_version": docker_version,
        "compose_supported": compose_supported,
        "stack_supported": stack_supported,
        "compose_version": compose_version,
        "swarm_mode": swarm_mode,
    }
```

## 前端显示逻辑

```javascript
// 根据主机能力过滤可用的 Compose 模式
const getAvailableComposeModes = (host) => {
  const dockerInfo = host.docker_info || {};
  const modes = [];

  if (dockerInfo.compose_supported === true) {
    modes.push({ value: "docker-compose", label: "docker-compose" });
  }

  if (dockerInfo.stack_supported === true) {
    modes.push({ value: "docker-stack", label: "docker stack deploy" });
  }

  return modes;
};

// 检查主机是否支持指定的 Compose 模式
const isComposeModeSupported = (host, mode) => {
  const dockerInfo = host.docker_info || {};
  if (mode === "docker-compose") {
    return dockerInfo.compose_supported === true;
  } else if (mode === "docker-stack") {
    return dockerInfo.stack_supported === true;
  }
  return false;
};
```

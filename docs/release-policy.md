# Git 主线与不可变发布版本

仓库根 `.app2docker.yaml` 的 `release` 规则适用于所有 profile，不能通过另选 profile 绕过。

```yaml
release:
  enabled: true
  platform: jbm # iot / building，各自独立占号
  mainline: py-7.3
  version_file: VERSION
  timezone: Asia/Shanghai
  immutable: true
  require_git_tag: true
```

`VERSION` 为 `py-7.3-YYYYMMDD.N`；IoT、建筑的主线均为 `py-2.0`。
统一入口在各仓库 `tools/release.py`：远端 Git 原子预留序号，提交推送生成配置，冻结同名 Git tag，再运行原流水线。

服务端只允许 Git 来源，核对 VERSION、构建 Git tag、远端主线 SHA 和全部输出镜像 tag。
同一镜像版本在 App2Docker 持久数据库内原子占用；失败、取消也不释放，不能覆盖或回用更小序号。
多组件可共用一个平台版本，组件由不同镜像名区分。构建跨日沿用已冻结版本。
构建参数 `{full_commit}` 为完整 SHA；服务端强制设置 `JBM_COMMIT` / `SOURCE_REVISION` 和 `RELEASE_VERSION`，写入镜像 OCI 元数据。

未启用 release 的其他项目保留既有行为。本机制不自动部署，不改变密钥、数据库或设备状态。

#!/usr/bin/env node
/**
 * 启动 Vite 开发服务器：
 * 1. 清除 Cursor/VS Code 注入的调试环境变量，避免多次 Debugger attached 导致卡死
 * 2. 若 3000 端口仍被旧 dev 进程占用则先释放（与 vite.config.js 中 port 一致）
 */
import { spawn, execSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const DEV_PORT = 3000
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const viteBin = path.join(root, 'node_modules', 'vite', 'bin', 'vite.js')

function freePort(port) {
  if (process.platform === 'win32') {
    try {
      const out = execSync(`netstat -ano | findstr ":${port}" | findstr LISTENING`, {
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'ignore'],
      })
      const pids = new Set()
      for (const line of out.trim().split(/\r?\n/)) {
        const parts = line.trim().split(/\s+/)
        const pid = parts[parts.length - 1]
        if (pid && /^\d+$/.test(pid) && pid !== '0') pids.add(pid)
      }
      for (const pid of pids) {
        try {
          execSync(`taskkill /PID ${pid} /F`, { stdio: 'ignore' })
          console.log(`[dev] 已结束占用端口 ${port} 的进程 (PID ${pid})`)
        } catch {
          /* ignore */
        }
      }
    } catch {
      /* 无监听进程 */
    }
    return
  }

  try {
    const out = execSync(`lsof -ti :${port}`, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] })
    for (const pid of out.trim().split(/\s+/).filter(Boolean)) {
      try {
        process.kill(Number(pid), 'SIGTERM')
        console.log(`[dev] 已结束占用端口 ${port} 的进程 (PID ${pid})`)
      } catch {
        /* ignore */
      }
    }
  } catch {
    /* 无监听进程 */
  }
}

function buildEnv() {
  const env = { ...process.env }
  delete env.NODE_OPTIONS
  delete env.VSCODE_INSPECTOR_OPTIONS
  delete env.VSCODE_INSPECTOR_OPTIONS_TEMPLATE
  return env
}

freePort(DEV_PORT)

const child = spawn(process.execPath, [viteBin], {
  cwd: root,
  env: buildEnv(),
  stdio: 'inherit',
  windowsHide: false,
})

child.on('exit', (code, signal) => {
  if (signal) process.exit(1)
  process.exit(code ?? 0)
})

child.on('error', (err) => {
  console.error('[dev] 启动失败:', err.message)
  process.exit(1)
})

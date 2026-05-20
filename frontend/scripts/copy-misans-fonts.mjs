import { cpSync, existsSync, mkdirSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const srcDir = join(root, 'node_modules', 'misans-vf', 'lib')
const destDir = join(root, 'public', 'fonts', 'misans')

if (!existsSync(srcDir)) {
  console.warn('[copy-misans-fonts] misans-vf 未安装，请先运行: npm install')
  process.exit(0)
}

mkdirSync(destDir, { recursive: true })

for (const name of readdirSync(srcDir)) {
  if (name.endsWith('.woff2') || name === 'MiSans.min.css') {
    cpSync(join(srcDir, name), join(destDir, name), { force: true })
  }
}

console.log('[copy-misans-fonts] 已复制 MiSans 字体到 public/fonts/misans/')

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  
  server: {
    port: 3000,
    host: '0.0.0.0',
    // 启用 HMR（热模块替换）
    hmr: {
      host: 'localhost',
      port: 3000,
    },
    // 文件监听配置（Windows 上可能需要轮询）
    watch: {
      usePolling: true, // Windows 上建议启用轮询
      interval: 1000,   // 轮询间隔（毫秒）
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 不需要 rewrite，直接转发 /api 路径
      }
    }
  },
  
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    assetsDir: 'assets'
  }
})

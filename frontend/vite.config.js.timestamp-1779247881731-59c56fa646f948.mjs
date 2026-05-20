// vite.config.js
import { defineConfig } from "file:///D:/workspaces/app2docker/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///D:/workspaces/app2docker/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import tailwindcss from "file:///D:/workspaces/app2docker/frontend/node_modules/@tailwindcss/vite/dist/index.mjs";
import path from "path";
var __vite_injected_original_dirname = "D:\\workspaces\\app2docker\\frontend";
var vite_config_default = defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "./src")
    }
  },
  server: {
    port: 3e3,
    host: "0.0.0.0",
    // 启用 HMR（热模块替换）
    hmr: {
      host: "localhost",
      port: 3e3
    },
    // 文件监听配置（Windows 上可能需要轮询）
    watch: {
      usePolling: true,
      // Windows 上建议启用轮询
      interval: 1e3
      // 轮询间隔（毫秒）
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
        // 不需要 rewrite，直接转发 /api 路径
      }
    }
  },
  build: {
    outDir: "../dist",
    emptyOutDir: true,
    assetsDir: "assets"
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFx3b3Jrc3BhY2VzXFxcXGFwcDJkb2NrZXJcXFxcZnJvbnRlbmRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkQ6XFxcXHdvcmtzcGFjZXNcXFxcYXBwMmRvY2tlclxcXFxmcm9udGVuZFxcXFx2aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovd29ya3NwYWNlcy9hcHAyZG9ja2VyL2Zyb250ZW5kL3ZpdGUuY29uZmlnLmpzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcclxuaW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXHJcbmltcG9ydCB0YWlsd2luZGNzcyBmcm9tICdAdGFpbHdpbmRjc3Mvdml0ZSdcclxuaW1wb3J0IHBhdGggZnJvbSAncGF0aCdcclxuXHJcbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XHJcbiAgcGx1Z2luczogW3Z1ZSgpLCB0YWlsd2luZGNzcygpXSxcclxuICBcclxuICByZXNvbHZlOiB7XHJcbiAgICBhbGlhczoge1xyXG4gICAgICAnQCc6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsICcuL3NyYycpLFxyXG4gICAgfSxcclxuICB9LFxyXG4gIFxyXG4gIHNlcnZlcjoge1xyXG4gICAgcG9ydDogMzAwMCxcclxuICAgIGhvc3Q6ICcwLjAuMC4wJyxcclxuICAgIC8vIFx1NTQyRlx1NzUyOCBITVJcdUZGMDhcdTcwRURcdTZBMjFcdTU3NTdcdTY2RkZcdTYzNjJcdUZGMDlcclxuICAgIGhtcjoge1xyXG4gICAgICBob3N0OiAnbG9jYWxob3N0JyxcclxuICAgICAgcG9ydDogMzAwMCxcclxuICAgIH0sXHJcbiAgICAvLyBcdTY1ODdcdTRFRjZcdTc2RDFcdTU0MkNcdTkxNERcdTdGNkVcdUZGMDhXaW5kb3dzIFx1NEUwQVx1NTNFRlx1ODBGRFx1OTcwMFx1ODk4MVx1OEY2RVx1OEJFMlx1RkYwOVxyXG4gICAgd2F0Y2g6IHtcclxuICAgICAgdXNlUG9sbGluZzogdHJ1ZSwgLy8gV2luZG93cyBcdTRFMEFcdTVFRkFcdThCQUVcdTU0MkZcdTc1MjhcdThGNkVcdThCRTJcclxuICAgICAgaW50ZXJ2YWw6IDEwMDAsICAgLy8gXHU4RjZFXHU4QkUyXHU5NUY0XHU5Njk0XHVGRjA4XHU2QkVCXHU3OUQyXHVGRjA5XHJcbiAgICB9LFxyXG4gICAgcHJveHk6IHtcclxuICAgICAgJy9hcGknOiB7XHJcbiAgICAgICAgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMTo4MDAwJyxcclxuICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWUsXHJcbiAgICAgICAgLy8gXHU0RTBEXHU5NzAwXHU4OTgxIHJld3JpdGVcdUZGMENcdTc2RjRcdTYzQTVcdThGNkNcdTUzRDEgL2FwaSBcdThERUZcdTVGODRcclxuICAgICAgfVxyXG4gICAgfVxyXG4gIH0sXHJcbiAgXHJcbiAgYnVpbGQ6IHtcclxuICAgIG91dERpcjogJy4uL2Rpc3QnLFxyXG4gICAgZW1wdHlPdXREaXI6IHRydWUsXHJcbiAgICBhc3NldHNEaXI6ICdhc3NldHMnXHJcbiAgfVxyXG59KVxyXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQTZSLFNBQVMsb0JBQW9CO0FBQzFULE9BQU8sU0FBUztBQUNoQixPQUFPLGlCQUFpQjtBQUN4QixPQUFPLFVBQVU7QUFIakIsSUFBTSxtQ0FBbUM7QUFLekMsSUFBTyxzQkFBUSxhQUFhO0FBQUEsRUFDMUIsU0FBUyxDQUFDLElBQUksR0FBRyxZQUFZLENBQUM7QUFBQSxFQUU5QixTQUFTO0FBQUEsSUFDUCxPQUFPO0FBQUEsTUFDTCxLQUFLLEtBQUssUUFBUSxrQ0FBVyxPQUFPO0FBQUEsSUFDdEM7QUFBQSxFQUNGO0FBQUEsRUFFQSxRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixNQUFNO0FBQUE7QUFBQSxJQUVOLEtBQUs7QUFBQSxNQUNILE1BQU07QUFBQSxNQUNOLE1BQU07QUFBQSxJQUNSO0FBQUE7QUFBQSxJQUVBLE9BQU87QUFBQSxNQUNMLFlBQVk7QUFBQTtBQUFBLE1BQ1osVUFBVTtBQUFBO0FBQUEsSUFDWjtBQUFBLElBQ0EsT0FBTztBQUFBLE1BQ0wsUUFBUTtBQUFBLFFBQ04sUUFBUTtBQUFBLFFBQ1IsY0FBYztBQUFBO0FBQUEsTUFFaEI7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBRUEsT0FBTztBQUFBLElBQ0wsUUFBUTtBQUFBLElBQ1IsYUFBYTtBQUFBLElBQ2IsV0FBVztBQUFBLEVBQ2I7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=

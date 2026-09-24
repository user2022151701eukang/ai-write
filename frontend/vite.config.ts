import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 配置
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // 别名指向项目根目录下的 src 目录
      '@': '/src'
    }
  },
  server: {
    port: 5173,
    proxy: {
      // 将 /api 代理到后端 FastAPI 服务
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      // 健康检查接口（首页用于判断大模型是否已配置）
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
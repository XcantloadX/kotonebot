import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: '@', replacement: path.resolve(__dirname, './src') },
      { find: /^@kotonebot\/shared(?:\/.*)?$/, replacement: path.resolve(__dirname, '../../packages/shared/src') },
    ],
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:1178',
        changeOrigin: true,
      }
    }
  }
})

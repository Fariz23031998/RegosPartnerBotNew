import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/regos-partner-bot/mini-app/',
  server: {
    port: 5175,
    host: true,
    proxy: {
      '/regos-partner-bot/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/regos-partner-bot\/api/, '/api'),
      },
    },
    allowedHosts: ['7813fb45748a.ngrok-free.app'],
  },
})

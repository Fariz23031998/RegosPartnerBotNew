import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/regos-partner-bot/admin/',
  server: {
    port: 5173,
    proxy: {
      '/regos-partner-bot/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/regos-partner-bot\/api/, '/api'),
      },
    },
  },
})



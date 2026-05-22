import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // Rewrite redirect Location to stay within Vite proxy
            if (proxyRes.statusCode >= 300 && proxyRes.statusCode < 400 && proxyRes.headers.location) {
              const loc = proxyRes.headers.location
              if (loc.startsWith('http://127.0.0.1:8000')) {
                proxyRes.headers.location = loc.replace('http://127.0.0.1:8000', '')
              }
            }
          })
        },
      },
    },
  },
})

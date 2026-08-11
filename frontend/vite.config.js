import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      usePolling: true,
    },
    host: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:5000',
        changeOrigin: true,
        timeout: 600000,      // 10 minutes — yt-dlp may take minutes for large videos
        proxyTimeout: 600000, // 10 minutes — wait for backend to finish extraction
      }
    }
  },
})

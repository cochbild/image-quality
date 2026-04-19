import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const devApiKey = process.env.IQA_API_KEY ?? ''

const withApiKey = {
  target: 'http://localhost:8100',
  changeOrigin: true,
  configure: (proxy: { on: (e: string, cb: (req: { setHeader: (k: string, v: string) => void }) => void) => void }) => {
    proxy.on('proxyReq', (proxyReq) => {
      if (devApiKey) proxyReq.setHeader('X-API-Key', devApiKey)
    })
  },
}

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Split heavy vendor libs into their own long-lived chunks so changes to
    // app code don't invalidate the cached vendor bundles.
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          mui: ['@mui/material', '@mui/icons-material'],
          emotion: ['@emotion/react', '@emotion/styled'],
        },
      },
    },
  },
  server: {
    port: 5180,
    strictPort: true,
    host: '0.0.0.0',
    proxy: {
      '/api': withApiKey,
    },
  },
})

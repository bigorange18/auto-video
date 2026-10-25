import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const appPort = Number(env.PORT || 8787)
  const devHost = env.DEV_HOST || '0.0.0.0'
  const devPort = Number(env.DEV_PORT || 5173)
  const apiTarget = env.DEV_API_TARGET || `http://127.0.0.1:${appPort}`

  return {
    plugins: [vue()],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (
              id.includes('/node_modules/marked/')
              || id.includes('/node_modules/highlight.js/')
            ) {
              return 'markdown-vendor'
            }
          },
        },
      },
    },
    server: {
      host: devHost,
      port: devPort,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})

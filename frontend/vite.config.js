import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const crispId = env.VITE_CRISP_ID || ''

  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'usina-html-vars',
        transformIndexHtml(html) {
          return html.replaceAll('__VITE_CRISP_ID__', crispId)
        },
      },
    ],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  }
})

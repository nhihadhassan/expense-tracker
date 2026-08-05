import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/app/',
  plugins: [react()],
  build: { outDir: 'web/app', emptyOutDir: true },
  server: { proxy: { '/api': 'http://localhost:8765' } },
})

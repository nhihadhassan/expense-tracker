import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const runtimeEnv = (globalThis as typeof globalThis & { process?: { env?: Record<string, string | undefined> } }).process?.env || {}
  const env = { ...loadEnv(mode, '.', ''), ...runtimeEnv }
  return {
    base: '/app/',
    publicDir: false,
    plugins: [react()],
    define: {
      'import.meta.env.VITE_SUPABASE_URL': JSON.stringify(env.SUPABASE_URL || env.VITE_SUPABASE_URL || ''),
      'import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY': JSON.stringify(env.SUPABASE_PUBLISHABLE_KEY || env.VITE_SUPABASE_PUBLISHABLE_KEY || ''),
    },
    build: {
      outDir: 'web/app',
      emptyOutDir: true,
      sourcemap: false,
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              { name: 'supabase', test: /node_modules[\\/]@supabase[\\/]/ },
              { name: 'icons', test: /node_modules[\\/]@phosphor-icons[\\/]/ },
            ],
          },
        },
      },
    },
    server: { proxy: { '/api': 'http://localhost:8765' } },
  }
})

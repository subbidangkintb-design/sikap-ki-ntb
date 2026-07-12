import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import os from 'node:os'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  cacheDir: path.join(os.tmpdir(), 'sikapki-vite-cache'),
  server: {
    host: '127.0.0.1',
    port: 5173,
  },
})

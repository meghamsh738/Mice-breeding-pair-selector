import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const ROOT_DIR = path.resolve(__dirname, '..')
const DIST_DIR = process.env.APP_DIST_DIR ?? path.join(ROOT_DIR, '.app-dist', 'web')

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    outDir: DIST_DIR,
    emptyOutDir: true,
    copyPublicDir: false,
  },
})

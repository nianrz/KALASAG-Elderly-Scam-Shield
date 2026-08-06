/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Frontend calls /api/*; vite proxies to the FastAPI backend in dev so
    // there is no CORS config to get wrong.
    proxy: { '/api': 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test-setup.ts',
    // Component tests live next to their components. E2E lives in qa/.
    include: ['src/**/*.test.{ts,tsx}'],
  },
})

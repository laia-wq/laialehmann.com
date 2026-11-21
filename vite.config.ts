import { defineConfig } from 'vite';

export default defineConfig({
  define: { __BUILD_DATE__: JSON.stringify(new Date().toISOString()) },
  base: '/',
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 800,
  },
});

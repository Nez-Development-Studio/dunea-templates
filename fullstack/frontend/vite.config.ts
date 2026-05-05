import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    dedupe: ['react', 'react-dom'],
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react/jsx-runtime'],
  },
  server: {
    host: '0.0.0.0',
    hmr: false,
    port: 5173,
    allowedHosts: true,
    proxy: {
      '/api': 'http://localhost:8000',
    },
    watch: {
      // Don't watch tsconfig — triggers a Vite cache-clear that segfaults Node in containers
      ignored: ['**/tsconfig*.json'],
    },
  },
});

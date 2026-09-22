import { resolve } from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [tailwindcss(), react()],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        map: resolve(__dirname, 'map.html'),
        weather: resolve(__dirname, 'weather.html'),
        awareness: resolve(__dirname, 'awareness.html'),
        community: resolve(__dirname, 'community.html'),
        alerts: resolve(__dirname, 'alerts.html'),
        evacuation: resolve(__dirname, 'evacuation.html'),
        xai: resolve(__dirname, 'xai.html'),
        digital_twin: resolve(__dirname, 'digital_twin.html'),
        simulation: resolve(__dirname, 'simulation.html'),
      },
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
    },
  },
});

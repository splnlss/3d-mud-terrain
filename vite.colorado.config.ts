import { defineConfig } from 'vite';
export default defineConfig({ publicDir:false, build:{outDir:'dist-colorado',rollupOptions:{input:'colorado.html'}} });

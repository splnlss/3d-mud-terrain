// Standalone build of the relief tiles preview for static hosting. Tiles are not bundled: set VITE_RELIEF_BASE to the
// published tileset folder. `scripts/build-relief-site.sh` runs this and adds the texture decoder.
import { defineConfig } from 'vite';

export default defineConfig({
  publicDir: false,
  build: { outDir: 'dist-relief', emptyOutDir: true, rollupOptions: { input: 'relief.html' } },
});

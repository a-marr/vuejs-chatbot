import { fileURLToPath, URL } from 'node:url'
import Components from 'unplugin-vue-components/vite';
import { PrimeVueResolver } from '@primevue/auto-import-resolver';

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
//import vueDevTools from 'vite-plugin-vue-devtools'




// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {  // Add this return statement
    plugins: [
      vue(),
      Components({
        resolvers: [
          PrimeVueResolver()
        ]
      })
    ],
    build: {
      outDir: 'dist',
      sourcemap: true
    },
    base: '/',
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    }
  }
})
const { defineConfig } = require('@vue/cli-service')

const BACKEND_URL = process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8000'

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    allowedHosts: "all",
    port: 8101,
    host: "0.0.0.0",
    // Disable HMR when running in serve mode with NODE_ENV=production
    // This prevents infinite reload loops in production deployments
    hot: process.env.NODE_ENV !== 'production',
    liveReload: process.env.NODE_ENV !== 'production',
    proxy: {
      '/api': {

        target: process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8100/',
        changeOrigin: true,
      },
      '/backend': {
        target: process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8100',

        changeOrigin: true,
      },
      '/media': {
        target: process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8100',
        changeOrigin: true,
      },
      '/notebook': {
        target: process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8100',
        changeOrigin: true,
      },
    },
  }
})

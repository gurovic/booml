const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 8101,
    host: "0.0.0.0",
    proxy: {
      '/api': {
        target: process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8100/',
        changeOrigin: true,
      },
      '/backend': {
        target: process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8100',
        changeOrigin: true,
      },
    },
  }
})

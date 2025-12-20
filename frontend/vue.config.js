const { defineConfig } = require('@vue/cli-service')

const BACKEND_URL = process.env.VUE_APP_BACKEND_URL || 'http://127.0.0.1:8000'

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 3000,
    host: "localhost",
    proxy: {
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/backend': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
    },
  }
})

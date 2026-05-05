const { defineConfig } = require('@vue/cli-service')
const fs = require('fs')

const runningInDocker = fs.existsSync('/.dockerenv')
const configuredBackendUrl = process.env.VUE_APP_BACKEND_URL || ''

const resolveBackendTarget = () => {
  const fallback = 'http://127.0.0.1:8100'
  if (!configuredBackendUrl) return fallback

  const pointsToDockerAlias = /^https?:\/\/backend(?::|\/|$)/.test(configuredBackendUrl)
  if (!runningInDocker && pointsToDockerAlias) return fallback

  return configuredBackendUrl.replace(/\/+$/, '')
}

const backendTarget = resolveBackendTarget()

module.exports = defineConfig({
  transpileDependencies: true,
  pages: {
    index: {
      entry: 'src/main.js',
      title: 'BOOML Dashboard',
    },
  },
  devServer: {
    allowedHosts: 'all',
    port: 8102,
    host: '0.0.0.0',
    hot: process.env.NODE_ENV !== 'production',
    liveReload: process.env.NODE_ENV !== 'production',
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/backend': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
})

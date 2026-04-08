const { defineConfig } = require('@vue/cli-service')
const fs = require('fs')

const runningInDocker = fs.existsSync('/.dockerenv')
const configuredBackendUrl = process.env.VUE_APP_BACKEND_URL || ''

const resolveBackendTarget = () => {
  const fallback = 'http://127.0.0.1:8100'
  if (!configuredBackendUrl) return fallback

  // Common local-dev pitfall: env from docker-compose leaks to host shell.
  // If frontend runs on host and target is docker DNS alias, use localhost.
  const pointsToDockerAlias = /^https?:\/\/backend(?::|\/|$)/.test(configuredBackendUrl)
  if (!runningInDocker && pointsToDockerAlias) return fallback

  return configuredBackendUrl.replace(/\/+$/, '')
}

const backendTarget = resolveBackendTarget()

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
        target: backendTarget,
        changeOrigin: true,
      },
      '/backend': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/media': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  }
})

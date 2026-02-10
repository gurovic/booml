import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import MonitoringDashboard from '../MonitoringDashboard.vue'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: {} }))
  }
}))

// Mock router
const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
  ]
})

describe('MonitoringDashboard', () => {
  beforeEach(() => {
    router.push('/')
    router.isReady()
  })

  it('renders monitoring dashboard for any authorized user', async () => {
    const wrapper = mount(MonitoringDashboard, {
      global: {
        plugins: [
          router,
          createTestingPinia({
            initialState: {
              user: {
                currentUser: {
                  id: 1,
                  username: 'user',
                  email: 'user@example.com',
                  role: 'student', // даже студент может видеть мониторинг
                  accessToken: 'fake-token',
                  refreshToken: 'fake-refresh-token'
                }
              }
            }
          })
        ]
      }
    })

    // Wait for component to update
    await wrapper.vm.$nextTick()

    // Проверяем, что компонент отображается без сообщения об ошибке доступа
    expect(wrapper.text()).toContain('Мониторинг системы')
    expect(wrapper.text()).not.toContain('Доступ запрещен')
  })

  it('allows access for teacher users', async () => {
    const wrapper = mount(MonitoringDashboard, {
      global: {
        plugins: [
          router,
          createTestingPinia({
            initialState: {
              user: {
                currentUser: {
                  id: 1,
                  username: 'teacher',
                  email: 'teacher@example.com',
                  role: 'teacher', // учитель также может видеть мониторинг
                  accessToken: 'fake-token',
                  refreshToken: 'fake-refresh-token'
                }
              }
            }
          })
        ]
      }
    })

    // Wait for component to update
    await wrapper.vm.$nextTick()

    // Проверяем, что компонент отображается без сообщения об ошибке доступа
    expect(wrapper.text()).toContain('Мониторинг системы')
    expect(wrapper.text()).not.toContain('Доступ запрещен')
  })
})
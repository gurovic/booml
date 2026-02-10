import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import UiHeader from '../UiHeader.vue'
import { useUserStore } from '@/stores/UserStore'

// Mock router
const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/courses', component: { template: '<div>Courses</div>' } },
    { path: '/polygon', component: { template: '<div>Polygon</div>' } },
    { path: '/monitoring', component: { template: '<div>Monitoring</div>' } },
  ]
})

describe('UiHeader', () => {
  beforeEach(() => {
    router.push('/')
    router.isReady()
  })

  it('renders monitoring link for authorized users', async () => {
    const wrapper = mount(UiHeader, {
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
                  role: 'student',
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

    // Find the monitoring button - it should exist for any authorized user
    const monitoringButtons = wrapper.findAll('button.header__nav-link')
    expect(monitoringButtons).toHaveLength(3) // 'Мои курсы', 'Полигон', 'Мониторинг'
    expect(monitoringButtons[2].text()).toContain('Мониторинг')
  })

  it('does not render monitoring link for unauthorized users', async () => {
    const wrapper = mount(UiHeader, {
      global: {
        plugins: [
          router,
          createTestingPinia({
            initialState: {
              user: {
                currentUser: null // Not logged in
              }
            }
          })
        ]
      }
    })

    // Wait for component to update
    await wrapper.vm.$nextTick()

    // Check that nav does not exist when not authorized
    const navElement = wrapper.find('.header__nav')
    expect(navElement.exists()).toBe(false)
  })

  it('calls router push when monitoring button is clicked', async () => {
    const spy = vi.spyOn(router, 'push')
    
    const wrapper = mount(UiHeader, {
      global: {
        plugins: [
          router,
          createTestingPinia({
            initialState: {
              user: {
                currentUser: {
                  id: 1,
                  username: 'admin',
                  email: 'admin@example.com',
                  role: 'admin',
                  accessToken: 'fake-token',
                  refreshToken: 'fake-refresh-token'
                }
              }
            }
          })
        ]
      }
    })

    await wrapper.vm.$nextTick()

    const monitoringButton = wrapper.find('button.header__nav-link')
    await monitoringButton.trigger('click')

    expect(spy).toHaveBeenCalledWith('/monitoring')
  })
})
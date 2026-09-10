import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useBackgroundJobs } from '@/composables/useBackgroundJobs'
import { apiClient } from '@/lib/api/client'

const Host = defineComponent({
  setup() {
    const { jobs, isSuccess } = useBackgroundJobs()
    return { jobs, isSuccess }
  },
  template: '<div>{{ isSuccess }}:{{ jobs.length }}:{{ jobs[0]?.id || "" }}</div>',
})

function render() {
  return mount(Host, {
    global: {
      plugins: [
        [
          VueQueryPlugin,
          {
            queryClient: new QueryClient({
              defaultOptions: { queries: { retry: false } },
            }),
          },
        ],
      ],
    },
  })
}

afterEach(() => vi.restoreAllMocks())

describe('useBackgroundJobs', () => {
  it('exposes an empty list when nothing is running', async () => {
    vi.spyOn(apiClient, 'getBackgroundJobs').mockResolvedValue({ jobs: [] })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('true:0:')
  })

  it('maps in-process ParseAll jobs', async () => {
    vi.spyOn(apiClient, 'getBackgroundJobs').mockResolvedValue({
      jobs: [{ id: 'anibelka:ParseAllTask', tracker: 'anibelka', job: 'ParseAllTask' }],
    })
    const wrapper = render()
    await flushPromises()
    expect(wrapper.text()).toContain('true:1:anibelka:ParseAllTask')
  })
})

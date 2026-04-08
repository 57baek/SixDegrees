import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

// 1. Mock router params.
const routeParams = { userId: undefined }

vi.mock('vue-router', () => {
  const mockPush = vi.fn()
  const mockBack = vi.fn()
  const mockReplace = vi.fn()

  const useRouter = vi.fn(() => ({ push: mockPush, back: mockBack, replace: mockReplace }))
  const useRoute = vi.fn(() => ({ params: routeParams }))

  return { useRouter, useRoute }
})

// 2. Mock Supabase with a controlled `supabase` object.
vi.mock('../lib/supabase', () => {
  const supabase = {
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'user-1' } } })
    },
    rpc: vi.fn()
  }

  supabase.rpc.mockImplementation((fnName) => {
    if (fnName === 'get_user_profile') {
      return {
        single: () => Promise.resolve({
          data: {
            id: 'user-1',
            nickname: 'Alice',
            bio: 'Hello CWRU',
            age: 25,
            city: 'Cleveland',
            state: 'OH',
            education: 'CWRU',
            occupation: 'Engineer',
            industry: 'Tech',
            interests: ['coding', 'hiking'],
            languages: ['English', 'Mandarin'],
            friends: ['u2', 'u3']
          },
          error: null
        })
      }
    }
    if (fnName === 'update_profile') {
      return Promise.resolve({ data: null, error: null })
    }
    if (fnName === 'request_friend') {
      return Promise.resolve({ data: true, error: null })
    }
    return Promise.resolve({ data: null, error: null })
  })

  return { supabase }
})

// 3. Import the component.
import Profile from '../views/Profile.vue'

// 4. Simple helpers (no `useRoute`).
function mountOwnProfile() {
  routeParams.userId = undefined
  return mount(Profile, {
    global: {
      stubs: { RouterLink: true },
    },
  })
}

function mountOtherProfile() {
  routeParams.userId = 'other-user-999'
  return mount(Profile, {
    global: {
      stubs: { RouterLink: true },
    },
  })
}

// 5. Minimal UI tests.
describe('Profile display', () => {
  afterEach(() => {
    vi.clearAllMocks()
    routeParams.userId = undefined
  })

  it('renders the nickname', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('Alice')
  })

  it('renders the bio', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('Hello CWRU')
  })

  it('renders age', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('25')
  })

  it('renders location as city, state', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('Cleveland, OH')
  })

  it('renders interests as tags', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('coding')
    expect(wrapper.text()).toContain('hiking')
  })

  it('renders languages', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('English')
    expect(wrapper.text()).toContain('Mandarin')
  })
})

describe('Own profile vs other profile', () => {
  afterEach(() => {
    vi.clearAllMocks()
    routeParams.userId = undefined
  })

  it('shows Edit Profile button on own profile', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.find('.edit-btn-header').exists()).toBe(true)
  })

  it('hides Edit Profile button on other user profile', async () => {
    const wrapper = mountOtherProfile()
    await flushPromises()
    expect(wrapper.find('.edit-btn-header').exists()).toBe(false)
  })

  it('shows Friends count button on own profile', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.find('#friends-btn').text()).toContain('Friends (2)')
  })

  it('shows Add Friend button on other user profile', async () => {
    const wrapper = mountOtherProfile()
    await flushPromises()
    expect(wrapper.find('.add-friend-btn').exists()).toBe(true)
  })
})

describe('Profile edit form', () => {
  afterEach(() => {
    vi.clearAllMocks()
    routeParams.userId = undefined
  })

  it('shows edit form after clicking Edit Profile', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    await wrapper.find('.edit-btn-header').trigger('click')
    expect(wrapper.find('.edit-form').exists()).toBe(true)
  })

  it('prefills nickname input with current nickname', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    await wrapper.find('.edit-btn-header').trigger('click')
    const input = wrapper.find('input.name-input')
    expect(input.element.value).toBe('Alice')
  })

  it('hides edit form after clicking Cancel', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    await wrapper.find('.edit-btn-header').trigger('click')
    await wrapper.find('.cancel-btn').trigger('click')
    expect(wrapper.find('.edit-form').exists()).toBe(false)
  })
})
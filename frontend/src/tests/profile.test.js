// src/tests/profile.test.js
// Component-level tests using @vue/test-utils
// Tests cover: profile rendering, own vs other profile, edit form, friend request button
// To run: npm profile test  (from /frontend directory)
// Framework: Vitest + @vue/test-utils (https://vitest.dev)

import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'

// use a real router so we can control params per-test
const routeParams = { userId: undefined }

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useRoute:  () => ({ params: routeParams }),
  }
})

// Mock Supabase
const mockProfile = {
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
  friends: ['u2', 'u3'],
}

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'user-1' } } }),
    },
    rpc: vi.fn((fnName) => {
      if (fnName === 'get_user_profile')   return { single: () => Promise.resolve({ data: mockProfile, error: null }) }
      if (fnName === 'extended_friends')   return Promise.resolve({ data: [], error: null })
      if (fnName === 'has_pending_request') return Promise.resolve({ data: false, error: null })
      if (fnName === 'update_profile')     return Promise.resolve({ data: null, error: null })
      if (fnName === 'request_friend')     return Promise.resolve({ data: true, error: null })
      return Promise.resolve({ data: null, error: null })
    }),
  },
}))

import Profile from '../views/Profile.vue'
import { supabase } from '../lib/supabase'

function mountOwnProfile() {
  routeParams.userId = undefined  // own profile: no userId in route
  return mount(Profile)
}

function mountOtherProfile() {
  routeParams.userId = 'other-user-999'  // other profile
  return mount(Profile)
}

// Tests profile display
describe('Profile display', () => {
  afterEach(() => { vi.clearAllMocks(); routeParams.userId = undefined })

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

  it('renders correct friend count on own profile', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.find('#friends-btn').text()).toContain('Friends (2)')
  })

  it('renders correct avatar initial', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.find('.profile-pic-circle').text()).toContain('A')
  })
})

// Tests own vs other profile
describe('Profile own vs other', () => {
  afterEach(() => { vi.clearAllMocks(); routeParams.userId = undefined })

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

  it('shows Friends count on own profile', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.find('#friends-btn').text()).toContain('Friends (2)')
  })

  it('shows Add Friend button on other user profile', async () => {
    const wrapper = mountOtherProfile()
    await flushPromises()
    expect(wrapper.find('.add-friend-btn').exists()).toBe(true)
  })

  it('shows fallback nickname when not set', async () => {
    supabase.rpc.mockImplementationOnce(() => ({
      single: () => Promise.resolve({ data: { ...mockProfile, nickname: null }, error: null })
    }))
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('Set your nickname')
  })

  it('shows fallback bio when not set', async () => {
    supabase.rpc.mockImplementationOnce(() => ({
      single: () => Promise.resolve({ data: { ...mockProfile, bio: null }, error: null })
    }))
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('Tell people about yourself')
  })
})

// Tests edit form
describe('Profile edit form', () => {
  afterEach(() => { vi.clearAllMocks(); routeParams.userId = undefined })

  it('shows edit form after clicking Edit Profile', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    await wrapper.find('.edit-btn-header').trigger('click')
    expect(wrapper.find('.edit-form').exists()).toBe(true)
  })

  it('pre-fills nickname input with current nickname', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    await wrapper.find('.edit-btn-header').trigger('click')
    expect(wrapper.find('.name-input').element.value).toBe('Alice')
  })

  it('pre-fills bio textarea with current bio', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    await wrapper.find('.edit-btn-header').trigger('click')
    expect(wrapper.find('.bio-input').element.value).toBe('Hello CWRU')
  })

  it('hides edit form after clicking Cancel', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    await wrapper.find('.edit-btn-header').trigger('click')
    await wrapper.find('.cancel-btn').trigger('click')
    expect(wrapper.find('.edit-form').exists()).toBe(false)
  })

  it('calls update_profile RPC on save', async () => {
    const wrapper = mountOwnProfile()
    await flushPromises()
    await wrapper.find('.edit-btn-header').trigger('click')
    await wrapper.find('.save-btn').trigger('click')
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('update_profile', expect.any(Object))
  })
})

// Tests empty states
describe('Profile empty states', () => {
  afterEach(() => { vi.clearAllMocks(); routeParams.userId = undefined })

  it('shows empty interests message when none set', async () => {
    supabase.rpc.mockImplementationOnce(() => ({
      single: () => Promise.resolve({ data: { ...mockProfile, interests: [] }, error: null })
    }))
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('No interests added yet')
  })

  it('shows empty languages message when none set', async () => {
    supabase.rpc.mockImplementationOnce(() => ({
      single: () => Promise.resolve({ data: { ...mockProfile, languages: [] }, error: null })
    }))
    const wrapper = mountOwnProfile()
    await flushPromises()
    expect(wrapper.text()).toContain('No languages added yet')
  })
})

// Tests friend request button
describe('Profile friend request', () => {
  afterEach(() => { vi.clearAllMocks(); routeParams.userId = undefined })

  it('calls request_friend RPC when Add Friend is clicked', async () => {
    const wrapper = mountOtherProfile()
    await flushPromises()
    await wrapper.find('.add-friend-btn').trigger('click')
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('request_friend', expect.any(Object))
  })

  it('shows Request Sent after clicking Add Friend', async () => {
    const wrapper = mountOtherProfile()
    await flushPromises()
    await wrapper.find('.add-friend-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.friend-requested').exists()).toBe(true)
  })
})
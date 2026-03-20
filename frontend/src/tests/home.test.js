// src/tests/home.test.js
// Component-level tests using @vue/test-utils
// Tests cover: feed rendering, friend requests, tier filter, friend request send/accept/reject
// To run: npm test home (from /frontend directory)
// Framework: Vitest + @vue/test-utils (https://vitest.dev)

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const mockPush = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute:  () => ({ params: {} }),
}))

vi.mock('../components/CreatePost.vue', () => ({
  default: { template: '<div class="create-post-stub" />' }
}))

vi.mock('../components/Post.vue', () => ({
  default: {
    props: ['post'],
    template: '<div class="post-stub">{{ post.content }}</div>'
  }
}))

const mockPosts = [
  { id: '1', content: 'Hello CWRU', tier: 1, nickname: 'Alice', like_count: 0, comment_count: 0, created_at: new Date().toISOString() },
  { id: '2', content: 'Second post', tier: 2, nickname: 'Bob',   like_count: 2, comment_count: 1, created_at: new Date().toISOString() },
  { id: '3', content: 'Third post',  tier: 3, nickname: 'Carol', like_count: 1, comment_count: 0, created_at: new Date().toISOString() },
]

const mockRequests = [
  { id: 'req-1', nickname: 'Dave' },
  { id: 'req-2', nickname: 'Eve'  },
]

// Default mock implementation for Supabase RPC calls, can be overridden per-test
function setupDefaultMocks() {
  supabase.rpc.mockImplementation((fnName) => {
    if (fnName === 'load_posts')      return Promise.resolve({ data: mockPosts, error: null })
    if (fnName === 'friend_requests') return Promise.resolve({ data: mockRequests, error: null })
    if (fnName === 'request_friend')  return Promise.resolve({ data: true, error: null })
    if (fnName === 'accept_friend')   return Promise.resolve({ data: true, error: null })
    if (fnName === 'reject_friend')   return Promise.resolve({ data: true, error: null })
    return Promise.resolve({ data: null, error: null })
  })
}

vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getUser:  vi.fn().mockResolvedValue({ data: { user: { id: 'user-1' } } }),
      signOut:  vi.fn().mockResolvedValue({}),
    },
    rpc: vi.fn(),
  },
}))

import Home from '../views/Home.vue'
import { supabase } from '../lib/supabase'

// ─── Tests feed rendering ─────────────────────────────────────────────────────
describe('Home feed rendering', () => {
  beforeEach(() => {
    vi.stubGlobal('alert', vi.fn())
    setupDefaultMocks()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('renders posts after loading', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    expect(wrapper.findAll('.post-stub').length).toBe(3)
  })

  it('shows no-posts message when feed is empty', async () => {
    supabase.rpc.mockImplementation((fnName) => {
      if (fnName === 'load_posts')      return Promise.resolve({ data: [], error: null })
      if (fnName === 'friend_requests') return Promise.resolve({ data: [], error: null })
      return Promise.resolve({ data: null, error: null })
    })
    const wrapper = mount(Home)
    await flushPromises()
    expect(wrapper.text()).toContain('No posts yet')
  })

  it('calls load_posts RPC on mount', async () => {
    mount(Home)
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('load_posts')
  })
})

// ─── Tests tier filter ────────────────────────────────────────────────────────
describe('Home tier filter', () => {
  beforeEach(() => {
    vi.stubGlobal('alert', vi.fn())
    setupDefaultMocks()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('shows all 3 tier filter buttons', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    expect(wrapper.findAll('.filter-btn').length).toBe(3)
  })

  it('defaults to showing all posts (tier 3 filter active)', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    expect(wrapper.findAll('.post-stub').length).toBe(3)
  })

  it('filters to tier 1 posts only when tier 1 button clicked', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    await wrapper.findAll('.filter-btn')[0].trigger('click')
    expect(wrapper.findAll('.post-stub').length).toBe(1)
  })

  it('filters to tier 1 and 2 posts when tier 2 button clicked', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    await wrapper.findAll('.filter-btn')[1].trigger('click')
    expect(wrapper.findAll('.post-stub').length).toBe(2)
  })

  it('marks the active filter button with active class', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    await wrapper.findAll('.filter-btn')[0].trigger('click')
    expect(wrapper.findAll('.filter-btn')[0].classes()).toContain('active')
    expect(wrapper.findAll('.filter-btn')[1].classes()).not.toContain('active')
  })
})

// ─── Tests friend requests ────────────────────────────────────────────────────
describe('Home friend requests', () => {
  beforeEach(() => {
    vi.stubGlobal('alert', vi.fn())
    setupDefaultMocks()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('calls friend_requests RPC on mount', async () => {
    mount(Home)
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('friend_requests')
  })

  it('renders incoming friend requests', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    expect(wrapper.text()).toContain('Dave')
    expect(wrapper.text()).toContain('Eve')
  })

  it('shows no pending requests message when list is empty', async () => {
    supabase.rpc.mockImplementation((fnName) => {
      if (fnName === 'load_posts')      return Promise.resolve({ data: mockPosts, error: null })
      if (fnName === 'friend_requests') return Promise.resolve({ data: [], error: null })
      return Promise.resolve({ data: null, error: null })
    })
    const wrapper = mount(Home)
    await flushPromises()
    expect(wrapper.text()).toContain('No pending requests')
  })

  it('calls accept_friend RPC when Accept is clicked', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    await wrapper.find('.accept-btn').trigger('click')
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('accept_friend', { friend_nickname: 'Dave' })
  })

  it('calls reject_friend RPC when Reject is clicked', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    await wrapper.find('.reject-btn').trigger('click')
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('reject_friend', { friend_nickname: 'Dave' })
  })

  it('refreshes requests after accepting', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    supabase.rpc.mockClear()
    await wrapper.find('.accept-btn').trigger('click')
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('friend_requests')
  })

  it('refreshes requests after rejecting', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    supabase.rpc.mockClear()
    await wrapper.find('.reject-btn').trigger('click')
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('friend_requests')
  })
})

// ─── Tests send friend request ────────────────────────────────────────────────
describe('Home send friend request', () => {
  beforeEach(() => {
    vi.stubGlobal('alert', vi.fn())
    setupDefaultMocks()
  })
  afterEach(() => vi.unstubAllGlobals())

  it('calls request_friend RPC when Send Friend Request is clicked', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    await wrapper.find('.test-input').setValue('Bob')
    await wrapper.find('.test-btn').trigger('click')
    await flushPromises()
    expect(supabase.rpc).toHaveBeenCalledWith('request_friend', { friend_nickname: 'Bob' })
  })

  it('clears input after sending friend request', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    await wrapper.find('.test-input').setValue('Bob')
    await wrapper.find('.test-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.test-input').element.value).toBe('')
  })
})
// ─── Tests Navigation ─────────────────────────────────────────────────────────
describe('Home navigation', () => {
  beforeEach(() => {
    mockPush.mockClear() 
    setupDefaultMocks()
  })

  it('navigates to Map and Profile pages when buttons are clicked', async () => {
    const wrapper = mount(Home)
    await flushPromises()
    
    await wrapper.find('.map-btn').trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/map')

    await wrapper.findAll('.nav-btn')[1].trigger('click')
    expect(mockPush).toHaveBeenCalledWith('/profile')
  })
})
// ─── Tests Logout ─────────────────────────────────────────────────────────────
describe('Home logout', () => {
  beforeEach(() => {
    mockPush.mockClear()
    supabase.auth.signOut.mockClear()
    setupDefaultMocks()
  })

  it('handles logout correctly (signOut, clear storage, redirect)', async () => {
    const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem')
    const wrapper = mount(Home)
    await flushPromises()
    await wrapper.find('.logout-btn').trigger('click')
    await flushPromises()

    expect(supabase.auth.signOut).toHaveBeenCalled()
    expect(removeItemSpy).toHaveBeenCalledWith('supabase_token')
    expect(mockPush).toHaveBeenCalledWith('/login')

    removeItemSpy.mockRestore()
  })
})
// ─── Tests Auto-refresh ───────────────────────────────────────────────────────
describe('Home auto-refresh', () => {
  beforeEach(() => {
    vi.useFakeTimers() 
    setupDefaultMocks()
  })
  afterEach(() => {
    vi.useRealTimers() 
  })

  it('polls load_posts every 30 seconds', async () => {
    const wrapper = mount(Home)
    await flushPromises()

    supabase.rpc.mockClear()

    vi.advanceTimersByTime(30000)

    expect(supabase.rpc).toHaveBeenCalledWith('load_posts')

    wrapper.unmount()
  })
})
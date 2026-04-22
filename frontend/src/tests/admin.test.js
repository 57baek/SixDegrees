// src/tests/admin.test.js

import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest'
import Admin from '../views/Admin.vue'

// vi.useFakeTimers() (called in beforeEach) replaces window.localStorage with a
// stub that strips its methods. Replace it with a working in-memory implementation
// once, before any tests run, so logout and other localStorage calls succeed.
beforeAll(() => {
  let store = {}
  const localStorageMock = {
    getItem: (key) => Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null,
    setItem: (key, value) => { store[key] = String(value) },
    removeItem: (key) => { delete store[key] },
    clear: () => { store = {} },
  }
  Object.defineProperty(window, 'localStorage', { value: localStorageMock, writable: true, configurable: true })
})

// ─── 1. Hoist mocks so they exist before vi.mock() runs ───────────────────────
const {
  mockGetSession,
  mockOnAuthStateChange,
  mockRpc,
  mockSignOut,
  mockPush,
} = vi.hoisted(() => ({
  mockGetSession: vi.fn(),
  mockOnAuthStateChange: vi.fn(() => ({
    data: { subscription: { unsubscribe: vi.fn() } },
  })),
  mockRpc: vi.fn(),
  mockSignOut: vi.fn(),
  mockPush: vi.fn(),
}))

// ─── 2. Mock vue-router ───────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({ push: mockPush })),
}))

// ─── 3. Mock Supabase ─────────────────────────────────────────────────────────
vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: mockGetSession,
      onAuthStateChange: mockOnAuthStateChange,
      signOut: mockSignOut,
    },
    rpc: mockRpc,
  },
}))

// ─── 4. Stub child component ─────────────────────────────────────────────────
const PostStub = {
  name: 'Post',
  template: '<div data-testid="post-stub" />',
  props: ['post'],
  emits: ['delete-post', 'check-report'],
}

// ─── 5. Mount helper ──────────────────────────────────────────────────────────
// Admin.vue has TWO onMounted hooks, both call getSession.
// mockResolvedValue (not Once) ensures both calls get a valid session.
const mountAdmin = (session = { user: { id: 'user-1' } }) => {
  mockGetSession.mockResolvedValue({ data: { session } })
  // Default: true response for is_admin check
  mockRpc.mockResolvedValueOnce({ data: true, error: null})
  // Default: empty responses for load_reported_post
  mockRpc.mockResolvedValue({ data: [], error: null })

  return mount(Admin, {
    global: {
      stubs: {
        Post: PostStub,
      },
    },
  })
}

// ─────────────────────────────────────────────────────────────────────────────

describe('Admin.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ── SECTION: Rendering ──────────────────────────────────────────────────────

  describe('Rendering', () => {
    it('renders the page header with "Reported Post"', async () => {
      const wrapper = mountAdmin()
      await flushPromises()
      expect(wrapper.find('h1').text()).toBe('Reported Post')
    })

    it('renders the Logout navigation button', async () => {
      const wrapper = mountAdmin()
      await flushPromises()
      const texts = wrapper.findAll('button').map((b) => b.text())
      expect(texts).toContain('Logout')
    })

    it('shows loading state while reported post is being fetched', async () => {
      // Use a promise we control so loading stays true during the check
      let resolveRpc
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc.mockReturnValue(new Promise((res) => { resolveRpc = res }))

      const wrapper = mount(Admin, {
        global: { stubs: { Post: PostStub } },
      })

      // Before the RPC resolves, loading should be visible
      await vi.waitFor(() => expect(wrapper.find('.loading').exists()).toBe(true))

      // Clean up
      resolveRpc({ data: [], error: null })
      await flushPromises()
    })

    it('shows "No reported posts! All is well!" message when post object is empty', async () => {
      const wrapper = mountAdmin()
      await flushPromises()
      expect(wrapper.find('.no-posts').exists()).toBe(true)
      expect(wrapper.find('.no-posts').text()).toContain('No reported posts! All is well!')
    })

    it('renders Post stub when post is loaded', async () => {
      const post = [{ id: 1, content: 'Hello', friend_tier: 1, user_id: 'other' }]
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc
        .mockResolvedValueOnce({ data: true, error: null })    // is_admin
        .mockResolvedValueOnce({ data: post, error: null }) // load_reported_post

      const wrapper = mount(Admin, {
        global: { stubs: { Post: PostStub } },
      })
      await flushPromises()

      expect(wrapper.findAll('[data-testid="post-stub"]')).toHaveLength(1)
    })
  })

  // ── SECTION: Auth & Redirect ────────────────────────────────────────────────

  describe('Auth & Redirect', () => {
    it('redirects to /login if there is no session', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })
      mockRpc.mockResolvedValue({ data: [], error: null })

      mount(Admin, {
        global: { stubs: { Post: PostStub } },
      })
      await flushPromises()

      expect(mockPush).toHaveBeenCalledWith('/login')
    })
    
    it('redirects to / if user is not admin', async () => {
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc.mockResolvedValue({ data: false, error: null })

      mount(Admin, {
        global: { stubs: { Post: PostStub } },
      })
      await flushPromises()

      expect(mockPush).toHaveBeenCalledWith('/')
    })

    it('does NOT redirect when session is valid and admin', async () => {
      const wrapper = mountAdmin()
      await flushPromises()
      // With a valid session but valid is_admin rpc, it should not push any redirects
      expect(mockRpc).toHaveBeenCalled()
      expect(mockPush).not.toHaveBeenCalled
    })

    it('redirects to /login when auth state changes to null mid-session', async () => {
      let authCallback = null
      mockOnAuthStateChange.mockImplementation((cb) => {
        authCallback = cb
        return { data: { subscription: { unsubscribe: vi.fn() } } }
      })

      mountAdmin()
      await flushPromises()

      // Simulate signing out mid-session
      authCallback('SIGNED_OUT', null)
      await flushPromises()

      expect(mockPush).toHaveBeenCalledWith('/login')
    })
  })

  // ── SECTION: Logout ─────────────────────────────────────────────────────────

  describe('Logout', () => {
    it('calls supabase.auth.signOut, clears storage, and redirects to /login', async () => {
      mockSignOut.mockResolvedValue({})

      const wrapper = mountAdmin()
      await flushPromises()

      await wrapper.find('button.logout-btn').trigger('click')
      await flushPromises()

      expect(mockSignOut).toHaveBeenCalledOnce()
      expect(mockPush).toHaveBeenCalledWith('/login')
    })
  })

  // ── SECTION: Delete Post ─────────────────────────────────────────────────────

  describe('Delete Post', () => {
    const setupWithPost = async () => {
      const post = [{ id: 1, content: 'Post One', friend_tier: 1, user_id: 'other' }]
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc
        .mockResolvedValueOnce({ data: true, error: null }) // is_admin
        .mockResolvedValueOnce({ data: post, error: null }) // load_reported_post

      const wrapper = mount(Admin, {
        global: { stubs: { Post: PostStub } },
      })
      await flushPromises()
      return wrapper
    }

    it('does nothing if the user cancels the confirm dialog', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false)
      const wrapper = await setupWithPost()

      // Use name string instead of stub reference for reliable lookup
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(mockRpc).not.toHaveBeenCalledWith('delete_post', expect.anything())
      expect(wrapper.findAllComponents({ name: 'Post' })).toHaveLength(1)
    })

    it('calls delete_post RPC when user confirms deletion', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await setupWithPost()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('delete_post', { post_id: 1 })
    })

    it('removes the deleted post from the feed on success', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await setupWithPost()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(wrapper.findAllComponents({ name: 'Post' })).toHaveLength(0)
    })

    it('alerts success after a post is deleted', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      const wrapper = await setupWithPost()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith('Post deleted successfully.')
    })

    it('alerts permission error when delete_post returns false', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      const wrapper = await setupWithPost()

      mockRpc.mockResolvedValueOnce({ data: false, error: null })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith(
        'You do not have permission to delete this post.'
      )
    })

    it('alerts an error message if delete_post RPC throws', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      const wrapper = await setupWithPost()

      mockRpc.mockResolvedValueOnce({ data: null, error: { message: 'Delete failed' } })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith('Failed to delete post: Delete failed')
    })
  })

  // ── SECTION: Resolve Reports On Post ─────────────────────────────────────────────────────

  describe('Resolve Reports', () => {
    const setupWithPost = async () => {
      const post = [{ id: 1, content: 'Post One', friend_tier: 1, user_id: 'other' }]
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc
        .mockResolvedValueOnce({ data: true, error: null }) // is_admin
        .mockResolvedValueOnce({ data: post, error: null }) // load_reported_post

      const wrapper = mount(Admin, {
        global: { stubs: { Post: PostStub } },
      })
      await flushPromises()
      return wrapper
    }

    it('removes the resolved post from the feed on success', async () => {
      const wrapper = await setupWithPost()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('check-report', 1)
      await flushPromises()

      expect(mockRpc).toHaveBeenLastCalledWith('load_reported_post')
    })
  })
})
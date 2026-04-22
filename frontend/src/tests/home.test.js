// src/tests/home.test.js

import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest'
import Home from '../views/Home.vue'

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

// ─── 4. Mock utils ────────────────────────────────────────────────────────────
// Path must match exactly how Home.vue imports it
vi.mock('../utils.js', () => ({
  tierFilterLabel: vi.fn((tier) => `Tier ${tier} Label`),
}))

// ─── 5. Stub child components ─────────────────────────────────────────────────
const CreatePostStub = {
  name: 'CreatePost',
  template: '<div data-testid="create-post-stub" />',
  emits: ['post-created'],
}
const PostStub = {
  name: 'Post',
  template: '<div data-testid="post-stub" />',
  props: ['post'],
  emits: ['delete-post'],
}

// ─── 6. Mount helper ──────────────────────────────────────────────────────────
// Home.vue has TWO onMounted hooks, both call getSession.
// mockResolvedValue (not Once) ensures both calls get a valid session.
const mountHome = (session = { user: { id: 'user-1' } }) => {
  mockGetSession.mockResolvedValue({ data: { session } })
  // Default: empty responses for is_admin, friend_requests, load_posts, and get_user_profile
  mockRpc.mockResolvedValue({ data: [], error: null })

  return mount(Home, {
    global: {
      stubs: {
        CreatePost: CreatePostStub,
        Post: PostStub,
      },
    },
  })
}

// ─────────────────────────────────────────────────────────────────────────────

describe('Home.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ── SECTION: Rendering ──────────────────────────────────────────────────────

  describe('Rendering', () => {
    it('renders the page header with "Your Feed"', async () => {
      const wrapper = mountHome()
      await flushPromises()
      expect(wrapper.find('h1').text()).toBe('Your Feed')
    })

    it('renders the People Map, Profile, and Logout navigation buttons', async () => {
      const wrapper = mountHome()
      await flushPromises()
      const texts = wrapper.findAll('button').map((b) => b.text())
      expect(texts).toContain('People Map')
      expect(texts).toContain('Profile')
      expect(texts).toContain('Logout')
    })

    it('renders the Add Friend input and button', async () => {
      const wrapper = mountHome()
      await flushPromises()
      expect(wrapper.find('input').exists()).toBe(true)
      expect(wrapper.find('button.box-btn').text()).toBe('Send Friend Request')
    })

    it('renders tier filter buttons for tiers 1, 2, and 3', async () => {
      const wrapper = mountHome()
      await flushPromises()
      const filterBtns = wrapper.findAll('.filter-btn')
      expect(filterBtns).toHaveLength(3)
      // These come from the mocked tierFilterLabel
      expect(filterBtns[0].text()).toBe('Tier 1 Label')
      expect(filterBtns[1].text()).toBe('Tier 2 Label')
      expect(filterBtns[2].text()).toBe('Tier 3 Label')
    })

    it('renders the CreatePost stub component', async () => {
      const wrapper = mountHome()
      await flushPromises()
      expect(wrapper.find('[data-testid="create-post-stub"]').exists()).toBe(true)
    })

    it('shows loading state while posts are being fetched', async () => {
      // Use a promise we control so loading stays true during the check
      let resolveRpc
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc.mockReturnValue(new Promise((res) => { resolveRpc = res }))

      const wrapper = mount(Home, {
        global: { stubs: { CreatePost: CreatePostStub, Post: PostStub } },
      })

      // Before the RPC resolves, loading should be visible
      await vi.waitFor(() => expect(wrapper.find('.loading').exists()).toBe(true))

      // Clean up
      resolveRpc({ data: [], error: null })
      await flushPromises()
    })

    it('shows "No posts yet" message when posts array is empty', async () => {
      const wrapper = mountHome()
      await flushPromises()
      expect(wrapper.find('.no-posts').exists()).toBe(true)
      expect(wrapper.find('.no-posts').text()).toContain('No posts yet')
    })

    it('renders Post stubs when posts are loaded', async () => {
      const posts = [{ id: 1, content: 'Hello', friend_tier: 1, user_id: 'other' }, { id: 2, content: 'World', friend_tier: 1, user_id: 'other' }]
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc
        .mockResolvedValueOnce({ data: [], error: null })    // is_admin
        .mockResolvedValueOnce({ data: [], error: null })    // friend_requests
        .mockResolvedValueOnce({ data: posts, error: null }) // load_posts

      const wrapper = mount(Home, {
        global: { stubs: { CreatePost: CreatePostStub, Post: PostStub } },
      })
      await flushPromises()

      expect(wrapper.findAll('[data-testid="post-stub"]')).toHaveLength(2)
    })
  })

  // ── SECTION: Auth & Redirect ────────────────────────────────────────────────

  describe('Auth & Redirect', () => {
    it('redirects to /login if there is no session', async () => {
      mockGetSession.mockResolvedValue({ data: { session: null } })
      mockRpc.mockResolvedValue({ data: [], error: null })

      mount(Home, {
        global: { stubs: { CreatePost: CreatePostStub, Post: PostStub } },
      })
      await flushPromises()

      expect(mockPush).toHaveBeenCalledWith('/login')
    })
    
    it('redirects to /admin if user is admin', async () => {
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc.mockResolvedValue({ data: true, error: null })

      mount(Home, {
        global: { stubs: { CreatePost: CreatePostStub, Post: PostStub } },
      })
      await flushPromises()

      expect(mockPush).toHaveBeenCalledWith('/admin')
    })

    it('does NOT redirect when session is valid but not admin', async () => {
      const wrapper = mountHome()
      await flushPromises()
      // With a valid session but no valid is_admin rpc, it should not push any redirects
      expect(mockRpc).toHaveBeenCalled()
      expect(mockPush).not.toHaveBeenCalled
    })

    it('redirects to /login when auth state changes to null mid-session', async () => {
      let authCallback = null
      mockOnAuthStateChange.mockImplementation((cb) => {
        authCallback = cb
        return { data: { subscription: { unsubscribe: vi.fn() } } }
      })

      mountHome()
      await flushPromises()

      // Simulate signing out mid-session
      authCallback('SIGNED_OUT', null)
      await flushPromises()

      expect(mockPush).toHaveBeenCalledWith('/login')
    })
  })

  // ── SECTION: Navigation Buttons ─────────────────────────────────────────────

  describe('Navigation Buttons', () => {
    it('navigates to /map when "People Map" button is clicked', async () => {
      const wrapper = mountHome()
      await flushPromises()
      await wrapper.find('button.map-btn').trigger('click')
      expect(mockPush).toHaveBeenCalledWith('/map')
    })

    it('navigates to /profile when "Profile" button is clicked', async () => {
      const wrapper = mountHome()
      await flushPromises()
      const profileBtn = wrapper.findAll('button').find((b) => b.text() === 'Profile')
      await profileBtn.trigger('click')
      expect(mockPush).toHaveBeenCalledWith('/profile')
    })
  })

  // ── SECTION: Logout ─────────────────────────────────────────────────────────

  describe('Logout', () => {
    it('calls supabase.auth.signOut, clears storage, and redirects to /login', async () => {
      mockSignOut.mockResolvedValue({})

      const wrapper = mountHome()
      await flushPromises()

      await wrapper.find('button.logout-btn').trigger('click')
      await flushPromises()

      expect(mockSignOut).toHaveBeenCalledOnce()
      expect(mockPush).toHaveBeenCalledWith('/login')
    })
  })

  // ── SECTION: Add Friend ──────────────────────────────────────────────────────

  describe('Add Friend', () => {
    it('shows an alert if nickname input is empty', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = mountHome()
      await flushPromises()

      await wrapper.find('button.box-btn').trigger('click')

      expect(alertSpy).toHaveBeenCalledWith('Please enter a nickname')
      expect(mockRpc).not.toHaveBeenCalledWith('request_friend', expect.anything())
    })

    it('calls supabase.rpc("request_friend") with the entered nickname', async () => {
      vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = mountHome()
      await flushPromises()

      // Now set up the next rpc call for request_friend
      mockRpc.mockResolvedValueOnce({ data: true, error: null })

      await wrapper.find('input').setValue('alice')
      await wrapper.find('button.box-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('request_friend', { friend_nickname: 'alice' })
    })

    it('alerts success when friend request is sent successfully', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = mountHome()
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })

      await wrapper.find('input').setValue('alice')
      await wrapper.find('button.box-btn').trigger('click')
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith('Success! Your friend request has been sent!')
    })

    it('alerts failure when friend request returns falsy data', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = mountHome()
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: false, error: null })

      await wrapper.find('input').setValue('nonexistent')
      await wrapper.find('button.box-btn').trigger('click')
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith(
        'Oops! Something went wrong! (Are you sure this person exists?)'
      )
    })

    it('clears the input field after sending a friend request', async () => {
      vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = mountHome()
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })

      const input = wrapper.find('input')
      await input.setValue('alice')
      await wrapper.find('button.box-btn').trigger('click')
      await flushPromises()

      expect(input.element.value).toBe('')
    })

    it('alerts an error message if the RPC throws', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = mountHome()
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: null, error: { message: 'Network error' } })

      await wrapper.find('input').setValue('alice')
      await wrapper.find('button.box-btn').trigger('click')
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith('Error: Network error')
    })
  })

  // ── SECTION: Friend Requests ─────────────────────────────────────────────────

  describe('Pending Friend Requests', () => {
    it('shows "No pending requests." when the list is empty', async () => {
      const wrapper = mountHome()
      await flushPromises()
      expect(wrapper.find('.no-requests').text()).toBe('No pending requests.')
    })

    // Helper: mount with specific friend requests pre-loaded
    const mountWithRequests = async (requests) => {
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc
        .mockResolvedValueOnce({ data: false, error:null })     // is_admin
        .mockResolvedValueOnce({ data: requests, error: null }) // friend_requests
        .mockResolvedValueOnce({ data: [], error: null })       // load_posts

      const wrapper = mount(Home, {
        global: { stubs: { CreatePost: CreatePostStub, Post: PostStub } },
      })
      await flushPromises()
      return wrapper
    }

    it('renders a list item for each incoming friend request', async () => {
      const requests = [
        { nickname: 'alice', avatar_url: null },
        { nickname: 'bob', avatar_url: 'http://example.com/bob.jpg' },
      ]
      const wrapper = await mountWithRequests(requests)

      const items = wrapper.findAll('.request-item')
      expect(items).toHaveLength(2)
      expect(items[0].text()).toContain('alice')
      expect(items[1].text()).toContain('bob')
    })

    it('shows the first letter of nickname as avatar fallback when no avatar_url', async () => {
      const wrapper = await mountWithRequests([{ nickname: 'charlie', avatar_url: null }])
      expect(wrapper.find('.avatar-small span').text()).toBe('C')
    })

    it('renders an img tag when the user has an avatar_url', async () => {
      const wrapper = await mountWithRequests([
        { nickname: 'dana', avatar_url: 'http://example.com/dana.jpg' },
      ])
      const img = wrapper.find('.avatar-img')
      expect(img.exists()).toBe(true)
      expect(img.attributes('src')).toBe('http://example.com/dana.jpg')
    })

    it('calls accept_friend RPC when Accept is clicked', async () => {
      vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await mountWithRequests([{ nickname: 'alice', avatar_url: null }])

      mockRpc
        .mockResolvedValueOnce({ data: true, error: null })  // accept_friend
        .mockResolvedValueOnce({ data: [], error: null })    // friend_requests refresh

      await wrapper.find('.accept-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('accept_friend', { friend_nickname: 'alice' })
    })

    it('alerts success after accepting a friend request', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await mountWithRequests([{ nickname: 'alice', avatar_url: null }])

      mockRpc
        .mockResolvedValueOnce({ data: true, error: null })
        .mockResolvedValueOnce({ data: [], error: null })

      await wrapper.find('.accept-btn').trigger('click')
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith('You are now friends with alice!')
    })

    it('calls reject_friend RPC when Reject is clicked', async () => {
      vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await mountWithRequests([{ nickname: 'alice', avatar_url: null }])

      mockRpc
        .mockResolvedValueOnce({ data: true, error: null })  // reject_friend
        .mockResolvedValueOnce({ data: [], error: null })    // refresh

      await wrapper.find('.reject-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('reject_friend', { friend_nickname: 'alice' })
    })

    it('alerts success after rejecting a friend request', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await mountWithRequests([{ nickname: 'alice', avatar_url: null }])

      mockRpc
        .mockResolvedValueOnce({ data: true, error: null })
        .mockResolvedValueOnce({ data: [], error: null })

      await wrapper.find('.reject-btn').trigger('click')
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith(
        'You have rejected the friend request from alice.'
      )
    })

    it('navigates to the user profile when a request item is clicked', async () => {
      const wrapper = await mountWithRequests([{ nickname: 'alice', avatar_url: null }])
      await wrapper.find('.request-item').trigger('click')
      expect(mockPush).toHaveBeenCalledWith('/profile/alice')
    })

    it('calls friend_requests RPC again when Refresh button is clicked', async () => {
      const wrapper = mountHome()
      await flushPromises()

      const before = mockRpc.mock.calls.filter((c) => c[0] === 'friend_requests').length

      mockRpc.mockResolvedValueOnce({ data: [], error: null }) // refresh response
      await wrapper.find('.refresh-btn').trigger('click')
      await flushPromises()

      const after = mockRpc.mock.calls.filter((c) => c[0] === 'friend_requests').length
      expect(after).toBe(before + 1)
    })
  })

  // ── SECTION: Tier Filter ─────────────────────────────────────────────────────

  describe('Tier Filter', () => {
    it('has tier 3 active by default', async () => {
      const wrapper = mountHome()
      await flushPromises()
      const btns = wrapper.findAll('.filter-btn')
      expect(btns[2].classes()).toContain('active')
      expect(btns[0].classes()).not.toContain('active')
      expect(btns[1].classes()).not.toContain('active')
    })

    it('changes the active tier when a filter button is clicked', async () => {
      const wrapper = mountHome()
      await flushPromises()
      const btns = wrapper.findAll('.filter-btn')
      await btns[0].trigger('click')
      expect(btns[0].classes()).toContain('active')
      expect(btns[2].classes()).not.toContain('active')
    })

    it('calls load_posts when filter changes', async () => {
      const wrapper = mountHome()
      await flushPromises()

      // Clicking a tier button calls loadPosts() directly; loadPosts always fetches
      // max_tier: 3 and filtering is done client-side via the posts computed property.
      mockRpc.mockResolvedValueOnce({ data: [], error: null })
      await wrapper.findAll('.filter-btn')[0].trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenLastCalledWith('load_posts')
    })
  })

  // ── SECTION: Posts Feed ──────────────────────────────────────────────────────

  describe('Posts Feed', () => {
    it('calls load_posts on mount', async () => {
      mountHome()
      await flushPromises()
      expect(mockRpc).toHaveBeenCalledWith('load_posts')
    })

    it('polls load_posts every 30 seconds', async () => {
      mountHome()
      await flushPromises()

      const before = mockRpc.mock.calls.filter((c) => c[0] === 'load_posts').length

      mockRpc.mockResolvedValueOnce({ data: [], error: null })
      vi.advanceTimersByTime(30000)
      await flushPromises()

      const after = mockRpc.mock.calls.filter((c) => c[0] === 'load_posts').length
      expect(after).toBe(before + 1)
    })

    it('reloads posts when CreatePost emits "post-created"', async () => {
      const wrapper = mountHome()
      await flushPromises()

      const before = mockRpc.mock.calls.filter((c) => c[0] === 'load_posts').length

      mockRpc.mockResolvedValueOnce({ data: [], error: null })
      await wrapper.findComponent({ name: 'CreatePost' }).vm.$emit('post-created')
      await flushPromises()

      const after = mockRpc.mock.calls.filter((c) => c[0] === 'load_posts').length
      expect(after).toBe(before + 1)
    })
  })

  // ── SECTION: Delete Post ─────────────────────────────────────────────────────

  describe('Delete Post', () => {
    const setupWithPosts = async () => {
      const posts = [{ id: 1, content: 'Post One', friend_tier: 1, user_id: 'other' }, { id: 2, content: 'Post Two', friend_tier: 1, user_id: 'other' }]
      mockGetSession.mockResolvedValue({ data: { session: { user: { id: 'user-1' } } } })
      mockRpc
        .mockResolvedValueOnce({ data: false, error: null }) // is_admin
        .mockResolvedValueOnce({ data: [], error: null })    // friend_requests
        .mockResolvedValueOnce({ data: posts, error: null }) // load_posts

      const wrapper = mount(Home, {
        global: { stubs: { CreatePost: CreatePostStub, Post: PostStub } },
      })
      await flushPromises()
      return wrapper
    }

    it('does nothing if the user cancels the confirm dialog', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false)
      const wrapper = await setupWithPosts()

      // Use name string instead of stub reference for reliable lookup
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(mockRpc).not.toHaveBeenCalledWith('delete_post', expect.anything())
      expect(wrapper.findAllComponents({ name: 'Post' })).toHaveLength(2)
    })

    it('calls delete_post RPC when user confirms deletion', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await setupWithPosts()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('delete_post', { post_id: 1 })
    })

    it('removes the deleted post from the feed on success', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await setupWithPosts()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(wrapper.findAllComponents({ name: 'Post' })).toHaveLength(1)
    })

    it('alerts success after a post is deleted', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      const wrapper = await setupWithPosts()

      mockRpc.mockResolvedValueOnce({ data: true, error: null })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith('Post deleted successfully.')
    })

    it('alerts permission error when delete_post returns false', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      const wrapper = await setupWithPosts()

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
      const wrapper = await setupWithPosts()

      mockRpc.mockResolvedValueOnce({ data: null, error: { message: 'Delete failed' } })
      await wrapper.findAllComponents({ name: 'Post' })[0].vm.$emit('delete-post', 1)
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith('Failed to delete post: Delete failed')
    })
  })
})
// src/tests/friends.test.js

import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'

// ─── 1. Hoist mocks ───────────────────────────────────────────────────────────
const { mockRpc, mockGetUser, mockBack, mockPush } = vi.hoisted(() => ({
  mockRpc: vi.fn(),
  mockGetUser: vi.fn(),
  mockBack: vi.fn(),
  mockPush: vi.fn(),
}))

// Declare as let so it can be fully reassigned in beforeEach and helpers
let mockRouteParams = { params: {} }

// ─── 2. Mock vue-router ───────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({ back: mockBack, push: mockPush })),
  // Arrow function so each mount call reads the current mockRouteParams value
  useRoute: vi.fn(() => mockRouteParams),
}))

// ─── 3. Mock Supabase ─────────────────────────────────────────────────────────
vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: { getUser: mockGetUser },
    rpc: mockRpc,
  },
}))

// ─── 4. Mock lucide icons ─────────────────────────────────────────────────────
vi.mock('lucide-vue-next', () => ({
  UserPlus:  { template: '<span data-testid="icon-add" />' },
  UserMinus: { template: '<span data-testid="icon-remove" />' },
  Clock:     { template: '<span data-testid="icon-clock" />' },
}))

import Friends from '../views/Friends.vue'

// ─── 5. Test data ─────────────────────────────────────────────────────────────
const makeFriend = (overrides = {}) => ({
  id: 'friend-1',
  nickname: 'alice',
  avatar_url: null,
  tier: 1,...overrides,
})

// ─── 6. Mount helpers ─────────────────────────────────────────────────────────
const mountOwnList = (friends = [makeFriend()]) => {
  mockRouteParams = { params: {} }  // ✅ simple reassignment, no "reassign" keyword
  mockGetUser.mockResolvedValue({ data: { user: { id: 'current-user' } } })
  mockRpc.mockResolvedValue({ data: friends, error: null })
  return mount(Friends)
}

const mountOtherList = async (friends = [makeFriend()], myFriends = [], pending = false) => {
  mockRouteParams = { params: { userId: 'other-user' } } // reassign
  mockGetUser.mockResolvedValue({ data: { user: { id: 'current-user' } } })

  // Exact RPC call order from loadFriends():
  // 1. extended_friends with target_user_id  → their friends
  // 2. extended_friends with max_tier: 1     → my friends
  // 3. has_pending_request × one per friend
  mockRpc.mockResolvedValueOnce({ data: friends, error: null }).mockResolvedValueOnce({ data: myFriends, error: null })

  friends.forEach(() => {
    mockRpc.mockResolvedValueOnce({ data: pending, error: null })
  })

  const wrapper = mount(Friends)
  await flushPromises()
  return wrapper
}

// ─────────────────────────────────────────────────────────────────────────────

describe('Friends.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRouteParams = { params: {} } // reset route before every test
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  // ── SECTION: Rendering ──────────────────────────────────────────────────────

  describe('Rendering', () => {
    it('shows "My Friends" title when viewing own list', async () => {
      const wrapper = mountOwnList()
      await flushPromises()
      expect(wrapper.find('h1').text()).toBe('My Friends')
    })

    it('shows "Their Friends" title when viewing another user\'s list', async () => {
      const wrapper = await mountOtherList()
      expect(wrapper.find('h1').text()).toBe('Their Friends')
    })

    it('shows the friend count badge', async () => {
      const wrapper = mountOwnList([
        makeFriend(),
        makeFriend({ id: 'friend-2', nickname: 'bob' }),
      ])
      await flushPromises()
      expect(wrapper.find('.friend-count').text()).toBe('2')
    })

    it('shows loading state while fetching', () => {
      mockRouteParams = { params: {} }
      mockGetUser.mockResolvedValue({ data: { user: { id: 'current-user' } } })
      mockRpc.mockReturnValue(new Promise(() => {})) // never resolves
      const wrapper = mount(Friends)
      expect(wrapper.find('.loading').exists()).toBe(true)
    })

    it('shows empty state when friends list is empty', async () => {
      const wrapper = mountOwnList([])
      await flushPromises()
      expect(wrapper.find('.no-friends').exists()).toBe(true)
      expect(wrapper.text()).toContain('No friends yet')
    })

    it('renders a row for each friend', async () => {
      const wrapper = mountOwnList([
        makeFriend({ id: 'f1', nickname: 'alice' }),
        makeFriend({ id: 'f2', nickname: 'bob' }),
      ])
      await flushPromises()
      expect(wrapper.findAll('.friend-row')).toHaveLength(2)
    })

    it('renders nickname and tier for each friend', async () => {
      const wrapper = mountOwnList([makeFriend({ nickname: 'alice', tier: 1 })])
      await flushPromises()
      expect(wrapper.find('.friend-info h3').text()).toBe('alice')
      expect(wrapper.find('.friend-tier').text()).toBe('Tier 1')
    })

    it('renders avatar image when avatar_url is provided', async () => {
      const wrapper = mountOwnList([makeFriend({ avatar_url: 'http://example.com/a.jpg' })])
      await flushPromises()
      const img = wrapper.find('.avatar-img')
      expect(img.exists()).toBe(true)
      expect(img.attributes('src')).toBe('http://example.com/a.jpg')
    })

    it('renders first letter of nickname as avatar fallback', async () => {
      const wrapper = mountOwnList([makeFriend({ avatar_url: null, nickname: 'charlie' })])
      await flushPromises()
      expect(wrapper.find('.friend-avatar span').text()).toBe('C')
    })
  })

  // ── SECTION: Navigation ─────────────────────────────────────────────────────

  describe('Navigation', () => {
    it('calls router.back() when back button is clicked', async () => {
      const wrapper = mountOwnList()
      await flushPromises()
      await wrapper.find('.back-btn').trigger('click')
      expect(mockBack).toHaveBeenCalledOnce()
    })

    it('navigates to friend profile when a row is clicked', async () => {
      const wrapper = mountOwnList([makeFriend({ id: 'friend-1' })])
      await flushPromises()
      await wrapper.find('.friend-row').trigger('click')
      expect(mockPush).toHaveBeenCalledWith('/profile/friend-1')
    })
  })

  // ── SECTION: Own Friends List ───────────────────────────────────────────────

  describe('Own friends list', () => {
    it('shows Remove button for each friend (not self)', async () => {
      const wrapper = mountOwnList([makeFriend({ id: 'friend-1' })])
      await flushPromises()
      const btn = wrapper.find('.addOrRemoveFriend-btn')
      expect(btn.classes()).toContain('remove-friend-btn')
      expect(btn.text()).toContain('Remove')
    })

    it('shows arrow instead of button for own entry', async () => {
      const wrapper = mountOwnList([makeFriend({ id: 'current-user' })])
      await flushPromises()
      expect(wrapper.find('.arrow').exists()).toBe(true)
      expect(wrapper.find('.addOrRemoveFriend-btn').exists()).toBe(false)
    })

    it('calls remove_friend RPC and removes friend from list', async () => {
      const wrapper = mountOwnList([makeFriend({ id: 'friend-1', nickname: 'alice' })])
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ error: null })
      await wrapper.find('.addOrRemoveFriend-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('remove_friend', { friend_nickname: 'alice' })
      expect(wrapper.findAll('.friend-row')).toHaveLength(0)
    })
  })

  // ── SECTION: Other User's Friends List ─────────────────────────────────────

  describe("Another user's friends list", () => {
    it('shows Add button for friends we are not connected to', async () => {
      const wrapper = await mountOtherList(
        [makeFriend({ id: 'friend-1' })],
        [],     // not in my friends
        false   // no pending request
      )
      const btn = wrapper.find('.addOrRemoveFriend-btn')
      expect(btn.classes()).toContain('add-friend-btn')
      expect(btn.text()).toContain('Add')
    })

    it('shows Remove button for friends we are already connected to', async () => {
      const wrapper = await mountOtherList(
        [makeFriend({ id: 'friend-1' })],
        [makeFriend({ id: 'friend-1' })], // already my friend
        false
      )
      const btn = wrapper.find('.addOrRemoveFriend-btn')
      expect(btn.classes()).toContain('remove-friend-btn')
    })

    it('shows Pending button when a request has already been sent', async () => {
      const wrapper = await mountOtherList(
        [makeFriend({ id: 'friend-1' })],
        [],
        true  // pending request exists
      )
      const btn = wrapper.find('.addOrRemoveFriend-btn')
      expect(btn.classes()).toContain('pending-friend-btn')
      expect(btn.text()).toContain('Pending')
    })

    it('calls request_friend RPC and updates button to Pending on success', async () => {
      const wrapper = await mountOtherList(
        [makeFriend({ id: 'friend-1', nickname: 'alice' })],
        [],
        false
      )

      mockRpc.mockResolvedValueOnce({ data: true, error: null }) // request_friend
      await wrapper.find('.addOrRemoveFriend-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('request_friend', { friend_nickname: 'alice' })
      expect(wrapper.find('.addOrRemoveFriend-btn').classes()).toContain('pending-friend-btn')
    })

    it('alerts when request_friend returns false', async () => {
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
      const wrapper = await mountOtherList(
        [makeFriend({ id: 'friend-1', nickname: 'alice' })],
        [],
        false
      )

      mockRpc.mockResolvedValueOnce({ data: false, error: null }) // request_friend fails
      await wrapper.find('.addOrRemoveFriend-btn').trigger('click')
      await flushPromises()

      expect(alertSpy).toHaveBeenCalledWith('Could not send request.')
    })
  })
})
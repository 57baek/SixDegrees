// src/tests/posts.test.js

import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Post from '../components/Post.vue'
import { tierIcon } from '../utils'

// ─── 1. Hoist mocks ───────────────────────────────────────────────────────────
const { mockRpc, mockGetUser, mockPush } = vi.hoisted(() => ({
  mockRpc: vi.fn(),
  mockGetUser: vi.fn(),
  mockPush: vi.fn(),
}))

// ─── 2. Mock Supabase ─────────────────────────────────────────────────────────
vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: { getUser: mockGetUser },
    rpc: mockRpc,
  },
}))

// ─── 3. Mock vue-router ───────────────────────────────────────────────────────
vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({ push: mockPush })),
}))

// ─── 4. Mock utils ────────────────────────────────────────────────────────────
vi.mock('../utils.js', () => ({
  formatDate: vi.fn(() => 'Jan 1, 2025'),
  tierIcon: vi.fn((tier) => {template: '<span />'}),
  tierLabel: vi.fn((tier) => `Tier ${tier}`),
}))

// ─── 5. Mock lucide icons so they don't break the test renderer ───────────────
vi.mock('lucide-vue-next', () => ({
  Heart: { template: '<span data-testid="icon-heart" />' },
  MessageCircle: { template: '<span data-testid="icon-message" />' },
  Archive: { template: '<span />' },
  Trash2: { template: '<span data-testid="icon-trash" />' },
  Flag: { template: '<span data-testid="icon-flag" />' },
  CheckCircle: { template: '<span data-testid="icon-check" />' },
}))

// ─── 6. Default test post ─────────────────────────────────────────────────────
const makePost = (overrides = {}) => ({
  id: 'post-1',
  user_id: 'user-abc',
  nickname: 'alice',
  avatar_url: null,
  content: 'Hello world!',
  created_at: '2025-01-01T00:00:00Z',
  tier: 1,
  ...overrides,
})

// ─── 7. Mount helper ──────────────────────────────────────────────────────────
const mountPost = (postOverrides = {}, userId = 'other-user') => {
  mockGetUser.mockResolvedValue({ data: { user: { id: userId } } })
  // Default RPC responses for onMounted calls:
  // is_user_liked, is_user_reported, like_count, comment_count
  mockRpc
    .mockResolvedValueOnce({ data: false, error: null }) // is_user_liked
    .mockResolvedValueOnce({ data: false, error: null }) // is_user_reported
    .mockResolvedValueOnce({ data: 5, error: null })     // like_count
    .mockResolvedValueOnce({ data: 1, error: null })     // comment_count

  return mount(Post, {
    props: { post: makePost(postOverrides) },
  })
}

// ─────────────────────────────────────────────────────────────────────────────

describe('Post.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  // ── SECTION: Rendering ──────────────────────────────────────────────────────

  describe('Rendering', () => {
    it('renders the post content', async () => {
      const wrapper = mountPost()
      await flushPromises()
      expect(wrapper.find('.post-content').text()).toContain('Hello world!')
    })

    it('renders the nickname', async () => {
      const wrapper = mountPost()
      await flushPromises()
      expect(wrapper.find('.nickname').text()).toBe('alice')
    })

    it('renders the formatted date from utils', async () => {
      const wrapper = mountPost()
      await flushPromises()
      expect(wrapper.find('.timestamp').text()).toBe('Jan 1, 2025')
    })

    it('renders the tier label from utils', async () => {
      const wrapper = mountPost()
      await flushPromises()
      expect(wrapper.find('.tier-badge').text()).toContain('Tier 1')
    })

    it('renders the first letter of nickname as avatar fallback', async () => {
      const wrapper = mountPost({ avatar_url: null, nickname: 'bob' })
      await flushPromises()
      expect(wrapper.find('.avatar span').text()).toBe('B')
    })

    it('renders an avatar image when avatar_url is provided', async () => {
      const wrapper = mountPost({ avatar_url: 'http://example.com/avatar.jpg' })
      await flushPromises()
      const img = wrapper.find('.avatar-img')
      expect(img.exists()).toBe(true)
      expect(img.attributes('src')).toBe('http://example.com/avatar.jpg')
    })

    it('shows the like count', async () => {
      const wrapper = mountPost()
      await flushPromises()
      const likeBtn = wrapper.find('.action-btn')
      expect(likeBtn.text()).toContain('5')
    })

    it('shows the comment count', async () => {
      const wrapper = mountPost()
      await flushPromises()
      const buttons = wrapper.findAll('.action-btn')
      expect(buttons[1].text()).toContain('1')
    })
  })

  // ── SECTION: Image Gallery ──────────────────────────────────────────────────

  describe('Image Gallery', () => {
    it('renders images when post has image_urls', async () => {
      const wrapper = mountPost({ image_urls: ['http://example.com/img1.jpg', 'http://example.com/img2.jpg'] })
      await flushPromises()
      
      const images = wrapper.findAll('.post-img')
      expect(images).toHaveLength(2)
      expect(images[0].attributes('src')).toBe('http://example.com/img1.jpg')
    })

    it('applies single-image class when there is exactly one image', async () => {
      const wrapper = mountPost({ image_urls: ['http://example.com/img1.jpg'] })
      await flushPromises()
      
      const imageContainer = wrapper.find('.post-image-item')
      expect(imageContainer.classes()).toContain('single-image')
    })

    it('does not render gallery if image_urls is empty', async () => {
      const wrapper = mountPost({ image_urls: [] })
      await flushPromises()
      
      expect(wrapper.find('.post-gallery').exists()).toBe(false)
    })
  })

  // ── SECTION: Own Post vs Other Post ─────────────────────────────────────────

  describe('Own post vs other post', () => {
    it('shows delete button when the post belongs to the current user', async () => {
      // Mount with userId matching post.user_id
      const wrapper = mountPost({}, 'user-abc')
      await flushPromises()
      expect(wrapper.find('.delete-icon-btn').exists()).toBe(true)
    })

    it('hides delete button when the post belongs to another user', async () => {
      const wrapper = mountPost({}, 'other-user')
      await flushPromises()
      expect(wrapper.find('.delete-icon-btn').exists()).toBe(false)
    })

    it('shows report button when the post belongs to another user', async () => {
      const wrapper = mountPost({}, 'other-user')
      await flushPromises()
      // Flag button should be visible for other users' posts
      expect(wrapper.find('[data-testid="icon-flag"]').exists()).toBe(true)
    })

    it('hides report button when the post belongs to the current user', async () => {
      const wrapper = mountPost({}, 'user-abc')
      await flushPromises()
      expect(wrapper.find('[data-testid="icon-flag"]').exists()).toBe(false)
    })
  })

  // ── SECTION: Navigation ──────────────────────────────────────────────────────

  describe('Navigation', () => {
    it('navigates to user profile when avatar is clicked', async () => {
      const wrapper = mountPost()
      await flushPromises()
      await wrapper.find('.avatar').trigger('click')
      expect(mockPush).toHaveBeenCalledWith('/profile/alice')
    })
  })

  // ── SECTION: Delete Post ─────────────────────────────────────────────────────

  describe('Delete Post', () => {
    it('emits delete-post with the post id when delete button is clicked', async () => {
      const wrapper = mountPost({}, 'user-abc')
      await flushPromises()

      await wrapper.find('.delete-icon-btn').trigger('click')

      expect(wrapper.emitted('delete-post')).toBeTruthy()
      expect(wrapper.emitted('delete-post')[0]).toEqual(['post-1'])
    })
  })

  // ── SECTION: Likes ───────────────────────────────────────────────────────────

  describe('Likes', () => {
    it('calls like_post RPC when like button is clicked and post is not liked', async () => {
      const wrapper = mountPost()
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: null, error: null }) // like_post
      await wrapper.find('.action-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('like_post', { liked_post_id: 'post-1' })
    })

    it('increments like count optimistically when liking', async () => {
      const wrapper = mountPost()
      await flushPromises()

      const initialCount = Number(wrapper.find('.action-btn').text().trim())

      mockRpc.mockResolvedValueOnce({ data: null, error: null })
      await wrapper.find('.action-btn').trigger('click')
      await flushPromises()

      const newCount = Number(wrapper.find('.action-btn').text().trim())
      expect(newCount).toBe(initialCount + 1)
    })

    it('calls unlike_post RPC when like button is clicked and post is already liked', async () => {
      // Override is_user_liked to return true
      mockGetUser.mockResolvedValue({ data: { user: { id: 'other-user' } } })
      mockRpc
        .mockResolvedValueOnce({ data: true, error: null })  // is_user_liked → already liked
        .mockResolvedValueOnce({ data: false, error: null }) // is_user_reported
        .mockResolvedValueOnce({ data: 5, error: null })     // like_count
        .mockResolvedValueOnce({ data: 0, error: null })     // comment_count

      const wrapper = mount(Post, { props: { post: makePost() } })
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: null, error: null }) // unlike_post
      await wrapper.find('.action-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('unlike_post', { liked_post_id: 'post-1' })
    })
  })

  // ── SECTION: Comments ────────────────────────────────────────────────────────

  describe('Comments', () => {
    it('comments section is hidden by default', async () => {
      const wrapper = mountPost()
      await flushPromises()
      expect(wrapper.find('.comments-section').exists()).toBe(false)
    })

    it('shows comments section when comment button is clicked', async () => {
      mockRpc.mockResolvedValueOnce({ data: [], error: null }) // load_comments
      const wrapper = mountPost()
      await flushPromises()

      const buttons = wrapper.findAll('.action-btn')
      await buttons[1].trigger('click')
      await flushPromises()

      expect(wrapper.find('.comments-section').exists()).toBe(true)
    })

    it('loads comments from supabase when section is first opened', async () => {
      const comments = [
        { id: 'c1', nickname: 'bob', content: 'Nice post!', user_id: 'user-bob' },
      ]

      const wrapper = mountPost()
      await flushPromises()

      // ✅ Set up load_comments mock AFTER mount resolves
      mockRpc.mockResolvedValueOnce({ data: comments, error: null })

      await wrapper.findAll('.action-btn')[1].trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('load_comments', { post_id: 'post-1' })
      expect(wrapper.find('.comment-text').text()).toContain('Nice post!')
    })

    it('disables Send button when comment input is empty', async () => {
      mockRpc.mockResolvedValueOnce({ data: [], error: null })
      const wrapper = mountPost()
      await flushPromises()

      await wrapper.findAll('.action-btn')[1].trigger('click')
      await flushPromises()

      const sendBtn = wrapper.find('.comment-input button')
      expect(sendBtn.attributes('disabled')).toBeDefined()
    })

    it('enables Send button when comment input has text', async () => {
      mockRpc.mockResolvedValueOnce({ data: [], error: null })
      const wrapper = mountPost()
      await flushPromises()

      await wrapper.findAll('.action-btn')[1].trigger('click')
      await flushPromises()

      await wrapper.find('.comment-input input').setValue('Great post!')
      const sendBtn = wrapper.find('.comment-input button')
      expect(sendBtn.attributes('disabled')).toBeUndefined()
    })

    it('submits a comment and clears the input', async () => {
      mockGetUser.mockResolvedValue({ data: { user: { id: 'other-user' } } })
      mockRpc
        .mockResolvedValueOnce({ data: false, error: null }) // is_user_liked
        .mockResolvedValueOnce({ data: false, error: null }) // is_user_reported
        .mockResolvedValueOnce({ data: 5, error: null })     // like_count
        .mockResolvedValueOnce({ data: 0, error: null })     // comment_count
        .mockResolvedValueOnce({ data: [], error: null })    // load_comments
        .mockResolvedValueOnce({                             // comment RPC
          data: [{ id: 'c2', nickname: 'me', content: 'Great post!', user_id: 'other-user' }],
          error: null,
        })

      const wrapper = mount(Post, { props: { post: makePost() } })
      await flushPromises()

      await wrapper.findAll('.action-btn')[1].trigger('click')
      await flushPromises()

      const input = wrapper.find('.comment-input input')
      await input.setValue('Great post!')
      await wrapper.find('.comment-input button').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('comment', {
        post_id: 'post-1',
        comment_content: 'Great post!',
      })
      expect(input.element.value).toBe('')
    })
    it('deletes a comment after confirmation', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true)
      
      const comments = [
        { id: 'c1', nickname: 'bob', content: 'Delete me!', user_id: 'user-bob' },
      ]

      const wrapper = mountPost({}, 'user-bob')
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: comments, error: null }) // load_comments
      await wrapper.findAll('.action-btn')[1].trigger('click')
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: true, error: null }) // delete_comment RPC
      await wrapper.find('.delete-comment-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('delete_comment', { comment_id: 'c1' })
      
      expect(wrapper.text()).not.toContain('Delete me!')
      
      window.confirm.mockRestore()
    })
  })

  // ── SECTION: Report ──────────────────────────────────────────────────────────

  describe('Report', () => {
    it('shows the report button without fill before reporting', async () => {
      const wrapper = mountPost({}, 'other-user')
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: null, error: null })
      expect(wrapper.find('[data-testid="icon-flag"]').attributes('fill')).toBe('none')
    })

    it('calls report_post RPC when flag button is clicked', async () => {
      const wrapper = mountPost({}, 'other-user')
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: null, error: null }) // report_post
      await wrapper.find('[data-testid="icon-flag"]').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('report_post', { reported_post_id: 'post-1' })
    })

    it('emits check-report with the post id when report button is clicked', async () => {
      const wrapper = mountPost({}, 'other-user')
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: null, error: null }) // report_post
      await wrapper.find('[data-testid="icon-flag"]').trigger('click')
      await flushPromises()

      expect(wrapper.emitted('check-report')).toBeTruthy()
      expect(wrapper.emitted('check-report')[0]).toEqual(['post-1'])
    })
    
    it('fills the report button after reporting', async () => {
      const wrapper = mountPost({}, 'other-user')
      await flushPromises()

      mockRpc.mockResolvedValueOnce({ data: null, error: null })
      await wrapper.find('[data-testid="icon-flag"]').trigger('click')
      await flushPromises()

      // After reporting, isReported = true, so the flag button should be filled
      expect(wrapper.find('[data-testid="icon-flag"]').attributes('fill')).not.toBe('none')
    })
  })
})
// src/tests/createpost.test.js

import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CreatePost from '../components/CreatePost.vue'

// ─── 1. Hoist mocks ───────────────────────────────────────────────────────────
const { mockRpc, mockGetUser, mockUpload, mockGetPublicUrl } = vi.hoisted(() => ({
  mockRpc: vi.fn(),
  mockGetUser: vi.fn(),
  mockUpload: vi.fn(),
  mockGetPublicUrl: vi.fn(),
}))

// ─── 2. Mock Supabase ─────────────────────────────────────────────────────────
vi.mock('../lib/supabase', () => ({
  supabase: {
    auth: { getUser: mockGetUser },
    rpc: mockRpc,
    storage: {
      from: vi.fn(() => ({
        upload: mockUpload,
        getPublicUrl: mockGetPublicUrl,
      })),
    },
  },
}))

// ─── 3. Default mount helper ──────────────────────────────────────────────────
const mountCreatePost = () => {
  mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } } })
  mockRpc.mockResolvedValue({
    data: [{ id: 'post-1', content: 'Hello!' }],
    error: null,
  })
  mockUpload.mockResolvedValue({ error: null })
  mockGetPublicUrl.mockReturnValue({ data: { publicUrl: 'http://example.com/img.jpg' } })
  return mount(CreatePost)
}

// ─── 4. File selection helper ─────────────────────────────────────────────────
const selectFiles = async (wrapper, files) => {
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', {
    value: files,
    configurable: true,
  })
  await input.trigger('change')
}

// ─── 5. Stub URL globally with both methods ───────────────────────────────────
const stubURL = () => {
  URL.createObjectURL = vi.fn(() => 'blob:mock-url')
  URL.revokeObjectURL = vi.fn()
}

// ─────────────────────────────────────────────────────────────────────────────

describe('CreatePost.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(console, 'log').mockImplementation(() => {})
    // ✅ Reset URL stubs between tests
    URL.createObjectURL = vi.fn()
    URL.revokeObjectURL = vi.fn()
    })

  // ── SECTION: Rendering ──────────────────────────────────────────────────────

  describe('Rendering', () => {
    it('renders the textarea, tier selector, and post button', () => {
      const wrapper = mountCreatePost()
      expect(wrapper.find('textarea').exists()).toBe(true)
      expect(wrapper.find('select').exists()).toBe(true)
      expect(wrapper.find('button.post-btn').exists()).toBe(true)
    })

    it('post button is disabled when textarea is empty', () => {
      const wrapper = mountCreatePost()
      expect(wrapper.find('button.post-btn').attributes('disabled')).toBeDefined()
    })

    it('post button is enabled when textarea has content', async () => {
      const wrapper = mountCreatePost()
      await wrapper.find('textarea').setValue('Hello world!')
      expect(wrapper.find('button.post-btn').attributes('disabled')).toBeUndefined()
    })

    it('shows "Inner Circle Only" as the default tier option', () => {
      const wrapper = mountCreatePost()
      expect(wrapper.find('select').element.value).toBe('inner_circle')
    })

    it('does not show image previews section when no images are selected', () => {
      const wrapper = mountCreatePost()
      expect(wrapper.find('.image-previews').exists()).toBe(false)
    })

    it('does not show error message initially', () => {
      const wrapper = mountCreatePost()
      expect(wrapper.find('.error').exists()).toBe(false)
    })
  })

  // ── SECTION: Posting ────────────────────────────────────────────────────────

  describe('Posting', () => {
    it('calls supabase.rpc("post") with content and selected tier', async () => {
      const wrapper = mountCreatePost()
      await wrapper.find('textarea').setValue('My new post')
      await wrapper.find('select').setValue('third_degree')
      await wrapper.find('button.post-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('post', {
        post_content: 'My new post',
        post_tier: 'third_degree',
        post_image_urls: [],
      })
    })

    it('clears the textarea after a successful post', async () => {
      const wrapper = mountCreatePost()
      await wrapper.find('textarea').setValue('My new post')
      await wrapper.find('button.post-btn').trigger('click')
      await flushPromises()
      expect(wrapper.find('textarea').element.value).toBe('')
    })

    it('emits "post-created" after a successful post', async () => {
      const wrapper = mountCreatePost()
      await wrapper.find('textarea').setValue('My new post')
      await wrapper.find('button.post-btn').trigger('click')
      await flushPromises()

      expect(wrapper.emitted('post-created')).toBeTruthy()
      expect(wrapper.emitted('post-created')[0][0]).toEqual({
        id: 'post-1',
        content: 'Hello!',
      })
    })

    it('shows "Posting..." on the button while submitting', async () => {
      let resolveGetUser
      mockGetUser.mockReturnValue(
        new Promise((res) => { resolveGetUser = res })
      )

      const wrapper = mount(CreatePost)
      await wrapper.find('textarea').setValue('My new post')
      wrapper.find('button.post-btn').trigger('click')

      await vi.waitFor(() =>
        expect(wrapper.find('button.post-btn').text()).toBe('Posting...')
      )

      resolveGetUser({ data: { user: { id: 'user-1' } } })
      mockRpc.mockResolvedValueOnce({ data: [{ id: 'post-1' }], error: null })
      await flushPromises()
    })

    it('does not submit if content is only whitespace', async () => {
      const wrapper = mountCreatePost()
      await wrapper.find('textarea').setValue('   ')
      expect(wrapper.find('button.post-btn').attributes('disabled')).toBeDefined()
    })

    it('shows an error message when the RPC fails', async () => {
      mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1' } } })
      mockRpc.mockResolvedValue({ data: null, error: { message: 'Database error' } })

      const wrapper = mount(CreatePost)
      await wrapper.find('textarea').setValue('My new post')
      await wrapper.find('button.post-btn').trigger('click')
      await flushPromises()

      expect(wrapper.find('.error').exists()).toBe(true)
      expect(wrapper.find('.error').text()).toContain('Database error')
    })

    it('shows an error if user is not authenticated', async () => {
      mockGetUser.mockResolvedValue({ data: { user: null } })

      const wrapper = mount(CreatePost)
      await wrapper.find('textarea').setValue('My new post')
      await wrapper.find('button.post-btn').trigger('click')
      await flushPromises()

      expect(wrapper.find('.error').exists()).toBe(true)
      expect(wrapper.find('.error').text()).toContain('Not authenticated')
    })
  })

  // ── SECTION: Tier Selector ──────────────────────────────────────────────────

  describe('Tier Selector', () => {
    it('renders all three tier options', () => {
      const wrapper = mountCreatePost()
      const options = wrapper.findAll('select option')
      expect(options).toHaveLength(3)
      expect(options[0].attributes('value')).toBe('inner_circle')
      expect(options[1].attributes('value')).toBe('second_degree')
      expect(options[2].attributes('value')).toBe('third_degree')
    })

    it('posts with the selected tier', async () => {
      const wrapper = mountCreatePost()
      await wrapper.find('textarea').setValue('Hello!')
      await wrapper.find('select').setValue('second_degree')
      await wrapper.find('button.post-btn').trigger('click')
      await flushPromises()

      expect(mockRpc).toHaveBeenCalledWith('post', expect.objectContaining({
        post_tier: 'second_degree',
      }))
    })
  })

  // ── SECTION: Image Handling ─────────────────────────────────────────────────

  describe('Image Handling', () => {
    it('shows image preview after a file is selected', async () => {
      const wrapper = mountCreatePost()
      stubURL() //  stub both createObjectURL and revokeObjectURL

      const file = new File(['img'], 'photo.jpg', { type: 'image/jpeg' })
      await selectFiles(wrapper, [file])

      expect(wrapper.find('.image-previews').exists()).toBe(true)
      expect(wrapper.find('.preview-img').attributes('src')).toBe('blob:mock-url')
    })

    it('removes an image when the remove button is clicked', async () => {
      const wrapper = mountCreatePost()
      stubURL() //  stub both — partner added revokeObjectURL to removeImage()

      const file = new File(['img'], 'photo.jpg', { type: 'image/jpeg' })
      await selectFiles(wrapper, [file])
      expect(wrapper.find('.preview-item').exists()).toBe(true)

      await wrapper.find('.remove-btn').trigger('click')
      expect(wrapper.find('.preview-item').exists()).toBe(false)
    })

    it('shows an error if more than 5 images are added', async () => {
      const wrapper = mountCreatePost()
      stubURL() //  stub both

      const files = Array.from({ length: 6 }, (_, i) =>
        new File(['img'], `photo${i}.jpg`, { type: 'image/jpeg' })
      )
      await selectFiles(wrapper, files)

      expect(wrapper.find('.error').text()).toContain('Maximum 5 images allowed')
    })

    it('disables the add photo button when 5 images are selected', async () => {
      const wrapper = mountCreatePost()
      stubURL() //  stub both

      const files = Array.from({ length: 5 }, (_, i) =>
        new File(['img'], `photo${i}.jpg`, { type: 'image/jpeg' })
      )
      await selectFiles(wrapper, files)

      expect(wrapper.find('.add-photo-btn').attributes('disabled')).toBeDefined()
    })

    it('uploads images to supabase storage and includes urls in the post', async () => {
      const wrapper = mountCreatePost()
      stubURL() //  stub both — form reset calls revokeObjectURL after successful post

      const file = new File(['img'], 'photo.jpg', { type: 'image/jpeg' })
      await selectFiles(wrapper, [file])

      await wrapper.find('textarea').setValue('Post with image')
      await wrapper.find('button.post-btn').trigger('click')
      await flushPromises()

      expect(mockUpload).toHaveBeenCalledOnce()
      expect(mockRpc).toHaveBeenCalledWith('post', expect.objectContaining({
        post_image_urls: ['http://example.com/img.jpg'],
      }))
    })

    it('shows an error for unsupported file types', async () => {
      const wrapper = mountCreatePost()
      stubURL()

      const file = new File(['doc'], 'document.pdf', { type: 'application/pdf' })
      await selectFiles(wrapper, [file])

      expect(wrapper.find('.error').text()).toContain('only JPEG, PNG, GIF, or WebP allowed')
    })
  })
})
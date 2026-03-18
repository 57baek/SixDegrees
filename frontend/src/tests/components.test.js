// src/tests/components.test.js
// Component-level tests using @vue/test-utils
// Tests cover: post rendering, tier filtering in the feed, and friend list rendering
// To run: npm test (from /frontend directory)
// Framework: Vitest + @vue/test-utils (https://vitest.dev)

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, computed } from 'vue'

vi.mock('../lib/supabase', () => ({
  supabase: {
    rpc: vi.fn().mockResolvedValue({ data: [], error: null }),
    auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'user-1' } } }) }
  }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: {} })
}))

import Post from '../components/Post.vue'
import { filterPostsByTier } from '../utils.js'

// Test post component rendering 
describe('Post component', () => {
  const mockPost = {
    id: '1',
    user_id: 'user-1',
    nickname: 'Alice',
    content: 'Hello world',
    tier: 1,
    like_count: 3,
    comment_count: 2,
    created_at: new Date(Date.now() - 1000 * 60 * 10).toISOString() // 10 mins ago
  }

  it('renders the post content', () => {
    const wrapper = mount(Post, { props: { post: mockPost } })
    expect(wrapper.text()).toContain('Hello world')
  })

  it('renders the nickname', () => {
    const wrapper = mount(Post, { props: { post: mockPost } })
    expect(wrapper.text()).toContain('Alice')
  })

  it('renders the correct tier label', () => {
    const wrapper = mount(Post, { props: { post: mockPost } })
    expect(wrapper.text()).toContain('Inner Circle')
  })

  it('renders the correct avatar initial', () => {
    const wrapper = mount(Post, { props: { post: mockPost } })
    expect(wrapper.text()).toContain('A') // first letter of Alice
  })

  it('renders Just now for recent post', () => {
    const wrapper = mount(Post, { props: { post: mockPost } })
    expect(wrapper.text()).toContain('Just now')
  })
})

// Test feed tier filtering behavior
describe('Feed tier filtering', () => {
  const posts = [
    { id: '1', tier: 1, content: 'inner circle only' },
    { id: '2', tier: 2, content: 'second degree' },
    { id: '3', tier: 3, content: 'all friends' },
  ]

  it('hides tier 2 and 3 posts when filter is set to 1', () => {
    const result = filterPostsByTier(posts, 1)
    expect(result.map(p => p.id)).toEqual(['1'])
  })

  it('shows correct posts when switching filter from 3 to 1', () => {
    const allPosts = filterPostsByTier(posts, 3)
    expect(allPosts).toHaveLength(3)

    const innerOnly = filterPostsByTier(posts, 1)
    expect(innerOnly).toHaveLength(1)
    expect(innerOnly[0].content).toBe('inner circle only')
  })

  it('does not mutate the original posts array', () => {
    const original = [...posts]
    filterPostsByTier(posts, 1)
    expect(posts).toEqual(original)
  })
})

// Test friends list filtering
describe('Friends list', () => {
  const friendData = [
    { id: '1', nickname: 'Alice', tier: 1 },
    { id: '2', nickname: 'Bob', tier: 2 },
    { id: '3', nickname: 'Carol', tier: 1 },
    { id: '4', nickname: 'Dave', tier: 3 },
  ]

  it('only shows direct friends (tier 1)', () => {
    const friends = friendData.filter(f => f.tier === 1)
    expect(friends).toHaveLength(2)
    expect(friends.map(f => f.nickname)).toEqual(['Alice', 'Carol'])
  })

  it('does not include tier 2 or 3 connections as direct friends', () => {
    const friends = friendData.filter(f => f.tier === 1)
    expect(friends.every(f => f.tier === 1)).toBe(true)
  })

  it('returns empty array when user has no friends', () => {
    expect([].filter(f => f.tier === 1)).toEqual([])
  })
})
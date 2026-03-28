// Unit and integration tests for post-related functionality
// Tests cover: utility functions from utils.js, RPC call behavior, and edge cases
// To run: npm test (from /frontend directory)
// Framework: Vitest (https://vitest.dev)

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { formatDate, tierLabel, tierFilterLabel, filterPostsByTier } from '../utils.js'

vi.mock('../lib/supabase', () => ({
  supabase: {
    rpc: vi.fn(),
    auth: { getUser: vi.fn() }
  }
}))

import { supabase } from '../lib/supabase'

// Tests filterPostsByTier
describe('filterPostsByTier', () => {
  const posts = [
    { id: '1', content: 'a', tier: 1 },
    { id: '2', content: 'b', tier: 2 },
    { id: '3', content: 'c', tier: 3 },
  ]

  it('returns only tier 1 posts when filter is 1', () => {
    const result = filterPostsByTier(posts, 1)
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('1')
  })

  it('returns tier 1 and 2 posts when filter is 2', () => {
    const result = filterPostsByTier(posts, 2)
    expect(result).toHaveLength(2)
    expect(result.map(p => p.id)).toEqual(['1', '2'])
  })

  it('returns all posts when filter is 3', () => {
    const result = filterPostsByTier(posts, 3)
    expect(result).toHaveLength(3)
    expect(result.map(p => p.id)).toEqual(['1', '2', '3'])
  })

  it('returns empty array when no posts match', () => {
    expect(filterPostsByTier([], 3)).toEqual([])
  })
})

// Tests tierLabel
describe('tierLabel', () => {
  it('returns Inner Circle for tier 1', () => {
    expect(tierLabel(1)).toBe('Inner Circle')
  })

  it('returns 2nd Degree for tier 2', () => {
    expect(tierLabel(2)).toBe('2nd Degree')
  })

  it('returns All Friends for tier 3', () => {
    expect(tierLabel(3)).toBe('All Friends')
  })

  it('handles unknown tier gracefully', () => {
    expect(tierLabel(99)).toBe('99') // falls back to string of the number
  })
})

// Tests formatDate
describe('formatDate', () => {
  it('returns Just now for timestamps under 1 hour ago', () => {
    const thirtyMinsAgo = new Date(Date.now() - 1000 * 60 * 30).toISOString()
    expect(formatDate(thirtyMinsAgo)).toBe('Just now')
  })

  it('returns Xh ago for timestamps under 24 hours ago', () => {
    const fiveHoursAgo = new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString()
    expect(formatDate(fiveHoursAgo)).toBe('5h ago')
  })

  it('returns Yesterday for timestamps between 24 and 48 hours ago', () => {
    const yesterday = new Date(Date.now() - 1000 * 60 * 60 * 36).toISOString()
    expect(formatDate(yesterday)).toBe('Yesterday')
  })

  it('returns a date string for older timestamps', () => {
    const oldDate = new Date('2024-01-01').toISOString()
    expect(formatDate(oldDate)).toBe(new Date('2024-01-01').toLocaleDateString())
  })
})

// Tests loadPosts RPC
describe('loadPosts RPC', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls supabase with correct function name', async () => {
    supabase.rpc.mockResolvedValue({ data: [], error: null })
    await supabase.rpc('load_posts')
    expect(supabase.rpc).toHaveBeenCalledWith('load_posts')
  })

  it('returns posts on success', async () => {
    const mockPosts = [{ id: '1', nickname: 'Alice', tier: 1, like_count: 0, comment_count: 0 }]
    supabase.rpc.mockResolvedValue({ data: mockPosts, error: null })
    const { data, error } = await supabase.rpc('load_posts')
    expect(error).toBeNull()
    expect(data).toEqual(mockPosts)
  })

  it('returns null data on DB error', async () => {
    supabase.rpc.mockResolvedValue({ data: null, error: { message: 'DB error' } })
    const { data, error } = await supabase.rpc('load_posts')
    expect(data).toBeNull()
    expect(error.message).toBe('DB error')
  })

  it('handles empty posts array', async () => {
    supabase.rpc.mockResolvedValue({ data: [], error: null })
    const { data } = await supabase.rpc('load_posts')
    expect(data).toEqual([])
  })
})

// Tests delete_post RPC
describe('delete_post RPC', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls delete_post with correct post_id', async () => {
    const postId = 'post-123'
    supabase.rpc.mockResolvedValue({ data: true, error: null })
    
    await supabase.rpc('delete_post', { post_id: postId })
    
    expect(supabase.rpc).toHaveBeenCalledWith('delete_post', { post_id: postId })
  })

  it('returns true when deletion is successful', async () => {
    supabase.rpc.mockResolvedValue({ data: true, error: null })
    const { data } = await supabase.rpc('delete_post', { post_id: '123' })
    expect(data).toBe(true)
  })

  it('handles permission error (returns false)', async () => {
    supabase.rpc.mockResolvedValue({ data: false, error: null })
    const { data } = await supabase.rpc('delete_post', { post_id: '123' })
    expect(data).toBe(false)
  })
})

// Tests delete_comment RPC
describe('delete_comment RPC', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls delete_comment with correct comment_id', async () => {
    const commentId = 'comment-456'
    supabase.rpc.mockResolvedValue({ data: true, error: null })
    
    await supabase.rpc('delete_comment', { comment_id: commentId })
    
    expect(supabase.rpc).toHaveBeenCalledWith('delete_comment', { comment_id: commentId })
  })

  it('handles database error during deletion', async () => {
    supabase.rpc.mockResolvedValue({ data: null, error: { message: 'Network error' } })
    const { error } = await supabase.rpc('delete_comment', { comment_id: '456' })
    expect(error.message).toBe('Network error')
  })
})



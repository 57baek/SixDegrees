// src/utils.js
// Shared utility functions used across components.
// Extracted here so they can be properly unit tested and reused.

/**
 * Formats a post timestamp to relative time
 */
export function formatDate(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diffInHours = (now - date) / (1000 * 60 * 60)

  if (diffInHours < 1) return 'Just now'
  if (diffInHours < 24) return `${Math.floor(diffInHours)}h ago`
  if (diffInHours < 48) return 'Yesterday'
  return date.toLocaleDateString()
}

/**
 * Returns display label for a post visibility tier
 */
export function tierLabel(tier) {
  return { 1: 'Inner Circle', 2: '2nd Degree', 3: 'All Friends' }[tier] ?? String(tier)
}

/**
 * Returns display label for the feed tier filter
 */
export function tierFilterLabel(tier) {
  return { 1: 'Inner Circle', 2: '+ 2nd Degree', 3: 'All Friends' }[tier]
}

/**
 * Filters posts up to and including the selected tier
 */
export function filterPostsByTier(posts, selectedTier) {
  return posts.filter(p => p.tier <= selectedTier)
}
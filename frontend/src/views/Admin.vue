<template>
<div class="home">
    <div class="container">
      <header class="page-header">
        <h1>Reported Post</h1>
        <nav class="nav-buttons">
          <button @click="handleLogout" class="logout-btn">Logout</button>
        </nav>
      </header>

      <div v-if="loading" class="loading">Loading posts...</div>

      <div v-else-if="posts.length === 0" class="no-posts">
        <p>No reported posts! All is well!</p>
      </div>

      <div v-else class="feed">
        <Post
          v-for="post in posts"
          :key="post.id"
          :post="post"
          @delete-post="handleDeletePost"
          @check-report="loadPost"
        />
      </div>
    </div>
  </div>
</template>

<script setup>

import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase.js'
import Post from '../components/Post.vue'

const router = useRouter()

// Auth redirect
const session = ref(null)
let authListener = null

onMounted(async () => {
  // if no active session, redirect to login page
  const { data } = await supabase.auth.getSession()
  session.value = data.session
  if (!session.value) router.push('/login')

  // if somehow not admin, redirect to home page
  const { data: adminStatus, error : adminError } = await supabase.rpc('is_admin')
  if (adminError || adminStatus == null || !adminStatus) router.push('/')

  // Listen for sign-out only (ignore token refresh events)
  const { data: { subscription } } = supabase.auth.onAuthStateChange((event, newSession) => {
    if (event === 'SIGNED_OUT') {
      session.value = null
      router.push('/login')
    } else if (newSession) {
      session.value = newSession
      localStorage.setItem('supabase_token', newSession.access_token)
    }
  })
  authListener = subscription
})

onUnmounted(() => {
  authListener?.unsubscribe()
})

const posts = ref([])
const loading = ref(false)
const pollInterval = ref(null)

onMounted(async () => {
  // Get session
  const { data } = await supabase.auth.getSession()
  session.value = data.session
  if (!session.value) {
    router.push('/login')
    return
  }

  currentUserId.value = data.session?.user?.id ?? null

  // Fetch initial data
  loadPost()
  prefetchProfile(data.session)
  
  // Poll posts every 30s
  pollInterval.value = setInterval(loadPost, 30000)
})

onUnmounted(() => {
  clearInterval(pollInterval.value)
})

const currentUserId = ref(null)

/*
  Always fetches all posts (max_tier=3); tier filtering is done client-side.
*/
async function loadPost() {
  if (posts.value.length === 0) loading.value = true

  try {
    const { data, error } = await supabase.rpc('load_reported_post')
    if (error) throw error
    posts.value = data || []
  } catch (err) {
    console.error('Error loading post:', err)
  } finally {
    loading.value = false
  }
}

/*
  Logs the current user out, clears local storage, and redirects to login
*/
// Warms the profile cache in the background so /profile loads instantly
async function prefetchProfile(session) {
  if (!session) return
  try {
    const { data, error } = await supabase.rpc('get_user_profile', { target_user_id: session.user.id })
    if (!error && data) {
      localStorage.setItem('sixdeg_own_profile_cache', JSON.stringify(data))
    }
  } catch {}
}

async function handleLogout() {
  await supabase.auth.signOut()
  localStorage.removeItem('supabase_token')
  router.push('/login')
}

/*
  Prompts for confirmation, then deleted a post and removes it from the feed
*/
async function handleDeletePost(postId) {
  if (!confirm('Are you sure you want to delete this post?')) return

  try {
    const { data, error } = await supabase.rpc('delete_post', { 
      post_id: postId 
    })

    if (error) throw error

    if (data) {
      alert('Post deleted successfully.')
      loadPost()
    } else {
      alert('You do not have permission to delete this post.')
    }

  } catch (err) {
    console.error('Error deleting post:', err)
    alert('Failed to delete post: ' + err.message)
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: #1a1a1a;
  padding: 2rem 1rem;
}

.container {
  max-width: 600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #333;
  color: white;
}

.page-header h1 {
  margin: 0;
  font-size: 1.8rem;
}

.nav-buttons{
  display: flex;
  gap: 1rem;
  align-items: center;
}

.nav-btn{
  padding: 0.6rem 1.5rem;
  background: #088F8F;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.2s;
}

.nav-button:hover {
  background: #0CC6C6;
  transform: translateY(-1px);
}

.map-btn {
  background: #788ac5 100%;
  color: #0a0c18;
  font-weight: 700;
  border: none;
  box-shadow: 0 0 10px rgba(96, 212, 247, 0.2);
}

.map-btn:hover {
  background: linear-gradient(135deg, #a78bfa 0%, #60d4f7 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(96, 212, 247, 0.4);
  color: #000;
}

.logout-btn {
  padding: 0.6rem 1.5rem;
  background: transparent;
  color: #B0B0B0;
  border: 1px solid #444;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: #2D2D2D;
  color: white;
  border-color: #555;

}

.loading, .no-posts {
  text-align: center;
  color: #b0b0b0;
  padding: 3rem 1rem;
}

/* Test/Debug Boxes */
.test-box {
  padding: 20px;
  margin-bottom: 20px;
  background: #2a2a2a;
  border-radius: 8px;
}

.add-friend-box {
  border: 3px dashed #ff4444;
}

.friend-requests-box {
  border: 3px dashed #44ff44;
}

.test-title {
  color: white;
  margin-top: 0;
}

.test-input {
  padding: 8px;
  margin-right: 10px;
  width: 200px;
}

.test-btn {
  padding: 8px 16px;
  cursor: pointer;
  font-weight: bold;
  background: white;
  color: black;
  border: none;
  border-radius: 4px;
}

/* Friend Requests */
.no-requests {
  color: #888;
}

.requests-list {
  color: white;
  list-style: none;
  padding: 0;
}

.request-item {
  background: #333;
  padding: 10px;
  margin-bottom: 5px;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.request-text {
  color: white;
}

.request-buttons {
  display: flex;
  gap: 10px;
}

.accept-btn {
  background: #44ff44;
  color: black;
  border: none;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.reject-btn {
  background: #ff4444;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

.refresh-btn {
  margin-top: 10px;
  padding: 5px;
  cursor: pointer;
}

.request-user {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-small {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #088F8F;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: white;
  font-size: 1.2rem;
  flex-shrink: 0;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.tier-filter {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.filter-label {
  color: #888;
  font-size: 0.85rem;
  margin-right: 0.25rem;
}

.filter-btn {
  padding: 0.4rem 1rem;
  background: #2d2d2d;
  color: #b0b0b0;
  border: 1px solid #444;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.filter-btn:hover {
  border-color: #088F8F;
  color: white;
}

.filter-btn.active {
  background: #088F8F;
  border-color: #088F8F;
  color: white;
}
</style>
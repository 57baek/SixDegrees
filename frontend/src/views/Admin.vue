<template>
<div class="home">
    <div class="container">
      <header class="page-header">
        <h1>Reported Post</h1>
        <nav class="nav-buttons">
          <button @click="handleLogout" class="logout-btn">Logout</button>
        </nav>
      </header>

      <div v-if="loading" class="loading">Loading post...</div>

      <div v-else-if="posts.length === 0" class="no-posts">
        <p>No reported posts! All is well!</p>
      </div>

      <div v-else class="feed">
        <Post
          v-for="post in posts"
          :key="post.id"
          :post="post"
          :admin=true
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
  
  // Poll post every 30s
  pollInterval.value = setInterval(loadPost, 30000)
})

onUnmounted(() => {
  clearInterval(pollInterval.value)
})

const currentUserId = ref(null)

/*
  Fetches top reported post
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

.nav-buttons {
  display: flex;
  gap: 1rem;
  align-items: center;
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
</style>
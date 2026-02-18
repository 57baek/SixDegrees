<template>
  <div class="home">
    <div class="container">
      <header class="page-header">
        <h1> Your Feed </h1>
        <button @click="handleLogout" class="logout-btn">Logout</button>
      </header>

      <CreatePost @post-created="fetchPosts" />

      <div v-if="loading" class="loading">Loading posts...</div>

      <div v-else-if="posts.length === 0" class="no-posts">
        <p>No posts yet. Be the first to share something!</p>
      </div>

      <div v-else class="feed">
        <Post
          v-for="post in posts"
          :key="post.id"
          :post="post"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase'
import CreatePost from '../components/CreatePost.vue'
import Post from '../components/Post.vue'

const router = useRouter()

// arr to store all posts from the feed 
// TODO: remove mock data once db is set up 
const posts = ref([
  {
    id: 1,
    user_id: '123',
    content: 'This is a test post!',
    tier: 'inner_circle',
    created_at: new Date().toISOString(),
    profiles: { username: 'TestUser' },
    like_count: 5,
    comment_count: 2
  }
])

// loading state while fetching posts
const loading = ref(false)

// TODO: Uncomment this once db tables (posts, profiles, likes, comments) are set up!
// onMounted(() => {
//   loadPosts()
// })

/** Function to fetch posts from the database w/ user info, like count, comment count
 * posts ordered by recency (newst first)
*/
async function loadPosts() {
  loading.value = true
  
  try {
    const { data, error } = await supabase
      .from('posts')
      .select(`
        *,
        profiles (username),
        like_count:likes(count),
        comment_count:comments(count)
      `)
      .order('created_at', { ascending: false })
    
    if (error) throw error
    
    posts.value = data || []
  } catch (err) {
    console.error('Error loading posts:', err)
  } finally {
    loading.value = false
  }

  /**
   * Logs current user out and redirects to login page. 
   */
  async function handleLogout() {
    await supabase.auth.signOut()
    localStorage.removeItem('supabase_token')
    router.push('/login')
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
  color: white;
}

.page-header h1 {
  margin: 0;
}

.logout-btn {
  padding: 0.5rem 1rem;
  background: #444;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.3s;
}

.logout-btn:hover {
  background: #555;
}

.loading, .no-posts {
  text-align: center;
  color: #b0b0b0;
  padding: 3rem 1rem;
}

.feed {
  /* Posts will stack naturally */
}
</style>
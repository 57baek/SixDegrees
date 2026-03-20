<template>
  <div class="post-card">
    <div class="post-header">
      <div class="user-info">
        <div 
          class="avatar" 
          @click="router.push(`/profile/${post.user_id}`)"
          style="cursor:pointer"
        >{{ userInitial }}</div>        
        <div>
            <div class="nickname">{{ post.nickname || 'Unknown User' }}</div>
            <div class="post-meta">
              <span class="timestamp">{{ formatDate(post.created_at) }}</span>
              <span class="tier-badge" :class="`tier-${post.tier}`">
                <component :is="tierIcon(post.tier)" :size="12" />
                {{ tierLabel(post.tier) }}
              </span>
            </div>
        </div> 
      </div>
    </div>
  
    <div class="post-content">
      {{ post.content }}
    </div>
    
    <div class="post-actions-wrapper">
      <div class="post-actions">
        <button 
          @click="handleLike" 
          :class="{ liked: isLiked }"
          class="action-btn"
        >
          <Heart :size="18" :fill="isLiked ? 'currentColor' : 'none'" />
          {{ likeCount }}
        </button>
        
        <button @click="toggleComments" class="action-btn">
          <MessageCircle :size="18"/>
          {{ commentCount }}
        </button>
      </div>

      <button 
        v-if="isOwnPost" 
        class="delete-icon-btn" 
        @click="emitDelete"
        title="Delete Post"
      >
        <Trash2 :size="18" />
      </button>
    </div>
    
    <div v-if="showComments" class="comments-section">
      <div class="comment-input">
        <input 
          v-model="newComment"
          placeholder="Write a comment..."
          @keyup.enter="handleComment"
        />
        <button @click="handleComment" :disabled="!newComment.trim()">
          Send
        </button>
      </div>
      
      <div v-for="comment in comments" :key="comment.id" class="comment">
        <strong>{{ comment.nickname || 'Unknown' }}</strong>
        <span>{{ comment.content }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase'
import CreatePost from '../components/CreatePost.vue'
import Post from '../components/Post.vue'
import { filterPostsByTier, tierFilterLabel } from '../utils.js'

const router = useRouter()

// ===== Add Friend Test Function =====
const testNickname = ref('')

const testAddFriend = async () => {
  if (!testNickname.value) {
    alert('Please enter a nickname')
    return
  }
  
  try {
    const { data, error } = await supabase.rpc('request_friend', {
      friend_nickname: testNickname.value
    })
    
    if (error) throw error
    
     if (data)
      alert('Success! Your friend request has been sent!')
    else
      alert('Oops! Something went wrong! (Are you sure this person exists?)')
    testNickname.value = '' // Clear the input field
    
  } catch (err) {
    console.error('Error adding friend:', err)
    alert('Error: ' + err.message)
  }
}

// Request List
const incomingRequests = ref([]) // store like { id, nickname }

const fetchIncomingRequests = async () => {
  try {
    const { data : requestNicks, error: incomingRequestError } = await supabase.rpc('friend_requests')
    if (incomingRequestError) throw incomingRequestError
    incomingRequests.value = requestNicks
  } catch (err) {
    console.error('Error fetching nicknames:', err.message)
  }
}
// Accept request
const handleAccept = async (friendNickname) => {
  try {
    const { data, error } = await supabase.rpc('accept_friend', {
      friend_nickname: friendNickname
    })

    if (error) throw error
    
    alert(`You are now friends with ${friendNickname}!`)
    fetchIncomingRequests() // Refresh the list
  } catch (err) {
    alert('Error accepting friend: ' + err.message)
  }
}

// Reject request
const handleReject = async (friendNickname) => {
  try {
    const { data, error } = await supabase.rpc('reject_friend', {
      friend_nickname: friendNickname
    })

    if (error) throw error
    
    alert(`You have rejected the friend request from ${friendNickname}.`)
    fetchIncomingRequests() // Refresh the list to remove them
  } catch (err) {
    alert('Error rejecting friend: ' + err.message)
  }
}

// arr to store all posts from the feed 
const posts = ref([])

// loading state while fetching posts
const loading = ref(false)
const pollInterval = ref(null)

onMounted(() => {
  fetchIncomingRequests()
  loadPosts()
  pollInterval.value = setInterval(loadPosts, 30000) // auto-refresh every 30s
})

onUnmounted(() => {
  clearInterval(pollInterval.value)
})

/** Function to fetch posts from the database w/ user info, like count, comment count
 * posts ordered by recency (newst first)
*/


async function loadPosts() {
  loading.value = true
  
  try {
    const { data, error } = await supabase.rpc('load_posts')
    
    if (error) throw error
    
    posts.value = data || []
  } catch (err) {
    console.error('Error loading posts:', err)
  } finally {
    loading.value = false
  }
}

const goToProfile = (userId) => {
  router.push(`/profile/${userId}`)
}

  /**
   * Logs current user out and redirects to login page. 
   */
  async function handleLogout() {
    await supabase.auth.signOut()
    localStorage.removeItem('supabase_token')
    router.push('/login')
  }

  // computing filtered posts based on selected tier filter
  const selectedTierFilter = ref(3)

  const filteredPosts = computed(() => filterPostsByTier(posts.value, selectedTierFilter.value))
  // Delete posts
  async function handleDeletePost(postId) {
    if (!confirm('Are you sure you want to delete this post?')) return

    try {
      const { data, error } = await supabase.rpc('delete_post', { 
        post_id: postId 
      })

      if (error) throw error

      if (data) {
        posts.value = posts.value.filter(p => p.id !== postId)
        alert('Post deleted successfully.')
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

.feed {
  /* Posts will stack naturally */
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
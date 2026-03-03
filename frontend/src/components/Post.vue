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
import { ref, computed, onMounted} from 'vue'
import { supabase } from '../lib/supabase'
import { Heart, MessageCircle, Lock, Users, Globe } from 'lucide-vue-next' 
import { useRouter } from 'vue-router'
const router = useRouter()

// post data passed from parent
const props = defineProps({
  post: {
    type: Object,
    required: true
  }
})

const showComments = ref(false)
const newComment = ref('')
const comments = ref([])
const isLiked = ref(false)
const likeCount = ref(props.post.like_count || 0)
const commentCount = ref(props.post.comment_count || 0)

/**
 * Get first initial of nickname for avatar
 */
const userInitial = computed(() => {
  const nickname = props.post.nickname || 'U'
  return nickname.charAt(0).toUpperCase()
})

/**
 * Formats post timestamp to relative time 
 * @param dateString ISO date string
 */
function formatDate(dateString) {
  const date = new Date(dateString)
  const now = new Date()
  const diffInHours = (now - date) / (1000 * 60 * 60)
  
  if (diffInHours < 1) return 'Just now'
  if (diffInHours < 24) return `${Math.floor(diffInHours)}h ago`
  if (diffInHours < 48) return 'Yesterday'
  return date.toLocaleDateString()
}

/**
 * Returns label for a visibility tier
 * @param tier tier value from db (1, 2, 3)
 */
function tierLabel(tier) {
  const labels = {
    1: 'Inner Circle',
    2: '2nd Degree',
    3: 'All Friends'
  }
  return labels[tier] || tier
}

/**
 * returns icon component for a visibility tier
 * @param tier tier value from db (1, 2, 3)
 */
function tierIcon(tier) {
  return {
    1: Lock,
    2: Users,
    3: Globe
  }[tier] || Lock
}

/**
 * Handles liking/unliking a post. 
 * Checks if user is authenticated, then toggles like state in db and updates local state for instant UI feedback.
 */
async function handleLike() {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return
  
  try {
    if (isLiked.value) {
      // Unlike
      await supabase.rpc('unlike_post', {
        liked_post_id: props.post.id
      })
      
      isLiked.value = false
      likeCount.value--
    } else {
      // Like
      await supabase.rpc('like_post', {
        liked_post_id: props.post.id
      })
      
      isLiked.value = true
      likeCount.value++
    }
  } catch (err) {
    console.error('Like error:', err)
  }
}

// Check if current user has liked the post
async function fetchUserLike() {
  const { data, error } = await supabase.rpc('is_user_liked', {
    post_id: props.post.id
  })

  if (!error && data) {
    isLiked.value = true
  }
}

// On component mount, check if user has liked the post and fetch latest like count
onMounted(async () => {
  await fetchUserLike()

  // refresh like count from DB
  const { data , error } = await supabase.rpc('like_count', {
    post_id: props.post.id
  })

  if (!error) likeCount.value = data
})

/**
 * Toggles the comments section visibility. 
 * Loads comments from db on first open
*/
async function toggleComments() {
  showComments.value = !showComments.value
  
  if (showComments.value && comments.value.length === 0) {
    // Load comments
    const { data } = await supabase.rpc('load_comments', {
      post_id: props.post.id
    })
    
    if (data) comments.value = data
  }
}

/**
 * Submits a new comment
 * Inserts comment into db, adds comment to local arr, clears input field.
 */
async function handleComment() {
  if (!newComment.value.trim()) return
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return
  
  try {
    const { data, error } = await supabase.rpc('comment', { 
      post_id: props.post.id, 
      comment_content: newComment.value.trim() 
    })
    
    if (error) throw error
    
    comments.value.push(data[0])
    commentCount.value++
    newComment.value = ''
  } catch (err) {
    console.error('Comment error:', err)
  }
}
</script>

<style scoped>
.post-card {
  background: #2d2d2d;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.post-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.user-info {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #088F8F;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: white;
}

.nickname {
  font-weight: bold;
  color: white;
}

.post-meta {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.85rem;
  color: #888;
}

.tier-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
}

.tier-1 {
  background: #1e3a5f;
  color: #6bb6ff;
}

.tier-2 {
  background: #3a2f1e;
  color: #ffb66b;
}

.tier-3 {
  background: #2f3a1e;
  color: #b6ff6b;
}

.post-content {
  color: #e0e0e0;
  line-height: 1.6;
  margin-bottom: 1rem;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.post-actions {
  display: flex;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #444;
}

.action-btn {
  background: none;
  border: none;
  color: #b0b0b0;
  cursor: pointer;
  font-size: 0.9rem;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #1a1a1a;
  color: white;
}

.action-btn.liked {
  color: #ff6b6b;
}

.comments-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #444;
}

.comment-input {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.comment-input input {
  flex: 1;
  background: #1a1a1a;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  color: white;
}

.comment-input input:focus {
  outline: none;
  border-color: #088F8F;
}

.comment-input button {
  padding: 0.5rem 1rem;
  background: #088F8F;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.comment-input button:disabled {
  background: #444;
  cursor: not-allowed;
}

.comment {
  padding: 0.75rem;
  background: #1a1a1a;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  color: #e0e0e0;
}

.comment strong {
  color: #088F8F;
  margin-right: 0.5rem;
}

.tier-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;  /* Add this */
}
</style>
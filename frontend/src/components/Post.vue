<template>
  <div class="post-card">
    <div class="post-header">
      <div class="user-info">
        <div 
          class="avatar" 
          @click="router.push(`/profile/${post.nickname}`)"
          style="cursor:pointer"
        >
          <img v-if="post.avatar_url" :src="post.avatar_url" class="avatar-img" />
          <span v-else>{{ userInitial }}</span>
        </div>
        <div
          class="nickname"
          @click="router.push(`/profile/${post.nickname}`)"
          style="cursor:pointer"
        >{{ post.nickname || 'Unknown User' }}</div>
        <div class="post-meta">
          <span class="timestamp">{{ formatDate(post.created_at) }}</span>
          <span class="tier-badge" :class="`tier-${post.tier}`">
            <component :is="tierIcon(post.tier)" :size="12" />
            {{ tierLabel(post.tier) }}
          </span>
        </div>
      </div>
    </div>
  
   
    <div class="post-content">
      <p class="post-content">{{ post.content }}</p>

      <div v-if="post.image_urls && post.image_urls.length > 0" class="post-gallery">
        <div 
          v-for="(url, index) in post.image_urls" 
          :key="index" 
          class="post-image-item"
          :class="{ 'single-image': post.image_urls.length === 1 }"
        >
          <img :src="url" alt="Post content" class="post-img" loading="lazy" />
        </div>
      </div>
    </div>
    
    <div class="post-actions-wrapper">
      <div v-if="!props.admin" class="post-actions">
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
        v-if="isOwnPost || props.admin" 
        class="delete-icon-btn" 
        @click="emitDelete"
        title="Delete Post"
      >
        <Trash2  :size="18" />
      </button>
    
      <button 
        v-if="!isOwnPost"
        @click="handleReport" 
        class="action-btn"
        title="Report/Unreport Post"
      >
        <Flag :size="18" :fill="isReported ? 'currentColor' : 'none'" v-if="!props.admin"/>
        <CheckCircle :size="18" :fill="isReported ? 'currentColor' : 'none'" v-else/>
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
        <div class="comment-main-content">
          <strong 
            class="comment-author" 
            @click="router.push(`/profile/${comment.nickname}`)"
          >
            {{ comment.nickname || 'Unknown' }}
          </strong>
          <span class="comment-text">{{ comment.content }}</span>
        </div>
        
        <button 
          v-if="currentUserId && comment.user_id === currentUserId" 
          class="delete-comment-btn"
          @click="handleDeleteComment(comment.id)"
          title="Archive Comment"
        >
          <Archive :size="16" />
        </button>
      </div>
    </div>
  </div>
</template>


<script setup>
import { ref, computed, onMounted} from 'vue'
import { supabase } from '../lib/supabase'
import { Heart, MessageCircle, Archive, Trash2, Flag, CheckCircle } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { formatDate, tierIcon, tierLabel } from '../utils.js'


const router = useRouter()
const emit = defineEmits(['delete-post','check-report'])
const currentUserId = ref(null)


// Checks if this post belongs to the current user (controls delete button visibility)
const isOwnPost = computed(() => {
  return currentUserId.value && props.post.user_id === currentUserId.value
})

// Emits delete event to parent with the post ID
function emitDelete() {
  emit('delete-post', props.post.id)
}

// post data passed from parent
const props = defineProps({
  post: {
    type: Object,
    required: true
  },
  admin: {
    type: Boolean,
    required: false
  }
})

const showComments = ref(false)
const newComment = ref('')
const comments = ref([])
const isLiked = ref(false)
const likeCount = ref(0)
const commentCount = ref(0)
const isReported = ref(false)

/**
 * Get first initial of nickname for avatar
 */
const userInitial = computed(() => {
  const nickname = props.post.nickname || 'U'
  return nickname.charAt(0).toUpperCase()
})

/**
 * Handles liking/unliking a post. 
 * Checks if user is authenticated, then toggles like state in db and updates local state for instant UI feedback.
 */
async function handleLike() {
  if (!currentUserId.value) return

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
  }
}

/*
  * Loads in relevant post data in parallel:
  *  If the user has liked or reported the post, and total like and comment counts for the post
*/
onMounted(async () => {
  const { data: { user } } = await supabase.auth.getUser()
  if (user) {
    currentUserId.value = user.id
  }

  const [
    { data: liked },
    { data: reported },
    { data: likes, error: likeError },
    { data: commentsData, error: commentError },
  ] = await Promise.all([
    supabase.rpc('is_user_liked', { post_id: props.post.id }),
    supabase.rpc('is_user_reported', { post_id: props.post.id }),
    supabase.rpc('like_count', { post_id: props.post.id }),
    supabase.rpc('comment_count', { post_id: props.post.id }),
  ])

  if (liked) isLiked.value = true
  if (reported) isReported.value = true
  if (!likeError && likes !== null) likeCount.value = likes
  if (!commentError && commentsData !== null) commentCount.value = commentsData
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
  if (!newComment.value.trim() || !currentUserId.value) return

  try {
    const { data, error } = await supabase.rpc('comment', {
      post_id: props.post.id,
      comment_content: newComment.value.trim()
    })

    if (error) throw error

    const newAddedComment = {
      ...data[0],
      user_id: currentUserId.value
    }
    
    comments.value.push(newAddedComment)
    commentCount.value++
    newComment.value = ''
  } catch (err) {
  }
}

// Prompts for confirmation, deletes the comment, and removes it from the local list
async function handleDeleteComment(commentId) {
  if (!confirm('Are you sure you want to delete this comment?')) return
  
  try {
    const { data, error } = await supabase.rpc('delete_comment', { 
      comment_id: commentId 
    })

    if (error) throw error 
    if (data) {
      comments.value = comments.value.filter(c => c.id !== commentId)
      if (commentCount.value > 0) {
        commentCount.value--
      }
    }
  } catch (err) {
  }
}

/**
 * Handles reporting/unreporting a post. 
 * Checks if user is authenticated, then toggles report state in db and updates local state for instant UI feedback.
 */
async function handleReport() {
  if (!currentUserId.value) return
  
  try {
    if (isReported.value) {
      // Unreport
      await supabase.rpc('unreport_post', {
        reported_post_id: props.post.id
      })
      
      isReported.value = false
    } else {
      // Report
      await supabase.rpc('report_post', {
        reported_post_id: props.post.id
      })
      
      isReported.value = true
    }
    emit('check-report',props.post.id)
  } catch (err) {
  }
}


</script>

<style scoped>

.avatar {
  overflow: hidden;
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}
.post-card {
  background: #2d2d2d;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.delete-btn {
  background: transparent;
  color: #888;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 0.25rem 0.6rem;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  height: fit-content;
}

.delete-btn:hover {
  background: #ff444422;
  color: #ff4444;
  border-color: #ff4444;
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

.post-actions-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1rem;
  border-top: 1px solid #444;
}

.post-actions {
  display: flex;
  gap: 1rem;
}

.delete-icon-btn {
  background: transparent;
  border: none;
  color: #888;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-icon-btn:hover {
  background: rgba(255, 68, 68, 0.1);
  color: #ff4444;
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
  display: flex; 
  justify-content: space-between; 
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

.delete-comment-btn {
  background: transparent;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 4px;
  transition: color 0.2s;
}

.delete-comment-btn:hover {
  color: #ff4444;
}


.delete-comment-btn {
  background: transparent;
  border: none;
  color: #555; 
  cursor: pointer;
  padding: 6px; 
  border-radius: 50%; 
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0; 
  margin-top: -5px;
}

.delete-comment-btn:hover {
  background: rgba(255, 68, 68, 0.1); 
  color: #ff6b6b; 
  transform: scale(1.1); 
}
/* --- New Gallery Styles --- */
.post-gallery {
  display: grid;
  gap: 8px;
  margin-top: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  border-radius: 8px;
  overflow: hidden;
}

.post-image-item {
  width: 100%;
  aspect-ratio: 16 / 9; 
  background: #1a1a1a;
  border-radius: 4px;
  overflow: hidden;
}

.post-img {
  width: 100%;
  height: 100%;
  object-fit: cover; 
  display: block;
  transition: transform 0.3s ease;
}

.post-img:hover {
  transform: scale(1.02); 
}

.post-image-item.single-image {
  aspect-ratio: auto; 
  max-height: 500px;
}
</style>
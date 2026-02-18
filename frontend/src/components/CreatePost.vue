<template>
  <div class="create-post">
    <div class="post-box">
      <textarea
        v-model="content"
        placeholder="What's on your mind?"
        rows="4"
        maxlength="5000"
      ></textarea>
      
      <div class="post-controls">
        <div class="tier-selector">
          <label>Visible to:</label>
          <select v-model="selectedTier">
            <option value="inner_circle">Inner Circle Only</option>
            <option value="2nd_degree">Inner Circle + 2nd Degree</option>
            <option value="3rd_degree">All Friends</option>
          </select>
        </div>
        
        <button 
          @click="handlePost" 
          :disabled="!content.trim() || posting"
          class="post-btn"
        >
          {{ posting ? 'Posting...' : 'Post' }}
        </button>
      </div>
      
      <div v-if="error" class="error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { supabase } from '../lib/supabase'

const content = ref('')
const selectedTier = ref('inner_circle')
const posting = ref(false)
const error = ref('')

const emit = defineEmits(['post-created'])

async function handlePost() {
  if (!content.value.trim()) return
  
  posting.value = true
  error.value = ''
  
  try {
    const { data: { user } } = await supabase.auth.getUser()
    
    if (!user) {
      error.value = 'Not authenticated'
      return
    }
    
    const { data, error: postError } = await supabase
      .from('posts')
      .insert({
        user_id: user.id,
        content: content.value.trim(),
        tier: selectedTier.value,
        created_at: new Date().toISOString()
      })
      .select()
    
    if (postError) throw postError
    
    // Clear form
    content.value = ''
    selectedTier.value = 'inner_circle'
    
    // Emit event to parent to refresh feed
    emit('post-created', data[0])
    
  } catch (err) {
    error.value = err.message || 'Failed to create post'
    console.error('Post error:', err)
  } finally {
    posting.value = false
  }
}
</script>

<style scoped>
.create-post {
  margin-bottom: 2rem;
}

.post-box {
  background: #2d2d2d;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

textarea {
  width: 100%;
  background: #1a1a1a;
  color: white;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 1rem;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 1rem;
}

textarea:focus {
  outline: none;
  border-color: #088F8F;
}

.post-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.tier-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #b0b0b0;
}

.tier-selector label {
  font-size: 0.9rem;
}

select {
  background: #1a1a1a;
  color: white;
  border: 1px solid #444;
  border-radius: 4px;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  cursor: pointer;
}

select:focus {
  outline: none;
  border-color: #088F8F;
}

.post-btn {
  padding: 0.5rem 2rem;
  background: #088F8F;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s ease;
}

.post-btn:hover:not(:disabled) {
  background: #0CC6C6;
}

.post-btn:disabled {
  background: #444;
  cursor: not-allowed;
  opacity: 0.5;
}

.error {
  color: #ff6b6b;
  margin-top: 1rem;
  padding: 0.75rem;
  background: #3d1f1f;
  border-radius: 4px;
  border: 1px solid #ff6b6b;
}
</style>
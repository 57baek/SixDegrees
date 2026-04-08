<template>
  <div class="create-post">
    <div class="post-box">
      <textarea
        v-model="content"
        placeholder="What's on your mind?"
        rows="4"
        maxlength="5000"
      ></textarea>
      <div v-if="previewUrls.length > 0" class="image-previews">
        <div v-for="(url, index) in previewUrls" :key="index" class="preview-item">
          <img :src="url" class="preview-img" />
          <button @click="removeImage(index)" class="remove-btn" type="button">✕</button>
        </div>
        <div v-if="previewUrls.length < 5" class="add-more" @click="$refs.fileInput.click()">
          <span>+</span>
        </div>
      </div>
      <div class="post-controls">
        <input 
            type="file" 
            ref="fileInput" 
            @change="onFileSelected" 
            accept="image/*" 
            multiple 
            style="display: none"
          />
          <button 
            type="button" 
            class="add-photo-btn" 
            @click="$refs.fileInput.click()"
            :disabled="previewUrls.length >= 5"
          >
            📷 Add Photo ({{ previewUrls.length }}/5)
          </button>
        <div class="tier-selector">
          <label>Visible to:</label>
          <select v-model="selectedTier">
            <option value="inner_circle">Inner Circle Only</option>
            <option value="second_degree">Inner Circle + 2nd Degree</option>
            <option value="third_degree">All Friends</option>
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
const selectedFiles = ref([])
const previewUrls = ref([])
const fileInput = ref(null)

// Handles multi-file selection
function onFileSelected(event) {
  const files = Array.from(event.target.files)
  
  if (selectedFiles.value.length + files.length > 5) {
    error.value = 'Maximum 5 images allowed'
    return
  }

  files.forEach(file => {
    selectedFiles.value.push(file)
    previewUrls.value.push(URL.createObjectURL(file))
  })
}

// Removes a specific image from selection
function removeImage(index) {
  selectedFiles.value.splice(index, 1)
  previewUrls.value.splice(index, 1)
}

const emit = defineEmits(['post-created'])

/*
  Submits the post with the selected tier visibility
  Clears the form and notifies the parent to refresh the feed
*/
async function handlePost() {
  if (!content.value.trim() && selectedFiles.value.length === 0) return
  
  posting.value = true
  error.value = ''
  
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error('Not authenticated')

    // Upload all selected images to Supabase Storage
    const uploadPromises = selectedFiles.value.map(async (file) => {
      const fileExt = file.name.split('.').pop()
      const fileName = `${Date.now()}-${Math.random().toString(36).substring(7)}.${fileExt}`
      const filePath = `${user.id}/${fileName}`

      const { error: uploadError } = await supabase.storage
        .from('post-images')
        .upload(filePath, file)

      if (uploadError) throw uploadError

      const { data } = supabase.storage.from('post-images').getPublicUrl(filePath)
      return data.publicUrl
    })

    const allPublicUrls = await Promise.all(uploadPromises)

    // Call RPC to save post data (Make sure your SQL function accepts post_image_urls text[])
    const { data, error: postError } = await supabase.rpc('post', {
      post_content: content.value.trim(),
      post_tier: selectedTier.value, 
      post_image_urls: allPublicUrls
    })
        
        
    if (postError) throw postError
    
    // Reset Form
    content.value = ''
    selectedFiles.value = []
    previewUrls.value = []
    selectedTier.value = 1
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
.image-previews {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 10px;
  margin-bottom: 1rem;
}

.preview-item {
  position: relative;
  flex: 0 0 100px;
  height: 100px;
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
  border: 1px solid #444;
}

.remove-btn {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #ff6b6b;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  font-size: 12px;
  cursor: pointer;
}

.add-more {
  flex: 0 0 100px;
  height: 100px;
  border: 2px dashed #444;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  cursor: pointer;
}

.add-photo-btn {
  background: transparent;
  border: 1px solid #444;
  color: #b0b0b0;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.add-photo-btn:hover {
  border-color: #088F8F;
  color: white;
}
</style>
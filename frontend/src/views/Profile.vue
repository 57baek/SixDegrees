<template>
  <div class="page-container">
    <header class="profile-header">
      <button @click="router.back()" class="back-btn">← Back</button>
      <button v-if="!isEditing && isOwnProfile" @click="startEditing" class="edit-btn-header">Edit Profile</button>
    </header>

    <div id="main-profile-box">
      <div class="profile-picture-container">
        <div class="profile-pic-circle" :class="{ 'no-bg': profile.avatar_url }" @click="isOwnProfile && isEditing &&triggerUpload()">
        <img v-if="profile.avatar_url" :src="profile.avatar_url" class="avatar-img" />
        <span v-else>{{ userInitial }}</span>
        <div v-if="isOwnProfile && isEditing" class="avatar-overlay">Change</div>
        <input ref="fileInput" type="file" accept="image/*" hidden @change="uploadAvatar" />
      </div>
        <button v-if="isOwnProfile" type="button" id="friends-btn" @click="router.push('/friends')">
          Friends ({{ friendCount }})
        </button>
        <button v-else type="button" id="friends-btn" @click="router.push(`/friends/${profile.id}`)">
          Friends
        </button>

        <div v-if="!isOwnProfile" class="friendship-status">
          <div v-if="!isOwnProfile" class="friendship-status">
            <button class="addOrRemoveFriend-btn"
              type="button"
              :class="isFriend ? 'remove-friend-btn' : requestSent ? 'pending-friend-btn' : 'add-friend-btn'"
              @click="isFriend ? removeFriend() : !requestSent && sendFriendRequest()"
              :disabled="requesting || requestSent">
              <template v-if="requesting">Loading...</template>
              <template v-else-if="isFriend"><UserMinus :size="16" /> Remove Friend</template>
              <template v-else-if="requestSent"><Clock :size="16" /> Pending</template>
              <template v-else><UserPlus :size="16" /> Add Friend</template>
            </button>
            <button v-if="!isOwnProfile && requestSent"
              type="button"
              class="remove-friend-btn"
              @click="rescindRequest()"
              :disabled="requesting">
              Cancel
            </button>
          </div>
        </div>

        <div v-if="!isOwnProfile" class="block-status">
          <button class="blockOrUnblock-btn"
            type="button"
            :class="isBlocked ? 'unblock-btn' : 'block-btn'"
            @click="isBlocked ? unblockUser() : blockUser()"
            :disabled="blocking">
            <template v-if="blocking">Loading...</template>
            <template v-else-if="isBlocked">Unblock</template>
            <template v-else>Block</template>
          </button>
        </div>
      </div>

      <div class="bio-container">
        <div v-if="!isEditing">
          <h1 id="profile-name">{{ profile.nickname || 'Unnamed User' }}</h1>
          <p id="bio">{{ profile.bio || 'No bio added yet' }}</p>
          
          <div class="profile-details">
            <div class="detail-row" v-if="profile.age">
              <span class="label">Age:</span>
              <span>{{ profile.age }}</span>
            </div>
            <div class="detail-row" v-if="locationDisplay">
              <span class="label">Location:</span>
              <span>{{ locationDisplay }}</span>
            </div>
            <div class="detail-row" v-if="profile.education">
              <span class="label">Education:</span>
              <span>{{ profile.education }}</span>
            </div>
            <div class="detail-row" v-if="profile.occupation">
              <span class="label">Occupation:</span>
              <span>{{ profile.occupation }}</span>
            </div>
          </div>
        </div>

        <!-- Edit Form -->
        <div v-else class="edit-form">
          <input v-model="editForm.nickname" placeholder="Nickname" class="input-field name-input" />
          <textarea v-model="editForm.bio" placeholder="Tell people about yourself..." class="input-field bio-input"></textarea>
          
          <div class="form-row">
            <input v-model.number="editForm.age" type="number" placeholder="Age" class="input-field small-input" />
            <input v-model="editForm.city" placeholder="City" class="input-field" />
            <input v-model="editForm.state" placeholder="State" class="input-field small-input" />
          </div>
          
          <input v-model="editForm.education" placeholder="Education" class="input-field" />
          <input v-model="editForm.occupation" placeholder="Occupation" class="input-field" />
          <input v-model="editForm.industry" placeholder="Industry" class="input-field" />
          
          <div class="form-actions">
            <button @click="cancelEdit" class="cancel-btn">Cancel</button>
            <button @click="saveProfile" class="save-btn" :disabled="saving">
              {{ saving ? 'Saving...' : 'Save' }}
            </button>
          </div>
          
          <div v-if="error" class="error">{{ error }}</div>
        </div>
      </div>
    </div>

    <div id="hobbies-box">
      <h3>Interests</h3>
      
      <div v-if="!isEditing">
        <ul v-if="profile.interests?.length">
          <li v-for="interest in profile.interests" :key="interest">{{ interest }}</li>
        </ul>
        <p v-else class="empty-state">No interests added yet</p>
      </div>
      
      <div v-else>
        <input 
          v-model="interestsInput" 
          placeholder="Enter interests separated by commas" 
          class="input-field"
        />
        <p class="hint">Example: hiking, coding, music</p>
      </div>
    </div>

    <div id="hobbies-box" style="margin-top: 1.5rem;">
      <h3>Languages</h3>
      
      <div v-if="!isEditing">
        <ul v-if="profile.languages?.length">
          <li v-for="lang in profile.languages" :key="lang">{{ lang }}</li>
        </ul>
        <p v-else class="empty-state">No languages added yet</p>
      </div>
      
      <div v-else>
        <input 
          v-model="languagesInput" 
          placeholder="Enter languages separated by commas" 
          class="input-field"
        />
        <p class="hint">Example: English, Spanish, Mandarin</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { supabase } from '../lib/supabase'
import { UserPlus, UserMinus, Clock } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

const profile = ref({})
const currentUserId = ref(null)
const isEditing = ref(false)
const saving = ref(false)
const error = ref('')
const isFriend = ref(false)

const isBlocked = ref(false)
const blocking = ref(false)

const fileInput = ref(null)
const uploading = ref(false)

const editForm = ref({
  nickname: '',
  bio: '',
  age: null,
  city: '',
  state: '',
  education: '',
  occupation: '',
  industry: '',
  interests: [],
  languages: []
})

const interestsInput = ref('')
const languagesInput = ref('')

// check if user is viewing their own profile or someone else's
const isOwnProfile = computed(() => {
  return !route.params.userId || route.params.userId === currentUserId.value
})

const userInitial = computed(() => {
  return profile.value.nickname?.charAt(0).toUpperCase() || 'U'
})

const locationDisplay = computed(() => {
  if (profile.value.city && profile.value.state) {
    return `${profile.value.city}, ${profile.value.state}`
  } else if (profile.value.city) {
    return profile.value.city
  } else if (profile.value.state) {
    return profile.value.state
  }
  return null
})

const friendCount = computed(() => {
  return profile.value.friends?.length || 0
})

async function loadProfile() {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) {
      error.value = 'Not logged in'
      return
    }

    currentUserId.value = user.id

    //if userid in route, load that profile, otherwise load current user's profile
    const targetUser = route.params.userId || user.id

    const { data, error: profileError } = (targetUser.length == 36) ? 
      await supabase
        .rpc('get_user_profile', { target_user_id: targetUser })
        .single()
      :
      await supabase
        .rpc('get_user_profile', { target_nickname : targetUser })
        .single()

    if (profileError) throw profileError
    profile.value = data || {}

    if(profile.value.id != user.id) {
      const { data: friends } = await supabase.rpc('extended_friends', { max_tier: 1 })
      isFriend.value = (friends || []).some(f => f.id === profile.value.id)

      const { data: pending } = await supabase.rpc('has_pending_request', { target_user_id: profile.value.id })
      requestSent.value = pending

      const { data : blocked } = await supabase.rpc('is_blocked', {blocked_id: profile.value.id })
      isBlocked.value = blocked

      router.replace(`/profile/${profile.value.nickname}`)
    }
    else
      router.replace(`/profile`)
  } catch (err) {
    console.error('Error loading profile:', err)
    error.value = 'Failed to load profile'
  }
}

function startEditing() {
  editForm.value = {
    nickname: profile.value.nickname || '',
    bio: profile.value.bio || '',
    age: profile.value.age || null,
    city: profile.value.city || '',
    state: profile.value.state || '',
    education: profile.value.education || '',
    occupation: profile.value.occupation || '',
    industry: profile.value.industry || '',
    interests: profile.value.interests || [],
    languages: profile.value.languages || []
  }
  
  interestsInput.value = editForm.value.interests.join(', ')
  languagesInput.value = editForm.value.languages.join(', ')
  
  isEditing.value = true
}

function cancelEdit() {
  isEditing.value = false
  error.value = ''
}

async function saveProfile() {
  saving.value = true
  error.value = ''
  
  try {
    
    // Parse comma-separated inputs
    const interests = interestsInput.value
      .split(',')
      .map(i => i.trim())
      .filter(i => i.length > 0)
    
    const languages = languagesInput.value
      .split(',')
      .map(l => l.trim())
      .filter(l => l.length > 0)
    
    const { error: updateError } = await supabase.rpc('update_profile', {
        nickname: editForm.value.nickname,
        bio: editForm.value.bio,
        age: editForm.value.age,
        city: editForm.value.city,
        state: editForm.value.state,
        education: editForm.value.education,
        occupation: editForm.value.occupation,
        industry: editForm.value.industry,
        interests,
        languages,
        avatar_url: profile.value.avatar_url || null
    })
    
    if (updateError) throw updateError
    
    await loadProfile()
    isEditing.value = false
  } catch (err) {
    error.value = err.message || 'Failed to save profile'
    console.error('Save error:', err)
  } finally {
    saving.value = false
  }
}

// direct friend requesting from profile
const requestSent = ref(false)
const requesting = ref(false)

async function sendFriendRequest() {
  requesting.value = true
  try {
    const { data, error } = await supabase.rpc('request_friend', {
      friend_nickname: profile.value.nickname
    })
    if (error) throw error
    if (data) requestSent.value = true
    else alert('Could not send request — you may already be friends or have a pending request.')
  } catch (err) {
    console.error('Error sending friend request:', err)
  } finally {
    requesting.value = false
  }
}

async function removeFriend() {
  requesting.value = true
  try {
    const { error } = await supabase.rpc('remove_friend', {
      friend_nickname: profile.value.nickname
    })
    if (error) throw error
    isFriend.value = false
  } catch (err) {
    console.error('Error removing friend:', err)
  } finally {
    requesting.value = false
  }
}

async function rescindRequest() {
  requesting.value = true
  try {
    const { error } = await supabase.rpc('rescind_friend_request', {
      friend_nickname: profile.value.nickname
    })
    if (error) throw error
    requestSent.value = false
  } catch (err) {
    console.error('Error rescinding request:', err)
  } finally {
    requesting.value = false
  }
}

async function blockUser() {
  blocking.value = true
  try {
    const { error } = await supabase.rpc('block', {
      blocked_nickname: profile.value.nickname
    })
    if (error) throw error
    isBlocked.value = true
  } catch (err) {
    console.error('Error blocking user:', err)
  } finally {
    blocking.value = false
  }
}

async function unblockUser() {
  blocking.value = true
  try {
    const { error } = await supabase.rpc('unblock', {
      blocked_nickname: profile.value.nickname
    })
    if (error) throw error
    isBlocked.value = false
  } catch (err) {
    console.error('Error unblocking user:', err)
  } finally {
    blocking.value = false
  }
}

function triggerUpload() {
  fileInput.value.click()
}

async function uploadAvatar(event) {
  const file = event.target.files[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) return alert('Max file size is 2MB')
  if (!file.type.startsWith('image/')) return alert('Please upload an image')

  uploading.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    const ext = file.name.split('.').pop()
    const path = `${user.id}/avatar.${ext}`

    const { error: uploadError } = await supabase.storage
      .from('avatars')
      .upload(path, file, { upsert: true })
    if (uploadError) throw uploadError

    const { data: { publicUrl } } = supabase.storage
      .from('avatars')
      .getPublicUrl(path)

    const { error: updateError } = await supabase.rpc('update_profile', {
      nickname: profile.value.nickname,
      bio: profile.value.bio,
      age: profile.value.age,
      city: profile.value.city,
      state: profile.value.state,
      education: profile.value.education,
      occupation: profile.value.occupation,
      industry: profile.value.industry,
      interests: profile.value.interests || [],
      languages: profile.value.languages || [],
      avatar_url: publicUrl
    })
    if (updateError) throw updateError

    profile.value.avatar_url = publicUrl
  } catch (err) {
    console.error('Avatar upload failed:', err)
    alert(err.message || 'Upload failed')
  } finally {
    uploading.value = false
  }
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100vh;
  background: #1a1a1a;
  padding: 2rem 1rem;
}

.profile-header {
  width: 100%;
  max-width: 800px;
  display: flex;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.back-btn, .edit-btn-header {
  padding: 0.5rem 1rem;
  background: #444;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: background 0.2s;
}

.edit-btn-header {
  background: #088F8F;
}

.back-btn:hover {
  background: #555;
}

.edit-btn-header:hover {
  background: #0CC6C6;
}

#main-profile-box {
  display: flex;
  gap: 2rem;
  background: #2d2d2d;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  width: 100%;
  max-width: 800px;
}

.profile-picture-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  min-width: 200px;
}

.profile-pic-circle {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  background: #088F8F;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  font-weight: bold;
  color: white;
  position: relative;
  overflow: hidden;
}

.profile-pic-circle.no-bg {
  background: transparent;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.avatar-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0,0,0,0.5);
  color: white;
  text-align: center;
  padding: 0.4rem;
  font-size: 0.85rem;
  opacity: 0;
  transition: opacity 0.2s;
}

.profile-pic-circle:hover .avatar-overlay {
  opacity: 1;
  cursor: pointer;
}

#friends-btn {
  width: 100%;
  padding: 0.75rem;
  background: #444;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: background 0.2s;
}

#friends-btn:hover {
  background: #555;
}

.bio-container {
  flex: 1;
}

#profile-name {
  font-weight: bold;
  font-size: 2rem;
  color: white;
  margin: 0 0 1rem 0;
}

#bio {
  color: #b0b0b0;
  line-height: 1.6;
  margin-bottom: 2rem;
  font-style: italic;
}

.profile-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.detail-row {
  display: flex;
  gap: 1rem;
  color: #e0e0e0;
}

.detail-row .label {
  font-weight: bold;
  color: #088F8F;
  min-width: 100px;
}

#hobbies-box {
  background: #2d2d2d;
  padding: 2rem;
  margin-top: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  width: 100%;
  max-width: 800px;
}

#hobbies-box h3 {
  color: #088F8F;
  margin: 0 0 1rem 0;
  font-size: 1.2rem;
}

ul {
  color: #fff;
  list-style: none;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

li {
  background: #088F8F;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
}

.empty-state {
  color: #888;
  font-style: italic;
}

/* Edit Form Styles */
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.input-field {
  width: 100%;
  background: #1a1a1a;
  border: 1px solid #444;
  border-radius: 6px;
  padding: 0.75rem;
  color: white;
  font-size: 1rem;
}

.input-field:focus {
  outline: none;
  border-color: #088F8F;
}

.name-input {
  font-size: 1.5rem;
  font-weight: bold;
}

.bio-input {
  min-height: 100px;
  resize: vertical;
  font-family: inherit;
}

.form-row {
  display: grid;
  grid-template-columns: 80px 1fr 100px;
  gap: 0.5rem;
}

.small-input {
  max-width: 100px;
}

.hint {
  color: #888;
  font-size: 0.85rem;
  margin-top: 0.25rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.cancel-btn, .save-btn {
  flex: 1;
  padding: 0.75rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background: #444;
  color: white;
}

.cancel-btn:hover {
  background: #555;
}

.save-btn {
  background: #088F8F;
  color: white;
}

.save-btn:hover:not(:disabled) {
  background: #0CC6C6;
}

.save-btn:disabled {
  background: #444;
  cursor: not-allowed;
  opacity: 0.5;
}

.error {
  color: #ff6b6b;
  padding: 0.75rem;
  background: #3d1f1f;
  border-radius: 6px;
  border: 1px solid #ff6b6b;
}

.friendship-status {
  display: flex;
  width: 100%;
}

.add-friend-btn {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  color: #088F8F;
  border: 1px solid #088F8F;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.add-friend-btn:hover:not(:disabled) {
  background: #088F8F;
  color: white;
}

.add-friend-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.friend-badge {
  width: 100%;
  padding: 0.75rem;
  background: #088F8F22;
  color: #088F8F;
  border: 1px solid #088F8F44;
  border-radius: 6px;
  font-size: 0.95rem;
  text-align: center;
}

.remove-friend-btn {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  color: #ff6b6b;
  border: 1px solid #ff6b6b;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.remove-friend-btn:hover:not(:disabled) {
  background: #ff6b6b;
  color: white;
}

.remove-friend-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pending-friend-btn {
  width: 250%;
  padding: 0.75rem;
  background: transparent;
  color: #f0a500;
  border: 1px solid #f0a500;
  border-radius: 6px;
  cursor: not-allowed;
  font-size: 0.95rem;
  opacity: 0.8;
}

.addOrRemoveFriend-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
}

.block-status {
  width: 100%;
}

.unblock-btn {
  width: 100%;
  padding: 0.75rem;
  background: transparent;
  color: #088F8F;
  border: 1px solid #088F8F;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.unblock-btn:hover:not(:disabled) {
  background: #088F8F;
  color: white;
}

.unblock-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.block-btn {
  width: 40%;
  padding: 0.75rem;
  background: transparent;
  color: #ff6b6b;
  border: 1px solid #ff6b6b;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
  text-align: center;
}

.block-btn:hover:not(:disabled) {
  background: #ff6b6b;
  color: white;
}

.block-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
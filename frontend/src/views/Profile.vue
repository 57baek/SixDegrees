<template>
  <div class="page-container">
    <header class="profile-header">
      <button @click="router.push('/')" class="back-btn">← Back to Feed</button>
      <button v-if="!isEditing" @click="startEditing" class="edit-btn-header">Edit Profile</button>
    </header>

    <div id="main-profile-box">
      <div class="profile-picture-container">
        <div class="profile-pic-circle">
          {{ userInitial }}
        </div>
        <button type="button" id="friends-btn" @click="router.push('/friends')">
          Friends ({{ friendCount }})
        </button>
      </div>

      <div class="bio-container">
        <div v-if="!isEditing">
          <h1 id="profile-name">{{ profile.nickname || 'Set your nickname' }}</h1>
          <p id="bio">{{ profile.bio || 'Tell people about yourself...' }}</p>
          
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase'

const router = useRouter()

const profile = ref({})
const isEditing = ref(false)
const saving = ref(false)
const error = ref('')

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

    const { data, error: profileError } = await supabase.rpc('user_profile').single()
    
    if (profileError) throw profileError
    
    profile.value = data || {}
  } catch (err) {
    console.error('Error loading profile:', err)
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
        languages
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
</style>
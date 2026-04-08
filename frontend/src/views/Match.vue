<template>
  <div class="match">
    <div class="container">
      <header class="page-header">
        <h1>Your Matches</h1>
        <nav class="nav-buttons">
          <button @click="router.push('/')" class="nav-btn">Feed</button>
          <button @click="router.push('/map')" class="nav-btn map-btn">People Map</button>
          <button @click="router.push('/profile')" class="nav-btn">Profile</button>
        </nav>
      </header>

      <div v-if="loading" class="loading">Finding your matches...</div>

      <div v-else-if="error" class="error">{{ error }}</div>

      <div v-else-if="matches.length === 0" class="no-matches">
        <p>No matches found yet. Complete your profile to get better matches!</p>
      </div>

      <ul v-else class="match-list">
        <li
          v-for="match in matches"
          :key="match.user_id"
          class="match-item"
          @click="router.push(`/profile/${match.nickname}`)"
        >
          <div class="avatar">
            <img v-if="match.avatar_url" :src="match.avatar_url" class="avatar-img" />
            <span v-else>{{ match.nickname.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="match-info">
            <span class="nickname">{{ match.nickname }}</span>
            <span class="score">{{ Math.round(match.similarity_score * 100) }}% match</span>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase'

const router = useRouter()
const matches = ref([])
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) {
    router.push('/login')
    return
  }

  try {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const res = await fetch(`${apiUrl}/match`, {
      headers: { Authorization: `Bearer ${session.access_token}` }
    })
    if (!res.ok) throw new Error(`Request failed: ${res.status}`)
    const data = await res.json()
    matches.value = data.matches || []
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.match {
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

.nav-btn {
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

.map-btn {
  background: #788ac5;
  color: #0a0c18;
  font-weight: 700;
}

.loading, .no-matches, .error {
  text-align: center;
  color: #b0b0b0;
  padding: 3rem 1rem;
}

.error {
  color: #ff6b6b;
}

.match-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.match-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: #2a2a2a;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 0.75rem;
  cursor: pointer;
  transition: background 0.2s;
}

.match-item:hover {
  background: #333;
}

.avatar {
  width: 48px;
  height: 48px;
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

.match-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nickname {
  color: white;
  font-weight: 600;
  font-size: 1rem;
}

.score {
  color: #088F8F;
  font-size: 0.85rem;
  font-weight: 500;
}
</style>

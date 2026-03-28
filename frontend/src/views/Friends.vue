<template>
  <div class="friends-page">
    <div class="container">
      <header class="friends-header">
        <button @click="router.back()" class="back-btn">← Back</button>
        <h1>{{ route.params.userId ? "Their Friends" : "My Friends" }}</h1>
        <span class="friend-count">{{ friends.length }}</span>
      </header>

      <div v-if="loading" class="loading">Loading friends...</div>

      <div v-else-if="friends.length === 0" class="no-friends">
        <p>No friends yet. Send some friend requests!</p>
      </div>

      <div v-else class="friends-list">
        <div
          v-for="friend in friends"
          :key="friend.id"
          class="friend-row"
          @click="router.push(`/profile/${friend.id}`)"
        >
          <div class="friend-avatar">
            <img v-if="friend.avatar_url" :src="friend.avatar_url" class="avatar-img" />
            <span v-else>{{ friend.nickname.charAt(0).toUpperCase() }}</span>
          </div>

          <div class="friend-info">
            <h3>{{ friend.nickname }}</h3>
            <div class="friend-meta">
              <span class="friend-tier">Tier {{ friend.tier }}</span>
            </div>
          </div>

          <span class="arrow">→</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { supabase } from '../lib/supabase'

const router = useRouter()
const route = useRoute()
const friends = ref([])
const loading = ref(true)

async function loadFriends() {
  loading.value = true
  try {
    const { data, error } = await supabase.rpc('extended_friends', 
      { max_tier: 3,
        target_user_id: route.params.userId || null
      })
    if (error) throw error
    friends.value = (data || []).filter(f => f.tier === 1)
    console.log('Friend fields:', friends.value[0]) // add this
  } catch (err) {
    console.error('Error loading friends:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadFriends()
})
</script>

<style scoped>
.friends-page {
  min-height: 100vh;
  background: #1a1a1a;
  padding: 2rem 1rem;
}

.container {
  max-width: 700px;
  margin: 0 auto;
}

.friends-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.friends-header h1 {
  color: white;
  margin: 0;
  flex: 1;
}

.friend-count {
  background: #088F8F;
  color: white;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
}

.back-btn {
  padding: 0.5rem 1rem;
  background: #444;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: background 0.2s;
}

.back-btn:hover {
  background: #555;
}

.loading {
  text-align: center;
  color: #b0b0b0;
  padding: 3rem;
}

.no-friends {
  text-align: center;
  color: #888;
  padding: 3rem;
  background: #2d2d2d;
  border-radius: 12px;
}

.friends-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.friend-row {
  background: #2d2d2d;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.friend-row:hover {
  background: #333;
  transform: translateX(4px);
}

.friend-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #088F8F;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  font-weight: bold;
  color: white;
  flex-shrink: 0;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.friend-info {
  flex: 1;
}

.friend-info h3 {
  color: white;
  margin: 0 0 0.25rem 0;
  font-size: 1rem;
}

.friend-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.friend-tier {
  color: #088F8F;
  font-size: 0.82rem;
  font-weight: 600;
}

.separator {
  color: #555;
  font-size: 0.8rem;
}

.friend-since {
  color: #888;
  font-size: 0.82rem;
}

.arrow {
  color: #555;
  font-size: 1rem;
  transition: color 0.2s;
}

.friend-row:hover .arrow {
  color: #088F8F;
}
</style>
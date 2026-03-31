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

          <button
            v-if="friend.id !== currentUserId"
            class="addOrRemoveFriend-btn"
            :class="!route.params.userId || friendStatuses[friend.id]?.isFriend ? 'remove-friend-btn' : friendStatuses[friend.id]?.requestSent ? 'pending-friend-btn' : 'add-friend-btn'"
            :disabled="requesting === friend.id || friendStatuses[friend.id]?.requestSent"
            @click.stop="!route.params.userId || friendStatuses[friend.id]?.isFriend ? removeFriend(friend) : !friendStatuses[friend.id]?.requestSent && sendFriendRequest(friend)"
          >
            <template v-if="requesting === friend.id">Loading...</template>
            <template v-else-if="!route.params.userId || friendStatuses[friend.id]?.isFriend"><UserMinus :size="16" /> Remove</template>
            <template v-else-if="friendStatuses[friend.id]?.requestSent"><Clock :size="16" /> Pending</template>
            <template v-else><UserPlus :size="16" /> Add</template>
          </button>

          <span v-else class="arrow">→</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { supabase } from '../lib/supabase'
import { UserPlus, UserMinus, Clock } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const friends = ref([])
const loading = ref(true)
const currentUserId = ref(null)
const friendStatuses = ref({}) // tracking isFriend/requestSent per user
const requesting = ref(null) // tracks which user id is currently requesting

async function loadFriends() {
  loading.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    currentUserId.value = user.id
    
    const { data, error } = await supabase.rpc('extended_friends', 
      { max_tier: 3,
        target_user_id: route.params.userId || null
      })
    if (error) throw error
    friends.value = (data || []).filter(f => f.tier === 1)
    
    if (route.params.userId) {
      const { data: myFriends } = await supabase.rpc('extended_friends', { max_tier: 1 })
      const myFriendIds = new Set((myFriends || []).map(f => f.id))

      await Promise.all(friends.value.map(async (f) => {
        const { data: pending } = await supabase.rpc('has_pending_request', { target_user_id: f.id })
        friendStatuses.value[f.id] = {
          isFriend: myFriendIds.has(f.id),
          requestSent: !!pending
        }
      }))
    }
  } catch (err) {
    console.error('Error loading friends:', err)
  } finally {
    loading.value = false
  }
}

async function sendFriendRequest(friend) {
  requesting.value = friend.id
  try {
    const { data, error } = await supabase.rpc('request_friend', {
      friend_nickname: friend.nickname
    })
    if (error) throw error
    if (data) friendStatuses.value[friend.id].requestSent = true
    else alert('Could not send request.')
  } catch (err) {
    console.error('Error sending friend request:', err)
  } finally {
    requesting.value = null
  }
}

async function removeFriend(friend) {
  requesting.value = friend.id
  try {
    const { error } = await supabase.rpc('remove_friend', {
      friend_nickname: friend.nickname
    })
    if (error) throw error

    // remove from list instantly
    friends.value = friends.value.filter(f => f.id !== friend.id)

    // also update status in case we're on someone else's list
    if (friendStatuses.value[friend.id]) {
      friendStatuses.value[friend.id].isFriend = false
    }
  } catch (err) {
    console.error('Error removing friend:', err)
  } finally {
    requesting.value = null
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

.addOrRemoveFriend-btn {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.85rem;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  border: 1px solid;
  background: transparent;
  transition: all 0.2s;
  flex-shrink: 0;
}

.add-friend-btn {
  color: #088F8F;
  border-color: #088F8F;
}
.add-friend-btn:hover:not(:disabled) {
  background: #088F8F;
  color: white;
}

.remove-friend-btn {
  color: #ff6b6b;
  border-color: #ff6b6b;
}
.remove-friend-btn:hover:not(:disabled) {
  background: #ff6b6b;
  color: white;
}

.pending-friend-btn {
  color: #f0a500;
  border-color: #f0a500;
  cursor: not-allowed;
  opacity: 0.8;
}
</style>
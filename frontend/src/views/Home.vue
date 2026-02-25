<template>
<div class="home">
    <div class="container">
      <header class="page-header">
        <h1> Your Feed </h1>
        <nav class="nav-buttons">
          <button @click="router.push('/profile')" class="nav-btn">Profile</button>
          <button @click="handleLogout" class="logout-btn">Logout</button>
        </nav>
      </header>

      <div style="border: 3px dashed #ff4444; padding: 20px; margin-bottom: 20px; background: #2a2a2a; border-radius: 8px;">
        <h3 style="color: white; margin-top: 0;"> Add Friend API Test</h3>
        <input 
          v-model="testNickname" 
          placeholder="Enter an existing nickname" 
          style="padding: 8px; margin-right: 10px; width: 200px;"
        />
        <button @click="testAddFriend" style="padding: 8px 16px; cursor: pointer; font-weight: bold; background: white; color: black; border: none; border-radius: 4px;">
          Send Friend Request
        </button>
      </div>
      
    <div style="border: 3px dashed #44ff44; padding: 20px; margin-bottom: 20px; background: #2a2a2a; border-radius: 8px;">
      <h3 style="color: white; margin-top: 0;">Pending Friend Requests</h3>
      
      <div v-if="incomingRequests.length === 0" style="color: #888;">
        No pending requests.
      </div>
      
      <ul v-else style="color: white; list-style: none; padding: 0;">
        <li v-for="user in incomingRequests" :key="user.id" 
          style="background: #333; padding: 10px; margin-bottom: 5px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;">
        
        <span style="color: white;"><strong>{{ user.nickname }}</strong> wants to be friends!</span>
        
        <div style="display: flex; gap: 10px;">
          <button @click="handleAccept(user.nickname)" 
                  style="background: #44ff44; color: black; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight: bold;">
            Accept
          </button>

          <button @click="handleReject(user.nickname)" 
                  style="background: #ff4444; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; font-weight: bold;">
            Reject
          </button>
        </div>
        </li>
      </ul>
      <button @click="fetchIncomingRequests" style="margin-top: 10px; padding: 5px; cursor: pointer;">
        Refresh
      </button>

      
    </div>

      
      <CreatePost @post-created="loadPosts" />

      <div v-if="loading" class="loading">Loading posts...</div>

      <div v-else-if="posts.length === 0" class="no-posts">
        <p>No posts yet. Be the first to share something!</p>
      </div>

      <div v-else class="feed">
        <Post
          v-for="post in posts"
          :key="post.id"
          :post="post"
        />
      </div>
    </div>
  </div>
</template>

<script setup>

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase'
import CreatePost from '../components/CreatePost.vue'
import Post from '../components/Post.vue'

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
    
    alert('Success! Response: ' + data)
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
    const { data: { user } } = await supabase.auth.getUser()
    
    // Get the array of UUIDs
    const { data: profileData, error: profileError } = await supabase
      .from('profiles')
      .select('pending_friend_requests')
      .eq('id', user.id)
      .single()

    if (profileError) throw profileError
    
    const ids = profileData.pending_friend_requests || []

    if (ids.length > 0) {
      // Fetch the nicknames for all those IDs at once
      const { data: nickData, error: nickError } = await supabase
        .from('profiles')
        .select('id, nickname')
        .in('id', ids) // Filters profiles where ID is in our list

      if (nickError) throw nickError
      incomingRequests.value = nickData
    } else {
      incomingRequests.value = []
    }
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

onMounted(() => {
  fetchIncomingRequests()
   loadPosts()
})

/** Function to fetch posts from the database w/ user info, like count, comment count
 * posts ordered by recency (newst first)
*/


async function loadPosts() {
  loading.value = true
  
  try {
    const { data, error } = await supabase
      .from('posts')
      .select(`
        *,
        profiles (nickname),
        like_count:likes(count),
        comment_count:comments(count)
      `)
      .order('created_at', { ascending: false })
    
    if (error) throw error
    
    posts.value = data || []
  } catch (err) {
    console.error('Error loading posts:', err)
  } finally {
    loading.value = false
  }
}

  /**
   * Logs current user out and redirects to login page. 
   */
  async function handleLogout() {
    await supabase.auth.signOut()
    localStorage.removeItem('supabase_token')
    router.push('/login')
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
</style>
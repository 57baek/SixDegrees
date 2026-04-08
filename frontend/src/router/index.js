import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import SignUp from '../views/SignUp.vue'
import ProfileSetup from '../views/ProfileSetup.vue'
import PeopleMap from '../views/PeopleMap.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/signup',
    name: 'Signup',
    component: SignUp
  },
  {
    path: '/profile/:userId?',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile-setup',
    name: 'ProfileSetup',
    component: ProfileSetup,
    meta: { requiresAuth: true }
  },
  {
    path: '/map',
    name: 'PeopleMap',
    component: PeopleMap,
    //meta: { requiresAuth: true }
  },
  {
    path: '/friends/:userId?',
    name: 'Friends',
    component: () => import('../views/Friends.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/match',
    name: 'Match',
    component: () => import('../views/Match.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard - runs before every route change
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('supabase_token')
  
  // If route requires auth and user isn't logged in, redirect to login
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
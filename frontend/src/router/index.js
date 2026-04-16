import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import SignUp from '../views/SignUp.vue'
import ProfileSetup from '../views/ProfileSetup.vue'
import PeopleMap from '../views/PeopleMap.vue'
import Admin from '../views/Admin.vue'
import { supabase } from '../lib/supabase'

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
    meta: { requiresAuth: true }
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
  },
  {
    path: '/admin',
    name: 'Admin',
    component: Admin,
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard - checks Supabase session (handles token refresh automatically)
router.beforeEach(async (to, from, next) => {
  if (!to.meta.requiresAuth) return next()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) {
    next('/login')
  } else if (!to.meta.requiresAdmin) {
    next()
  } else {
    const { data: admin_status } = await supabase.rpc('is_admin')
    if(!admin_status) {
      next('/')
    } else {
      next()
    }
  }
})

export default router
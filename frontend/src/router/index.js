import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import SignUp from '../views/SignUp.vue'

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
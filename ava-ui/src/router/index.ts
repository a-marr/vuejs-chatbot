import { createRouter, createWebHistory } from 'vue-router'
import LoginComponent from '@/components/LoginComponent.vue'
import ChatComponent from '@/components/ChatComponent.vue'
import { Amplify } from 'aws-amplify'
import { getCurrentUser } from 'aws-amplify/auth';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'login',
      component: LoginComponent
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatComponent,
      meta: { requiresAuth: true }
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})



router.beforeEach(async (to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    try {
      await getCurrentUser()
      next()
    } catch {
      next('/')
    }
  } else {
    next()
  }
})

export default router

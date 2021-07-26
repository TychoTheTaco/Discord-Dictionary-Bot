import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Statistics from "@/views/Statistics";

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/statistics',
    name: 'Statistics',
    component: Statistics
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router

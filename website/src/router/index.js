import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Statistics from "@/views/Statistics";
import Documentation from "@/views/Documentation";

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
  },
  {
    path: '/documentation',
    name: 'Documentation',
    component: Documentation
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router

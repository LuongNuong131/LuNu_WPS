import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../components/layout/MainLayout.vue'
import HomeView from '../views/HomeView.vue'
import ToolView from '../views/ToolView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: HomeView
        },
        {
          path: 'tools/:slug',
          name: 'tool',
          component: ToolView
        }
      ]
    }
  ]
})

export default router
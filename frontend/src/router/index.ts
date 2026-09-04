import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../components/layout/MainLayout.vue'
import HomeView from '../views/HomeView.vue'
import ToolView from '../views/ToolView.vue'
import DashboardView from '../views/DashboardView.vue'
import PricingView from '../views/PricingView.vue'

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
        },
        {
          path: 'dashboard',
          name: 'dashboard',
          component: DashboardView
        },
        {
          path: 'pricing',
          name: 'pricing',
          component: PricingView
        }
      ]
    }
  ]
})

export default router
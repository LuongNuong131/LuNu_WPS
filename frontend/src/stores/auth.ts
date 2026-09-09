import { computed, ref } from 'vue'
import api from '../services/api'

const token = ref(localStorage.getItem('access_token') || '')
const user = ref<{ id: string; username: string } | null>(JSON.parse(localStorage.getItem('auth_user') || 'null'))

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(token.value))
  function setSession(payload: { access_token: string; user: { id: string; username: string } }) {
    token.value = payload.access_token
    user.value = payload.user
    localStorage.setItem('access_token', payload.access_token)
    localStorage.setItem('auth_user', JSON.stringify(payload.user))
  }
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('auth_user')
  }
  return { token, user, isAuthenticated, setSession, logout }
}

api.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem('access_token')
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

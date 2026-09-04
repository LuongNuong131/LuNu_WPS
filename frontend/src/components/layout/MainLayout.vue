<template>
  <div class="min-h-screen flex flex-col bg-[#f7f9fc] text-slate-900">
    <header class="sticky top-0 z-30 border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
      <div class="mx-auto flex h-[72px] w-full max-w-7xl items-center justify-between px-5 sm:px-8">
        <router-link to="/" class="flex items-center gap-3" aria-label="OfficeFlow home">
          <span class="brand-mark"><span>O</span></span>
          <span class="text-[17px] font-bold tracking-[-0.02em] text-slate-950">OfficeFlow</span>
        </router-link>

        <nav class="hidden items-center gap-1 md:flex" aria-label="Main navigation">
          <router-link v-for="item in navItems" :key="item.label" :to="item.to" class="nav-link">
            {{ item.label }}
          </router-link>
        </nav>

        <div class="flex items-center gap-2">
          <router-link to="/dashboard" class="hidden rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 sm:block">
          Dashboard
        </router-link>
          <router-link to="/#tools" class="primary-button hidden sm:inline-flex">Get started <ArrowUpRight :size="16" /></router-link>
          <button class="icon-button md:hidden" aria-label="Open navigation" @click="mobileOpen = !mobileOpen">
            <Menu v-if="!mobileOpen" :size="21" />
            <X v-else :size="21" />
          </button>
        </div>
      </div>

      <div v-if="mobileOpen" class="border-t border-slate-100 bg-white px-5 py-4 md:hidden">
        <nav class="flex flex-col gap-1" aria-label="Mobile navigation">
          <router-link v-for="item in navItems" :key="item.label" :to="item.to" class="mobile-nav-link" @click="mobileOpen = false">
            {{ item.label }}
          </router-link>
          <router-link to="/#tools" class="primary-button mt-3 justify-center" @click="mobileOpen = false">Get started <ArrowUpRight :size="16" /></router-link>
        </nav>
      </div>
    </header>

    <main class="flex-1"><router-view /></main>

    <footer class="border-t border-slate-200 bg-white">
      <div class="mx-auto flex w-full max-w-7xl flex-col gap-4 px-5 py-7 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div class="flex items-center gap-2 font-semibold text-slate-700"><span class="brand-mark brand-mark--small"><span>O</span></span> OfficeFlow</div>
        <p>Everything you need for documents, in one place.</p>
        <p>© {{ new Date().getFullYear() }} OfficeFlow</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ArrowUpRight, Menu, X } from '@lucide/vue'

const mobileOpen = ref(false)
const navItems = [
  { label: 'Tools', to: '/#tools' },
  { label: 'PDF', to: '/#pdf-tools' },
  { label: 'Office', to: '/#office-tools' },
  { label: 'Images', to: '/#image-tools' },
  { label: 'Dashboard', to: '/dashboard' },
  { label: 'Pricing', to: '/pricing' },
]
</script>

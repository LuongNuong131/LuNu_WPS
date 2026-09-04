<template>
  <div>
    <section class="hero-shell">
      <div class="hero-grid" />
      <div class="mx-auto grid w-full max-w-7xl items-center gap-14 px-5 pb-20 pt-16 sm:px-8 lg:grid-cols-[1.05fr_.95fr] lg:pb-28 lg:pt-24">
        <div class="relative z-10">
          <div class="eyebrow"><span class="status-dot" /> Document work, without the busywork</div>
          <h1 class="mt-6 max-w-3xl text-5xl font-bold leading-[1.03] tracking-[-0.055em] text-slate-950 sm:text-6xl lg:text-[76px]">
            Every document.<br /><span class="text-cobalt">One clear workspace.</span>
          </h1>
          <p class="mt-7 max-w-xl text-lg leading-8 text-slate-600 sm:text-xl">
            Convert, organize, and prepare your files in a focused workspace built for speed, clarity, and control.
          </p>
          <div class="mt-9 flex flex-col gap-3 sm:flex-row">
            <a href="#tools" class="primary-button justify-center">Explore tools <ArrowDown :size="17" /></a>
            <a href="#how-it-works" class="secondary-button justify-center">See how it works <Play :size="16" fill="currentColor" /></a>
          </div>
          <div class="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-slate-500">
            <span class="inline-flex items-center gap-2"><ShieldCheck :size="16" class="text-cobalt" /> Files stay private</span>
            <span class="inline-flex items-center gap-2"><Zap :size="16" class="text-amber-500" /> Fast processing</span>
            <span class="inline-flex items-center gap-2"><Check :size="16" class="text-emerald-500" /> No install required</span>
          </div>
        </div>

        <div class="relative z-10">
          <div class="workspace-card">
            <div class="flex items-center justify-between border-b border-slate-100 pb-4">
              <div><p class="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400">Quick workspace</p><p class="mt-1 text-sm font-semibold text-slate-800">Start with a document</p></div>
              <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-600">READY</span>
            </div>
            <div class="mt-5 rounded-2xl border-2 border-dashed border-cobalt/25 bg-[#f7faff] p-7 text-center transition hover:border-cobalt/50">
              <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-cobalt shadow-[0_8px_25px_rgba(40,93,255,.12)]"><UploadCloud :size="27" /></div>
              <p class="mt-4 font-semibold text-slate-800">Drop a file here to get started</p>
              <p class="mt-1 text-sm text-slate-500">or choose a tool below</p>
              <a href="#tools" class="mt-5 inline-flex items-center gap-2 text-sm font-bold text-cobalt hover:underline">Browse supported tools <ArrowRight :size="15" /></a>
            </div>
            <div class="mt-5 grid grid-cols-3 gap-2 text-center text-xs font-semibold text-slate-500">
              <div class="rounded-xl bg-slate-50 p-3"><FileText :size="18" class="mx-auto mb-1 text-slate-400" />PDF</div>
              <div class="rounded-xl bg-slate-50 p-3"><Table2 :size="18" class="mx-auto mb-1 text-slate-400" />Tables</div>
              <div class="rounded-xl bg-slate-50 p-3"><Layers3 :size="18" class="mx-auto mb-1 text-slate-400" />Pages</div>
            </div>
          </div>
          <div class="absolute -bottom-5 -left-5 hidden rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-[0_16px_40px_rgba(15,23,42,.1)] sm:flex sm:items-center sm:gap-3"><span class="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-500"><Check :size="18" /></span><div><p class="text-xs font-bold text-slate-800">Simple by design</p><p class="text-[11px] text-slate-500">One flow from upload to result</p></div></div>
        </div>
      </div>
    </section>

    <section id="tools" class="mx-auto w-full max-w-7xl px-5 py-20 sm:px-8 lg:py-24">
      <div class="flex flex-col justify-between gap-6 md:flex-row md:items-end">
        <div><p class="section-kicker">Tool library</p><h2 class="section-title">Find the right tool, fast.</h2><p class="section-copy">Start with what you need. Every available tool below connects to a real processing workflow.</p></div>
        <div class="relative w-full md:w-72"><Search :size="18" class="absolute left-3.5 top-3.5 text-slate-400" /><input v-model="search" class="search-input" placeholder="What do you want to do?" aria-label="Search tools" /></div>
      </div>

      <div class="mt-9 flex gap-2 overflow-x-auto pb-2" role="tablist" aria-label="Tool categories">
        <button v-for="category in categories" :key="category" class="category-pill" :class="{ 'category-pill--active': activeCategory === category }" @click="activeCategory = category">{{ category }}</button>
      </div>

      <div v-if="filteredTools.length" class="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <router-link v-for="tool in filteredTools" :key="tool.slug" :to="`/tools/${tool.slug}`" class="tool-card" :class="{ 'tool-card--soon': !tool.available }">
          <div class="flex items-start justify-between"><span class="tool-icon"><component :is="tool.icon" :size="21" /></span><span v-if="tool.badge" class="soon-badge">{{ tool.badge }}</span><span v-else-if="tool.popular" class="popular-badge">Popular</span></div>
          <div class="mt-5 flex items-start justify-between gap-3"><div><p class="text-base font-bold text-slate-900">{{ tool.name }}</p><p class="mt-2 text-sm leading-6 text-slate-500">{{ tool.description }}</p></div><ArrowUpRight :size="18" class="mt-0.5 shrink-0 text-slate-300 transition group-hover:text-cobalt" /></div>
          <div class="mt-5 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-400"><span>{{ tool.input }}</span><ArrowRight :size="13" /><span>{{ tool.output }}</span></div>
        </router-link>
      </div>
      <div v-else class="empty-state"><SearchX :size="24" class="text-slate-400" /><p class="mt-3 font-semibold text-slate-700">No tools match that search.</p><button class="mt-2 text-sm font-bold text-cobalt" @click="search = ''; activeCategory = 'All'">Clear filters</button></div>
    </section>

    <section id="how-it-works" class="border-y border-slate-200 bg-white">
      <div class="mx-auto w-full max-w-7xl px-5 py-20 sm:px-8 lg:py-24"><div class="max-w-2xl"><p class="section-kicker">How it works</p><h2 class="section-title">A calmer path from file to finished.</h2></div><div class="mt-12 grid gap-4 md:grid-cols-3"><div v-for="(step, index) in steps" :key="step.title" class="process-step"><span class="step-number">0{{ index + 1 }}</span><component :is="step.icon" :size="22" class="text-cobalt" /><h3 class="mt-5 text-lg font-bold text-slate-900">{{ step.title }}</h3><p class="mt-2 text-sm leading-6 text-slate-500">{{ step.description }}</p></div></div></div>
    </section>

    <section id="pricing" class="mx-auto w-full max-w-7xl px-5 py-16 sm:px-8"><div class="flex flex-col items-start justify-between gap-5 rounded-3xl bg-slate-950 px-7 py-9 text-white sm:flex-row sm:items-center sm:px-10"><div><p class="text-sm font-bold uppercase tracking-[0.14em] text-cobalt-200">Built for the next step</p><h2 class="mt-2 text-2xl font-bold tracking-tight">More document workflows are on the way.</h2><p class="mt-2 max-w-xl text-sm leading-6 text-slate-300">The MVP keeps the core flow focused. OCR, office conversion, history, and team features can be added without changing the workspace model.</p></div><a href="#tools" class="secondary-button whitespace-nowrap border-white/20 bg-white text-slate-900 hover:bg-slate-100">Explore MVP tools <ArrowRight :size="16" /></a></div></section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowDown, ArrowRight, ArrowUpRight, Check, Download, FileText, Layers3, Play, Search, SearchX, ShieldCheck, Table2, UploadCloud, Zap } from '@lucide/vue'
import { categories, tools } from '../data/tools'

const search = ref('')
const activeCategory = ref<(typeof categories)[number]>('All')
const filteredTools = computed(() => tools.filter((tool) => {
  const matchesCategory = activeCategory.value === 'All' || tool.category === activeCategory.value
  const query = search.value.trim().toLowerCase()
  return matchesCategory && (!query || `${tool.name} ${tool.description} ${tool.category}`.toLowerCase().includes(query))
}))
const steps = [
  { title: 'Choose a workflow', description: 'Pick a focused tool with clear input and output formats.', icon: Search },
  { title: 'Upload securely', description: 'Drop your file or browse from any device with accessible controls.', icon: UploadCloud },
  { title: 'Download the result', description: 'Track processing status and download your finished document.', icon: Download },
]

</script>

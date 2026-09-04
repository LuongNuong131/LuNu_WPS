<template>
  <div class="mx-auto w-full max-w-6xl px-5 py-14 sm:px-8 lg:py-20">
    <div class="mx-auto max-w-2xl text-center">
      <p class="section-kicker">Simple plans</p>
      <h1 class="mt-3 text-5xl font-bold tracking-[-0.05em] text-slate-950">Choose your pace.</h1>
      <p class="mt-5 text-lg leading-8 text-slate-500">Start free, then upgrade when document work becomes part of your everyday workflow.</p>
    </div>
    <div class="mt-12 grid gap-5 lg:grid-cols-3">
      <div v-for="plan in plans" :key="plan.name" class="relative rounded-3xl border p-7" :class="plan.featured ? 'border-[#285dff] bg-slate-950 text-white shadow-[0_25px_60px_rgba(40,93,255,.18)]' : 'border-slate-200 bg-white'">
        <span v-if="plan.featured" class="absolute right-6 top-6 rounded-full bg-[#285dff] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-white">Most popular</span>
        <p class="text-sm font-bold" :class="plan.featured ? 'text-blue-200' : 'text-slate-500'">{{ plan.name }}</p>
        <p class="mt-5 text-4xl font-bold">{{ plan.price }}<span class="text-sm font-medium text-slate-400">{{ plan.period }}</span></p>
        <p class="mt-4 min-h-12 text-sm leading-6" :class="plan.featured ? 'text-slate-300' : 'text-slate-500'">{{ plan.description }}</p>
        <router-link v-if="plan.name === 'Free'" to="/#tools" class="mt-7 flex w-full justify-center rounded-xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50">{{ plan.cta }}</router-link>
        <button v-else type="button" class="mt-7 w-full rounded-xl px-5 py-3 text-sm font-bold transition" :class="plan.featured ? 'bg-white text-slate-950 hover:bg-slate-100' : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'" @click="selectedPlan = plan.name">{{ plan.cta }}</button>
        <div class="mt-8 border-t pt-6" :class="plan.featured ? 'border-white/10' : 'border-slate-100'"><p v-for="feature in plan.features" :key="feature" class="flex gap-3 py-2 text-sm"><Check :size="16" class="mt-0.5 shrink-0 text-emerald-400" />{{ feature }}</p></div>
      </div>
    </div>
    <p v-if="selectedPlan" class="mx-auto mt-7 max-w-md rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-center text-sm font-semibold text-cobalt">{{ selectedPlan }} billing will be available after authentication and payment integration are connected.</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Check } from '@lucide/vue'

const selectedPlan = ref('')
const plans = [
  { name: 'Free', price: '$0', period: ' / forever', description: 'For occasional document tasks and trying the core workflow.', cta: 'Start for free', features: ['10 conversions / month', '25 MB per file', 'Core PDF tools', 'Downloadable results'] },
  { name: 'Pro', price: '$12', period: ' / month', description: 'For individuals who work with documents every week.', cta: 'Choose Pro', featured: true, features: ['Unlimited core conversions', '100 MB per file', 'Batch processing', 'OCR and advanced tools'] },
  { name: 'Business', price: '$39', period: ' / seat / month', description: 'For teams that need collaboration and an API-ready workspace.', cta: 'Talk to us', features: ['Everything in Pro', '1 GB per file', 'Team workspace', 'API access and usage limits'] },
]
</script>

<template>
  <section v-if="tasks.length" class="mt-6 rounded-2xl border border-amber-200 bg-amber-50/70 p-5">
    <div class="flex items-start justify-between gap-4"><div><p class="text-xs font-bold uppercase tracking-[.14em] text-amber-700">Human review</p><h3 class="mt-1 text-lg font-bold text-slate-900">{{ tasks.length }} value{{ tasks.length > 1 ? 's' : '' }} need checking</h3><p class="mt-1 text-sm text-amber-800">Raw extraction is preserved. Corrections are stored separately.</p></div><span class="rounded-full bg-amber-200 px-3 py-1 text-xs font-bold text-amber-900">{{ remaining }} open</span></div>
    <div v-for="(task, index) in tasks" :key="task.task_id || index" class="mt-4 rounded-xl border border-amber-200 bg-white p-4">
      <div class="flex flex-wrap items-center justify-between gap-2"><span class="text-xs font-bold uppercase tracking-wider text-slate-500">{{ task.field }}</span><span class="text-xs font-bold" :class="(task.confidence || 0) < .5 ? 'text-rose-600' : 'text-amber-600'">Confidence {{ Math.round((task.confidence || 0) * 100) }}%</span></div>
      <p class="mt-2 text-sm text-slate-500">Raw value</p><code class="mt-1 block rounded-lg bg-slate-100 p-2 text-sm text-slate-800">{{ task.value || '—' }}</code>
      <input v-model="drafts[index]" class="mt-3 h-10 w-full rounded-lg border border-slate-200 px-3 text-sm focus:border-cobalt focus:outline-none" :placeholder="task.value || 'Enter verified value'" />
      <div class="mt-3 flex flex-wrap items-center justify-between gap-3"><p class="text-xs text-slate-500">{{ task.reason }} · {{ task.evidence?.length || 0 }} evidence item(s)</p><button class="rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white disabled:opacity-40" :disabled="!drafts[index]?.trim()" @click="confirm(index)">{{ confirmed[index] ? 'Saved separately' : 'Mark verified' }}</button></div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
type ReviewTask = { task_id?: string; field: string; value?: string; confidence?: number; reason?: string; evidence?: unknown[] }
const props = defineProps<{ tasks: ReviewTask[] }>()
const emit = defineEmits<{ verified: [payload: { task: ReviewTask; verifiedValue: string }] }>()
const drafts = reactive<Record<number, string>>({})
const confirmed = reactive<Record<number, boolean>>({})
const remaining = computed(() => props.tasks.filter((_, index) => !confirmed[index]).length)
function confirm(index: number) { confirmed[index] = true; emit('verified', { task: props.tasks[index], verifiedValue: drafts[index].trim() }) }
</script>

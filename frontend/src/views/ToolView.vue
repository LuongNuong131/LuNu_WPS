<template>
  <div class="mx-auto w-full max-w-6xl px-5 py-10 sm:px-8 lg:py-16">
    <div class="mb-8 flex items-center gap-2 text-sm text-slate-400"><router-link to="/" class="hover:text-cobalt">Tools</router-link><ChevronRight :size="15" /><span class="font-medium text-slate-600">{{ tool?.name || 'Tool' }}</span></div>
    <div v-if="!tool" class="rounded-3xl border border-slate-200 bg-white p-12 text-center"><h1 class="text-2xl font-bold">Tool not found</h1><router-link to="/" class="primary-button mx-auto mt-6">Back home</router-link></div>
    <div v-else class="grid gap-8 lg:grid-cols-[.75fr_1.25fr] lg:items-start">
      <aside><span class="tool-icon tool-icon--large"><component :is="tool.icon" :size="26" /></span><p class="section-kicker mt-6">{{ tool.category }} tool</p><h1 class="mt-2 text-4xl font-bold tracking-[-0.04em] text-slate-950">{{ tool.name }}</h1><p class="mt-4 leading-7 text-slate-500">{{ tool.description }}</p><div class="mt-7 grid grid-cols-2 gap-3"><div class="meta-card"><span>Input</span><strong>{{ tool.input }}</strong></div><div class="meta-card"><span>Output</span><strong>{{ tool.output }}</strong></div></div><div class="mt-7 flex items-start gap-3 rounded-2xl bg-blue-50/70 p-4 text-sm leading-6 text-slate-600"><ShieldCheck :size="18" class="mt-0.5 shrink-0 text-cobalt" /><p>Files are processed for this job only. Completed jobs are remembered locally on this device.</p></div></aside>
      <section class="workspace-panel">
        <div class="flex items-center justify-between border-b border-slate-100 pb-5"><div><p class="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">Workspace</p><h2 class="mt-1 text-lg font-bold text-slate-900">Upload and process</h2></div><span class="status-chip"><span class="status-dot" /> Ready</span></div>
        <div v-if="status === 'IDLE'" class="pt-6">
          <div v-if="tool.options?.includes('degrees')" class="mb-5 rounded-2xl border border-slate-200 bg-slate-50 p-4"><label class="block text-xs font-bold uppercase tracking-[.13em] text-slate-500" for="degrees">Rotation angle</label><select id="degrees" v-model="options.degrees" class="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 focus:border-cobalt focus:outline-none sm:w-56"><option value="90">90 degrees</option><option value="180">180 degrees</option><option value="270">270 degrees</option></select></div>
          <div v-if="tool.options?.includes('pages')" class="mb-5 rounded-2xl border border-slate-200 bg-slate-50 p-4"><label class="block text-xs font-bold uppercase tracking-[.13em] text-slate-500" for="pages">Page selection</label><input id="pages" v-model="options.pages" class="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 placeholder:text-slate-400 focus:border-cobalt focus:outline-none" placeholder="Example: 1, 3-5" /><p class="mt-2 text-xs text-slate-400">Use page numbers and ranges separated by commas.</p></div>
          <FileUploader :accept="acceptForTool(tool)" :multiple="allowsMultiple(tool)" @files-selected="startConversion" /><p class="mt-5 text-center text-xs text-slate-400">Supported input: {{ tool.input }} · Maximum file size: 25 MB</p>
        </div>
        <div v-else-if="status === 'UPLOADING' || status === 'PROCESSING'" class="py-16 text-center"><div class="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-cobalt-50 text-cobalt"><LoaderCircle :size="28" class="animate-spin" /></div><h3 class="mt-6 text-xl font-bold text-slate-900">{{ status === 'UPLOADING' ? 'Uploading your files' : 'Processing your document' }}</h3><p class="mt-2 text-sm text-slate-500">{{ stageMessage }}</p><div class="mx-auto mt-8 max-w-sm"><div class="mb-2 flex justify-between text-xs font-bold text-slate-500"><span>{{ status === 'UPLOADING' ? 'Uploading' : 'Working' }}</span><span>{{ progress }}%</span></div><div class="h-2 overflow-hidden rounded-full bg-slate-100"><div class="h-full rounded-full bg-cobalt transition-all duration-500" :style="{ width: `${progress}%` }" /></div></div></div>
        <div v-else-if="status === 'SUCCESS'" class="py-12 text-center"><div class="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-500"><CheckCircle2 :size="30" /></div><h3 class="mt-6 text-2xl font-bold text-slate-900">Your result is ready</h3><p class="mt-2 text-slate-500">{{ outputFilename || `OfficeFlow_${tool.output}` }}</p><div class="mt-8 flex flex-col justify-center gap-3 sm:flex-row"><button class="primary-button justify-center" @click="downloadFile">Download {{ tool.output }} <Download :size="16" /></button><button class="secondary-button justify-center" @click="resetTool">Process another file <RotateCcw :size="16" /></button></div></div>
        <div v-else class="py-12 text-center"><div class="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-rose-50 text-rose-500"><AlertTriangle :size="29" /></div><h3 class="mt-6 text-2xl font-bold text-slate-900">We couldn't finish that job</h3><p class="mx-auto mt-2 max-w-md text-sm leading-6 text-rose-600">{{ errorMessage }}</p><button class="secondary-button mx-auto mt-8 justify-center" @click="resetTool">Try again <RotateCcw :size="16" /></button></div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { AlertTriangle, CheckCircle2, ChevronRight, Download, LoaderCircle, RotateCcw, ShieldCheck } from '@lucide/vue'
import api from '../services/api'
import FileUploader from '../components/upload/FileUploader.vue'
import { allowsMultiple, acceptForTool, getTool } from '../data/tools'
import { saveHistory } from '../data/history'

const route = useRoute()
const tool = computed(() => getTool(route.params.slug as string))
const status = ref<'IDLE' | 'UPLOADING' | 'PROCESSING' | 'SUCCESS' | 'FAILED'>('IDLE')
const progress = ref(0)
const currentJobId = ref('')
const outputFilename = ref('')
const errorMessage = ref('')
const options = reactive<{ degrees: string; pages: string }>({ degrees: '90', pages: '' })
let pollingInterval: number | null = null
const stageMessage = computed(() => status.value === 'UPLOADING' ? 'Preparing your files for the processing pipeline.' : `Running ${tool.value?.name || 'document'} and validating the output.`)

async function startConversion(files: File[]) {
  if (!files.length || !tool.value) return
  if ((tool.value.options?.includes('pages') && !options.pages.trim())) { errorMessage.value = 'Please enter the pages you want to process.'; status.value = 'FAILED'; return }
  status.value = 'UPLOADING'; progress.value = 12; errorMessage.value = ''
  const formData = new FormData(); formData.append('tool_slug', tool.value.slug); formData.append('options_json', JSON.stringify(options)); files.forEach((file) => formData.append('files', file))
  try { const response = await api.post('/jobs/', formData, { headers: { 'Content-Type': 'multipart/form-data' } }); currentJobId.value = response.data.id; status.value = 'PROCESSING'; progress.value = 35; startPolling() }
  catch (error: any) { status.value = 'FAILED'; errorMessage.value = error.response?.data?.detail || 'Upload failed. Please check the server and try again.' }
}
function startPolling() { if (pollingInterval) window.clearInterval(pollingInterval); pollingInterval = window.setInterval(async () => { try { const response = await api.get(`/jobs/${currentJobId.value}`); progress.value = response.data.progress; if (response.data.status === 'SUCCESS') { status.value = 'SUCCESS'; outputFilename.value = response.data.output_filename || ''; saveHistory({ id: currentJobId.value, name: response.data.original_filename, tool: tool.value?.name || 'Document tool', output: response.data.output_filename || '', completedAt: new Date().toISOString() }); window.clearInterval(pollingInterval!) } if (response.data.status === 'FAILED') { status.value = 'FAILED'; errorMessage.value = response.data.error_message || 'The processing job failed.'; window.clearInterval(pollingInterval!) } } catch { status.value = 'FAILED'; errorMessage.value = 'The connection was interrupted. Please try again.'; window.clearInterval(pollingInterval!) } }, 1200) }
function downloadFile() { if (currentJobId.value) window.location.href = `${api.defaults.baseURL}/jobs/${currentJobId.value}/download` }
function resetTool() { if (pollingInterval) window.clearInterval(pollingInterval); status.value = 'IDLE'; progress.value = 0; currentJobId.value = ''; outputFilename.value = ''; errorMessage.value = '' }
onUnmounted(() => { if (pollingInterval) window.clearInterval(pollingInterval) })
</script>

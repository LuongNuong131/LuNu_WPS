<template>
  <div>
    <div class="upload-zone" :class="{ 'upload-zone--active': isDragging, 'upload-zone--error': errorMessage }" @dragenter.prevent="isDragging = true" @dragover.prevent="isDragging = true" @dragleave.prevent="isDragging = false" @drop.prevent="handleDrop">
      <input ref="fileInput" type="file" class="sr-only" :accept="accept" :multiple="multiple" @change="handleFileSelect" />
      <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-cobalt-50 text-cobalt"><UploadCloud :size="27" /></div>
      <h3 class="mt-5 text-lg font-bold text-slate-900">{{ multiple ? 'Drop your files here' : 'Drop your file here' }}</h3>
      <p class="mt-2 text-sm text-slate-500">or <button class="font-bold text-cobalt underline-offset-4 hover:underline" type="button" @click="openPicker">browse from your device</button></p>
      <p class="mt-4 text-xs font-medium text-slate-400">{{ formatHint }} · Up to {{ maxSizeLabel }} per file</p>
    </div>
    <p v-if="errorMessage" class="mt-3 flex items-center gap-2 text-sm font-medium text-rose-600" role="alert"><AlertCircle :size="16" />{{ errorMessage }}</p>

    <div v-if="selectedFiles.length" class="mt-5 rounded-2xl border border-slate-200 bg-white p-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3"><p class="text-sm font-bold text-slate-800">Selected files <span class="text-slate-400">({{ selectedFiles.length }})</span></p><button type="button" class="text-xs font-bold text-slate-400 hover:text-rose-500" @click="clearFiles">Clear all</button></div>
      <ul class="mt-2 divide-y divide-slate-100"><li v-for="(file, index) in selectedFiles" :key="`${file.name}-${file.lastModified}`" class="flex items-center gap-3 py-3"><span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500"><FileText :size="17" /></span><span class="min-w-0 flex-1"><span class="block truncate text-sm font-semibold text-slate-700">{{ file.name }}</span><span class="block text-xs text-slate-400">{{ formatSize(file.size) }}</span></span><button type="button" class="icon-button icon-button--small text-slate-400 hover:text-rose-500" :aria-label="`Remove ${file.name}`" @click="removeFile(index)"><X :size="16" /></button></li></ul>
      <button type="button" class="primary-button mt-4 w-full justify-center" @click="submitFiles">Continue with {{ selectedFiles.length }} {{ selectedFiles.length === 1 ? 'file' : 'files' }} <ArrowRight :size="16" /></button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { AlertCircle, ArrowRight, FileText, UploadCloud, X } from '@lucide/vue'

const props = withDefaults(defineProps<{ accept?: string; multiple?: boolean; maxSizeMb?: number }>(), { accept: '.pdf', multiple: false, maxSizeMb: 25 })
const emit = defineEmits<{ (event: 'files-selected', files: File[]): void }>()
const isDragging = ref(false)
const selectedFiles = ref<File[]>([])
const errorMessage = ref('')
const fileInput = ref<HTMLInputElement>()
const formatHint = computed(() => props.accept.replaceAll('.', '').replaceAll(',', ', ').toUpperCase())
const maxSizeLabel = computed(() => `${props.maxSizeMb} MB`)

function openPicker() { fileInput.value?.click() }
function handleDrop(event: DragEvent) { isDragging.value = false; addFiles(event.dataTransfer?.files) }
function handleFileSelect(event: Event) { addFiles((event.target as HTMLInputElement).files); (event.target as HTMLInputElement).value = '' }
function addFiles(files?: FileList | null) {
  errorMessage.value = ''
  if (!files?.length) return
  const incoming = Array.from(files)
  const tooLarge = incoming.find((file) => file.size > props.maxSizeMb * 1024 * 1024)
  if (tooLarge) { errorMessage.value = `${tooLarge.name} is larger than ${props.maxSizeMb} MB.`; return }
  const accepted = props.multiple ? incoming : [incoming[0]]
  selectedFiles.value = props.multiple ? [...selectedFiles.value, ...accepted].filter((file, index, all) => all.findIndex((item) => item.name === file.name && item.size === file.size) === index) : accepted
}
function removeFile(index: number) { selectedFiles.value.splice(index, 1) }
function clearFiles() { selectedFiles.value = []; errorMessage.value = '' }
function submitFiles() { if (selectedFiles.value.length) emit('files-selected', selectedFiles.value) }
function formatSize(bytes: number) { if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`; return `${(bytes / 1024 / 1024).toFixed(1)} MB` }
</script>

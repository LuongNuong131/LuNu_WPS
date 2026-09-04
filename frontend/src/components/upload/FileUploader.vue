<template>
  <div>
    <div 
      class="relative border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 mb-6"
      :class="[isDragging ? 'border-primary bg-blue-50' : 'border-gray-300 bg-gray-50 hover:border-primary']"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <div class="flex flex-col items-center justify-center pointer-events-none">
        <svg class="w-16 h-16 text-primary mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
        </svg>
        <h3 class="text-xl font-semibold text-gray-700 mb-2">
          {{ multiple ? 'Drag & Drop your files here' : 'Drag & Drop your file here' }}
        </h3>
        <p class="text-sm text-gray-500 mb-6">or click to browse from your computer</p>
      </div>
      
      <input 
        type="file" 
        class="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
        :accept="accept"
        :multiple="multiple"
        @change="handleFileSelect"
      />
    </div>

    <!-- Hiển thị danh sách file đã chọn -->
    <div v-if="selectedFiles.length > 0" class="text-left bg-white border border-gray-200 rounded-lg p-4 shadow-sm mb-6">
      <h4 class="font-semibold text-gray-700 mb-3 border-b pb-2">Selected Files ({{ selectedFiles.length }})</h4>
      <ul class="space-y-2 max-h-48 overflow-y-auto">
        <li v-for="(file, index) in selectedFiles" :key="index" class="flex items-center justify-between text-sm text-gray-600 bg-gray-50 p-2 rounded">
          <span class="truncate pr-4">{{ file.name }}</span>
          <button @click="removeFile(index)" class="text-red-500 hover:text-red-700 font-bold px-2">&times;</button>
        </li>
      </ul>
    </div>

    <button 
      v-if="selectedFiles.length > 0" 
      @click="submitFiles" 
      class="w-full py-4 bg-primary text-white font-bold text-lg rounded-xl shadow-md hover:bg-blue-700 transition"
    >
      Convert {{ selectedFiles.length > 1 ? 'Files' : 'File' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps({
  accept: { type: String, default: '.pdf' },
  multiple: { type: Boolean, default: false }
});

const emit = defineEmits(['files-selected']);
const isDragging = ref(false);
const selectedFiles = ref<File[]>([]);

const handleDrop = (e: DragEvent) => {
  isDragging.value = false;
  addFiles(e.dataTransfer?.files);
};

const handleFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement;
  addFiles(target.files);
  target.value = ''; // Reset input
};

const addFiles = (files: FileList | null | undefined) => {
  if (!files) return;
  const newFiles = Array.from(files);
  if (props.multiple) {
    selectedFiles.value.push(...newFiles);
  } else {
    selectedFiles.value = [newFiles[0]]; // Ghi đè nếu chỉ chọn 1 file
  }
};

const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1);
};

const submitFiles = () => {
  emit('files-selected', selectedFiles.value);
};
</script>
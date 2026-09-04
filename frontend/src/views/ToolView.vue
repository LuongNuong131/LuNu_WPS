<template>
  <div class="max-w-4xl mx-auto px-4 py-12">
    <div class="text-center mb-10">
      <h1 class="text-3xl font-bold text-gray-900 capitalize">{{ currentToolName }}</h1>
      <p class="text-gray-500 mt-2">Upload your files and let OfficeFlow do the magic.</p>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
      <FileUploader 
        v-if="status === 'IDLE'" 
        accept=".pdf" 
        :multiple="isMultiple"
        @files-selected="startConversion" 
      />

      <!-- Trạng thái Uploading / Processing -->
      <div v-else-if="status === 'UPLOADING' || status === 'PROCESSING'" class="text-center py-12">
        <svg class="w-12 h-12 text-primary animate-spin mx-auto mb-4" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <h3 class="text-xl font-bold text-gray-800 mb-2">
          {{ status === 'UPLOADING' ? 'Uploading...' : 'Processing...' }}
        </h3>
        <div class="w-64 mx-auto bg-gray-200 rounded-full h-2.5 mt-4">
          <div class="bg-primary h-2.5 rounded-full transition-all duration-300" :style="{ width: progress + '%' }"></div>
        </div>
        <p class="text-sm text-gray-500 mt-2">{{ progress }}%</p>
      </div>

      <!-- Thành công -->
      <div v-else-if="status === 'SUCCESS'" class="text-center py-12">
        <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
          </svg>
        </div>
        <h3 class="text-2xl font-bold text-gray-800 mb-2">Completed!</h3>
        <p class="text-gray-500 mb-8">Your file is ready.</p>
        
        <div class="flex justify-center gap-4">
          <button @click="downloadFile" class="px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-blue-700 transition">
            Download Result
          </button>
          <button @click="resetTool" class="px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition">
            Start Over
          </button>
        </div>
      </div>

      <!-- Thất bại -->
      <div v-else-if="status === 'FAILED'" class="text-center py-12">
        <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </div>
        <h3 class="text-2xl font-bold text-gray-800 mb-2">Error</h3>
        <p class="text-red-500 mb-8">{{ errorMessage }}</p>
        <button @click="resetTool" class="px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition">
          Try Again
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import api from '../services/api';
import FileUploader from '../components/upload/FileUploader.vue';

const route = useRoute();
const toolSlug = route.params.slug as string;
const currentToolName = computed(() => toolSlug.replace(/-/g, ' '));
const isMultiple = computed(() => toolSlug === 'merge-pdf'); // Chỉ Merge PDF là bật chế độ Multiple

const status = ref<'IDLE' | 'UPLOADING' | 'PROCESSING' | 'SUCCESS' | 'FAILED'>('IDLE');
const progress = ref(0);
const currentJobId = ref('');
const errorMessage = ref('');
let pollingInterval: number | null = null;

const startConversion = async (files: File[]) => {
  if (files.length === 0) return;
  status.value = 'UPLOADING';
  progress.value = 10;
  
  const formData = new FormData();
  formData.append('tool_slug', toolSlug);
  // Thêm mảng file vào FormData
  files.forEach(file => {
    formData.append('files', file);
  });

  try {
    const res = await api.post('/jobs/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    
    currentJobId.value = res.data.id;
    status.value = 'PROCESSING';
    startPolling();
  } catch (error: any) {
    status.value = 'FAILED';
    errorMessage.value = error.response?.data?.detail || 'Lỗi tải file lên server.';
  }
};

const startPolling = () => {
  if (pollingInterval) clearInterval(pollingInterval);
  pollingInterval = setInterval(async () => {
    try {
      const res = await api.get(`/jobs/${currentJobId.value}`);
      progress.value = res.data.progress;
      
      if (res.data.status === 'SUCCESS') {
        status.value = 'SUCCESS';
        clearInterval(pollingInterval!);
      } else if (res.data.status === 'FAILED') {
        status.value = 'FAILED';
        errorMessage.value = res.data.error_message || 'Lỗi xử lý file.';
        clearInterval(pollingInterval!);
      }
    } catch (error) {
      status.value = 'FAILED';
      errorMessage.value = 'Mất kết nối với server.';
      clearInterval(pollingInterval!);
    }
  }, 1500) as unknown as number;
};

const downloadFile = () => {
  window.location.href = `http://127.0.0.1:8000/api/v1/jobs/${currentJobId.value}/download`;
};

const resetTool = () => {
  status.value = 'IDLE';
  progress.value = 0;
  currentJobId.value = '';
  errorMessage.value = '';
};

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval);
});
</script>
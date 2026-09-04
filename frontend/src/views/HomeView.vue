<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <div class="text-center max-w-3xl mx-auto mb-16">
      <h1 class="text-4xl md:text-5xl font-extrabold text-gray-900 mb-6">
        All Your Document Tools <br/> <span class="text-primary">In One Place</span>
      </h1>
      <p class="text-lg text-gray-600 mb-8">
        Convert, compress, edit and manage your documents online. Fast, secure, and free.
      </p>
    </div>

    <div>
      <h2 class="text-2xl font-bold text-gray-900 mb-6">Popular Tools</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <router-link 
          v-for="tool in tools" 
          :key="tool.slug"
          :to="`/tools/${tool.slug}`"
          class="bg-white p-6 rounded-xl border border-gray-200 shadow-sm hover:shadow-md hover:border-primary transition-all cursor-pointer flex items-start gap-4"
        >
          <div class="p-3 bg-blue-50 text-primary rounded-lg flex-shrink-0">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
            </svg>
          </div>
          <div>
            <h3 class="font-bold text-gray-900">{{ tool.name }}</h3>
            <p class="text-sm text-gray-500 mt-1 line-clamp-2">{{ tool.description }}</p>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const tools = ref([
  { slug: 'pdf-to-excel', name: 'PDF to Excel', description: 'Convert PDF tables into editable Excel spreadsheets.' },
  { slug: 'merge-pdf', name: 'Merge PDF', description: 'Combine multiple PDFs into one unified document.' },
  { slug: 'split-pdf', name: 'Split PDF', description: 'Extract pages from your PDF or save each page as a separate PDF (ZIP).' }
]);
</script>
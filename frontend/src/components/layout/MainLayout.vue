<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center gap-2 cursor-pointer" @click="$router.push('/')">
          <!-- Logo Placeholder -->
          <div class="w-8 h-8 bg-primary rounded flex items-center justify-center text-white font-bold">O</div>
          <span class="font-bold text-xl tracking-tight text-gray-900">OfficeFlow</span>
        </div>
        <nav class="hidden md:flex space-x-8">
          <router-link to="/" class="text-gray-600 hover:text-primary font-medium">Home</router-link>
          <a href="#" class="text-gray-600 hover:text-primary font-medium">PDF Tools</a>
          <a href="#" class="text-gray-600 hover:text-primary font-medium">Pricing</a>
        </nav>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-grow">
      <router-view />
    </main>

    <!-- Footer -->
    <footer class="bg-white border-t border-gray-200 mt-auto">
      <div class="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500 text-sm">
        &copy; 2026 OfficeFlow. All document tools in one place.
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
// Layout logic here
</script>
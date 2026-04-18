<template>
  <div class="flex items-center justify-center py-16 px-6 animate-fade-in">
    <div class="text-center max-w-sm">
      <!-- Icon container -->
      <div class="w-16 h-16 mx-auto mb-5 rounded-2xl bg-surface-800/60 border border-surface-700/40 flex items-center justify-center">
        <svg class="w-7 h-7 text-surface-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.4">
          <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
        </svg>
      </div>
      <h3 class="text-base font-semibold text-surface-300 mb-1.5">{{ title }}</h3>
      <p class="text-sm text-surface-500 leading-relaxed">{{ description }}</p>
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ icon?: string; title: string; description: string }>()
</script>

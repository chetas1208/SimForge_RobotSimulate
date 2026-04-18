<template>
  <div class="animate-pulse space-y-3">
    <div
      v-for="i in rows"
      :key="i"
      class="h-4 bg-surface-800/70 rounded-xl"
      :class="i % 3 === 0 ? 'w-3/4' : i % 2 === 0 ? 'w-5/6' : 'w-full'"
    ></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ rows?: number }>(), { rows: 4 })
</script>

<template>
  <div class="card p-5 animate-fade-in">
    <!-- Score ring + value -->
    <div class="flex items-center justify-between mb-3">
      <span class="text-4xl font-bold tabular-nums" :class="valueColor">
        {{ (score * 100).toFixed(0) }}<span class="text-xl font-semibold opacity-60">%</span>
      </span>
      <span class="badge" :class="badgeCls">{{ level }}</span>
    </div>

    <!-- Bar -->
    <div class="score-bar-track mb-3">
      <div
        class="h-full rounded-full transition-all duration-700 ease-out"
        :class="barCls"
        :style="{ width: `${score * 100}%` }"
      ></div>
    </div>

    <!-- Label -->
    <p class="text-sm font-semibold text-surface-200 leading-tight">{{ label }}</p>
    <p v-if="description" class="text-xs text-surface-500 mt-1 leading-snug">{{ description }}</p>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ label: string; score: number; description?: string }>()

const level = computed(() => {
  if (props.score < 0.3) return 'Low'
  if (props.score < 0.6) return 'Moderate'
  if (props.score < 0.8) return 'High'
  return 'Critical'
})

const valueColor = computed(() => {
  if (props.score < 0.3) return 'text-success'
  if (props.score < 0.6) return 'text-warning'
  if (props.score < 0.8) return 'text-orange-400'
  return 'text-danger'
})

const badgeCls = computed(() => {
  if (props.score < 0.3) return 'bg-success/10 text-success border border-success/20'
  if (props.score < 0.6) return 'bg-warning/10 text-warning border border-warning/20'
  if (props.score < 0.8) return 'bg-orange-500/10 text-orange-400 border border-orange-500/20'
  return 'bg-danger/10 text-danger border border-danger/20'
})

const barCls = computed(() => {
  if (props.score < 0.3) return 'bg-success'
  if (props.score < 0.6) return 'bg-warning'
  if (props.score < 0.8) return 'bg-orange-500'
  return 'bg-danger'
})
</script>

<template>
  <div class="stat-card animate-fade-in group">
    <!-- Top row: label + icon -->
    <div class="flex items-start justify-between mb-4">
      <p class="text-[11px] font-semibold text-surface-500 uppercase tracking-widest leading-none mt-1">{{ label }}</p>
      <div :class="['w-10 h-10 rounded-xl flex items-center justify-center shrink-0', iconBg]">
        <slot name="icon">
          <svg class="w-5 h-5" :class="iconColor" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
        </slot>
      </div>
    </div>

    <!-- Value -->
    <p class="text-4xl font-bold text-white tabular-nums tracking-tight leading-none">{{ value }}</p>
    <p v-if="subtitle" class="text-xs text-surface-500 mt-2 leading-snug">{{ subtitle }}</p>

    <!-- Trend -->
    <div v-if="trend !== undefined" class="mt-4 pt-4 border-t border-surface-800/50 flex items-center gap-1.5">
      <span :class="['text-xs font-semibold', trend >= 0 ? 'text-success' : 'text-danger']">
        {{ trend >= 0 ? '↑' : '↓' }} {{ Math.abs(trend) }}%
      </span>
      <span class="text-xs text-surface-600">vs last period</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  label: string
  value: string | number
  subtitle?: string
  iconBg?: string
  iconColor?: string
  trend?: number
  icon?: string
}>()

const iconBg    = computed(() => props.iconBg    ?? 'bg-forge-500/10')
const iconColor = computed(() => props.iconColor ?? 'text-forge-400')
</script>

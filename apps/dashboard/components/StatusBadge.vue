<template>
  <span :class="cls">
    <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="dotCls"></span>
    {{ label || status }}
  </span>
</template>

<script setup lang="ts">
const props = defineProps<{ status: string; label?: string }>()

const map: Record<string, { badge: string; dot: string }> = {
  queued:    { badge: 'badge-queued',    dot: 'bg-info' },
  preparing: { badge: 'badge-preparing', dot: 'bg-warning' },
  running:   { badge: 'badge-running',   dot: 'bg-forge-400 animate-pulse' },
  rendering: { badge: 'badge-rendering', dot: 'bg-purple-400 animate-pulse' },
  completed: { badge: 'badge-completed', dot: 'bg-success' },
  failed:    { badge: 'badge-failed',    dot: 'bg-danger' },
  draft:     { badge: 'badge-draft',     dot: 'bg-surface-500' },
  compiled:  { badge: 'badge-compiled',  dot: 'bg-forge-400' },
}

const cls    = computed(() => map[props.status]?.badge ?? 'badge-draft')
const dotCls = computed(() => map[props.status]?.dot   ?? 'bg-surface-500')
</script>

<template>
  <div class="space-y-6 animate-fade-in">

    <div class="card overflow-hidden">
      <div class="px-6 py-4 border-b border-surface-800/40 flex items-center justify-between">
        <h3 class="section-title">Event Timeline</h3>
        <button class="btn-secondary text-xs" @click="loadActivity">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          Refresh
        </button>
      </div>

      <div v-if="activity.length" class="divide-y divide-surface-800/30">
        <div
          v-for="log in activity"
          :key="log.id"
          class="flex items-start gap-4 px-6 py-4 hover:bg-surface-800/20 transition-colors animate-fade-in"
        >
          <!-- Icon -->
          <div class="mt-0.5 shrink-0">
            <div class="w-9 h-9 rounded-xl flex items-center justify-center" :class="iconBg(log.event_type)">
              <svg class="w-4 h-4" :class="iconColor(log.event_type)" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" :d="iconPath(log.event_type)" />
              </svg>
            </div>
          </div>

          <!-- Content -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between gap-3 mb-1.5">
              <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full border" :class="typeChipClass(log.event_type)">
                {{ log.event_type.replace(/_/g, ' ') }}
              </span>
              <span class="text-[11px] text-surface-600 shrink-0">{{ formatTime(log.created_at) }}</span>
            </div>
            <p class="text-sm text-surface-200 leading-snug">{{ log.message }}</p>
            <p v-if="log.related_entity_id" class="text-xs text-surface-600 font-mono mt-1">
              {{ log.related_entity_type }}: {{ log.related_entity_id.slice(0, 20) }}…
            </p>
          </div>
        </div>
      </div>

      <EmptyState v-else title="No activity" description="System events will appear here as you use the platform." />
    </div>

  </div>
</template>

<script setup lang="ts">
const api      = useApi()
const activity = ref<any[]>([])

const iconPath = (type: string) => {
  if (type.includes('fail'))     return 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z'
  if (type.includes('completed')) return 'M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
  if (type.includes('submitted') || type.includes('started')) return 'M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z'
  if (type.includes('compiled')) return 'M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z'
  if (type.includes('created'))  return 'M12 4.5v15m7.5-7.5h-15'
  return 'M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z'
}

const iconBg = (type: string) => {
  if (type.includes('fail'))     return 'bg-danger/10'
  if (type.includes('completed')) return 'bg-success/10'
  if (type.includes('submitted') || type.includes('started')) return 'bg-forge-500/10'
  if (type.includes('compiled')) return 'bg-warning/10'
  return 'bg-surface-800/60'
}

const iconColor = (type: string) => {
  if (type.includes('fail'))     return 'text-danger'
  if (type.includes('completed')) return 'text-success'
  if (type.includes('submitted') || type.includes('started')) return 'text-forge-400'
  if (type.includes('compiled')) return 'text-warning'
  return 'text-surface-500'
}

const typeChipClass = (type: string) => {
  if (type.includes('fail'))     return 'bg-danger/10   text-danger    border-danger/20'
  if (type.includes('completed')) return 'bg-success/10  text-success   border-success/20'
  if (type.includes('submitted')) return 'bg-forge-500/10 text-forge-300 border-forge-500/20'
  return 'bg-surface-800/60 text-surface-400 border-surface-700/40'
}

const formatTime = (d: string) => d ? new Date(d).toLocaleString() : '—'

const loadActivity = async () => {
  try { activity.value = await api.getActivity(50) } catch (e) { console.error(e) }
}

onMounted(loadActivity)
</script>

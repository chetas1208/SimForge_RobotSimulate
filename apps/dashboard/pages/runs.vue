<template>
  <div class="space-y-6">
    <div v-if="scenarioId" class="glass-card p-4 flex items-center justify-between">
      <div>
        <p class="text-xs uppercase tracking-[0.2em] text-surface-500">Scenario Runs</p>
        <h2 class="text-lg font-semibold text-white font-display">{{ scenarioId }}</h2>
      </div>
      <div class="flex items-center gap-2">
        <NuxtLink :to="`/evaluation?scenarioId=${scenarioId}`" class="btn-ghost text-sm">Compare</NuxtLink>
        <NuxtLink :to="`/outputs?scenarioId=${scenarioId}`" class="btn-ghost text-sm">Outputs</NuxtLink>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex items-center gap-3 flex-wrap">
      <select v-model="statusFilter" class="select-field w-40">
        <option value="">All Statuses</option>
        <option value="queued">Queued</option>
        <option value="preparing">Preparing</option>
        <option value="running">Running</option>
        <option value="rendering">Rendering</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
      </select>
      <button @click="loadJobs" class="btn-secondary text-sm">↻ Refresh</button>
    </div>

    <!-- Jobs Table -->
    <div class="glass-card overflow-hidden">
      <div v-if="filtered.length" class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800/50">
              <th class="table-header">Job ID</th>
              <th class="table-header">Scenario</th>
              <th class="table-header">Provider</th>
              <th class="table-header">Status</th>
              <th class="table-header">Duration</th>
              <th class="table-header">Submitted</th>
              <th class="table-header">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="j in filtered" :key="j.id" class="table-row">
              <td class="table-cell font-mono text-xs text-surface-400">{{ j.id.slice(0, 12) }}…</td>
              <td class="table-cell font-mono text-xs">{{ j.scenario_id.slice(0, 8) }}…</td>
              <td class="table-cell">
                <span class="px-2 py-0.5 rounded bg-surface-800 text-xs font-medium text-surface-300">{{ j.provider_type }}</span>
              </td>
              <td class="table-cell"><StatusBadge :status="j.status" /></td>
              <td class="table-cell text-surface-400">{{ j.duration_seconds ? `${j.duration_seconds.toFixed(1)}s` : '—' }}</td>
              <td class="table-cell text-surface-500 text-xs">{{ formatDate(j.submitted_at) }}</td>
              <td class="table-cell">
                <div class="flex gap-2">
                  <button v-if="j.status === 'failed'" @click="retryJob(j.id)" class="btn-ghost text-xs text-warning">🔄 Retry</button>
                  <button v-if="j.error_message" @click="showError(j)" class="btn-ghost text-xs text-danger">⚠️ Error</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="🚀" title="No simulation runs" description="Submit a scenario run from the Scenarios page." />
    </div>

    <!-- Error Modal -->
    <div v-if="errorModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="errorModal = null">
      <div class="glass-card p-6 max-w-lg w-full mx-4 animate-slide-up">
        <h3 class="section-title text-danger mb-3">Error Details</h3>
        <div class="bg-surface-950 rounded-lg p-4 font-mono text-sm text-danger/80 overflow-x-auto">
          {{ errorModal }}
        </div>
        <button @click="errorModal = null" class="btn-secondary mt-4">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const route = useRoute()
const statusFilter = ref('')
const jobs = ref<any[]>([])
const errorModal = ref<string | null>(null)
const scenarioId = computed(() => typeof route.query.scenarioId === 'string' ? route.query.scenarioId : '')

const filtered = computed(() => {
  if (!statusFilter.value) return jobs.value
  return jobs.value.filter(j => j.status === statusFilter.value)
})

const formatDate = (d: string) => d ? new Date(d).toLocaleString() : '—'

const loadJobs = async () => {
  try {
    jobs.value = await api.getJobs(scenarioId.value ? { scenario_id: scenarioId.value } : undefined)
  } catch (e) { console.error(e) }
}

const retryJob = async (id: string) => {
  try {
    await api.retryJob(id)
    await loadJobs()
  } catch (e) { console.error(e) }
}

const showError = (job: any) => {
  errorModal.value = job.error_message
}

onMounted(loadJobs)
watch(scenarioId, loadJobs)

// Auto-refresh every 5 seconds
const interval = setInterval(loadJobs, 5000)
onUnmounted(() => clearInterval(interval))
</script>

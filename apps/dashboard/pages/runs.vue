<template>
  <div class="space-y-6 animate-fade-in">

    <!-- Toolbar -->
    <div class="flex items-center gap-3 flex-wrap">
      <select v-model="statusFilter" class="select-field w-44">
        <option value="">All Statuses</option>
        <option value="queued">Queued</option>
        <option value="preparing">Preparing</option>
        <option value="running">Running</option>
        <option value="rendering">Rendering</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
      </select>
      <button class="btn-secondary" @click="loadJobs">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
        </svg>
        Refresh
      </button>
      <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-900 border border-surface-800/60 text-xs text-surface-500">
        <div class="w-1.5 h-1.5 rounded-full bg-forge-400 animate-pulse"></div>
        Auto-refreshing
      </div>
    </div>

    <!-- Jobs table -->
    <div class="card overflow-hidden">
      <div v-if="filtered.length" class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800/40">
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
              <td class="table-cell">
                <span class="font-mono text-xs text-surface-400 bg-surface-800/50 px-2 py-0.5 rounded-lg">{{ j.id.slice(0, 12) }}…</span>
              </td>
              <td class="table-cell">
                <span class="font-mono text-xs text-surface-500">{{ j.scenario_id.slice(0, 8) }}…</span>
              </td>
              <td class="table-cell">
                <span class="px-2 py-0.5 rounded-lg bg-surface-800/60 text-xs font-semibold text-surface-300 border border-surface-700/40">{{ j.provider_type }}</span>
              </td>
              <td class="table-cell"><StatusBadge :status="j.status" /></td>
              <td class="table-cell text-surface-400 tabular-nums text-xs">
                {{ j.duration_seconds ? `${j.duration_seconds.toFixed(1)}s` : '—' }}
              </td>
              <td class="table-cell text-surface-500 text-xs">{{ formatDate(j.submitted_at) }}</td>
              <td class="table-cell">
                <div class="flex gap-1">
                  <button
                    v-if="j.status === 'failed'"
                    class="btn-ghost text-xs py-1.5 px-2.5 text-warning"
                    @click="retryJob(j.id)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                    </svg>
                    Retry
                  </button>
                  <button
                    v-if="j.error_message"
                    class="btn-ghost text-xs py-1.5 px-2.5 text-danger"
                    @click="showError(j)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                    Error
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <EmptyState v-else title="No simulation runs" description="Submit a run from the Scenarios page to see jobs here." />
    </div>

    <!-- Error modal -->
    <Teleport to="body">
      <div
        v-if="errorModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-surface-950/80 backdrop-blur-sm"
        @click.self="errorModal = null"
      >
        <div class="card p-6 max-w-lg w-full mx-4 animate-slide-up border-danger/20">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-semibold text-danger">Error Details</h3>
            <button class="btn-icon" @click="errorModal = null">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div class="bg-surface-950 rounded-xl p-4 font-mono text-sm text-danger/80 overflow-x-auto border border-danger/10">
            {{ errorModal }}
          </div>
          <button class="btn-secondary mt-4" @click="errorModal = null">Close</button>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup lang="ts">
const api = useApi()
const statusFilter = ref('')
const jobs         = ref<any[]>([])
const errorModal   = ref<string | null>(null)

const filtered = computed(() => statusFilter.value
  ? jobs.value.filter(j => j.status === statusFilter.value)
  : jobs.value)

const formatDate = (d: string) => d ? new Date(d).toLocaleString() : '—'

const loadJobs = async () => {
  try { jobs.value = await api.getJobs() } catch (e) { console.error(e) }
}

const retryJob = async (id: string) => {
  try { await api.retryJob(id); await loadJobs() } catch (e) { console.error(e) }
}

const showError = (job: any) => { errorModal.value = job.error_message }

onMounted(loadJobs)
const interval = setInterval(loadJobs, 5000)
onUnmounted(() => clearInterval(interval))
</script>

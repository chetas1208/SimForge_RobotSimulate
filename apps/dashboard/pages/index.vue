<template>
  <div class="space-y-8 animate-fade-in">

    <!-- ── Stats row ───────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <StatCard label="Total Scenarios" :value="stats.scenarios" icon-bg="bg-forge-500/10" icon-color="text-forge-400">
        <template #icon>
          <svg class="w-5 h-5 text-forge-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" />
          </svg>
        </template>
      </StatCard>

      <StatCard label="Total Runs" :value="stats.totalJobs" icon-bg="bg-info/10" icon-color="text-info">
        <template #icon>
          <svg class="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
          </svg>
        </template>
      </StatCard>

      <StatCard label="Completed" :value="stats.completedJobs" icon-bg="bg-success/10" icon-color="text-success">
        <template #icon>
          <svg class="w-5 h-5 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </template>
      </StatCard>

      <StatCard label="Failed" :value="stats.failedJobs" icon-bg="bg-danger/10" icon-color="text-danger">
        <template #icon>
          <svg class="w-5 h-5 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        </template>
      </StatCard>
    </div>

    <!-- ── Middle row ──────────────────────────────────────── -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- Activity feed -->
      <div class="lg:col-span-2 card p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="section-title">Recent Activity</h3>
          <NuxtLink to="/activity" class="text-xs text-forge-400 hover:text-forge-300 font-medium transition-colors">
            View all →
          </NuxtLink>
        </div>

        <div v-if="activity.length" class="relative">
          <!-- Vertical connector line -->
          <div class="absolute left-[15px] top-3 bottom-3 w-px bg-surface-800/60"></div>

          <div class="space-y-1">
            <div
              v-for="log in activity.slice(0, 8)"
              :key="log.id"
              class="flex items-start gap-4 py-3 px-1 rounded-xl hover:bg-surface-800/30 transition-colors duration-150"
            >
              <!-- Event dot -->
              <div class="relative z-10 mt-0.5">
                <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border border-surface-800/60" :class="activityDotClass(log.event_type)">
                  <div class="w-2 h-2 rounded-full" :class="activityDotInner(log.event_type)"></div>
                </div>
              </div>

              <div class="flex-1 min-w-0 pt-1">
                <p class="text-sm text-surface-200 leading-snug">{{ log.message }}</p>
                <div class="flex items-center gap-2 mt-1.5">
                  <span class="text-[11px] px-2 py-0.5 rounded-full border" :class="activityTypeClass(log.event_type)">
                    {{ log.event_type.replace(/_/g, ' ') }}
                  </span>
                  <span class="text-[11px] text-surface-600">{{ formatTime(log.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <EmptyState v-else title="No activity yet" description="Activity will appear as you create scenarios and run simulations." />
      </div>

      <!-- Right column -->
      <div class="space-y-4">
        <!-- Status distribution -->
        <div class="card p-5">
          <h3 class="text-xs font-semibold text-surface-500 uppercase tracking-widest mb-4">Job Status</h3>
          <div v-if="Object.keys(statusCounts).length" class="space-y-3">
            <div v-for="(count, status) in statusCounts" :key="status" class="flex items-center gap-3">
              <StatusBadge :status="String(status)" class="w-24 justify-center" />
              <div class="flex-1 h-1 bg-surface-800 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-700"
                  :class="statusBarClass(String(status))"
                  :style="{ width: `${(count / Math.max(stats.totalJobs, 1)) * 100}%` }"
                ></div>
              </div>
              <span class="text-xs text-surface-400 font-mono w-4 text-right">{{ count }}</span>
            </div>
          </div>
          <p v-else class="text-sm text-surface-600 text-center py-4">No jobs yet</p>
        </div>

        <!-- Platform info -->
        <div class="card p-5">
          <h3 class="text-xs font-semibold text-surface-500 uppercase tracking-widest mb-4">Platform</h3>
          <div class="space-y-3">
            <div v-for="[key, val, cls] in platformInfo" :key="key" class="flex items-center justify-between">
              <span class="text-xs text-surface-500">{{ key }}</span>
              <span class="text-xs font-semibold font-mono" :class="cls">{{ val }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Recent scenarios ────────────────────────────────── -->
    <div class="card overflow-hidden">
      <div class="flex items-center justify-between px-6 py-4 border-b border-surface-800/40">
        <h3 class="section-title">Recent Scenarios</h3>
        <NuxtLink to="/scenarios" class="btn-ghost text-xs">View All →</NuxtLink>
      </div>

      <div v-if="scenarios.length" class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800/40">
              <th class="table-header">Name</th>
              <th class="table-header">Template</th>
              <th class="table-header">Variants</th>
              <th class="table-header">Status</th>
              <th class="table-header">Created</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in scenarios.slice(0, 5)"
              :key="s.id"
              class="table-row cursor-pointer"
              @click="navigateTo('/scenarios')"
            >
              <td class="table-cell font-semibold text-white">{{ s.name }}</td>
              <td class="table-cell">
                <span class="font-mono text-xs text-surface-500 bg-surface-800/50 px-2 py-0.5 rounded-lg">{{ s.environment_template }}</span>
              </td>
              <td class="table-cell text-surface-400">{{ s.variant_count }}</td>
              <td class="table-cell"><StatusBadge :status="s.status" /></td>
              <td class="table-cell text-surface-500 text-xs">{{ formatDate(s.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <EmptyState v-else title="No scenarios" description="Create your first scenario to get started." >
        <template #action>
          <NuxtLink to="/builder" class="btn-primary mt-5 inline-flex">Create Scenario</NuxtLink>
        </template>
      </EmptyState>
    </div>

  </div>
</template>

<script setup lang="ts">
const api = useApi()

const scenarios = ref<any[]>([])
const jobs      = ref<any[]>([])
const activity  = ref<any[]>([])

const stats = computed(() => ({
  scenarios:     scenarios.value.length,
  totalJobs:     jobs.value.length,
  completedJobs: jobs.value.filter(j => j.status === 'completed').length,
  failedJobs:    jobs.value.filter(j => j.status === 'failed').length,
}))

const statusCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const j of jobs.value) counts[j.status] = (counts[j.status] || 0) + 1
  return counts
})

const platformInfo = computed(() => [
  ['Provider',    'Mock',      'text-forge-400'],
  ['SDK Version', '0.1.0',     'text-surface-300'],
  ['API Version', '0.1.0',     'text-surface-300'],
  ['Database',    'Connected', 'text-success'],
])

const statusBarClass = (s: string) => ({
  queued: 'bg-info', preparing: 'bg-warning', running: 'bg-forge-500',
  rendering: 'bg-purple-500', completed: 'bg-success', failed: 'bg-danger',
}[s] ?? 'bg-surface-600')

const activityDotClass = (type: string) => {
  if (type.includes('fail'))      return 'bg-danger/10'
  if (type.includes('completed')) return 'bg-success/10'
  if (type.includes('submitted') || type.includes('started')) return 'bg-forge-500/10'
  return 'bg-surface-800'
}

const activityDotInner = (type: string) => {
  if (type.includes('fail'))      return 'bg-danger'
  if (type.includes('completed')) return 'bg-success'
  if (type.includes('submitted') || type.includes('started')) return 'bg-forge-400'
  return 'bg-surface-500'
}

const activityTypeClass = (type: string) => {
  if (type.includes('fail'))      return 'bg-danger/10 text-danger border-danger/20'
  if (type.includes('completed')) return 'bg-success/10 text-success border-success/20'
  if (type.includes('submitted')) return 'bg-forge-500/10 text-forge-300 border-forge-500/20'
  return 'bg-surface-800 text-surface-500 border-surface-700/40'
}

const formatDate = (d: string) => d ? new Date(d).toLocaleDateString() : '—'
const formatTime = (d: string) => {
  if (!d) return '—'
  const diff = Date.now() - new Date(d).getTime()
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`
  return new Date(d).toLocaleDateString()
}

onMounted(async () => {
  try {
    const [s, j, a] = await Promise.all([api.getScenarios(), api.getJobs(), api.getActivity(20)])
    scenarios.value = s
    jobs.value      = j
    activity.value  = a
  } catch (e) { console.error('Failed to load dashboard data:', e) }
})
</script>

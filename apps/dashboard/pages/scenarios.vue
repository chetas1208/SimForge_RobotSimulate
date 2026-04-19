<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <input v-model="search" placeholder="Search scenarios..." class="input-field w-64" />
      </div>
      <NuxtLink to="/builder" class="btn-primary">+ New Scenario</NuxtLink>
    </div>

    <!-- Scenarios Table -->
    <div class="glass-card overflow-hidden">
      <div v-if="filtered.length" class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800/50">
              <th class="table-header">Name</th>
              <th class="table-header">Environment</th>
              <th class="table-header">Path Type</th>
              <th class="table-header">Variants</th>
              <th class="table-header">Status</th>
              <th class="table-header">Created</th>
              <th class="table-header">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in filtered" :key="s.id" class="table-row">
              <td class="table-cell">
                <div>
                  <p class="font-medium text-white">{{ s.name }}</p>
                  <p class="text-xs text-surface-500 mt-0.5 max-w-xs truncate">{{ s.description }}</p>
                </div>
              </td>
              <td class="table-cell font-mono text-xs">{{ s.environment_template }}</td>
              <td class="table-cell font-mono text-xs">{{ s.robot_path_type }}</td>
              <td class="table-cell">{{ s.variant_count }}</td>
              <td class="table-cell"><StatusBadge :status="s.status" /></td>
              <td class="table-cell text-surface-500 text-xs">{{ formatDate(s.created_at) }}</td>
              <td class="table-cell">
                <div class="flex items-center gap-2">
                  <button @click="compileScenario(s.id)" class="btn-ghost text-xs" :disabled="compiling === s.id">
                    {{ compiling === s.id ? 'Compiling...' : '⚙️ Compile' }}
                  </button>
                  <button @click="runScenario(s.id)" class="btn-ghost text-xs text-forge-400" :disabled="s.status === 'draft'">
                    ▶ Run
                  </button>
                  <NuxtLink :to="`/runs?scenarioId=${s.id}`" class="btn-ghost text-xs">🏃 Runs</NuxtLink>
                  <NuxtLink :to="`/evaluation?scenarioId=${s.id}`" class="btn-ghost text-xs">📊 Compare</NuxtLink>
                  <NuxtLink :to="`/outputs?scenarioId=${s.id}`" class="btn-ghost text-xs">📦 Outputs</NuxtLink>
                  <a :href="scenarioExportUrl(s.id)" class="btn-ghost text-xs" target="_blank" rel="noopener">⬇ Export</a>
                  <button @click="deleteScenario(s.id)" class="btn-ghost text-xs text-danger">🗑</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="📋" title="No scenarios found" description="Create a new scenario using the Scenario Builder.">
        <template #action>
          <NuxtLink to="/builder" class="btn-primary mt-4 inline-block">Create Scenario</NuxtLink>
        </template>
      </EmptyState>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const search = ref('')
const scenarios = ref<any[]>([])
const compiling = ref<string | null>(null)

const filtered = computed(() => {
  if (!search.value) return scenarios.value
  const q = search.value.toLowerCase()
  return scenarios.value.filter(s =>
    s.name.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q)
  )
})

const formatDate = (d: string) => d ? new Date(d).toLocaleDateString() : '—'
const scenarioExportUrl = (id: string) => api.getScenarioExportUrl(id)

const loadScenarios = async () => {
  try { scenarios.value = await api.getScenarios() } catch (e) { console.error(e) }
}

const compileScenario = async (id: string) => {
  compiling.value = id
  try {
    await api.compileScenario(id)
    await loadScenarios()
  } catch (e) { console.error(e) }
  compiling.value = null
}

const runScenario = async (id: string) => {
  try {
    await api.submitRun(id)
    await loadScenarios()
  } catch (e) { console.error(e) }
}

const deleteScenario = async (id: string) => {
  if (!confirm('Delete this scenario?')) return
  try {
    await api.deleteScenario(id)
    await loadScenarios()
  } catch (e) { console.error(e) }
}

onMounted(loadScenarios)
</script>

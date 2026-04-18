<template>
  <div class="space-y-6 animate-fade-in">

    <!-- Toolbar -->
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <div class="relative">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-500 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        <input v-model="search" placeholder="Search scenarios…" class="input-field pl-10 w-72" />
      </div>
      <NuxtLink to="/builder" class="btn-primary">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        New Scenario
      </NuxtLink>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div v-if="filtered.length" class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800/40">
              <th class="table-header">Name</th>
              <th class="table-header">Environment</th>
              <th class="table-header">Path</th>
              <th class="table-header">Variants</th>
              <th class="table-header">Status</th>
              <th class="table-header">Created</th>
              <th class="table-header">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in filtered" :key="s.id" class="table-row">
              <td class="table-cell">
                <p class="font-semibold text-white leading-tight">{{ s.name }}</p>
                <p v-if="s.description" class="text-xs text-surface-500 mt-0.5 max-w-xs truncate">{{ s.description }}</p>
              </td>
              <td class="table-cell">
                <span class="font-mono text-xs text-surface-400 bg-surface-800/50 px-2 py-0.5 rounded-lg">{{ s.environment_template }}</span>
              </td>
              <td class="table-cell">
                <span class="font-mono text-xs text-surface-400 bg-surface-800/50 px-2 py-0.5 rounded-lg">{{ s.robot_path_type }}</span>
              </td>
              <td class="table-cell text-surface-400 tabular-nums">{{ s.variant_count }}</td>
              <td class="table-cell"><StatusBadge :status="s.status" /></td>
              <td class="table-cell text-surface-500 text-xs">{{ formatDate(s.created_at) }}</td>
              <td class="table-cell">
                <div class="flex items-center gap-1">
                  <button
                    class="btn-ghost text-xs py-1.5 px-2.5 text-surface-400"
                    :disabled="compiling === s.id"
                    @click="compileScenario(s.id)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                    </svg>
                    {{ compiling === s.id ? 'Compiling…' : 'Compile' }}
                  </button>
                  <button
                    class="btn-ghost text-xs py-1.5 px-2.5 text-forge-400"
                    :disabled="s.status === 'draft'"
                    @click="runScenario(s.id)"
                  >
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                    </svg>
                    Run
                  </button>
                  <button class="btn-ghost text-xs py-1.5 px-2.5 text-danger hover:bg-danger/10" @click="deleteScenario(s.id)">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <EmptyState v-else title="No scenarios found" description="Create a new scenario using the Scenario Builder.">
        <template #action>
          <NuxtLink to="/builder" class="btn-primary mt-5 inline-flex">Create Scenario</NuxtLink>
        </template>
      </EmptyState>
    </div>

  </div>
</template>

<script setup lang="ts">
const api = useApi()
const search   = ref('')
const scenarios = ref<any[]>([])
const compiling = ref<string | null>(null)

const filtered = computed(() => {
  if (!search.value) return scenarios.value
  const q = search.value.toLowerCase()
  return scenarios.value.filter(s => s.name.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q))
})

const formatDate = (d: string) => d ? new Date(d).toLocaleDateString() : '—'

const loadScenarios = async () => {
  try { scenarios.value = await api.getScenarios() } catch (e) { console.error(e) }
}

const compileScenario = async (id: string) => {
  compiling.value = id
  try { await api.compileScenario(id); await loadScenarios() } catch (e) { console.error(e) }
  compiling.value = null
}

const runScenario = async (id: string) => {
  try { await api.submitRun(id); await loadScenarios() } catch (e) { console.error(e) }
}

const deleteScenario = async (id: string) => {
  if (!confirm('Delete this scenario?')) return
  try { await api.deleteScenario(id); await loadScenarios() } catch (e) { console.error(e) }
}

onMounted(loadScenarios)
</script>

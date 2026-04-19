<template>
  <div class="max-w-3xl space-y-6">
    <!-- Provider Settings -->
    <div class="glass-card p-6">
      <h3 class="section-title mb-5">Simulation Provider</h3>
      <div class="space-y-4">
        <div>
          <label class="label-text">Active Provider</label>
          <select v-model="settings.simulation_provider" class="select-field w-64">
            <option value="mock">Mock (Local Development)</option>
            <option value="track4">Track 4 (Local HPC Pipeline)</option>
            <option value="isaac">Isaac Sim (Remote HPC)</option>
          </select>
        </div>
        <div v-if="settings.simulation_provider === 'track4'" class="p-4 rounded-lg bg-primary/5 border border-primary/20">
          <p class="text-sm text-primary">✓ Track 4 provider is active. Local scenario generation and XGBoost scoring will run on this host.</p>
          <p class="text-xs text-surface-500 mt-1">Use this when the backend and model runtime live on the same HPC node.</p>
        </div>
        <div v-else-if="settings.simulation_provider === 'isaac'" class="p-4 rounded-lg bg-warning/5 border border-warning/20">
          <p class="text-sm text-warning">⚠ Isaac Sim provider requires remote HPC configuration.</p>
          <p class="text-xs text-surface-500 mt-1">Configure HPC connection details below.</p>
        </div>
      </div>
    </div>

    <!-- Defaults -->
    <div class="glass-card p-6">
      <h3 class="section-title mb-5">Defaults</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="label-text">Default Variant Count</label>
          <input v-model="settings.default_variant_count" type="number" class="input-field" />
        </div>
        <div>
          <label class="label-text">Max Concurrent Jobs</label>
          <input v-model="settings.max_concurrent_jobs" type="number" class="input-field" />
        </div>
        <div>
          <label class="label-text">Output Storage Path</label>
          <input v-model="settings.output_storage_path" class="input-field" />
        </div>
      </div>
    </div>

    <!-- HPC Settings -->
    <div class="glass-card p-6">
      <h3 class="section-title mb-5">HPC Configuration</h3>
      <p class="text-sm text-surface-500 mb-4">Remote HPC settings for Isaac Sim execution.</p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="label-text">HPC Host</label>
          <input v-model="settings.hpc_host" class="input-field" placeholder="e.g. hpc.cluster.edu" />
        </div>
        <div>
          <label class="label-text">HPC User</label>
          <input v-model="settings.hpc_user" class="input-field" placeholder="username" />
        </div>
      </div>
      <div class="flex items-center gap-3 mt-4">
        <div class="w-2 h-2 rounded-full" :class="settings.hpc_host ? 'bg-warning' : 'bg-surface-600'"></div>
        <span class="text-xs text-surface-500">{{ settings.hpc_host ? 'HPC configured (not connected)' : 'HPC not configured' }}</span>
      </div>
    </div>

    <!-- Save -->
    <div class="flex justify-end">
      <button @click="saveSettings" :disabled="saving" class="btn-primary">
        {{ saving ? 'Saving...' : '💾 Save Settings' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const saving = ref(false)

const settings = reactive<Record<string, string>>({
  simulation_provider: 'mock',
  default_variant_count: '5',
  max_concurrent_jobs: '4',
  output_storage_path: './storage',
  hpc_enabled: 'false',
  hpc_host: '',
  hpc_user: '',
})

const loadSettings = async () => {
  try {
    const data = await api.getSettings()
    Object.assign(settings, data)
  } catch (e) { console.error(e) }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await api.updateSettings(settings)
  } catch (e) { console.error(e) }
  saving.value = false
}

onMounted(loadSettings)
</script>

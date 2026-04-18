<template>
  <div class="max-w-3xl space-y-6 animate-fade-in">

    <!-- Provider Settings -->
    <div class="card p-6">
      <h3 class="section-title mb-1">Simulation Provider</h3>
      <p class="text-sm text-surface-500 mb-5">Choose the backend used to execute simulation jobs.</p>
      <div class="space-y-4">
        <div>
          <label class="label-text">Active Provider</label>
          <select v-model="settings.simulation_provider" class="select-field w-72">
            <option value="mock">Mock (Local Development)</option>
            <option value="isaac">Isaac Sim (Remote HPC)</option>
          </select>
        </div>
        <div
          v-if="settings.simulation_provider === 'mock'"
          class="flex items-start gap-3 p-4 rounded-xl bg-success/5 border border-success/15"
        >
          <svg class="w-4 h-4 text-success mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p class="text-sm font-semibold text-success">Mock provider active</p>
            <p class="text-xs text-surface-500 mt-0.5">No GPU required. Jobs generate placeholder outputs for development.</p>
          </div>
        </div>
        <div
          v-else
          class="flex items-start gap-3 p-4 rounded-xl bg-warning/5 border border-warning/15"
        >
          <svg class="w-4 h-4 text-warning mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
          </svg>
          <div>
            <p class="text-sm font-semibold text-warning">Isaac Sim selected</p>
            <p class="text-xs text-surface-500 mt-0.5">Requires remote HPC configuration below.</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Defaults -->
    <div class="card p-6">
      <h3 class="section-title mb-1">Defaults</h3>
      <p class="text-sm text-surface-500 mb-5">Default values used when creating new scenarios and runs.</p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="label-text">Default Variant Count</label>
          <input v-model="settings.default_variant_count" type="number" class="input-field" />
        </div>
        <div>
          <label class="label-text">Max Concurrent Jobs</label>
          <input v-model="settings.max_concurrent_jobs" type="number" class="input-field" />
        </div>
        <div class="md:col-span-2">
          <label class="label-text">Output Storage Path</label>
          <input v-model="settings.output_storage_path" class="input-field font-mono" />
        </div>
      </div>
    </div>

    <!-- HPC Config -->
    <div class="card p-6">
      <h3 class="section-title mb-1">HPC Configuration</h3>
      <p class="text-sm text-surface-500 mb-5">Remote cluster settings for Isaac Sim execution. Leave empty when using mock provider.</p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="label-text">HPC Host</label>
          <input v-model="settings.hpc_host" class="input-field font-mono" placeholder="e.g. hpc.cluster.edu" />
        </div>
        <div>
          <label class="label-text">HPC User</label>
          <input v-model="settings.hpc_user" class="input-field font-mono" placeholder="username" />
        </div>
      </div>
      <div class="flex items-center gap-2 mt-4">
        <div class="w-1.5 h-1.5 rounded-full" :class="settings.hpc_host ? 'bg-warning' : 'bg-surface-600'"></div>
        <span class="text-xs text-surface-500">{{ settings.hpc_host ? 'HPC configured — not connected' : 'HPC not configured' }}</span>
      </div>
    </div>

    <!-- Save -->
    <div class="flex justify-end">
      <button class="btn-primary" :disabled="saving" @click="saveSettings">
        <svg v-if="!saving" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ saving ? 'Saving…' : 'Save Settings' }}
      </button>
    </div>

  </div>
</template>

<script setup lang="ts">
const api    = useApi()
const saving = ref(false)

const settings = reactive<Record<string, string>>({
  simulation_provider:    'mock',
  default_variant_count:  '5',
  max_concurrent_jobs:    '4',
  output_storage_path:    './storage',
  hpc_enabled:            'false',
  hpc_host:               '',
  hpc_user:               '',
})

const loadSettings = async () => {
  try { Object.assign(settings, await api.getSettings()) } catch (e) { console.error(e) }
}

const saveSettings = async () => {
  saving.value = true
  try { await api.updateSettings(settings) } catch (e) { console.error(e) }
  saving.value = false
}

onMounted(loadSettings)
</script>

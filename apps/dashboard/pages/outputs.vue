<template>
  <div class="space-y-6 animate-fade-in">

    <!-- Toolbar -->
    <div class="flex items-center gap-3">
      <select v-model="typeFilter" class="select-field w-52">
        <option value="">All Types</option>
        <option value="preview_image">Preview Image</option>
        <option value="manifest_json">Manifest</option>
        <option value="labels_json">Labels</option>
        <option value="evaluation_json">Evaluation</option>
        <option value="log_file">Log</option>
      </select>
      <button class="btn-secondary" @click="loadArtifacts">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Grid -->
    <div v-if="filtered.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="a in filtered" :key="a.id" class="card-hover p-5 animate-fade-in group">
        <!-- Thumbnail -->
        <div class="w-full h-36 rounded-xl bg-surface-800/40 border border-surface-700/30 flex items-center justify-center mb-4 overflow-hidden">
          <div class="text-center">
            <div class="w-12 h-12 mx-auto mb-2 rounded-xl bg-surface-800/60 flex items-center justify-center">
              <component :is="artifactIcon(a.artifact_type)" class="w-6 h-6 text-surface-500" />
            </div>
            <p class="text-[10px] text-surface-600 font-mono uppercase tracking-wider">{{ a.artifact_type }}</p>
          </div>
        </div>

        <!-- Meta -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-semibold px-2 py-1 rounded-lg bg-surface-800/60 border border-surface-700/40 text-surface-400 uppercase tracking-wider">
              {{ a.artifact_type.replace(/_/g, ' ') }}
            </span>
            <span class="text-xs text-surface-600">{{ formatDate(a.created_at) }}</span>
          </div>
          <p class="text-xs text-surface-500 font-mono truncate">{{ a.file_path }}</p>
          <p class="text-[11px] text-surface-600">Job: <span class="font-mono">{{ a.job_id.slice(0, 12) }}…</span></p>
        </div>
      </div>
    </div>

    <EmptyState v-else title="No artifacts yet" description="Artifacts are generated after simulation runs complete." />

  </div>
</template>

<script setup lang="ts">
import { defineComponent, h } from 'vue'

const api        = useApi()
const typeFilter = ref('')
const artifacts  = ref<any[]>([])

const filtered = computed(() => typeFilter.value
  ? artifacts.value.filter(a => a.artifact_type === typeFilter.value)
  : artifacts.value)

function SvgIcon(d: string) {
  return defineComponent({
    render: () =>
      h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '1.5' },
        [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d })]),
  })
}

const artifactIcon = (type: string) => ({
  preview_image:   SvgIcon('M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z'),
  preview_video:   SvgIcon('M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 01-1.125-1.125M3.375 19.5h1.5C5.496 19.5 6 18.996 6 18.375m-3.75.125v-6.75m0 0A1.125 1.125 0 014.5 10.5h15a1.125 1.125 0 011.125 1.125v6.75m-17.25 0h1.5m15.75 0h-1.5m-15 0a1.125 1.125 0 01-1.125 1.125M21.375 19.5h-1.5c-.621 0-1.125-.504-1.125-1.125M21.375 19.5v-6.75m0 0A1.125 1.125 0 0020.25 11.25H3.75A1.125 1.125 0 002.625 12.75v6.75m-5.25 0h17.25'),
  manifest_json:   SvgIcon('M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z'),
  labels_json:     SvgIcon('M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z'),
  evaluation_json: SvgIcon('M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z'),
  log_file:        SvgIcon('M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z'),
}[type] ?? SvgIcon('M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m8.25 3v6.75m0 0l-3-3m3 3l3-3M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z'))

const formatDate = (d: string) => d ? new Date(d).toLocaleDateString() : '—'

const loadArtifacts = async () => {
  try { artifacts.value = await api.getArtifacts() } catch (e) { console.error(e) }
}

onMounted(loadArtifacts)
</script>

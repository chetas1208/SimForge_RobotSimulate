<template>
  <div class="space-y-6">
    <div v-if="scenarioResults" class="glass-card p-5 flex items-center justify-between gap-4 flex-wrap">
      <div>
        <p class="text-xs uppercase tracking-[0.2em] text-surface-500">Scenario Outputs</p>
        <h2 class="text-xl font-semibold text-white font-display">{{ scenarioResults.scenario.name }}</h2>
        <p class="text-sm text-surface-400 mt-1">
          {{ scenarioResults.summary.completed_jobs }} completed jobs across {{ scenarioResults.summary.variant_count }} variants
        </p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <NuxtLink :to="`/runs?scenarioId=${scenarioId}`" class="btn-ghost text-sm">Runs</NuxtLink>
        <NuxtLink :to="`/evaluation?scenarioId=${scenarioId}`" class="btn-ghost text-sm">Compare</NuxtLink>
        <a :href="scenarioExportUrl" class="btn-primary text-sm" target="_blank" rel="noopener">Download ZIP</a>
      </div>
    </div>

    <div class="flex items-center gap-3 flex-wrap">
      <select v-model="typeFilter" class="select-field w-48">
        <option value="">All Types</option>
        <option value="preview_video">Preview Video</option>
        <option value="prompt_json">Prompt Package</option>
        <option value="manifest_json">Manifest</option>
        <option value="config_json">Scenario Config</option>
        <option value="feature_json">Features</option>
        <option value="evaluation_json">Evaluation</option>
        <option value="usd_scene">OpenUSD Scene</option>
        <option value="log_file">Log</option>
      </select>
      <button @click="loadArtifacts" class="btn-secondary text-sm">↻ Refresh</button>
    </div>

    <div v-if="filtered.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="artifact in filtered" :key="artifact.id" class="glass-card-hover p-5 animate-fade-in space-y-4">
        <div class="w-full h-40 rounded-lg bg-surface-800/50 flex items-center justify-center overflow-hidden">
          <video
            v-if="artifact.artifact_type === 'preview_video'"
            :src="artifactDownloadUrl(artifact)"
            class="w-full h-full object-cover"
            controls
            preload="metadata"
          />
          <div v-else class="text-center">
            <span class="text-3xl">{{ artifactIcon(artifact.artifact_type) }}</span>
            <p class="text-xs text-surface-500 mt-1">{{ artifact.artifact_type }}</p>
          </div>
        </div>

        <div class="space-y-2">
          <div class="flex items-center justify-between gap-3">
            <span class="text-xs font-medium px-2 py-0.5 rounded bg-surface-800 text-surface-400">
              {{ artifactBadge(artifact) }}
            </span>
            <span class="text-xs text-surface-500">{{ formatDate(artifact.created_at) }}</span>
          </div>
          <p class="text-sm font-semibold text-surface-100">
            {{ artifactTitle(artifact) }}
          </p>
          <p v-if="artifact.metadata?.seedance_status" class="text-xs text-surface-400">
            Seedance status: <span class="font-medium text-surface-200">{{ artifact.metadata.seedance_status }}</span>
          </p>
          <p v-if="artifact.variant_index !== undefined" class="text-xs text-surface-500">
            Variant {{ artifact.variant_index + 1 }}
          </p>
          <p v-if="artifact.metadata?.refined_prompt_excerpt" class="text-xs text-surface-400 leading-relaxed">
            {{ artifact.metadata.refined_prompt_excerpt }}
          </p>
          <p class="text-xs text-surface-500 font-mono truncate">{{ artifact.file_path }}</p>
          <p class="text-xs text-surface-600">Job: {{ artifact.job_id.slice(0, 12) }}…</p>
        </div>

        <div class="flex items-center gap-2">
          <a :href="artifactDownloadUrl(artifact)" class="btn-secondary text-xs" target="_blank" rel="noopener">
            Download
          </a>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      icon="📦"
      :title="scenarioResults ? 'No outputs for this scenario' : 'No artifacts'"
      :description="scenarioResults ? 'Run the scenario to generate artifacts and export bundles.' : 'Artifacts will appear here after simulation runs complete.'"
    />
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const route = useRoute()
const typeFilter = ref('')
const artifacts = ref<any[]>([])
const scenarioResults = ref<any | null>(null)
const scenarioId = computed(() => typeof route.query.scenarioId === 'string' ? route.query.scenarioId : '')
const scenarioExportUrl = computed(() => scenarioId.value ? api.getScenarioExportUrl(scenarioId.value) : '')

const filtered = computed(() => {
  if (!typeFilter.value) return artifacts.value
  return artifacts.value.filter(a => a.artifact_type === typeFilter.value)
})

const artifactIcon = (type: string) => {
  const map: Record<string, string> = {
    preview_image: '🖼️',
    preview_video: '🎬',
    manifest_json: '📄',
    config_json: '⚙️',
    feature_json: '📈',
    evaluation_json: '📊',
    log_file: '📝',
    usd_scene: '🎭',
    prompt_json: '✨',
  }
  return map[type] || '📦'
}

const artifactTitle = (artifact: any) => artifact.metadata?.label || artifact.artifact_type.replaceAll('_', ' ')
const artifactBadge = (artifact: any) => {
  if (artifact.artifact_type === 'preview_video' && artifact.metadata?.video_role === 'generated_concept') {
    return 'Seedance Video'
  }
  if (artifact.artifact_type === 'preview_video') {
    return 'Simulated Video'
  }
  if (artifact.artifact_type === 'prompt_json') {
    return 'Prompt Package'
  }
  return artifact.artifact_type
}

const artifactDownloadUrl = (artifact: any) => api.getArtifactDownloadUrl(artifact.id)
const formatDate = (d: string) => d ? new Date(d).toLocaleString() : '—'

const loadArtifacts = async () => {
  try {
    if (scenarioId.value) {
      scenarioResults.value = await api.getScenarioResults(scenarioId.value)
      artifacts.value = scenarioResults.value.variant_results.flatMap((item: any) =>
        (item.artifacts || []).map((artifact: any) => ({
          ...artifact,
          variant_index: item.variant?.variant_index,
        })),
      )
      return
    }

    scenarioResults.value = null
    artifacts.value = await api.getArtifacts()
  } catch (e) {
    console.error(e)
  }
}

onMounted(loadArtifacts)
watch(scenarioId, loadArtifacts)
</script>

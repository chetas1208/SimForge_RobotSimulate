<template>
  <div class="space-y-6">
    <div v-if="scenarioResults" class="glass-card p-5 flex items-center justify-between gap-4 flex-wrap">
      <div>
        <p class="text-xs uppercase tracking-[0.2em] text-surface-500">Variant Comparison</p>
        <h2 class="text-xl font-semibold text-white font-display">{{ scenarioResults.scenario.name }}</h2>
        <p class="text-sm text-surface-400 mt-1">
          Compare risk distribution across {{ rows.length }} completed variants
        </p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <NuxtLink :to="`/runs?scenarioId=${scenarioId}`" class="btn-ghost text-sm">Runs</NuxtLink>
        <NuxtLink :to="`/outputs?scenarioId=${scenarioId}`" class="btn-ghost text-sm">Outputs</NuxtLink>
        <a :href="scenarioExportUrl" class="btn-primary text-sm" target="_blank" rel="noopener">Download ZIP</a>
      </div>
    </div>

    <div v-if="rows.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <ScoreCard label="Avg Collision Risk" :score="avgScore('collision_risk_score')" description="Likelihood of robot-human collision" />
      <ScoreCard label="Avg Occlusion" :score="avgScore('occlusion_score')" description="Sensor field obstruction level" />
      <ScoreCard label="Avg Path Conflict" :score="avgScore('path_conflict_score')" description="Route intersection intensity" />
      <ScoreCard label="Avg Severity" :score="avgScore('severity_score')" description="Overall edge-case severity" />
      <ScoreCard label="Avg Diversity" :score="avgScore('diversity_score')" description="Scenario variation coverage" />
    </div>

    <div class="glass-card overflow-hidden">
      <div class="p-5 border-b border-surface-800/50">
        <h3 class="section-title">{{ scenarioResults ? 'Scenario Comparison' : 'Evaluation Reports' }}</h3>
      </div>
      <div v-if="rows.length" class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800/50">
              <th class="table-header">Variant</th>
              <th class="table-header">Job</th>
              <th class="table-header">Collision</th>
              <th class="table-header">Occlusion</th>
              <th class="table-header">Conflict</th>
              <th class="table-header">Severity</th>
              <th class="table-header">Diversity</th>
              <th class="table-header">Risk Factors</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id" class="table-row cursor-pointer" @click="selected = row">
              <td class="table-cell">
                <span v-if="row.variant_index !== null" class="font-semibold text-white">Variant {{ row.variant_index + 1 }}</span>
                <span v-else class="text-surface-400">—</span>
              </td>
              <td class="table-cell font-mono text-xs text-surface-400">{{ row.job_id.slice(0, 12) }}…</td>
              <td class="table-cell"><ScorePill :score="row.collision_risk_score" /></td>
              <td class="table-cell"><ScorePill :score="row.occlusion_score" /></td>
              <td class="table-cell"><ScorePill :score="row.path_conflict_score" /></td>
              <td class="table-cell"><ScorePill :score="row.severity_score" /></td>
              <td class="table-cell"><ScorePill :score="row.diversity_score" /></td>
              <td class="table-cell text-xs text-surface-400">{{ (row.top_risk_factors || []).length }} factors</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else icon="📊" title="No evaluations" description="Evaluations are generated after simulation runs complete." />
    </div>

    <div v-if="selected" class="glass-card p-6 animate-slide-up">
      <div class="flex items-center justify-between mb-4">
        <h3 class="section-title">Evaluation Detail</h3>
        <button @click="selected = null" class="btn-ghost text-sm">✕ Close</button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div class="bg-surface-950 rounded-lg p-4">
          <p class="text-xs uppercase tracking-[0.2em] text-surface-500 mb-2">Summary</p>
          <div class="space-y-2 text-sm text-surface-300">
            <p><span class="text-surface-500">Job:</span> {{ selected.job_id }}</p>
            <p v-if="selected.variant_index !== null"><span class="text-surface-500">Variant:</span> {{ selected.variant_index + 1 }}</p>
            <p><span class="text-surface-500">Collision risk:</span> {{ (selected.collision_risk_score * 100).toFixed(1) }}%</p>
          </div>
        </div>
        <div v-if="selected.variant_parameters" class="bg-surface-950 rounded-lg p-4">
          <p class="text-xs uppercase tracking-[0.2em] text-surface-500 mb-2">Variant Parameters</p>
          <div class="space-y-1 text-sm text-surface-300">
            <p v-for="(value, key) in selected.variant_parameters" :key="key">
              <span class="text-surface-500">{{ key }}:</span> {{ value }}
            </p>
          </div>
        </div>
      </div>

      <div class="bg-surface-950 rounded-lg p-4 font-mono text-sm text-surface-300 whitespace-pre-line mb-4">{{ selected.explanation }}</div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 class="text-sm font-semibold text-surface-300 mb-2">Top Risk Factors</h4>
          <ul class="space-y-1">
            <li v-for="risk in (selected.top_risk_factors || [])" :key="risk" class="text-sm text-danger/80 flex items-start gap-2">
              <span class="text-danger mt-0.5">⚠</span> {{ risk }}
            </li>
          </ul>
        </div>
        <div>
          <h4 class="text-sm font-semibold text-surface-300 mb-2">Recommended Actions</h4>
          <ul class="space-y-1">
            <li v-for="action in (selected.recommended_actions || [])" :key="action" class="text-sm text-forge-400/80 flex items-start gap-2">
              <span class="text-forge-400 mt-0.5">→</span> {{ action }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const api = useApi()
const route = useRoute()
const evaluations = ref<any[]>([])
const scenarioResults = ref<any | null>(null)
const selected = ref<any>(null)
const scenarioId = computed(() => typeof route.query.scenarioId === 'string' ? route.query.scenarioId : '')
const scenarioExportUrl = computed(() => scenarioId.value ? api.getScenarioExportUrl(scenarioId.value) : '')

const rows = computed(() => {
  if (scenarioResults.value) {
    return scenarioResults.value.variant_results
      .filter((item: any) => item.evaluation)
      .map((item: any) => ({
        ...item.evaluation,
        variant_index: item.variant?.variant_index ?? null,
        variant_parameters: item.variant?.variant_parameters ?? null,
      }))
  }
  return evaluations.value.map((item: any) => ({
    ...item,
    variant_index: null,
    variant_parameters: null,
  }))
})

const avgScore = (key: string) => {
  if (!rows.value.length) return 0
  return rows.value.reduce((sum, item) => sum + (item[key] || 0), 0) / rows.value.length
}

const loadEvaluations = async () => {
  selected.value = null
  try {
    if (scenarioId.value) {
      scenarioResults.value = await api.getScenarioResults(scenarioId.value)
      evaluations.value = []
      return
    }
    scenarioResults.value = null
    evaluations.value = await api.getEvaluations()
  } catch (e) {
    console.error(e)
  }
}

onMounted(loadEvaluations)
watch(scenarioId, loadEvaluations)

const ScorePill = defineComponent({
  props: { score: { type: Number, required: true } },
  setup(props) {
    const cls = computed(() => {
      if (props.score < 0.3) return 'bg-success/10 text-success'
      if (props.score < 0.6) return 'bg-warning/10 text-warning'
      if (props.score < 0.8) return 'bg-orange-500/10 text-orange-400'
      return 'bg-danger/10 text-danger'
    })
    return () => h('span', { class: `px-2 py-0.5 rounded text-xs font-semibold ${cls.value}` }, `${(props.score * 100).toFixed(0)}%`)
  }
})
</script>

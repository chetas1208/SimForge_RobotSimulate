<template>
  <div class="space-y-6 animate-fade-in">

    <!-- Score summary -->
    <div v-if="evaluations.length" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <ScoreCard label="Collision Risk"   :score="avgScore('collision_risk_score')" description="Robot-human collision likelihood" />
      <ScoreCard label="Occlusion"        :score="avgScore('occlusion_score')"      description="Sensor field obstruction" />
      <ScoreCard label="Path Conflict"    :score="avgScore('path_conflict_score')"  description="Route intersection intensity" />
      <ScoreCard label="Severity"         :score="avgScore('severity_score')"       description="Overall edge-case severity" />
      <ScoreCard label="Diversity"        :score="avgScore('diversity_score')"      description="Scenario variation coverage" />
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">
      <div class="px-6 py-4 border-b border-surface-800/40">
        <h3 class="section-title">Evaluation Reports</h3>
      </div>

      <div v-if="evaluations.length" class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-surface-800/40">
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
            <tr
              v-for="e in evaluations"
              :key="e.id"
              class="table-row cursor-pointer"
              :class="selected?.id === e.id ? 'bg-surface-800/30' : ''"
              @click="selected = selected?.id === e.id ? null : e"
            >
              <td class="table-cell">
                <span class="font-mono text-xs text-surface-400 bg-surface-800/50 px-2 py-0.5 rounded-lg">{{ e.job_id.slice(0, 12) }}…</span>
              </td>
              <td class="table-cell"><ScorePill :score="e.collision_risk_score" /></td>
              <td class="table-cell"><ScorePill :score="e.occlusion_score" /></td>
              <td class="table-cell"><ScorePill :score="e.path_conflict_score" /></td>
              <td class="table-cell"><ScorePill :score="e.severity_score" /></td>
              <td class="table-cell"><ScorePill :score="e.diversity_score" /></td>
              <td class="table-cell text-xs text-surface-400">{{ (e.top_risk_factors || []).length }} factors</td>
            </tr>
          </tbody>
        </table>
      </div>

      <EmptyState v-else title="No evaluations yet" description="Evaluations are generated automatically after simulation runs complete." />
    </div>

    <!-- Detail panel -->
    <div v-if="selected" class="card p-6 animate-slide-up">
      <div class="flex items-center justify-between mb-5">
        <div>
          <h3 class="section-title">Evaluation Detail</h3>
          <p class="text-xs text-surface-500 mt-0.5 font-mono">{{ selected.job_id.slice(0, 20) }}…</p>
        </div>
        <button class="btn-icon" @click="selected = null">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Explanation -->
      <div class="bg-surface-950/60 rounded-xl p-4 font-mono text-sm text-surface-300 whitespace-pre-line mb-5 border border-surface-800/50 leading-relaxed">
        {{ selected.explanation }}
      </div>

      <!-- Risk factors + actions -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 class="text-xs font-semibold text-surface-500 uppercase tracking-widest mb-3">Top Risk Factors</h4>
          <ul class="space-y-2">
            <li
              v-for="r in (selected.top_risk_factors || [])"
              :key="r"
              class="flex items-start gap-2.5 text-sm text-surface-300"
            >
              <svg class="w-4 h-4 text-danger mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
              </svg>
              {{ r }}
            </li>
          </ul>
        </div>
        <div>
          <h4 class="text-xs font-semibold text-surface-500 uppercase tracking-widest mb-3">Recommended Actions</h4>
          <ul class="space-y-2">
            <li
              v-for="a in (selected.recommended_actions || [])"
              :key="a"
              class="flex items-start gap-2.5 text-sm text-surface-300"
            >
              <svg class="w-4 h-4 text-forge-400 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
              {{ a }}
            </li>
          </ul>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { defineComponent, h, computed } from 'vue'

const api         = useApi()
const evaluations = ref<any[]>([])
const selected    = ref<any>(null)

const avgScore = (key: string) => {
  if (!evaluations.value.length) return 0
  return evaluations.value.reduce((sum, e) => sum + (e[key] || 0), 0) / evaluations.value.length
}

const ScorePill = defineComponent({
  props: { score: { type: Number, required: true } },
  setup(props) {
    const cls = computed(() => {
      if (props.score < 0.3) return 'bg-success/10 text-success border-success/20'
      if (props.score < 0.6) return 'bg-warning/10 text-warning border-warning/20'
      if (props.score < 0.8) return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
      return 'bg-danger/10 text-danger border-danger/20'
    })
    return () => h('span', { class: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold border tabular-nums ${cls.value}` },
      `${(props.score * 100).toFixed(0)}%`)
  },
})

onMounted(async () => {
  try { evaluations.value = await api.getEvaluations() } catch (e) { console.error(e) }
})
</script>

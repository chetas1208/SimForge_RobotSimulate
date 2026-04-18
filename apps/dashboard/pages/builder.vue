<template>
  <div class="max-w-3xl mx-auto animate-fade-in">

    <!-- ── Step indicator ─────────────────────────────────── -->
    <div class="mb-8">
      <div class="flex items-center gap-0">
        <template v-for="(step, i) in steps" :key="i">
          <button
            class="flex items-center gap-2 transition-all duration-200"
            @click="currentStep = i"
          >
            <div
              :class="[
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-200 border',
                i < currentStep  ? 'bg-forge-600 border-forge-600 text-white' :
                i === currentStep ? 'bg-forge-500/15 border-forge-500 text-forge-300' :
                                    'bg-surface-800/60 border-surface-700/40 text-surface-500'
              ]"
            >
              <svg v-if="i < currentStep" class="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              <span v-else>{{ i + 1 }}</span>
            </div>
            <span
              :class="[
                'text-xs font-medium hidden sm:block transition-colors',
                i === currentStep ? 'text-forge-300' : i < currentStep ? 'text-surface-400' : 'text-surface-600'
              ]"
            >{{ step }}</span>
          </button>
          <div v-if="i < steps.length - 1" class="flex-1 h-px mx-3" :class="i < currentStep ? 'bg-forge-600/40' : 'bg-surface-800'"></div>
        </template>
      </div>
    </div>

    <!-- ── Step content ───────────────────────────────────── -->

    <!-- Step 1: Basic Info -->
    <div v-show="currentStep === 0" class="card p-7 animate-slide-up space-y-5">
      <div>
        <h3 class="section-title mb-1">Basic Information</h3>
        <p class="text-sm text-surface-500">Name and describe your simulation scenario.</p>
      </div>
      <div class="space-y-4 pt-2">
        <div>
          <label class="label-text">Scenario Name *</label>
          <input v-model="form.name" class="input-field" placeholder="e.g. Blind Corner Human Crossing" />
        </div>
        <div>
          <label class="label-text">Description</label>
          <textarea v-model="form.description" rows="3" class="input-field" placeholder="Describe the edge case being tested…"></textarea>
        </div>
        <div>
          <label class="label-text">Notes</label>
          <textarea v-model="form.notes" rows="2" class="input-field" placeholder="Internal notes…"></textarea>
        </div>
      </div>
    </div>

    <!-- Step 2: Environment -->
    <div v-show="currentStep === 1" class="card p-7 animate-slide-up space-y-5">
      <div>
        <h3 class="section-title mb-1">Environment Setup</h3>
        <p class="text-sm text-surface-500">Choose the warehouse layout and robot path type.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        <div>
          <label class="label-text">Environment Template</label>
          <select v-model="form.environment_template" class="select-field">
            <option value="warehouse_aisle">Warehouse Aisle</option>
            <option value="warehouse_open_floor">Open Floor</option>
            <option value="warehouse_loading_dock">Loading Dock</option>
            <option value="warehouse_cold_storage">Cold Storage</option>
          </select>
        </div>
        <div>
          <label class="label-text">Robot Path Type</label>
          <select v-model="form.robot_path_type" class="select-field">
            <option value="left_turn_blind_corner">Left Turn (Blind Corner)</option>
            <option value="right_turn_blind_corner">Right Turn (Blind Corner)</option>
            <option value="straight_aisle">Straight Aisle</option>
            <option value="t_junction">T-Junction</option>
            <option value="cross_intersection">Cross Intersection</option>
            <option value="u_turn">U-Turn</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Step 3: Hazards -->
    <div v-show="currentStep === 2" class="card p-7 animate-slide-up space-y-6">
      <div>
        <h3 class="section-title mb-1">Hazard Configuration</h3>
        <p class="text-sm text-surface-500">Configure the types and probabilities of hazards.</p>
      </div>
      <div class="space-y-6 pt-2">
        <div>
          <div class="flex items-center justify-between mb-3">
            <label class="label-text mb-0">Human Crossing Probability</label>
            <span class="text-sm font-semibold text-forge-300 tabular-nums">{{ (form.human_crossing_probability * 100).toFixed(0) }}%</span>
          </div>
          <input type="range" v-model.number="form.human_crossing_probability" min="0" max="1" step="0.05" />
          <div class="flex justify-between text-xs text-surface-600 mt-1.5"><span>0%</span><span>100%</span></div>
        </div>
        <div>
          <label class="label-text">Dropped Obstacle Level</label>
          <select v-model="form.dropped_obstacle_level" class="select-field">
            <option value="none">None</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="extreme">Extreme</option>
          </select>
        </div>
        <div class="flex items-center gap-3 pt-1">
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" v-model="form.blocked_aisle_enabled" class="sr-only peer" />
            <div class="relative w-11 h-6 bg-surface-700 peer-checked:bg-forge-600 rounded-full transition-colors duration-200 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
          </label>
          <span class="text-sm text-surface-300 font-medium">Blocked Aisle Enabled</span>
        </div>
      </div>
    </div>

    <!-- Step 4: Dynamics -->
    <div v-show="currentStep === 3" class="card p-7 animate-slide-up space-y-5">
      <div>
        <h3 class="section-title mb-1">Dynamics & Timing</h3>
        <p class="text-sm text-surface-500">Configure lighting conditions and camera settings.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        <div>
          <label class="label-text">Lighting Preset</label>
          <select v-model="form.lighting_preset" class="select-field">
            <option value="normal">Normal</option>
            <option value="low_light">Low Light</option>
            <option value="high_contrast">High Contrast</option>
            <option value="flickering">Flickering</option>
            <option value="emergency">Emergency</option>
          </select>
        </div>
        <div>
          <label class="label-text">Camera Mode</label>
          <select v-model="form.camera_mode" class="select-field">
            <option value="overhead">Overhead</option>
            <option value="follow">Follow</option>
            <option value="fixed_angle">Fixed Angle</option>
            <option value="first_person">First Person</option>
            <option value="multi_view">Multi-View</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Step 5: Variants -->
    <div v-show="currentStep === 4" class="card p-7 animate-slide-up space-y-6">
      <div>
        <h3 class="section-title mb-1">Variant Settings</h3>
        <p class="text-sm text-surface-500">Set how many scenario variations to generate.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        <div>
          <div class="flex items-center justify-between mb-3">
            <label class="label-text mb-0">Variant Count</label>
            <span class="text-sm font-semibold text-forge-300 tabular-nums">{{ form.variant_count }}</span>
          </div>
          <input type="range" v-model.number="form.variant_count" min="1" max="50" step="1" />
          <div class="flex justify-between text-xs text-surface-600 mt-1.5"><span>1</span><span>50</span></div>
        </div>
        <div>
          <label class="label-text">Random Seed</label>
          <input v-model.number="form.random_seed" type="number" class="input-field" />
        </div>
      </div>
    </div>

    <!-- Step 6: Summary -->
    <div v-show="currentStep === 5" class="card p-7 animate-slide-up">
      <div class="mb-5">
        <h3 class="section-title mb-1">Summary</h3>
        <p class="text-sm text-surface-500">Review your configuration before creating.</p>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-0">
        <div v-for="[key, val] in summaryItems" :key="key" class="flex justify-between py-3 border-b border-surface-800/40 last:border-0">
          <span class="text-xs text-surface-500 font-medium">{{ key }}</span>
          <span class="text-xs text-white font-semibold text-right max-w-[180px] truncate">{{ val }}</span>
        </div>
      </div>
    </div>

    <!-- ── Navigation ─────────────────────────────────────── -->
    <div class="flex items-center justify-between mt-6">
      <button
        class="btn-secondary"
        :class="currentStep === 0 ? 'opacity-40 pointer-events-none' : ''"
        @click="currentStep = Math.max(0, currentStep - 1)"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back
      </button>

      <div class="flex items-center gap-2">
        <span class="text-xs text-surface-600">{{ currentStep + 1 }} / {{ steps.length }}</span>
      </div>

      <button v-if="currentStep < steps.length - 1" class="btn-primary" @click="currentStep++">
        Next
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
        </svg>
      </button>
      <button v-else class="btn-primary" :disabled="saving" @click="submitScenario">
        <svg v-if="!saving" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ saving ? 'Creating…' : 'Create Scenario' }}
      </button>
    </div>

  </div>
</template>

<script setup lang="ts">
const api = useApi()
const router = useRouter()

const steps = ['Basic Info', 'Environment', 'Hazards', 'Dynamics', 'Variants', 'Summary']
const currentStep = ref(0)
const saving      = ref(false)

const form = reactive({
  name:                      '',
  description:               '',
  notes:                     '',
  environment_template:      'warehouse_aisle',
  robot_path_type:           'left_turn_blind_corner',
  human_crossing_probability: 0.5,
  dropped_obstacle_level:    'medium',
  blocked_aisle_enabled:     false,
  lighting_preset:           'normal',
  camera_mode:               'overhead',
  variant_count:             5,
  random_seed:               42,
})

const summaryItems = computed(() => [
  ['Name',            form.name || '—'],
  ['Environment',     form.environment_template],
  ['Path Type',       form.robot_path_type],
  ['Human Prob.',     `${(form.human_crossing_probability * 100).toFixed(0)}%`],
  ['Obstacle Level',  form.dropped_obstacle_level],
  ['Blocked Aisle',   form.blocked_aisle_enabled ? 'Yes' : 'No'],
  ['Lighting',        form.lighting_preset],
  ['Camera',          form.camera_mode],
  ['Variants',        form.variant_count],
  ['Seed',            form.random_seed],
])

const submitScenario = async () => {
  if (!form.name.trim()) { currentStep.value = 0; return }
  saving.value = true
  try {
    await api.createScenario({ ...form })
    router.push('/scenarios')
  } catch (e) { console.error(e) }
  saving.value = false
}
</script>

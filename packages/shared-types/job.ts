// Shared TypeScript types — Jobs

export type JobStatus = 'queued' | 'preparing' | 'running' | 'rendering' | 'completed' | 'failed'
export type ProviderType = 'mock' | 'isaac' | 'track4'

export interface SimulationJob {
  id: string
  scenario_id: string
  variant_id: string | null
  provider_type: ProviderType
  mode: string
  status: JobStatus
  submitted_at: string
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  log_path: string | null
  error_message: string | null
}

export interface ScenarioVariant {
  id: string
  scenario_id: string
  variant_index: number
  variant_parameters: Record<string, any>
  deterministic_seed: number
  status: string
  created_at: string
}

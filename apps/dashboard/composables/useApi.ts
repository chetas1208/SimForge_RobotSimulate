/**
 * API composable for SimForge dashboard.
 */
export const useApi = () => {
  const config = useRuntimeConfig()
  const baseUrl = config.public.apiBaseUrl as string

  const apiFetch = async <T = any>(path: string, options: any = {}): Promise<T> => {
    const url = `${baseUrl}${path}`
    try {
      const data = await $fetch<T>(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })
      return data
    } catch (error: any) {
      console.error(`API Error [${path}]:`, error)
      throw error
    }
  }

  return {
    // Health
    health: () => apiFetch('/health'),

    // Scenarios
    getScenarios: () => apiFetch('/scenarios'),
    getScenario: (id: string) => apiFetch(`/scenarios/${id}`),
    createScenario: (data: any) => apiFetch('/scenarios', { method: 'POST', body: data }),
    updateScenario: (id: string, data: any) => apiFetch(`/scenarios/${id}`, { method: 'PUT', body: data }),
    deleteScenario: (id: string) => apiFetch(`/scenarios/${id}`, { method: 'DELETE' }),
    compileScenario: (id: string) => apiFetch(`/scenarios/${id}/compile`, { method: 'POST' }),
    getVariants: (id: string) => apiFetch(`/scenarios/${id}/variants`),
    getScenarioResults: (id: string) => apiFetch(`/scenarios/${id}/results`),

    // Runs / Jobs
    submitRun: (scenarioId: string) => apiFetch(`/scenarios/${scenarioId}/run`, { method: 'POST' }),
    getJobs: (params?: any) => apiFetch('/jobs', { params }),
    getJob: (id: string) => apiFetch(`/jobs/${id}`),
    retryJob: (id: string) => apiFetch(`/jobs/${id}/retry`, { method: 'POST' }),

    // Artifacts
    getArtifacts: () => apiFetch('/artifacts'),
    getArtifact: (id: string) => apiFetch(`/artifacts/${id}`),
    getJobArtifacts: (jobId: string) => apiFetch(`/jobs/${jobId}/artifacts`),
    getArtifactDownloadUrl: (artifactId: string) => `${baseUrl}/artifacts/${artifactId}/download`,
    getScenarioExportUrl: (scenarioId: string) => `${baseUrl}/scenarios/${scenarioId}/export`,

    // Evaluations
    getEvaluations: () => apiFetch('/evaluations'),
    getJobEvaluation: (jobId: string) => apiFetch(`/jobs/${jobId}/evaluation`),

    // Activity
    getActivity: (limit = 50) => apiFetch('/activity', { params: { limit } }),

    // Settings
    getSettings: () => apiFetch('/settings'),
    updateSettings: (data: any) => apiFetch('/settings', { method: 'PUT', body: data }),
  }
}

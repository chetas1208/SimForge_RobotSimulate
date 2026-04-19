// Shared TypeScript types — Artifacts

export type ArtifactType =
  | 'preview_video'
  | 'preview_image'
  | 'manifest_json'
  | 'config_json'
  | 'feature_json'
  | 'labels_json'
  | 'evaluation_json'
  | 'log_file'
  | 'usd_scene'
  | 'prompt_json'

export interface OutputArtifact {
  id: string
  job_id: string
  artifact_type: ArtifactType
  file_path: string
  preview_path: string | null
  download_url?: string
  metadata: Record<string, any>
  created_at: string
}

export type Region = [number, number, number, number]
export type Source = {
  id: string
  name: string
  camera_index: number
  roi: Region
  confidence: number
  motion_threshold: number
}
export type MonitorStatus = {
  state: MonitorPhase
  error: string | null
  people: number
  people_in_region: number
  motion: boolean
  motion_score: number
  warming_up: boolean
  inference_ms: number
  frame_age_ms: number
  processed_frames: number
  analysis_fps: number
  occurrence_id: string | null
  session_id: string | null
}
export type Review = { id: string; decision: ReviewDecision; note: string; created_at: string }
export type Evidence = { id: string; kind: string; captured_at: string }
export type Observation = {
  id: string
  captured_at: string
  person_count: number
  motion_score: number
  analysis_status: string
}
export type Occurrence = {
  id: string
  started_at: string
  ended_at: string | null
  last_activity_at: string
  status: string
  classification: Classification
  peak_people: number
  summary: { valid_samples?: number; max_analysis_gap_seconds?: number; analysis_failed?: boolean }
  evidence_id?: string | null
  review?: Review | null
  evidence?: Evidence[]
  observations?: Observation[]
  reviews?: Review[]
}
export type Page = { items: Occurrence[]; total: number; page: number; page_size: number }

export type View = 'monitor' | 'history' | 'settings'
export type MonitorPhase = 'idle' | 'starting' | 'running' | 'stopping' | 'error'
export type Classification = 'person_detected' | 'no_person_detected' | 'inconclusive'
export type ReviewDecision = 'person_present' | 'no_person' | 'uncertain'

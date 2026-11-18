export type Region = [number, number, number, number]
export type Source = { id: string; name: string; camera_index: number; roi: Region; confidence: number; motion_threshold: number }
export type MonitorStatus = {
  state: string; error: string | null; people: number; people_in_region: number;
  motion: boolean; motion_score: number; warming_up: boolean; inference_ms: number;
  frame_age_ms: number; processed_frames: number; analysis_fps: number;
  occurrence_id: string | null; session_id: string | null;
}
export type Review = { id: string; decision: string; note: string; created_at: string }
export type Evidence = { id: string; kind: string; captured_at: string }
export type Observation = { id: string; captured_at: string; person_count: number; motion_score: number; analysis_status: string }
export type Occurrence = {
  id: string; started_at: string; ended_at: string | null; last_activity_at: string;
  status: string; classification: string; peak_people: number;
  summary: { valid_samples?: number; max_analysis_gap_seconds?: number; analysis_failed?: boolean };
  evidence_id?: string | null; review?: Review | null;
  evidence?: Evidence[]; observations?: Observation[]; reviews?: Review[];
}
export type Page = { items: Occurrence[]; total: number; page: number; page_size: number }

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method, headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    let message = `Request failed (${response.status}).`
    try {
      const error = await response.json()
      message = typeof error.detail === 'string' ? error.detail : 'Check the form values and try again.'
    } catch { /* Keep a useful message when the backend is unreachable. */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export const labels: Record<string, string> = {
  person_detected: 'Person detected', no_person_detected: 'No person detected', inconclusive: 'Inconclusive',
  person_present: 'Person present', no_person: 'No person visible', uncertain: 'Uncertain',
}
export const date = (value: string) => new Date(value).toLocaleString('en', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })

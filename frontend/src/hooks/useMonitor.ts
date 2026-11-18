import { useCallback, useState } from 'react'
import { api } from '../api'
import type { MonitorStatus } from '../types'
import { usePollingTask } from './usePollingTask'

const INITIAL_STATUS: MonitorStatus = {
  state: 'idle',
  error: null,
  people: 0,
  people_in_region: 0,
  motion: false,
  motion_score: 0,
  warming_up: false,
  inference_ms: 0,
  frame_age_ms: 0,
  processed_frames: 0,
  analysis_fps: 0,
  occurrence_id: null,
  session_id: null,
}

export function useMonitor() {
  const [status, setStatus] = useState(INITIAL_STATUS)
  const [connected, setConnected] = useState(true)
  const poll = useCallback(async (signal: AbortSignal) => {
    try {
      const value = await api<MonitorStatus>('/monitor/status', 'GET', undefined, signal)
      if (!signal.aborted) {
        setStatus(value)
        setConnected(true)
      }
    } catch {
      if (!signal.aborted) setConnected(false)
    }
  }, [])
  usePollingTask(poll, 1000)
  const control = async (command: 'start' | 'stop') => {
    setStatus(await api<MonitorStatus>(`/monitor/${command}`, 'POST'))
  }
  return { status, connected, control }
}

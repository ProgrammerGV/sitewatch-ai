import { useCallback, useState } from 'react'
import { usePollingTask } from './usePollingTask'

type Health = { database: boolean; model_available: boolean }

export function useHealth() {
  const [health, setHealth] = useState<Health>({ database: false, model_available: false })
  const poll = useCallback(async (signal: AbortSignal) => {
    try {
      // A readiness response can be 503 and still contain valid diagnostic data.
      const response = await fetch('/health/ready', { signal })
      const value: Health = await response.json()
      if (!signal.aborted) setHealth(value)
    } catch {
      if (!signal.aborted) setHealth({ database: false, model_available: false })
    }
  }, [])
  usePollingTask(poll, 5000)
  return { dbOk: health.database, modelOk: health.model_available }
}

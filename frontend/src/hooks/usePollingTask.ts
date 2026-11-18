import { useEffect } from 'react'

/** Schedule one request at a time and cancel it when the owner unmounts or changes. */
export function usePollingTask(task: (signal: AbortSignal) => Promise<void>, intervalMs: number) {
  useEffect(() => {
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    const tick = async () => {
      await task(controller.signal)
      if (!controller.signal.aborted) timer = setTimeout(() => void tick(), intervalMs)
    }
    void tick()
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [task, intervalMs])
}

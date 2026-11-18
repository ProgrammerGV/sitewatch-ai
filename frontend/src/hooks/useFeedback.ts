import { useCallback, useEffect, useState } from 'react'

const NOTICE_DURATION_MS = 4000

export function useFeedback() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const reportError = useCallback((error: unknown) => {
    setError(error instanceof Error ? error.message : 'The operation could not be completed.')
  }, [])
  const dismissError = useCallback(() => setError(''), [])

  useEffect(() => {
    if (!notice) return
    const timer = setTimeout(() => setNotice(''), NOTICE_DURATION_MS)
    return () => clearTimeout(timer)
  }, [notice])

  const run = useCallback(
    async (operation: () => Promise<unknown>, success?: string) => {
      setBusy(true)
      setError('')
      try {
        await operation()
        if (success) setNotice(success)
      } catch (error) {
        reportError(error)
      } finally {
        setBusy(false)
      }
    },
    [reportError],
  )

  return { busy, error, notice, reportError, dismissError, run }
}

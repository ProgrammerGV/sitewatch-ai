export async function api<T>(
  path: string,
  method = 'GET',
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    signal,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    let message = `Request failed (${response.status}).`
    try {
      const error = await response.json()
      message =
        typeof error.detail === 'string' ? error.detail : 'Check the form values and try again.'
    } catch {
      /* Keep a useful message when the backend is unreachable. */
    }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

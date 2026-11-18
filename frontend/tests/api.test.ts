import assert from 'node:assert/strict'
import { afterEach, mock, test } from 'node:test'
import { api } from '../src/api.ts'

afterEach(() => mock.restoreAll())

test('sends JSON mutations with the cancellation signal intact', async () => {
  const controller = new AbortController()
  mock.method(globalThis, 'fetch', async (url: string, options: RequestInit) => {
    assert.equal(url, '/api/source')
    assert.equal(options.method, 'PATCH')
    assert.equal(options.signal, controller.signal)
    assert.equal(options.body, JSON.stringify({ name: 'Test source' }))
    assert.equal((options.headers as Record<string, string>)['Content-Type'], 'application/json')
    return new Response(JSON.stringify({ saved: true }), { status: 200 })
  })
  assert.deepEqual(await api('/source', 'PATCH', { name: 'Test source' }, controller.signal), { saved: true })
})

test('preserves a useful backend failure message', async () => {
  mock.method(globalThis, 'fetch', async () => new Response(JSON.stringify({ detail: 'Stop monitoring first.' }), { status: 409 }))
  await assert.rejects(api('/source', 'PATCH', {}), /Stop monitoring first/)
})

test('handles a proxy failure that returns HTML instead of JSON', async () => {
  mock.method(globalThis, 'fetch', async () => new Response('<html>Unavailable</html>', { status: 502 }))
  await assert.rejects(api('/monitor/status'), /Request failed \(502\)/)
})

test('lets cancellation reach the caller without turning it into a backend error', async () => {
  const aborted = new DOMException('Request aborted.', 'AbortError')
  mock.method(globalThis, 'fetch', async () => { throw aborted })
  await assert.rejects(api('/monitor/status'), error => error === aborted)
})

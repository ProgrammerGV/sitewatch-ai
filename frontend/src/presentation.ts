export const labels: Record<string, string> = {
  person_detected: 'Person detected',
  no_person_detected: 'No person detected',
  inconclusive: 'Inconclusive',
  person_present: 'Person present',
  no_person: 'No person visible',
  uncertain: 'Uncertain',
}
export const date = (value: string) =>
  new Date(value).toLocaleString('en', {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

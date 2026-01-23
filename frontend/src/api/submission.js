import { getCookie } from './http'

export async function submitSolution(problemId, file) {
  const formData = new FormData()
  formData.append('problem_id', problemId)
  formData.append('file', file)

  const csrftoken = getCookie('csrftoken');
  const res = await fetch('/api/submissions/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': csrftoken
    },
    body: formData,
    credentials: 'include'
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(`API Error: ${res.status} — ${errorText}`)
  }

  return await res.json()
}

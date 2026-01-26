import { ensureCsrfToken } from './http'

export async function submitSolution(problemId, file) {
  const formData = new FormData()
  formData.append('problem_id', problemId)
  formData.append('file', file)

  const csrftoken = await ensureCsrfToken();
  const res = await fetch('/api/submissions/', {
    method: 'POST',
    headers: {
      ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {})
    },
    body: formData,
    credentials: 'include'
  })

  if (!res.ok) {
    let errorMessage = `API Error: ${res.status}`
    const errorText = await res.text()
    if (errorText) {
      try {
        const errorData = JSON.parse(errorText)
        if (errorData.message) {
          errorMessage = errorData.message
        } else if (errorData.detail) {
          errorMessage = errorData.detail
        } else if (typeof errorData === 'object') {
          errorMessage = JSON.stringify(errorData)
        } else {
          errorMessage = errorText
        }
      } catch {
        errorMessage = errorText
      }
    }
    throw new Error(errorMessage)
  }

  return await res.json()
}

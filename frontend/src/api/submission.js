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
    let errorMessage = `API Error: ${res.status}`
    try {
      const errorData = await res.json()
      if (errorData.message) {
        errorMessage = errorData.message
      } else if (errorData.detail) {
        errorMessage = errorData.detail
      } else if (typeof errorData === 'object') {
        errorMessage = JSON.stringify(errorData)
      }
    } catch {
      // If JSON parsing fails, try text
      try {
        const errorText = await res.text()
        if (errorText) {
          errorMessage = errorText
        }
      } catch {
        // Use default error message
      }
    }
    throw new Error(errorMessage)
  }

  return await res.json()
}

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
        } else if (typeof errorData === 'object' && errorData !== null) {
          // Extract first error message from validation errors
          const values = Object.values(errorData)
          if (values.length > 0) {
            const firstVal = values[0]
            if (Array.isArray(firstVal) && firstVal.length > 0) {
              errorMessage = String(firstVal[0])
            } else if (typeof firstVal === 'string') {
              errorMessage = firstVal
            } else {
              errorMessage = JSON.stringify(errorData)
            }
          } else {
            errorMessage = JSON.stringify(errorData)
          }
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

export async function getProblemSubmissions(problemId, page = 1) {
  const res = await fetch(`/api/submissions/problem/${problemId}/?page=${page}`, {
    method: 'GET',
    credentials: 'include'
  })

  if (!res.ok) {
    let errorMessage = `API Error: ${res.status}`
    const errorText = await res.text()
    if (errorText) {
      try {
        const errorData = JSON.parse(errorText)
        errorMessage = errorData.detail || errorData.message || errorText
      } catch {
        errorMessage = errorText
      }
    }
    throw new Error(errorMessage)
  }

  return await res.json()
}

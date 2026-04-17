import { ensureCsrfToken } from './http'
import { toApiError } from './error'

async function fetchJsonWithFriendlyErrors(url, options = {}) {
  let res
  try {
    res = await fetch(url, options)
  } catch (_) {
    throw new Error('Не удалось связаться с сервером. Проверьте соединение и попробуйте снова.')
  }

  if (!res.ok) {
    const errorText = await res.text()
    throw toApiError(res.status, errorText)
  }

  return await res.json()
}

export async function submitSolution(problemId, payload = {}) {
  const { file = null, rawText = '', contestId = null } = payload
  const formData = new FormData()
  formData.append('problem_id', problemId)
  if (contestId != null && contestId !== '') {
    formData.append('contest_id', contestId)
  }
  if (file) {
    formData.append('file', file)
  }
  if (typeof rawText === 'string' && rawText.length > 0) {
    formData.append('raw_text', rawText)
  }

  const csrftoken = await ensureCsrfToken()
  return await fetchJsonWithFriendlyErrors('/api/submissions/', {
    method: 'POST',
    headers: {
      ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {})
    },
    body: formData,
    credentials: 'include'
  })
}

export async function getSubmission(submissionId, { contestId = null } = {}) {
  const params = new URLSearchParams()
  if (contestId != null && contestId !== '') {
    params.set('contest_id', String(contestId))
  }
  const query = params.toString()
  const url = query
    ? `/api/submissions/${submissionId}/?${query}`
    : `/api/submissions/${submissionId}/`

  return await fetchJsonWithFriendlyErrors(url, {
    method: 'GET',
    credentials: 'include'
  })
}

export async function getProblemSubmissions(problemId, page = 1) {
  return await fetchJsonWithFriendlyErrors(`/api/submissions/problem/${problemId}/?page=${page}`, {
    method: 'GET',
    credentials: 'include'
  })
}

export async function getMySubmissions() {
  return await fetchJsonWithFriendlyErrors('/api/submissions/mine/', {
    method: 'GET',
    credentials: 'include'
  })
}

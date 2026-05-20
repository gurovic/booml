const NETWORK_ERROR_MESSAGE = 'Не удалось связаться с сервером.'

function getAccessToken() {
  try {
    const user = JSON.parse(localStorage.getItem('currentUser'))
    return user?.accessToken || null
  } catch (_) {
    return null
  }
}

async function guardedFetch(url, init) {
  try {
    return await fetch(url, init)
  } catch (_) {
    throw new Error(NETWORK_ERROR_MESSAGE)
  }
}

export async function apiGet(endpoint) {
  const cleanEndpoint = endpoint.replace(/^\/+/, '')
  const headers = { 'Content-Type': 'application/json' }
  const token = getAccessToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await guardedFetch(`/${cleanEndpoint}`, {
    method: 'GET',
    headers,
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
  return await res.json()
}

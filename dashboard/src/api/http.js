const NETWORK_ERROR_MESSAGE = 'Не удалось связаться с сервером.'

async function guardedFetch(url, init) {
  try {
    return await fetch(url, init)
  } catch (_) {
    throw new Error(NETWORK_ERROR_MESSAGE)
  }
}

export async function apiGet(endpoint) {
  const cleanEndpoint = endpoint.replace(/^\/+/, '')
  const res = await guardedFetch(`/${cleanEndpoint}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
  return await res.json()
}

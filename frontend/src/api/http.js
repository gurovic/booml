import { toApiError } from './error'

// const API_BASE_RAW = process.env.VUE_APP_API_BASE || '/api'
// Normalize base and strip trailing slash to avoid double slashes.
// const API_BASE = API_BASE_RAW.replace(/\/+$/, '')

const buildUrl = (endpoint, params = {}) => {
  const cleanEndpoint = endpoint.replace(/^\/+/, '')
  const queryString = new URLSearchParams(params).toString()
  return `/${cleanEndpoint}${queryString ? `?${queryString}` : ''}`
}

const NETWORK_ERROR_MESSAGE = 'Не удалось связаться с сервером. Проверьте соединение и попробуйте снова.'

async function guardedFetch(url, init) {
  try {
    return await fetch(url, init)
  } catch (_) {
    throw new Error(NETWORK_ERROR_MESSAGE)
  }
}

async function throwApiError(res) {
  const errorText = await res.text()
  throw toApiError(res.status, errorText)
}

export async function apiGet(endpoint, params = {}) {
  const url = buildUrl(endpoint, params)

  const res = await guardedFetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    },
    credentials: 'include',
  })

  if (!res.ok) {
    await throwApiError(res)
  }

  return await res.json()
}

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

async function ensureCsrfToken() {
  const existing = getCookie('csrftoken');
  if (existing) {
    return existing;
  }

  try {
    const res = await fetch('/backend/csrf-token/', {
      method: 'GET',
      credentials: 'include',
    });
    if (!res.ok) {
      console.error('Failed to fetch CSRF token: non-OK response', {
        status: res.status,
        statusText: res.statusText,
      });
      return null;
    }
    const data = await res.json();
    return data.csrfToken || getCookie('csrftoken');
  } catch (error) {
    console.error('Failed to fetch CSRF token: network or parsing error', error);
    return null;
  }
}

export { getCookie, ensureCsrfToken };

async function apiWrite(method, endpoint, data = {}, options = {}) {
  const csrftoken = await ensureCsrfToken()
  const url = buildUrl(endpoint)
  const isFormData = data instanceof FormData
  const headers = {
    ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {}),
    ...(options.headers || {}),
  }
  const hasContentType = Object.keys(headers).some(k => k.toLowerCase() === 'content-type')
  if (!isFormData && !hasContentType) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await guardedFetch(url, {
    ...options,
    method,
    headers,
    body: isFormData ? data : JSON.stringify(data),
    credentials: options.credentials || 'include',
  })

  if (!res.ok) {
    await throwApiError(res)
  }

  return await res.json()
}

export async function apiPost(endpoint, data = {}, options = {}) {
  return await apiWrite('POST', endpoint, data, options)
}

export async function apiPut(endpoint, data = {}, options = {}) {
  return await apiWrite('PUT', endpoint, data, options)
}

export async function apiPatch(endpoint, data = {}, options = {}) {
  return await apiWrite('PATCH', endpoint, data, options)
}

export async function apiDelete(endpoint, data = {}, options = {}) {
  const hasBody = data != null && (!(typeof data === 'object') || Object.keys(data).length > 0)
  if (!hasBody) {
    const csrftoken = await ensureCsrfToken()
    const url = buildUrl(endpoint)
    const headers = {
      ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {}),
      ...(options.headers || {}),
    }
    const res = await guardedFetch(url, {
      ...options,
      method: 'DELETE',
      headers,
      credentials: options.credentials || 'include',
    })
    if (!res.ok) await throwApiError(res)
    if (res.status === 204) return null
    return await res.json()
  }
  // Keep one consistent error/CSRF/json path when body is provided.
  return await apiWrite('DELETE', endpoint, data, options)
}
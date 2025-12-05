const API_BASE_RAW = process.env.VUE_APP_API_BASE || '/api'
// Normalize base and strip trailing slash to avoid double slashes.
const API_BASE = API_BASE_RAW.replace(/\/+$/, '')

const buildUrl = (endpoint, params = {}) => {
  const cleanEndpoint = endpoint.replace(/^\/+/, '')
  const queryString = new URLSearchParams(params).toString()
  return `${API_BASE}/${cleanEndpoint}${queryString ? `?${queryString}` : ''}`
}

export async function apiGet(endpoint, params = {}) {
  const url = buildUrl(endpoint, params)

  const res = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    },
    credentials: 'include',
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(`API Error: ${res.status} — ${errorText}`)
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

export async function apiPost(endpoint, data = {}) {
  const csrftoken = getCookie('csrftoken');
  const url = buildUrl(endpoint)
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrftoken
    },
    body: JSON.stringify({
      ...data
    }),
    credentials: 'include'
  })

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(`API Error: ${res.status} — ${errorText}`)
  }

  const result = await res.json();
  console.log(result);
  return result;
}

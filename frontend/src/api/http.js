// const API_BASE_RAW = process.env.VUE_APP_API_BASE || '/api'
// Normalize base and strip trailing slash to avoid double slashes.
// const API_BASE = API_BASE_RAW.replace(/\/+$/, '')

const buildUrl = (endpoint, params = {}) => {
  const cleanEndpoint = endpoint.replace(/^\/+/, '')
  const queryString = new URLSearchParams(params).toString()
  return `/${cleanEndpoint}${queryString ? `?${queryString}` : ''}`
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

export async function apiPost(endpoint, data = {}, options = {}) {
  const csrftoken = await ensureCsrfToken();
  const url = buildUrl(endpoint)
  
  // Check if data is FormData
  const isFormData = data instanceof FormData;
  
  const headers = {
    ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {}),
    ...(options.headers || {})
  };
  
  // Don't set Content-Type for FormData - browser will set it with boundary
  // Check for Content-Type case-insensitively
  const hasContentType = Object.keys(headers).some(key => key.toLowerCase() === 'content-type');
  if (!isFormData && !hasContentType) {
    headers['Content-Type'] = 'application/json';
  }
  
  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: isFormData ? data : JSON.stringify(data),
    credentials: 'include'
  })

  if (!res.ok) {
    let errorData = null
    try {
      errorData = await res.json()
    } catch {
      const errorText = await res.text()
      throw new Error(`API Error: ${res.status} — ${errorText}`)
    }
    // Throw error with structured data
    const error = new Error(`API Error: ${res.status}`)
    error.response = { status: res.status, data: errorData }
    throw error
  }

  const result = await res.json();
  console.log(result);
  return result;
}

export async function apiPut(endpoint, data = {}) {
  const csrftoken = await ensureCsrfToken();
  const url = buildUrl(endpoint)
  const res = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {})
    },
    body: JSON.stringify(data),
    credentials: 'include'
  })

  if (!res.ok) {
    let errorData = null
    try {
      errorData = await res.json()
    } catch {
      const errorText = await res.text()
      throw new Error(`API Error: ${res.status} — ${errorText}`)
    }
    // Throw error with structured data
    const error = new Error(`API Error: ${res.status}`)
    error.response = { status: res.status, data: errorData }
    throw error
  }

  return await res.json();
}

export async function apiPatch(endpoint, data = {}) {
  const csrftoken = await ensureCsrfToken();
  const url = buildUrl(endpoint)
  const res = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {})
    },
    body: JSON.stringify(data),
    credentials: 'include'
  })

  if (!res.ok) {
    let errorData = null
    try {
      errorData = await res.json()
    } catch {
      const errorText = await res.text()
      throw new Error(`API Error: ${res.status} — ${errorText}`)
    }
    // Throw error with structured data
    const error = new Error(`API Error: ${res.status}`)
    error.response = { status: res.status, data: errorData }
    throw error
  }

  return await res.json();
}

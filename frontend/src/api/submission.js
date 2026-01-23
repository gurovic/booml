function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

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

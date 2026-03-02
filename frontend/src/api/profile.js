import { apiGet, apiPatch } from './http'

export function getCurrentProfile() {
    return apiGet('/backend/profiles/me/')
}

export function getProfileById(userId) {
    return apiGet(`/backend/profiles/${userId}/`)
}

export function getCurrentUser() {
    return apiGet('/backend/user/')
}

export async function getCurrentUserId() {
    const user = await getCurrentUser()
    return user.id
}

export function updateProfileInfo(data) {
    return apiPatch('/backend/profiles/update-info/', data)
}

export async function uploadProfileAvatar(file) {
    const formData = new FormData()
    formData.append('avatar', file)

    const { ensureCsrfToken } = await import('./http')
    const csrftoken = await ensureCsrfToken()

    const response = await fetch('/backend/profiles/update-avatar/', {
        method: 'PATCH',
        headers: {
            ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {})
        },
        body: formData,
        credentials: 'include'
    })

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
}

export async function deleteProfileAvatar() {
    const { ensureCsrfToken } = await import('./http')
    const csrftoken = await ensureCsrfToken()

    const response = await fetch('/backend/profiles/delete-avatar/', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {})
        },
        credentials: 'include'
    })

    if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
}

export function checkAuth() {
    return apiGet('/backend/check-auth/')
}
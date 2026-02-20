// api/profile.js
import { apiGet, apiPatch } from './http'

/**
 * Получение профиля текущего пользователя
 * @returns {Promise<Object>} Данные профиля
 */
export function getCurrentProfile() {
    return apiGet('/backend/profiles/me/')
}

/**
 * Получение профиля по ID пользователя
 * @param {number} userId - ID пользователя
 * @returns {Promise<Object>} Данные профиля
 */
export function getProfileById(userId) {
    return apiGet(`/backend/profiles/${userId}/`)
}

/**
 * Получение информации о текущем пользователе
 * @returns {Promise<Object>} Данные пользователя
 */
export function getCurrentUser() {
    return apiGet('/backend/user/')
}

/**
 * Получение ID текущего пользователя
 * @returns {Promise<number>} ID пользователя
 */
export async function getCurrentUserId() {
    const user = await getCurrentUser()
    return user.id
}


/**
 * Обновление информации профиля - используем PATCH
 * @param {Object} data - Данные для обновления {first_name, last_name}
 * @returns {Promise<Object>} Обновленный профиль
 */
export function updateProfileInfo(data) {
    return apiPatch('/backend/profiles/update-info/', data)
}

/**
 * Загрузка аватара - используем PATCH
 * @param {File} file - Файл изображения
 * @returns {Promise<Object>} Обновленный профиль
 */
export async function uploadProfileAvatar(file) {
    const formData = new FormData()
    formData.append('avatar', file)

    const { ensureCsrfToken } = await import('./http')
    const csrftoken = await ensureCsrfToken()

    const response = await fetch('/backend/profiles/update-avatar/', {
        method: 'PATCH',  // Меняем с POST на PATCH
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

/**
 * Удаление аватара - используем DELETE
 * @returns {Promise<Object>} Обновленный профиль
 */
export async function deleteProfileAvatar() {
    const { ensureCsrfToken } = await import('./http')
    const csrftoken = await ensureCsrfToken()

    const response = await fetch('/backend/profiles/delete-avatar/', {
        method: 'DELETE',  // Меняем с POST на DELETE
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

/**
 * Проверка авторизации
 * @returns {Promise<Object>} Статус авторизации
 */
export function checkAuth() {
    return apiGet('/backend/check-auth/')
}
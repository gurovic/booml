import { apiGet, apiPost } from './http'

export function login(credentials){
    return apiPost('backend/login/', credentials)
}

export async function register(userData){
    if (userData?.teacher_proof) {
        const formData = new FormData()
        Object.entries(userData).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                formData.append(key, value)
            }
        })

        return apiPost('backend/register/', formData)
    }

    return apiPost('backend/register/', userData)
}

export function logout(){
    return apiPost('backend/logout/')
}

export function checkAuth(){
    return apiGet('backend/check-auth/')
}

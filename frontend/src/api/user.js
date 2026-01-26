import { apiGet, apiPost } from './http'

export function login(credentials){
    return apiPost('backend/login/', credentials)
}

export function register(userData){
    return apiPost('backend/register/', userData)
}

export function logout(){
    return apiPost('backend/logout/')
}

export function checkAuth(){
    return apiGet('backend/check-auth/')
}

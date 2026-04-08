import { apiGet} from './http'

export function search(params){
    return apiGet('backend/search/', params)
}
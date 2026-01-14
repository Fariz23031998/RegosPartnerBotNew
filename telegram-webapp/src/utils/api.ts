/**
 * API utility for making requests with the correct base path
 */
const API_BASE = '/regos-partner-bot/api'

export const apiFetch = async (endpoint: string, options?: RequestInit): Promise<Response> => {
  // If endpoint already starts with http/https, use it as-is
  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
    return fetch(endpoint, options)
  }
  
  // If endpoint already includes the base path, use it as-is
  if (endpoint.startsWith(API_BASE)) {
    return fetch(endpoint, options)
  }
  
  // Otherwise, prepend the base path
  const url = endpoint.startsWith('/') ? `${API_BASE}${endpoint}` : `${API_BASE}/${endpoint}`
  return fetch(url, options)
}

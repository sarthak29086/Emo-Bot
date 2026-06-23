/**
 * Frontend Configuration
 * ----------------------
 * Centralized API base URL and other system constants.
 */

export const API_BASE_URL = 'http://localhost:8001';

// Optional: Helper for building full API URLs
export const getApiUrl = (endpoint: string) => {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

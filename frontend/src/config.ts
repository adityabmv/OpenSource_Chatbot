// config.ts
/**
 * Configuration utility for API base URL detection
 * Supports multiple deployment scenarios:
 * 1. Development: localhost:8000
 * 2. Production: Environment variable or same-origin detection
 * 3. Remote deployment: Configurable via environment variables
 */

// Get API base URL from environment variables or auto-detect
const getApiBaseUrl = (): string => {
  // Check for explicit environment variable (window-based for runtime config)
  if (typeof window !== 'undefined' && (window as any).VITE_API_BASE_URL) {
    return (window as any).VITE_API_BASE_URL;
  }

  // In development, use localhost
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  // In production/remote, try to detect from current location
  if (typeof window !== 'undefined') {
    const currentOrigin = window.location.origin;

    // Check if we're likely running on a remote host (not localhost)
    if (!currentOrigin.includes('localhost') && !currentOrigin.includes('127.0.0.1')) {
      // For remote deployments, assume backend is on same host but different port
      // You can customize this logic based on your deployment setup
      const port = window.location.port || '80';
      const backendPort = port === '3000' ? '8000' : port; // Common setup: frontend on 3000, backend on 8000
      return `${currentOrigin.replace(port, backendPort)}`;
    }
  }

  // Default fallback
  return 'http://localhost:8000';
};

export const API_BASE = getApiBaseUrl();

export default {
  API_BASE,
};

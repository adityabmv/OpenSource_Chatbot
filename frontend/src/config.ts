// config.ts
/**
 * Configuration utility for API base URL detection
 * Supports multiple deployment scenarios:
 * 1. Development: localhost:8000
 * 2. Production: Environment variable or same-origin detection
 * 3. Remote deployment: Configurable via environment variables
 */

declare const process: any;

// Get API base URL from environment variables or auto-detect
const getApiBaseUrl = (): string => {
  // Check for React environment variable (embedded at build time)
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }

  // Check for runtime config (for dynamic updates)
  if (typeof window !== 'undefined' && (window as any).REACT_APP_API_URL) {
    return (window as any).REACT_APP_API_URL;
  }

  // In development, use localhost
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  // Default fallback
  return 'http://localhost:8000';
};

export const API_BASE = getApiBaseUrl();

export default {
  API_BASE,
};

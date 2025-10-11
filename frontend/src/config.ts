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
export const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export default {
  API_BASE,
};

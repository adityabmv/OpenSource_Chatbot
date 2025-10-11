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
// Always use ngrok URL for API calls
export const API_BASE = 'http://localhost:8000';

export default {
  API_BASE,
};

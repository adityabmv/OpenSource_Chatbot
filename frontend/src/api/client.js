import axios from 'axios';

// Create axios instance with ngrok headers to skip warning page
const apiClient = axios.create({
  headers: {
    'ngrok-skip-browser-warning': 'true',
    'User-Agent': 'OpenSource-Chatbot/1.0'
  }
});

export default apiClient;
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: "AIzaSyA1812i4zlxb3WacL-Y3OfkMTy5MbSRHkI",
  authDomain: "oschatbot-19c9e.firebaseapp.com",
  projectId: "oschatbot-19c9e",
  storageBucket: "oschatbot-19c9e.firebasestorage.app",
  messagingSenderId: "43985069237",
  appId: "1:43985069237:web:c6d2bb6d431102e9ab8afc",
  measurementId: "G-RK6X72KNXH"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Get Auth instance
export const auth = getAuth(app);

// Get Firestore instance
export const db = getFirestore(app);

export default app;
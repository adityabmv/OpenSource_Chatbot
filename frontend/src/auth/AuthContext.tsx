import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth';
import { auth } from '../firebase/config.ts';

interface AuthContextType {
  user: User | null;
  uid: string | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [uid, setUid] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Listen for auth state changes
    const unsubscribe = auth.onAuthStateChanged((user) => {
      setUser(user);
      setUid(user ? user.uid : null);
      setLoading(false);
    });

    // Cleanup subscription
    return () => unsubscribe();
  }, []);

  const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    try {
      const result = await signInWithPopup(auth, provider);
      console.log("Successfully signed in:", result.user);
    } catch (error: any) {
      console.error("Error signing in with Google:", error);
      console.error("Error code:", error.code);
      console.error("Error message:", error.message);
      
      // Show more specific error messages
      if (error.code === 'auth/popup-closed-by-user') {
        alert("Sign-in was cancelled. Please try again.");
      } else if (error.code === 'auth/popup-blocked') {
        alert("Pop-up was blocked by your browser. Please allow pop-ups and try again.");
      } else if (error.code === 'auth/unauthorized-domain') {
        alert("This domain is not authorized for Google sign-in. Please check Firebase Console settings.");
      } else {
        alert(`Failed to sign in with Google: ${error.message}`);
      }
    }
  };

  const logout = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const value = {
  user,
  uid,
  loading,
  signInWithGoogle,
  logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

import React, { useState } from "react";
import BotDashboard from "./components/BotDashboard.tsx";
import BotChat from "./components/BotChat.tsx";
import { useAuth } from "./auth/AuthContext.tsx";
import { Login } from "./components/Login.tsx";
import { Bot } from './types/bot';


function App() {
  const { user, loading: authLoading, logout } = useAuth();
  const [currentView, setCurrentView] = useState<'dashboard' | 'chat'>('dashboard');
  const [selectedBot, setSelectedBot] = useState<Bot | null>(null);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  const handleBotSelect = (bot: Bot) => {
    setSelectedBot(bot);
    setCurrentView('chat');
  };

  const handleBackToDashboard = () => {
    setCurrentView('dashboard');
    setSelectedBot(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-900 via-zinc-800 to-zinc-900 text-white flex flex-col items-center py-8 px-4">
      <div className="w-full max-w-7xl">
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                RAG Chatbot Platform
              </h1>
              <p className="text-zinc-400 mt-1">{user.email}</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={logout}
                className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>

        {currentView === 'dashboard' && (
          <BotDashboard onBotSelect={handleBotSelect} />
        )}

        {currentView === 'chat' && selectedBot && (
          <BotChat bot={selectedBot} onBack={handleBackToDashboard} />
        )}

        <footer className="mt-8 text-zinc-600 text-xs text-center">
          &copy; {new Date().getFullYear()} RAG Chatbot UI
        </footer>
      </div>
    </div>
  );
}

export default App;

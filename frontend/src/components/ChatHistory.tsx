// ChatHistory.tsx
import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { API_BASE } from '../config.ts';

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: Array<{
    id: string;
    role: string;
    content: string;
    timestamp: string;
  }>;
}

interface ChatHistoryProps {
  botId: string;
  onLoadConversation: (conversationId: string, messages: any[]) => void;
  currentConversationId?: string | null;
  onNewConversation: () => void;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({
  botId,
  onLoadConversation,
  currentConversationId,
  onNewConversation
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showHistory, setShowHistory] = useState(true);

  useEffect(() => {
    loadConversations();
  }, [botId]);

  const loadConversations = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`${API_BASE}/bots/${botId}/chat/conversations`);
      setConversations(response.data.conversations || []);
    } catch (error) {
      console.error('Failed to load conversations:', error);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadConversation = async (conversationId: string) => {
    try {
      const response = await apiClient.get(`${API_BASE}/bots/${botId}/chat/conversations/${conversationId}`);
      const conversation = response.data.conversation;

      // Convert to messages format expected by BotChat
      const messages = conversation.messages.map((msg: any) => ({
        user: msg.role === 'user' ? msg.content : '',
        bot: msg.role === 'assistant' ? msg.content : '...',
        timestamp: new Date(msg.timestamp)
      }));

      onLoadConversation(conversationId, messages);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleDeleteConversation = async (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation();

    if (confirm('Are you sure you want to delete this conversation?')) {
      try {
        await apiClient.delete(`${API_BASE}/bots/${botId}/chat/conversations/${conversationId}`);
        await loadConversations(); // Reload the list
      } catch (error) {
        console.error('Failed to delete conversation:', error);
      }
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffInHours < 168) { // 1 week
      return date.toLocaleDateString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  if (loading) {
    return (
      <div className="w-80 border-r border-zinc-700 bg-zinc-900/30">
        <div className="p-4 border-b border-zinc-700">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Chat History</h3>
            <button
              onClick={() => setShowHistory(false)}
              className="text-zinc-400 hover:text-white"
            >
              ×
            </button>
          </div>
        </div>
        <div className="p-4 text-zinc-400">Loading conversations...</div>
      </div>
    );
  }

  return (
    <div className={`border-r border-zinc-700 bg-zinc-900/30 transition-all duration-200 ${
      showHistory ? 'w-80' : 'w-0 overflow-hidden'
    }`}>
      <div className="p-4 border-b border-zinc-700">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Chat History</h3>
          <div className="flex gap-2">
            <button
              onClick={onNewConversation}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
            >
              New
            </button>
            <button
              onClick={() => setShowHistory(false)}
              className="text-zinc-400 hover:text-white"
            >
              ×
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-zinc-400">
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs mt-1">Start chatting to create your first conversation</p>
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group p-3 mb-2 rounded-lg cursor-pointer transition-all duration-200 ${
                  conv.id === currentConversationId
                    ? 'bg-blue-600/20 border border-blue-500 shadow-md'
                    : 'bg-zinc-800/50 hover:bg-zinc-700/50 border border-transparent hover:border-zinc-600'
                }`}
                onClick={() => handleLoadConversation(conv.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h4 className="text-white text-sm font-medium truncate mb-1">
                      {conv.title}
                    </h4>
                    <div className="flex items-center gap-2 text-xs text-zinc-400">
                      <span>{formatDate(conv.created_at)}</span>
                      <span>•</span>
                      <span>{conv.message_count} messages</span>
                    </div>
                  </div>

                  <button
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-red-400 transition-all duration-200"
                    title="Delete conversation"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatHistory;

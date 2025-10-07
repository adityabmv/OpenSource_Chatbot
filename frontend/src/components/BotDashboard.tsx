// BotDashboard.tsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

interface Bot {
  id: string;
  name: string;
  description: string;
  chunk_size: number;
  chunk_overlap: number;
  embedding_model: string;
  ocr_lang: string;
  created_at: string;
  updated_at: string;
  vectorstore_path: string;
  is_active: boolean;
}

interface BotStats {
  num_chunks: number;
  vectorstore_exists: boolean;
  vectorstore_size_mb: number;
  num_files: number;
}

interface BotWithStats extends Bot {
  stats?: BotStats;
}

const BotDashboard: React.FC<{ onBotSelect: (bot: Bot) => void }> = ({ onBotSelect }) => {
  const [bots, setBots] = useState<BotWithStats[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedBot, setSelectedBot] = useState<Bot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create bot form state
  const [newBot, setNewBot] = useState({
    name: '',
    description: '',
    chunk_size: 500,
    chunk_overlap: 50,
    embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
    ocr_lang: 'eng'
  });

  useEffect(() => {
    loadBots();
  }, []);

  const loadBots = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/bots/active/`);
      const botsData = response.data.bots;

      // Load stats for each bot
      const botsWithStats = await Promise.all(
        botsData.map(async (bot: Bot) => {
          try {
            const statsResponse = await axios.get(`${API_BASE}/bots/${bot.id}/stats`);
            return { ...bot, stats: statsResponse.data.stats };
          } catch {
            return { ...bot, stats: { num_chunks: 0, vectorstore_exists: false, vectorstore_size_mb: 0, num_files: 0 } };
          }
        })
      );

      setBots(botsWithStats);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load bots');
    } finally {
      setLoading(false);
    }
  };

  const createBot = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.post(`${API_BASE}/bots/`, newBot);
      setShowCreateForm(false);
      setNewBot({
        name: '',
        description: '',
        chunk_size: 500,
        chunk_overlap: 50,
        embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
        ocr_lang: 'eng'
      });
      loadBots();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create bot');
    }
  };

  const deleteBot = async (botId: string) => {
    if (!confirm('Are you sure you want to delete this bot? This action cannot be undone.')) {
      return;
    }

    try {
      await axios.delete(`${API_BASE}/bots/${botId}`);
      loadBots();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete bot');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="w-full max-w-6xl mx-auto p-6">
        <div className="text-center text-zinc-400">Loading bots...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full max-w-6xl mx-auto p-6">
        <div className="text-center text-red-400 bg-red-900/20 p-4 rounded-lg border border-red-700">
          Error: {error}
          <button
            onClick={() => setError(null)}
            className="ml-4 px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm"
          >
            Dismiss
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-white">Bot Management</h2>
        <button
          onClick={() => setShowCreateForm(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
        >
          + Create Bot
        </button>
      </div>

      {showCreateForm && (
        <div className="mb-6 p-6 bg-zinc-900/50 rounded-lg border border-zinc-700">
          <h3 className="text-lg font-semibold text-white mb-4">Create New Bot</h3>
          <form onSubmit={createBot} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Bot Name</label>
                <input
                  type="text"
                  value={newBot.name}
                  onChange={(e) => setNewBot({...newBot, name: e.target.value})}
                  className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Description</label>
                <input
                  type="text"
                  value={newBot.description}
                  onChange={(e) => setNewBot({...newBot, description: e.target.value})}
                  className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Chunk Size</label>
                <input
                  type="number"
                  value={newBot.chunk_size}
                  onChange={(e) => setNewBot({...newBot, chunk_size: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="100"
                  max="2000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Chunk Overlap</label>
                <input
                  type="number"
                  value={newBot.chunk_overlap}
                  onChange={(e) => setNewBot({...newBot, chunk_overlap: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="0"
                  max="500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">OCR Language</label>
                <select
                  value={newBot.ocr_lang}
                  onChange={(e) => setNewBot({...newBot, ocr_lang: e.target.value})}
                  className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="eng">English</option>
                  <option value="hin">Hindi</option>
                  <option value="tam">Tamil</option>
                  <option value="tel">Telugu</option>
                  <option value="ben">Bengali</option>
                  <option value="guj">Gujarati</option>
                  <option value="kan">Kannada</option>
                  <option value="mal">Malayalam</option>
                  <option value="mar">Marathi</option>
                  <option value="pan">Punjabi</option>
                  <option value="ori">Odia</option>
                </select>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
              >
                Create Bot
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 bg-zinc-600 hover:bg-zinc-700 text-white rounded-lg font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {bots.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-zinc-400 mb-4">No bots created yet</div>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            Create Your First Bot
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {bots.map((bot) => (
            <div key={bot.id} className="bg-zinc-900/50 rounded-lg border border-zinc-700 p-6">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-white mb-1">{bot.name}</h3>
                  <p className="text-zinc-400 text-sm mb-2">{bot.description || 'No description'}</p>
                  <div className="flex items-center gap-4 text-xs text-zinc-500">
                    <span>Created: {formatDate(bot.created_at)}</span>
                    <span>Updated: {formatDate(bot.updated_at)}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => onBotSelect(bot)}
                    className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium transition-colors"
                  >
                    Select Bot
                  </button>
                  <button
                    onClick={() => deleteBot(bot.id)}
                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-medium transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-zinc-400">Chunk Size</div>
                  <div className="text-white font-medium">{bot.chunk_size}</div>
                </div>
                <div>
                  <div className="text-zinc-400">Chunk Overlap</div>
                  <div className="text-white font-medium">{bot.chunk_overlap}</div>
                </div>
                <div>
                  <div className="text-zinc-400">Embedding Model</div>
                  <div className="text-white font-medium text-xs">{bot.embedding_model.split('/').pop()}</div>
                </div>
                <div>
                  <div className="text-zinc-400">OCR Language</div>
                  <div className="text-white font-medium">{bot.ocr_lang.toUpperCase()}</div>
                </div>
              </div>

              {bot.stats && (
                <div className="mt-4 pt-4 border-t border-zinc-700">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="text-zinc-400">Chunks</div>
                      <div className="text-white font-medium">{bot.stats.num_chunks}</div>
                    </div>
                    <div>
                      <div className="text-zinc-400">Vectorstore Size</div>
                      <div className="text-white font-medium">{bot.stats.vectorstore_size_mb} MB</div>
                    </div>
                    <div>
                      <div className="text-zinc-400">Files</div>
                      <div className="text-white font-medium">{bot.stats.num_files}</div>
                    </div>
                    <div>
                      <div className="text-zinc-400">Status</div>
                      <div className={`font-medium ${bot.stats.vectorstore_exists ? 'text-green-400' : 'text-yellow-400'}`}>
                        {bot.stats.vectorstore_exists ? 'Ready' : 'Not Built'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BotDashboard;

// BotChat.tsx - Updated with Chat History
import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useDropzone } from 'react-dropzone';
import ChatHistory from './ChatHistory.tsx';
import { API_BASE } from '../config.ts';

import { Bot, BotStats } from '../types/bot';

interface BotChatProps {
  bot: Bot;
  onBack: () => void;
}

const BotChat: React.FC<BotChatProps> = ({ bot, onBack }) => {
  const [openRouterApiKey, setOpenRouterApiKey] = useState('');
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Array<{
    user: string, 
    bot: string, 
    timestamp: Date,
    sources?: Array<{
      content: string,
      metadata: {
        source: string,
        page?: number,
        chunk_index: number
      }
    }>
  }>>([]);
  const [loading, setLoading] = useState(false);
  const [llmModel, setLlmModel] = useState('deepseek/deepseek-r1-0528-qwen3-8b:free');
    // Remove availableModels state
  const [llmInstruction, setLlmInstruction] = useState('Answer in concise Markdown. Use bullet points when listing; cite brief sources when relevant.');
  const [topK, setTopK] = useState(5);

  // File upload and preprocessing state
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [buildStatus, setBuildStatus] = useState<'idle' | 'building' | 'success' | 'error'>('idle');
  const [buildError, setBuildError] = useState<string>('');
  const [jsonPreview, setJsonPreview] = useState<any>(null);
  const [dbStatus, setDbStatus] = useState<string | null>(null);
  const [showFileUpload, setShowFileUpload] = useState(false);

  // Bot status state
  const [botStats, setBotStats] = useState<BotStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  // Uploaded files state
  const [uploadedFiles, setUploadedFiles] = useState<Array<{name: string, size: number, uploaded_at: string}>>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

  // Preprocessing settings (can be different from bot defaults)
  const [tempChunkSize, setTempChunkSize] = useState("default");
  const [tempOcrLang, setTempOcrLang] = useState(bot.ocr_lang);

  // Chat history state
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(true);

  useEffect(() => {
    loadBotStats();
    loadUploadedFiles();
  }, [bot.id]);

  const loadBotStats = async () => {
    try {
      setLoadingStats(true);
      const response = await apiClient.get(`${API_BASE}/bots/${bot.id}/stats`);
      setBotStats(response.data.stats);
    } catch (error) {
      console.error('Failed to load bot stats:', error);
    } finally {
      setLoadingStats(false);
    }
  };

  const loadUploadedFiles = async () => {
    try {
      setLoadingFiles(true);
      const response = await apiClient.get(`${API_BASE}/bots/${bot.id}/files`);
      setUploadedFiles(response.data.files || []);
    } catch (error) {
      console.error('Failed to load uploaded files:', error);
    } finally {
      setLoadingFiles(false);
    }
  };

  const sendMessage = async () => {
    if (!prompt.trim()) return;

    const userMessage = prompt;
    setLoading(true);
    setMessages(prev => [...prev, { user: userMessage, bot: '...', timestamp: new Date() }]);

    try {
      const response = await apiClient.post(`${API_BASE}/bots/${bot.id}/query/`, {
        prompt: `${llmInstruction}\n\n${userMessage}`,
        llm_model: llmModel,
        top_k: topK,
        bot_id: bot.id,
        openrouter_api_key: openRouterApiKey
      });

      const botResponse = response.data.answer.message.content;
      const sources = response.data.retrieved_chunks;

      setMessages(prev =>
        prev.slice(0, -1).concat([{
          user: userMessage,
          bot: botResponse,
          timestamp: new Date(),
          sources: sources
        }])
      );

      // Save to chat history if we have a conversation ID
      if (currentConversationId) {
        try {
          await apiClient.post(`${API_BASE}/bots/${bot.id}/chat/conversations/${currentConversationId}/messages`, {
            role: 'user',
            content: userMessage
          });
          await apiClient.post(`${API_BASE}/bots/${bot.id}/chat/conversations/${currentConversationId}/messages`, {
            role: 'assistant',
            content: botResponse
          });
        } catch (error) {
          console.error('Failed to save message to history:', error);
        }
      }
    } catch (error: any) {
      setMessages(prev =>
        prev.slice(0, -1).concat([{
          user: userMessage,
          bot: `Error: ${error.response?.data?.detail || error.message}`,
          timestamp: new Date()
        }])
      );
    }

    setPrompt('');
    setLoading(false);
  };

  const handleLoadConversation = async (conversationId: string, loadedMessages: any[]) => {
    setCurrentConversationId(conversationId);
    setMessages(loadedMessages);
  };

  const handleNewConversation = async () => {
    try {
      const response = await apiClient.post(`${API_BASE}/bots/${bot.id}/chat/conversations`);
      setCurrentConversationId(response.data.conversation_id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create new conversation:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const onDrop = (acceptedFiles: File[]) => setFiles(acceptedFiles);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "text/csv": [".csv"],
      "application/json": [".json"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
      "text/plain": [".txt"]
    },
    multiple: true,
  });

  const uploadFiles = async () => {
    if (files.length === 0) return;

    setUploading(true);
    setDbStatus(null);
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    formData.append("ocr_lang", tempOcrLang);

    try {
      setBuildStatus('building');
      const res = await apiClient.post(
        `${API_BASE}/bots/${bot.id}/build_and_preview/?chunk_size=${tempChunkSize}&chunk_overlap=50&embedding_model=sentence-transformers/all-MiniLM-L6-v2`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      setBuildStatus('success');
      setDbStatus(`✅ Database built successfully! ${res.data.num_chunks} chunks created for ${bot.name}.`);
      setJsonPreview(res.data.preview || null);
      setFiles([]);
      setShowFileUpload(false);

      // Reload bot stats and uploaded files after successful build
      await loadBotStats();
      await loadUploadedFiles();
    } catch (e: any) {
      setBuildStatus('error');
      setBuildError(e.response?.data?.detail || 'Failed to build database');
    }
    setUploading(false);
  };

  const rebuildDatabase = async () => {
    if (!confirm('Are you sure you want to rebuild the database from scratch? This will delete all uploaded files and the current database.')) {
      return;
    }

    try {
      setBuildStatus('building');
      await apiClient.post(`${API_BASE}/bots/${bot.id}/rebuild`);
      setBuildStatus('success');
      setDbStatus('✅ Database cleared successfully. Upload new files to rebuild.');
      
      // Reload stats and files
      await loadBotStats();
      await loadUploadedFiles();
      
      // Show file upload section
      setShowFileUpload(true);
    } catch (e: any) {
      setBuildStatus('error');
      setBuildError(e.response?.data?.detail || 'Failed to rebuild database');
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={onBack}
          className="mb-4 px-4 py-2 bg-zinc-600 hover:bg-zinc-700 text-white rounded-lg font-medium transition-colors"
        >
          ← Back to Dashboard
        </button>
        <div className="bg-zinc-900/50 rounded-lg border border-zinc-700 p-6">
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-white mb-2">{bot.name}</h2>
              <p className="text-zinc-400 mb-4">{bot.description || 'No description'}</p>
            </div>
            <div className="text-right">
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                botStats?.vectorstore_exists
                  ? 'bg-green-900/30 text-green-400 border border-green-700'
                  : 'bg-yellow-900/30 text-yellow-400 border border-yellow-700'
              }`}>
                {botStats?.vectorstore_exists ? 'Database Ready' : 'No Database'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm mb-4">
            <div>
              <div className="text-zinc-400">Embedding Model</div>
              <div className="text-white font-medium text-xs">Default</div>
            </div>
            <div>
              <div className="text-zinc-400">OCR Language</div>
              <div className="text-white font-medium">{bot.ocr_lang.toUpperCase()}</div>
            </div>
            <div>
              <div className="text-zinc-400">Database</div>
              <div className={`font-medium ${botStats && botStats.vectorstore_exists ? 'text-green-400' : 'text-yellow-400'}`}>
                {botStats && botStats.vectorstore_exists ? 'Ready' : 'No Database'}
              </div>
            </div>
          </div>

          {/* Uploaded Files Section */}
          {uploadedFiles.length > 0 && (
            <div className="mt-4 pt-4 border-t border-zinc-700">
              <h3 className="text-sm font-semibold text-zinc-300 mb-2">Uploaded Documents ({uploadedFiles.length})</h3>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="flex justify-between items-center bg-zinc-800/50 p-2 rounded">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      <span className="text-sm text-white">{file.name}</span>
                    </div>
                    <span className="text-xs text-zinc-400">
                      {new Date(file.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* File Upload Toggle */}
          <div className="mt-4 pt-4 border-t border-zinc-700">
            <div className="flex gap-2">
              <button
                onClick={() => setShowFileUpload(!showFileUpload)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                {uploadedFiles.length > 0 ? (showFileUpload ? 'Hide File Upload' : 'Add More Files') : 'Upload Files & Build Database'}
              </button>
              {uploadedFiles.length > 0 && (
                <button
                  onClick={rebuildDatabase}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                >
                  Rebuild Database
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* File Upload Section */}
      {showFileUpload && (
        <div className="mb-6 p-6 bg-zinc-900/50 rounded-lg border border-zinc-700">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-white">Upload Files for {bot.name}</h3>
            {botStats?.vectorstore_exists && (
              <div className="text-sm text-yellow-400 bg-yellow-900/20 px-3 py-1 rounded border border-yellow-700">
                ⚠️ Warning: This will add to existing database (not replace)
              </div>
            )}
          </div>

          <div {...getRootProps()} className={`border-2 border-dashed rounded-xl p-6 transition-all duration-200 ${isDragActive ? "border-white bg-glass" : "border-zinc-700 bg-glass"}`}>
            <input {...getInputProps()} />
            <p className="text-center text-zinc-300">
              {isDragActive
                ? "Drop files here..."
                : "Drag & drop PDF/CSV files here, or click to select"}
            </p>
            <ul className="mt-2 text-sm text-zinc-400">
              {files.map((f) => (
                <li key={f.name}>{f.name}</li>
              ))}
            </ul>
          </div>

          {/* Preprocessing Options - Simplified */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">OCR Language</label>
              <select
                className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={tempOcrLang}
                onChange={(e) => setTempOcrLang(e.target.value)}
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

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Chunk Size</label>
              <input
                type="number"
                className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={tempChunkSize}
                onChange={(e) => setTempChunkSize(e.target.value)}
                placeholder="500"
              />
            </div>
          </div>

          <div className="mt-4 flex gap-2">
            <button
              className={`px-6 py-3 rounded-lg font-semibold transition-all duration-200 disabled:opacity-50 ${
                botStats?.vectorstore_exists
                  ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
              onClick={uploadFiles}
              disabled={files.length === 0 || uploading}
            >
              {uploading
                ? "Building Database..."
                : botStats?.vectorstore_exists
                  ? "Add Files to Database"
                  : "Build Database & Preview"
              }
            </button>
            {botStats?.vectorstore_exists && (
              <button
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded font-semibold transition-all duration-200"
                onClick={() => {
                  if (confirm('This will rebuild the entire database from scratch. Are you sure?')) {
                    // TODO: Implement full rebuild functionality
                    alert('Full rebuild functionality coming soon!');
                  }
                }}
              >
                Rebuild Database
              </button>
            )}
          </div>

          {jsonPreview && (
            <div className="mt-4">
              <h4 className="text-md font-semibold text-white mb-2">Preview</h4>
              <pre className="bg-zinc-900/80 p-4 rounded text-sm text-green-300 overflow-x-auto max-h-64">
                {Array.isArray(jsonPreview) ? jsonPreview.join("\n\n") : JSON.stringify(jsonPreview, null, 2)}
              </pre>
            </div>
          )}

          {dbStatus && (
            <div className="mt-4 p-3 rounded-lg bg-green-900/20 border border-green-700 text-green-300 text-sm">
              {dbStatus}
            </div>
          )}
        </div>
      )}

      {/* Chat Interface */}
      <div className="flex h-[600px]">
        {/* Chat History Sidebar */}
        {showHistory && (
          <ChatHistory
            botId={bot.id}
            onLoadConversation={handleLoadConversation}
            currentConversationId={currentConversationId}
            onNewConversation={handleNewConversation}
          />
        )}

        {/* Main Chat Area */}
        <div className="bg-zinc-900/50 rounded-lg border border-zinc-700 flex flex-col flex-1 min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-zinc-500 mt-16">
                {botStats?.vectorstore_exists
                  ? `Start a conversation with ${bot.name}!`
                  : `${bot.name} needs files uploaded first. Click "Upload Files & Build Database" above.`
                }
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className="space-y-2">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
                    You
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-zinc-300 font-medium mb-1">You</div>
                    <div className="bg-zinc-800/50 rounded-lg px-4 py-3 text-white break-words">
                      {msg.user}
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
                    Bot
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-zinc-300 font-medium mb-1">{bot.name}</div>
                    <div className="bg-zinc-800/50 rounded-lg px-4 py-3 text-white">
                      {msg.bot === '...' ? (
                        <div className="flex items-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Thinking...
                        </div>
                      ) : (
                        <div className="prose prose-invert max-w-none break-words">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              code: ({ className, children, ...props}) => (
                                <code className={`bg-black/30 px-1.5 py-0.5 rounded ${className || ""}`} {...props}>
                                  {children}
                                </code>
                              ),
                              pre: ({children}) => (
                                <pre className="bg-black/30 p-3 rounded whitespace-pre-wrap">{children}</pre>
                              ),
                              ul: ({children}) => <ul className="list-disc pl-6 space-y-1">{children}</ul>,
                              ol: ({children}) => <ol className="list-decimal pl-6 space-y-1">{children}</ol>,
                              a: ({children, ...props}) => <a className="text-blue-400 underline" {...props}>{children}</a>,
                              p: ({children}) => <p className="mb-2">{children}</p>,
                            }}
                          >
                            {msg.bot}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                    {/* Source citations */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 text-sm">
                        <div className="text-zinc-400 font-medium mb-1">Sources:</div>
                        <div className="space-y-2">
                          {msg.sources.map((source, idx) => (
                            <div key={idx} className="bg-zinc-800/30 rounded p-2">
                              <div className="flex flex-wrap gap-2 text-xs text-zinc-400 mb-1">
                                <span className="font-medium">Source:</span>
                                <span className="break-all">{source.metadata.source}</span>
                                {source.metadata.page && (
                                  <>
                                    <span>•</span>
                                    <span>Page {source.metadata.page}</span>
                                  </>
                                )}
                                <span>•</span>
                                <span>Chunk {source.metadata.chunk_index}</span>
                              </div>
                              <div className="text-zinc-300 text-sm break-words line-clamp-2">
                                {source.content}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Controls */}
          <div className="p-6 border-t border-zinc-700 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">OpenRouter API Key</label>
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={openRouterApiKey}
                    onChange={e => setOpenRouterApiKey(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Paste your OpenRouter API key"
                  />
                  <button
                    type="button"
                    className="px-3 py-2 bg-zinc-700 hover:bg-zinc-800 text-white rounded-lg font-medium"
                    onClick={() => setOpenRouterApiKey('')}
                  >
                    Clear
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">LLM Model</label>
                <input
                  type="text"
                  value={llmModel}
                  onChange={e => setLlmModel(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Paste or type model name (e.g. deepseek/deepseek-r1-0528-qwen3-8b:free)"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Top K Results</label>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="1"
                  max="20"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">LLM Instruction</label>
                <input
                  type="text"
                  value={llmInstruction}
                  onChange={(e) => setLlmInstruction(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter instruction for the LLM"
                />
              </div>
            </div>

            {/* Message Input */}
            <div className="flex gap-2">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={`Ask ${bot.name} a question...`}
                className="flex-1 px-4 py-3 bg-zinc-800 text-white border border-zinc-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                rows={2}
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !prompt.trim()}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-600 text-white rounded-lg font-medium transition-colors self-end"
              >
                {loading ? '...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BotChat;

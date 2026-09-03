import { useState, useEffect } from 'react';
import { MessageSquare, User, ChevronRight, RefreshCw, Search, ThumbsUp, ThumbsDown } from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { API_BASE, rateMessage as apiRateMessage } from '../api';

interface SessionItem {
  session_id: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  channel: string;
  customer_id: number | null;
  customer_name: string | null;
  message_count: number;
  last_message: string | null;
  last_message_at: string | null;
}

interface ConversationMessage {
  message_id: string;
  role: string;
  content: string;
  created_at: string;
  model_used: string | null;
  tokens_input: number | null;
  tokens_output: number | null;
  response_time_ms: number | null;
  rating: string | null;
}

export default function AdminConversations() {
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  async function loadSessions() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/sessions`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data);
      }
    } catch (error) {
      console.error('Erro ao carregar sessões:', error);
    } finally {
      setLoading(false);
    }
  }

  async function loadMessages(sessionId: string) {
    setLoadingMessages(true);
    setSelectedSession(sessionId);
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages?limit=100`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages);
      }
    } catch (error) {
      console.error('Erro ao carregar mensagens:', error);
    } finally {
      setLoadingMessages(false);
    }
  }

  async function rateMessage(messageId: string, rating: 'positive' | 'negative') {
    try {
      await apiRateMessage(messageId, rating);
      setMessages((prev) =>
        prev.map((m) => (m.message_id === messageId ? { ...m, rating } : m))
      );
    } catch (error) {
      console.error('Erro ao avaliar mensagem:', error);
    }
  }

  const filteredSessions = sessions.filter(s => 
    (s.customer_name?.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (s.last_message?.toLowerCase().includes(searchTerm.toLowerCase())) ||
    s.session_id.includes(searchTerm)
  );

  const selectedSessionData = sessions.find(s => s.session_id === selectedSession);

  return (
    <div className="flex h-full">
      {/* Sessions List */}
      <div className="w-96 border-r border-gray-200 flex flex-col bg-white">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800">Conversas</h2>
            <button 
              onClick={loadSessions}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Atualizar"
            >
              <RefreshCw className={`w-4 h-4 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar conversas..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emporio-primary"
            />
          </div>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-8 text-center text-gray-500">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
              <p>Carregando...</p>
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Nenhuma conversa encontrada</p>
            </div>
          ) : (
            filteredSessions.map((session) => (
              <button
                key={session.session_id}
                onClick={() => loadMessages(session.session_id)}
                className={`w-full p-4 text-left border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                  selectedSession === session.session_id ? 'bg-emporio-accent/20' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    session.status === 'active' ? 'bg-green-100' : 'bg-gray-100'
                  }`}>
                    <User className={`w-5 h-5 ${
                      session.status === 'active' ? 'text-green-600' : 'text-gray-500'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-800 truncate">
                        {session.customer_name || `Visitante`}
                      </span>
                      <span className="text-xs text-gray-500">
                        {session.last_message_at 
                          ? formatDistanceToNow(new Date(session.last_message_at), { addSuffix: true, locale: ptBR })
                          : format(new Date(session.started_at), 'dd/MM HH:mm')
                        }
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 truncate mt-1">
                      {session.last_message || 'Sem mensagens'}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        session.status === 'active' 
                          ? 'bg-green-100 text-green-700' 
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {session.status === 'active' ? 'Ativo' : 'Encerrado'}
                      </span>
                      <span className="text-xs text-gray-400">
                        {session.message_count || 0} msgs
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400 mt-1" />
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Conversation Detail */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {selectedSession ? (
          <>
            {/* Conversation Header */}
            <div className="bg-white border-b border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emporio-accent rounded-full flex items-center justify-center">
                  <User className="w-5 h-5 text-emporio-dark" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-800">
                    {selectedSessionData?.customer_name || 'Visitante'}
                  </h3>
                  <p className="text-sm text-gray-500">
                    Sessão iniciada em {selectedSessionData?.started_at 
                      ? format(new Date(selectedSessionData.started_at), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })
                      : '-'
                    }
                  </p>
                  <p className="text-xs text-emporio-primary mt-1">
                    Avalie as respostas do agente com 👍 / 👎 — isso alimenta a acurácia do Dashboard
                  </p>
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 chat-bg">
              {loadingMessages ? (
                <div className="flex items-center justify-center h-full">
                  <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
                </div>
              ) : (
                <div className="space-y-2 max-w-3xl mx-auto">
                  {messages.map((msg) => (
                    <div
                      key={msg.message_id}
                      className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg px-3 py-2 shadow ${
                          msg.role === 'user'
                            ? 'bg-whatsapp-light text-gray-800 rounded-br-none'
                            : 'bg-white text-gray-800 rounded-bl-none'
                        }`}
                      >
                        <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
                          <span>{msg.created_at ? format(new Date(msg.created_at), 'HH:mm') : ''}</span>
                          {msg.role === 'assistant' && msg.response_time_ms && (
                            <>
                              <span>•</span>
                              <span>{msg.response_time_ms}ms</span>
                            </>
                          )}
                          {msg.role === 'assistant' && msg.tokens_input && (
                            <>
                              <span>•</span>
                              <span>{msg.tokens_input}+{msg.tokens_output} tokens</span>
                            </>
                          )}
                        </div>
                        {msg.role === 'assistant' && (
                          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-100">
                            <span className="text-[10px] text-gray-400">Avaliar:</span>
                            <button
                              onClick={() => rateMessage(msg.message_id, 'positive')}
                              className={`p-1 rounded transition-colors ${
                                msg.rating === 'positive'
                                  ? 'bg-green-100 text-green-700'
                                  : 'text-gray-400 hover:bg-green-50 hover:text-green-600'
                              }`}
                              title="Resposta correta"
                            >
                              <ThumbsUp className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => rateMessage(msg.message_id, 'negative')}
                              className={`p-1 rounded transition-colors ${
                                msg.rating === 'negative'
                                  ? 'bg-red-100 text-red-700'
                                  : 'text-gray-400 hover:bg-red-50 hover:text-red-600'
                              }`}
                              title="Resposta incorreta"
                            >
                              <ThumbsDown className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>Selecione uma conversa para visualizar</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

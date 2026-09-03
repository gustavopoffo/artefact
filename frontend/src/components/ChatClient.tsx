import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Send, Music, Loader2, CheckCheck, Settings } from 'lucide-react';
import { createSession, sendMessage, getMessages } from '../api';
import type { Message, ChatResponse } from '../api';

export default function ChatClient() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    initSession();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function initSession() {
    try {
      // Check localStorage for existing session
      const savedSession = localStorage.getItem('chat_session_id');
      if (savedSession) {
        setSessionId(savedSession);
        const history = await getMessages(savedSession);
        setMessages(history.messages);
      } else {
        const session = await createSession('web');
        setSessionId(session.session_id);
        localStorage.setItem('chat_session_id', session.session_id);
        // Add welcome message
        setMessages([{
          message_id: 'welcome',
          role: 'assistant',
          content: 'Olá! Bem-vindo ao Empório da Música! 🎸\n\nSou o assistente virtual e estou aqui para ajudar você. Posso responder sobre:\n\n• Produtos e preços\n• Disponibilidade em estoque\n• Formas de pagamento\n• Status de pedidos\n• Trocas e devoluções\n\nComo posso ajudar?',
          created_at: new Date().toISOString(),
        }]);
      }
    } catch (error) {
      console.error('Erro ao iniciar sessão:', error);
    } finally {
      setInitializing(false);
    }
  }

  async function handleSend() {
    if (!input.trim() || !sessionId || loading) return;

    const userMessage: Message = {
      message_id: `temp-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response: ChatResponse = await sendMessage(sessionId, userMessage.content);
      
      const assistantMessage: Message = {
        message_id: response.message_id,
        role: 'assistant',
        content: response.content,
        created_at: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Erro ao enviar mensagem:', error);
      setMessages(prev => [...prev, {
        message_id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.',
        created_at: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyPress(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function formatTime(dateStr: string | null) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }

  function newConversation() {
    localStorage.removeItem('chat_session_id');
    setMessages([]);
    setSessionId(null);
    setInitializing(true);
    initSession();
  }

  if (initializing) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <Loader2 className="w-8 h-8 animate-spin text-emporio-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-emporio-dark text-white px-4 py-3 flex items-center gap-3 shadow-md">
        <div className="w-10 h-10 bg-emporio-secondary rounded-full flex items-center justify-center">
          <Music className="w-6 h-6" />
        </div>
        <div className="flex-1">
          <h1 className="font-semibold">Empório da Música</h1>
          <p className="text-xs text-green-200">Online</p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={newConversation}
            className="text-sm bg-emporio-primary hover:bg-emporio-secondary px-3 py-1.5 rounded transition-colors"
          >
            Nova conversa
          </button>
          <Link
            to="/admin"
            title="Painel da empresa"
            className="w-9 h-9 flex items-center justify-center rounded-full bg-white/10 hover:bg-white/20 transition-colors"
          >
            <Settings className="w-5 h-5" />
          </Link>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto chat-bg p-4">
        <div className="max-w-3xl mx-auto space-y-2">
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
                <div className={`flex items-center gap-1 mt-1 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  <span className="text-[10px] text-gray-500">{formatTime(msg.created_at)}</span>
                  {msg.role === 'user' && (
                    <CheckCheck className="w-4 h-4 text-blue-500" />
                  )}
                </div>
              </div>
            </div>
          ))}
          
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white rounded-lg px-4 py-3 shadow rounded-bl-none">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="bg-gray-200 px-4 py-3">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Digite uma mensagem..."
            disabled={loading}
            className="flex-1 px-4 py-2 rounded-full border-none outline-none focus:ring-2 focus:ring-emporio-primary"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="w-10 h-10 bg-emporio-primary hover:bg-emporio-dark disabled:bg-gray-400 text-white rounded-full flex items-center justify-center transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

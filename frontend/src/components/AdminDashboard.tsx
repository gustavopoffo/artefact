import { useState, useEffect } from 'react';
import { 
  MessageSquare, Users, Clock, Zap, 
  ThumbsUp, ThumbsDown, RefreshCw, Database, Brain 
} from 'lucide-react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

interface DashboardMetrics {
  total_sessions: number;
  active_sessions: number;
  total_messages: number;
  avg_response_time_ms: number;
  total_tokens_used: number;
  positive_ratings: number;
  negative_ratings: number;
  rag_queries: number;
  avg_rag_similarity: number;
  messages_by_day: { date: string; count: number }[];
  sessions_by_channel: { channel: string; count: number }[];
  top_rag_categories: { category: string; count: number }[];
  response_time_trend: { date: string; avg_ms: number }[];
}

const COLORS = ['#2E7D32', '#4CAF50', '#81C784', '#A5D6A7', '#C8E6C9'];

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
  }, []);

  async function loadMetrics() {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/admin/metrics');
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (error) {
      console.error('Erro ao carregar métricas:', error);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-8 h-8 animate-spin text-emporio-primary" />
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="p-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
          <p className="font-medium">Métricas não disponíveis</p>
          <p className="text-sm mt-1">Configure o endpoint /admin/metrics na API.</p>
        </div>
      </div>
    );
  }

  const accuracyPercent = metrics.positive_ratings + metrics.negative_ratings > 0
    ? Math.round((metrics.positive_ratings / (metrics.positive_ratings + metrics.negative_ratings)) * 100)
    : 0;

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-gray-500">Métricas de desempenho do agente</p>
          <p className="text-sm text-emporio-primary mt-1">
            A acurácia vem das avaliações 👍/👎 feitas em Conversas → mensagem do agente
          </p>
        </div>
        <button 
          onClick={loadMetrics}
          className="flex items-center gap-2 px-4 py-2 bg-emporio-primary text-white rounded-lg hover:bg-emporio-dark transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Atualizar
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={<MessageSquare className="w-6 h-6" />}
          label="Total de Mensagens"
          value={metrics.total_messages.toLocaleString('pt-BR')}
          color="bg-blue-500"
        />
        <KPICard
          icon={<Users className="w-6 h-6" />}
          label="Sessões Ativas"
          value={`${metrics.active_sessions} / ${metrics.total_sessions}`}
          color="bg-green-500"
        />
        <KPICard
          icon={<Clock className="w-6 h-6" />}
          label="Tempo Médio de Resposta"
          value={`${metrics.avg_response_time_ms.toFixed(0)}ms`}
          color="bg-orange-500"
        />
        <KPICard
          icon={<Zap className="w-6 h-6" />}
          label="Tokens Consumidos"
          value={metrics.total_tokens_used.toLocaleString('pt-BR')}
          color="bg-purple-500"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Messages by Day */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Mensagens por Dia</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={metrics.messages_by_day}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#4CAF50" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Response Time Trend */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Tempo de Resposta (Tendência)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={metrics.response_time_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} unit="ms" />
              <Tooltip />
              <Line 
                type="monotone" 
                dataKey="avg_ms" 
                stroke="#2E7D32" 
                strokeWidth={2}
                dot={{ fill: '#2E7D32', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sessions by Channel */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Sessões por Canal</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={metrics.sessions_by_channel}
                dataKey="count"
                nameKey="channel"
                cx="50%"
                cy="50%"
                outerRadius={70}
                label={(props) => {
                  const name = String(props.name ?? '');
                  const percent = props.percent ?? 0;
                  return `${name} (${(percent * 100).toFixed(0)}%)`;
                }}
              >
                {metrics.sessions_by_channel.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Accuracy */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Acurácia do Agente</h3>
          <div className="flex items-center justify-center h-[200px]">
            <div className="text-center">
              <div className="relative inline-flex">
                <svg className="w-32 h-32">
                  <circle
                    className="text-gray-200"
                    strokeWidth="12"
                    stroke="currentColor"
                    fill="transparent"
                    r="52"
                    cx="64"
                    cy="64"
                  />
                  <circle
                    className="text-emporio-primary"
                    strokeWidth="12"
                    strokeDasharray={`${accuracyPercent * 3.27} 327`}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r="52"
                    cx="64"
                    cy="64"
                    transform="rotate(-90 64 64)"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-3xl font-bold text-gray-800">
                  {accuracyPercent}%
                </span>
              </div>
              <div className="flex items-center justify-center gap-4 mt-4">
                <div className="flex items-center gap-1 text-green-600">
                  <ThumbsUp className="w-4 h-4" />
                  <span className="text-sm">{metrics.positive_ratings}</span>
                </div>
                <div className="flex items-center gap-1 text-red-500">
                  <ThumbsDown className="w-4 h-4" />
                  <span className="text-sm">{metrics.negative_ratings}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RAG Stats */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">RAG Performance</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-emporio-primary" />
                <span className="text-sm text-gray-600">Consultas RAG</span>
              </div>
              <span className="font-semibold text-gray-800">{metrics.rag_queries}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-emporio-primary" />
                <span className="text-sm text-gray-600">Similaridade Média</span>
              </div>
              <span className="font-semibold text-gray-800">{(metrics.avg_rag_similarity * 100).toFixed(1)}%</span>
            </div>
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">Top Categorias RAG</p>
              {metrics.top_rag_categories.slice(0, 3).map((cat, i) => (
                <div key={cat.category} className="flex items-center gap-2 text-sm py-1">
                  <span className="w-6 h-6 rounded-full bg-emporio-accent/30 flex items-center justify-center text-xs font-medium">
                    {i + 1}
                  </span>
                  <span className="flex-1 text-gray-700">{cat.category}</span>
                  <span className="text-gray-500">{cat.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function KPICard({ 
  icon, 
  label, 
  value, 
  color 
}: { 
  icon: React.ReactNode; 
  label: string; 
  value: string; 
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-4">
        <div className={`${color} text-white p-3 rounded-lg`}>
          {icon}
        </div>
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-800">{value}</p>
        </div>
      </div>
    </div>
  );
}

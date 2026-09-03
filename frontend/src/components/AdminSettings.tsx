import { useEffect, useState } from 'react';
import { Brain, Check, RefreshCw } from 'lucide-react';
import { getAdminSettings, updateAdminSettings } from '../api';
import type { AdminSettings } from '../api';

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminSettings();
      setSettings(data);
      setSelected(data.llm_model);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Falha ao carregar configurações');
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!selected || selected === settings?.llm_model) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const data = await updateAdminSettings(selected);
      setSettings(data);
      setSelected(data.llm_model);
      setMessage(`Modelo atualizado para ${data.llm_model}. Novas mensagens já usam esse modelo.`);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Falha ao salvar');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-8 h-8 animate-spin text-emporio-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <div>
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Brain className="w-7 h-7 text-emporio-primary" />
          Modelo de IA
        </h1>
        <p className="text-gray-500 mt-1">
          Escolha o modelo OpenAI usado nas respostas do agente. Padrão: gpt-4o.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 text-red-700 px-4 py-3 text-sm">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded-lg border border-green-200 bg-green-50 text-green-800 px-4 py-3 text-sm flex items-center gap-2">
          <Check className="w-4 h-4 shrink-0" />
          {message}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-xl space-y-4">
        <label className="block text-sm font-medium text-gray-700">Modelo ativo</label>
        <select
          value={selected}
          onChange={(e) => {
            setSelected(e.target.value);
            setMessage(null);
          }}
          className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-gray-800 focus:outline-none focus:ring-2 focus:ring-emporio-primary/40"
        >
          {(settings?.allowed_models ?? []).map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>

        <p className="text-sm text-gray-500">
          O <strong>GPT-4o</strong> tende a ser mais natural e completo. O Mini é mais barato, mas
          costuma soar mais seco.
        </p>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !selected || selected === settings?.llm_model}
            className="px-4 py-2 rounded-lg bg-emporio-primary text-white font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition"
          >
            {saving ? 'Salvando…' : 'Salvar modelo'}
          </button>
          <button
            type="button"
            onClick={load}
            className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition"
          >
            Recarregar
          </button>
        </div>
      </div>
    </div>
  );
}

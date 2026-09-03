import { useState, useEffect, useMemo } from 'react';
import { RefreshCw, Tag, Search, ToggleLeft, ToggleRight } from 'lucide-react';
import { listPromotions, togglePromotion } from '../api';
import type { Promotion } from '../api';

type Filter = 'all' | 'active' | 'inactive';

function formatBrl(value: number) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export default function AdminPromotions() {
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [loading, setLoading] = useState(true);
  const [togglingId, setTogglingId] = useState<number | null>(null);
  const [filter, setFilter] = useState<Filter>('all');
  const [search, setSearch] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPromotions();
  }, []);

  async function loadPromotions() {
    setLoading(true);
    setError(null);
    try {
      const data = await listPromotions();
      setPromotions(data);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Falha ao carregar promoções');
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(promo: Promotion) {
    setTogglingId(promo.promotion_id);
    setError(null);
    try {
      const updated = await togglePromotion(promo.promotion_id, !promo.is_active);
      setPromotions((prev) =>
        prev.map((p) => (p.promotion_id === updated.promotion_id ? updated : p))
      );
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Falha ao atualizar promoção');
    } finally {
      setTogglingId(null);
    }
  }

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return promotions.filter((p) => {
      if (filter === 'active' && !p.is_active) return false;
      if (filter === 'inactive' && p.is_active) return false;
      if (!q) return true;
      return (
        p.product_name.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        String(p.product_id).includes(q)
      );
    });
  }, [promotions, filter, search]);

  const activeCount = promotions.filter((p) => p.is_active).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-8 h-8 animate-spin text-emporio-primary" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Promoções</h1>
          <p className="text-gray-500">
            Ative ou desative descontos. O chat usa o preço com promoção quando estiver ativa.
          </p>
          <p className="text-sm text-emporio-primary mt-1">
            {activeCount} ativa{activeCount === 1 ? '' : 's'} de {promotions.length}
          </p>
        </div>
        <button
          onClick={loadPromotions}
          className="flex items-center gap-2 px-4 py-2 bg-emporio-primary text-white rounded-lg hover:bg-emporio-dark transition-colors self-start"
        >
          <RefreshCw className="w-4 h-4" />
          Atualizar
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por produto ou campanha..."
            className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-emporio-primary"
          />
        </div>
        <div className="flex gap-2">
          {([
            ['all', 'Todas'],
            ['active', 'Ativas'],
            ['inactive', 'Inativas'],
          ] as const).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                filter === key
                  ? 'bg-emporio-primary text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-gray-500">
              <tr>
                <th className="px-4 py-3 font-medium">Produto</th>
                <th className="px-4 py-3 font-medium">Campanha</th>
                <th className="px-4 py-3 font-medium">Preço</th>
                <th className="px-4 py-3 font-medium">Desconto</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium text-right">Ação</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-gray-500">
                    Nenhuma promoção encontrada.
                  </td>
                </tr>
              ) : (
                filtered.map((promo) => (
                  <tr key={promo.promotion_id} className="border-t border-gray-100 hover:bg-gray-50/80">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-800">{promo.product_name}</div>
                      <div className="text-xs text-gray-400">ID {promo.product_id}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 text-gray-700">
                        <Tag className="w-4 h-4 text-emporio-primary shrink-0" />
                        {promo.description}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {promo.is_active ? (
                        <div>
                          <div className="text-xs text-gray-400 line-through">
                            {formatBrl(promo.original_price)}
                          </div>
                          <div className="font-medium text-emporio-primary">
                            {formatBrl(promo.discounted_price)}
                          </div>
                        </div>
                      ) : (
                        <div className="text-gray-700">{formatBrl(promo.original_price)}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-700">
                      {promo.discount_percent.toFixed(0)}%
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                          promo.is_active
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {promo.is_active ? 'Ativa' : 'Inativa'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleToggle(promo)}
                        disabled={togglingId === promo.promotion_id}
                        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors disabled:opacity-50 ${
                          promo.is_active
                            ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            : 'bg-emporio-primary text-white hover:bg-emporio-dark'
                        }`}
                      >
                        {togglingId === promo.promotion_id ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : promo.is_active ? (
                          <ToggleRight className="w-4 h-4" />
                        ) : (
                          <ToggleLeft className="w-4 h-4" />
                        )}
                        {promo.is_active ? 'Desativar' : 'Ativar'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

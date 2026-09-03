import { NavLink } from 'react-router-dom';
import { MessageSquare, BarChart3, Music, Home, Settings } from 'lucide-react';

export default function AdminSidebar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
      isActive
        ? 'bg-emporio-primary text-white'
        : 'text-gray-700 hover:bg-gray-100'
    }`;

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col h-screen">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-emporio-primary rounded-lg flex items-center justify-center">
            <Music className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-gray-800">Empório da Música</h1>
            <p className="text-xs text-gray-500">Painel Admin</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        <p className="px-4 pb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Visão da empresa
        </p>
        <NavLink to="/admin" end className={linkClass}>
          <MessageSquare className="w-5 h-5" />
          <span>Conversas</span>
        </NavLink>
        <NavLink to="/admin/dashboard" className={linkClass}>
          <BarChart3 className="w-5 h-5" />
          <span>Dashboard</span>
        </NavLink>

        <p className="px-4 pt-4 pb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Atalhos
        </p>
        <NavLink to="/" className={linkClass}>
          <Home className="w-5 h-5" />
          <span>Chat do cliente</span>
        </NavLink>
      </nav>

      <div className="p-4 border-t border-gray-200 space-y-2">
        <div className="flex items-center gap-2 text-sm text-gray-500 px-2">
          <Settings className="w-4 h-4" />
          <span>Modo administração</span>
        </div>
      </div>
    </aside>
  );
}

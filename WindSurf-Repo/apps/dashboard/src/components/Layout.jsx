import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const NAV = [
  { to: '/', icon: '⬡', label: 'Overview', exact: true },
  { to: '/cost', icon: '💰', label: 'Cost Intelligence' },
  { to: '/budget', icon: '📊', label: 'Budget' },
  { to: '/routing', icon: '🔀', label: 'Routing' },
  { to: '/audit', icon: '🔍', label: 'Audit Logs' },
  { to: '/anomalies', icon: '⚠️', label: 'Anomalies' },
  { to: '/insights', icon: '💡', label: 'Insights' },
  { to: '/billing', icon: '💳', label: 'Billing' },
  { to: '/providers', icon: '🔌', label: 'Providers & Plugins' },
  { to: '/workspaces', icon: '🏢', label: 'Workspace' },
  { to: '/settings', icon: '⚙️', label: 'Settings' },
];

function SidebarLink({ to, icon, label, exact, onClick }) {
  return (
    <NavLink
      to={to}
      end={exact}
      onClick={onClick}
      className={({ isActive }) => isActive ? 'sidebar-link-active' : 'sidebar-link'}
    >
      <span className="text-base leading-none w-5 flex-shrink-0 text-center">{icon}</span>
      <span className="truncate">{label}</span>
    </NavLink>
  );
}

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const sidebar = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-sm font-bold">B</div>
          <div>
            <div className="text-sm font-semibold text-white">BYOS Backend</div>
            <div className="text-xs text-gray-500">Command Center</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {NAV.map((item) => (
          <SidebarLink
            key={item.to}
            {...item}
            onClick={() => setMobileOpen(false)}
          />
        ))}
      </nav>

      {/* User footer */}
      <div className="px-3 py-4 border-t border-gray-800">
        <div className="flex items-center gap-2 px-2 py-2 rounded-lg bg-gray-800/60">
          <div className="w-7 h-7 rounded-full bg-indigo-700 flex items-center justify-center text-xs font-semibold text-white flex-shrink-0">
            {user?.email?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-gray-200 truncate">{user?.email || 'Unknown'}</div>
            <div className="text-xs text-gray-500 truncate">WS: {user?.workspace_id?.slice(0, 8) || '—'}</div>
          </div>
          <button
            onClick={handleLogout}
            className="text-gray-500 hover:text-gray-300 transition-colors ml-1 flex-shrink-0"
            title="Sign out"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex-col">
        {sidebar}
      </aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex w-56 flex-col bg-gray-900 border-r border-gray-800">
            {sidebar}
          </aside>
        </div>
      )}

      {/* Main content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-3 flex-shrink-0">
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden text-gray-400 hover:text-gray-200 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div className="flex-1" />

          {/* Status pill */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-900/30 border border-emerald-800">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400 font-medium">Live</span>
          </div>

          <div className="text-xs text-gray-600">v{process.env.REACT_APP_VERSION || '1.0.0'}</div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-5">
          {children}
        </main>
      </div>
    </div>
  );
}

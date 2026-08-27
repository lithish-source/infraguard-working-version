import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  // Map routes to titles
  const titleMap = {
    '/dashboard': 'Citizen Dashboard',
    '/submit-report': 'Submit a Report',
    '/map': 'Damage Map',
    '/my-reports': 'My Reports',
    '/notifications': 'Notifications',
    '/settings': 'Settings',
    '/admin': 'Admin Dashboard',
    '/admin/analytics': 'Analytics',
    '/admin/reports': 'Report Management',
  };

  const title = titleMap[location.pathname] || (location.pathname.startsWith('/reports/') ? 'Report Details' : 'InfraGuard');

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar (mobile + breadcrumb) */}
        <header className="sticky top-0 z-20 h-16 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 lg:px-6">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden btn-ghost p-2"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <div>
              <h1 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h1>
              <p className="hidden sm:block text-xs text-slate-500">
                AI-Assisted Community Infrastructure Damage Mapping
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="/api/v1/docs"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex btn-ghost text-sm"
            >
              API Docs
            </a>
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-6 animate-fade-in">{children}</main>

        <footer className="px-6 py-4 text-center text-xs text-slate-500 border-t border-slate-200 dark:border-slate-800">
          InfraGuard v1.0.0 · Built with FastAPI, React &amp; OpenCV
        </footer>
      </div>
    </div>
  );
}

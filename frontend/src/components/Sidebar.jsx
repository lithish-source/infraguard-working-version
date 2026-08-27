import { NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { notificationService } from '../services';
import { useNotifications } from '../hooks/useNotifications';
import { getInitials } from '../utils/helpers';

const citizenNav = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/submit-report', label: 'Submit Report', icon: '📝' },
  { to: '/map', label: 'Damage Map', icon: '🗺️' },
  { to: '/my-reports', label: 'My Reports', icon: '📁' },
];

const adminNav = [
  { to: '/admin', label: 'Admin Dashboard', icon: '⚙️' },
  { to: '/admin/analytics', label: 'Analytics', icon: '📈' },
  { to: '/admin/reports', label: 'Report Management', icon: '🗂️' },
];

export default function Sidebar({ open, onClose }) {
  const { user, logout, isAdmin } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const { unreadCount } = useNotifications();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      toast.success('Logged out');
      navigate('/login');
    } catch {
      toast.error('Logout failed');
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-40 h-screen w-64 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col transition-transform duration-200 ${
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 px-5 h-16 border-b border-slate-200 dark:border-slate-800">
          <div className="w-9 h-9 rounded-lg bg-brand-600 text-white flex items-center justify-center font-bold text-lg">
            I
          </div>
          <div>
            <div className="font-bold text-slate-900 dark:text-white leading-tight">InfraGuard</div>
            <div className="text-xs text-slate-500">Damage Mapping</div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {!isAdmin && (
            <>
              <div className="px-3 py-1 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Citizen
              </div>
              {citizenNav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
                  }
                >
                  <span className="text-lg">{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </>
          )}

          {isAdmin && (
            <>
              <div className="px-3 py-1 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Administration
              </div>
              {adminNav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
                  }
                >
                  <span className="text-lg">{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </>
          )}

          <NavLink
            to="/notifications"
            onClick={onClose}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
            }
          >
            <span className="text-lg">🔔</span>
            <span>Notifications</span>
            {unreadCount > 0 && (
              <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-2 py-0.5">
                {unreadCount}
              </span>
            )}
          </NavLink>

          <NavLink
            to="/settings"
            onClick={onClose}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
            }
          >
            <span className="text-lg">⚙️</span>
            <span>Settings</span>
          </NavLink>
        </nav>

        {/* User footer */}
        <div className="border-t border-slate-200 dark:border-slate-800 p-3 space-y-2">
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg">
            <div className="w-9 h-9 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 flex items-center justify-center font-semibold text-sm">
              {getInitials(user?.full_name || 'User')}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-slate-900 dark:text-white truncate">
                {user?.full_name}
              </div>
              <div className="text-xs text-slate-500 truncate">{user?.email}</div>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={toggleTheme}
              className="btn-secondary flex-1 text-xs"
              title="Toggle theme"
            >
              {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
            </button>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="btn-danger flex-1 text-xs"
            >
              {loggingOut ? '...' : 'Logout'}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

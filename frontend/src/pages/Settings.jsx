import { useState } from 'react';
import toast from 'react-hot-toast';
import Layout from '../components/Layout.jsx';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

export default function Settings() {
  const { user, logout, updateUser } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [form, setForm] = useState({
    full_name: user?.full_name || '',
    phone: user?.phone || '',
  });

  const handleSave = (e) => {
    e.preventDefault();
    updateUser(form);
    toast.success('Profile updated (local only — backend profile editing is a future enhancement).');
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  return (
    <Layout>
      <div className="max-w-2xl">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">Settings</h2>
        <p className="text-sm text-slate-500 mb-6">Manage your profile and preferences.</p>

        {/* Profile */}
        <div className="card p-6 mb-4">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Profile Information</h3>
          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="label">Full Name</label>
              <input
                type="text"
                className="input"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Email (cannot be changed)</label>
              <input type="email" className="input bg-slate-100 dark:bg-slate-800 cursor-not-allowed" value={user?.email || ''} disabled />
            </div>
            <div>
              <label className="label">Phone</label>
              <input
                type="tel"
                className="input"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Role</label>
              <input
                type="text"
                className="input bg-slate-100 dark:bg-slate-800 cursor-not-allowed capitalize"
                value={user?.role || ''}
                disabled
              />
            </div>
            <button type="submit" className="btn-primary">Save Changes</button>
          </form>
        </div>

        {/* Preferences */}
        <div className="card p-6 mb-4">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Preferences</h3>
          <div className="flex items-center justify-between py-2">
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-white">Theme</div>
              <div className="text-xs text-slate-500">Switch between light and dark mode</div>
            </div>
            <button onClick={toggleTheme} className="btn-secondary text-sm">
              {theme === 'dark' ? '☀️ Switch to Light' : '🌙 Switch to Dark'}
            </button>
          </div>
        </div>

        {/* Danger zone */}
        <div className="card p-6 border-red-200 dark:border-red-900/40">
          <h3 className="font-semibold text-red-700 dark:text-red-400 mb-4">Danger Zone</h3>
          <div className="flex items-center justify-between py-2">
            <div>
              <div className="text-sm font-medium text-slate-900 dark:text-white">Sign out</div>
              <div className="text-xs text-slate-500">Sign out of your account on this device</div>
            </div>
            <button onClick={handleLogout} className="btn-danger text-sm">
              Sign Out
            </button>
          </div>
        </div>

        <p className="text-xs text-slate-400 mt-6 text-center">
          InfraGuard v1.0.0 · Account deletion requires admin contact.
        </p>
      </div>
    </Layout>
  );
}

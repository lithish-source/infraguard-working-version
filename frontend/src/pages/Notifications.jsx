import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import Loading from '../components/Loading.jsx';
import EmptyState from '../components/EmptyState.jsx';
import { useNotifications } from '../hooks/useNotifications';
import { timeAgo } from '../utils/helpers';

export default function Notifications() {
  const { notifications, loading, fetchAll, markRead, markAllRead } = useNotifications();
  const [fetched, setFetched] = useState(false);

  useEffect(() => {
    if (!fetched) {
      fetchAll();
      setFetched(true);
    }
  }, [fetchAll, fetched]);

  const typeIcon = {
    success: '✅',
    info: 'ℹ️',
    warning: '⚠️',
    error: '❌',
    critical: '🚨',
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Notifications</h2>
          <p className="text-sm text-slate-500">Updates on your reports and community activity.</p>
        </div>
        {notifications.some((n) => !n.is_read) && (
          <button onClick={markAllRead} className="btn-secondary text-sm">
            Mark all read
          </button>
        )}
      </div>

      {loading ? (
        <Loading size="lg" label="Loading notifications..." />
      ) : notifications.length === 0 ? (
        <EmptyState
          title="No notifications"
          message="You'll see updates here when your reports are verified or status changes."
        />
      ) : (
        <div className="card divide-y divide-slate-200 dark:divide-slate-800">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`p-4 flex items-start gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors ${
                !n.is_read ? 'bg-brand-50/50 dark:bg-brand-950/30' : ''
              }`}
            >
              <div className="text-xl flex-shrink-0">{typeIcon[n.type] || 'ℹ️'}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <h4 className={`text-sm ${!n.is_read ? 'font-semibold text-slate-900 dark:text-white' : 'font-medium text-slate-700 dark:text-slate-300'}`}>
                    {n.title}
                  </h4>
                  <span className="text-xs text-slate-400 flex-shrink-0">{timeAgo(n.created_at)}</span>
                </div>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">{n.message}</p>
                <div className="flex gap-3 mt-2">
                  {n.report_id && (
                    <Link
                      to={`/reports/${n.report_id}`}
                      className="text-xs text-brand-600 hover:text-brand-700 font-medium"
                    >
                      View report →
                    </Link>
                  )}
                  {!n.is_read && (
                    <button
                      onClick={() => markRead(n.id)}
                      className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                    >
                      Mark read
                    </button>
                  )}
                </div>
              </div>
              {!n.is_read && <div className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 flex-shrink-0" />}
            </div>
          ))}
        </div>
      )}
    </Layout>
  );
}

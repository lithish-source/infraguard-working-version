import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout.jsx';
import StatCard from '../components/StatCard.jsx';
import ReportCard from '../components/ReportCard.jsx';
import Loading from '../components/Loading.jsx';
import EmptyState, { ErrorState } from '../components/EmptyState.jsx';
import { reportService, referenceService } from '../services';
import { useAuth } from '../context/AuthContext';

export default function CitizenDashboard() {
  const { user, isAdmin } = useAuth();
  const [myReports, setMyReports] = useState([]);
  const [recentReports, setRecentReports] = useState([]);
  const [infraTypes, setInfraTypes] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [mineRes, recentRes, typesRes, distRes] = await Promise.allSettled([
          reportService.myReports(),
          reportService.list({ page: 1, page_size: 5, order_by: 'created_at_desc' }),
          referenceService.infrastructureTypes(),
          referenceService.districts(),
        ]);

        const mine = mineRes.status === 'fulfilled' && Array.isArray(mineRes.value) ? mineRes.value : [];
        const recent = recentRes.status === 'fulfilled' ? recentRes.value?.items || [] : [];
        const types = typesRes.status === 'fulfilled' && Array.isArray(typesRes.value) ? typesRes.value : [];
        const dist = distRes.status === 'fulfilled' && Array.isArray(distRes.value) ? distRes.value : [];

        setMyReports(mine);
        setRecentReports(recent);
        setInfraTypes(types);
        setDistricts(dist);
      } catch (err) {
        console.warn('Dashboard load warning:', err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Layout><Loading size="lg" label="Loading dashboard..." /></Layout>;

  const stats = {
    submitted: myReports.length,
    pending: myReports.filter((r) => r.status === 'Reported').length,
    verified: myReports.filter((r) => r.status === 'Verified' || r.status === 'Assigned' || r.status === 'In Progress').length,
    resolved: myReports.filter((r) => r.status === 'Resolved').length,
  };

  return (
    <Layout>
      {/* Welcome */}
      <div className="card p-6 mb-6 bg-gradient-to-br from-brand-600 to-brand-800 text-white border-0">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h2 className="text-2xl font-bold mb-1">Hello, {user?.full_name?.split(' ')[0]} 👋</h2>
            <p className="text-brand-100">
              Thank you for being an active citizen reporter. Your reports help make your community safer.
            </p>
          </div>
          <Link to="/submit-report" className="btn bg-accent-500 hover:bg-accent-600 text-white">
            + New Report
          </Link>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Reports" value={stats.submitted} icon="📝" color="brand" />
        <StatCard title="Pending" value={stats.pending} icon="⏳" color="amber" />
        <StatCard title="In Progress" value={stats.verified} icon="🔄" color="blue" />
        <StatCard title="Resolved" value={stats.resolved} icon="✅" color="green" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* My recent reports */}
        <div className="lg:col-span-2">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-900 dark:text-white">My Recent Reports</h3>
              <Link to="/my-reports" className="text-sm text-brand-600 hover:text-brand-700 font-medium">
                View all →
              </Link>
            </div>
            {myReports.length === 0 ? (
              <EmptyState
                title="No reports yet"
                message="Submit your first infrastructure damage report to get started."
                action={<Link to="/submit-report" className="btn-primary">+ Submit Report</Link>}
              />
            ) : (
              <div className="space-y-3">
                {myReports.slice(0, 5).map((r) => (
                  <ReportCard key={r.id} report={r} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Side column */}
        <div className="space-y-6">
          <div className="card p-5">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <Link to="/submit-report" className="btn-secondary w-full justify-start">
                📝 Submit a new report
              </Link>
              <Link to="/map" className="btn-secondary w-full justify-start">
                🗺️ View damage map
              </Link>
              <Link to="/notifications" className="btn-secondary w-full justify-start">
                🔔 View notifications
              </Link>
              {isAdmin && (
                <Link to="/admin" className="btn-secondary w-full justify-start">
                  ⚙️ Admin dashboard
                </Link>
              )}
            </div>
          </div>

          <div className="card p-5">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Categories</h3>
            <div className="grid grid-cols-2 gap-2">
              {infraTypes.slice(0, 8).map((t) => (
                <Link
                  key={t.id}
                  to={`/map?category=${t.id}`}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-xs"
                >
                  <span className="text-lg">{t.icon || '📌'}</span>
                  <span className="truncate">{t.name}</span>
                </Link>
              ))}
            </div>
          </div>

          <div className="card p-5">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Recent Community Reports</h3>
            <div className="space-y-2">
              {recentReports.slice(0, 4).map((r) => (
                <Link
                  key={r.id}
                  to={`/reports/${r.id}`}
                  className="block text-sm hover:text-brand-600 transition-colors"
                >
                  <div className="font-medium truncate">{r.title}</div>
                  <div className="text-xs text-slate-500">
                    {r.category_name} · {r.district_name || 'Unknown'}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import Layout from '../components/Layout.jsx';
import StatCard from '../components/StatCard.jsx';
import ReportCard from '../components/ReportCard.jsx';
import Loading from '../components/Loading.jsx';
import { ErrorState } from '../components/EmptyState.jsx';
import {
  SeverityDoughnut, CategoryBar, MonthlyTrendLine, DistrictAnalyticsBar,
} from '../components/Charts.jsx';
import {
  adminService, reportService,
} from '../services';

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [severity, setSeverity] = useState([]);
  const [category, setCategory] = useState([]);
  const [monthly, setMonthly] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [criticalReports, setCriticalReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, sev, cat, mon, dist, crit] = await Promise.all([
          adminService.dashboardSummary(),
          adminService.severityDist(),
          adminService.categoryDist(),
          adminService.monthlyTrend(6),
          adminService.districtAnalytics(),
          reportService.list({ page: 1, page_size: 5, severity: 'Critical', order_by: 'priority_desc' }),
        ]);
        setSummary(s);
        setSeverity(sev);
        setCategory(cat);
        setMonthly(mon);
        setDistricts(dist);
        setCriticalReports(crit.items || []);
      } catch (err) {
        setError(err.response?.data?.detail || 'Could not load admin dashboard.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleRecompute = async () => {
    try {
      const res = await adminService.recomputePriorities();
      toast.success(res.message);
    } catch {
      toast.error('Could not recompute priorities.');
    }
  };

  if (loading) return <Layout><Loading size="lg" label="Loading admin dashboard..." /></Layout>;
  if (error) return <Layout><ErrorState message={error} onRetry={() => window.location.reload()} /></Layout>;

  return (
    <Layout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Admin Dashboard</h2>
          <p className="text-sm text-slate-500">System-wide overview of infrastructure damage reports and response.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleRecompute} className="btn-secondary text-sm">
            🔄 Recompute Priorities
          </button>
          <Link to="/admin/reports" className="btn-primary text-sm">
            Manage Reports →
          </Link>
        </div>
      </div>

      {/* Critical alert banner */}
      {summary?.critical_incidents > 0 && (
        <div className="card p-4 mb-6 bg-gradient-to-r from-purple-600 to-red-600 text-white border-0 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🚨</span>
            <div>
              <div className="font-semibold">{summary.critical_incidents} critical incidents need attention</div>
              <div className="text-sm text-purple-100">Immediate response recommended within 2 hours.</div>
            </div>
          </div>
          <Link to="/admin/reports?severity=Critical" className="btn bg-white text-purple-700 hover:bg-purple-50 text-sm">
            View Critical →
          </Link>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Reports" value={summary.total_reports} icon="📝" color="brand" />
        <StatCard title="Pending" value={summary.pending_reports} icon="⏳" color="amber" />
        <StatCard title="Verified" value={summary.verified_reports} icon="✓" color="blue" />
        <StatCard title="Resolved" value={summary.resolved_reports} icon="✅" color="green" />
        <StatCard title="Critical Incidents" value={summary.critical_incidents} icon="🚨" color="purple" />
        <StatCard title="Total Citizens" value={summary.total_users} icon="👥" color="slate" />
        <StatCard title="Verifications" value={summary.total_verifications} icon="🔍" color="blue" />
        <StatCard
          title="Avg Response Time"
          value={summary.avg_response_time_hours ? `${summary.avg_response_time_hours}h` : '—'}
          subtitle={`Response rate: ${summary.response_rate}%`}
          icon="⏱️"
          color="green"
        />
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Severity Distribution</h3>
          <SeverityDoughnut data={severity} />
        </div>
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Monthly Trend (6 months)</h3>
          <MonthlyTrendLine data={monthly} />
        </div>
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Damage Categories</h3>
          <CategoryBar data={category} />
        </div>
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">District Analytics</h3>
          <DistrictAnalyticsBar data={districts} />
        </div>
      </div>

      {/* Critical reports list */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-slate-900 dark:text-white">🚨 Top Critical Reports</h3>
          <Link to="/admin/reports?severity=Critical" className="text-sm text-brand-600 hover:text-brand-700">
            View all →
          </Link>
        </div>
        {criticalReports.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-6">No critical incidents. 🎉</p>
        ) : (
          <div className="space-y-3">
            {criticalReports.map((r) => (
              <ReportCard key={r.id} report={r} />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import Layout from '../components/Layout.jsx';
import ReportCard from '../components/ReportCard.jsx';
import Loading from '../components/Loading.jsx';
import EmptyState, { ErrorState } from '../components/EmptyState.jsx';
import { reportService } from '../services';

const STATUSES = ['Reported', 'Verified', 'Assigned', 'In Progress', 'Resolved'];

export default function MyReports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('All');

  useEffect(() => {
    (async () => {
      try {
        const data = await reportService.myReports();
        setReports(data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Could not load your reports.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Layout><Loading size="lg" label="Loading your reports..." /></Layout>;
  if (error) return <Layout><ErrorState message={error} /></Layout>;

  const filtered = filter === 'All' ? reports : reports.filter((r) => r.status === filter);
  const counts = STATUSES.reduce((acc, s) => {
    acc[s] = reports.filter((r) => r.status === s).length;
    return acc;
  }, {});

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">My Reports</h2>
          <p className="text-sm text-slate-500">Track the status of infrastructure damage reports you've submitted.</p>
        </div>
        <Link to="/submit-report" className="btn-primary">+ New Report</Link>
      </div>

      {/* Filter tabs */}
      <div className="card p-2 mb-4 flex flex-wrap gap-1">
        <button
          onClick={() => setFilter('All')}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            filter === 'All' ? 'bg-brand-600 text-white' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          All ({reports.length})
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              filter === s ? 'bg-brand-600 text-white' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            {s} ({counts[s] || 0})
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title={filter === 'All' ? 'No reports yet' : `No ${filter} reports`}
          message={filter === 'All'
            ? 'Submit your first infrastructure damage report to get started.'
            : `You have no reports with status "${filter}".`}
          action={<Link to="/submit-report" className="btn-primary">+ Submit Report</Link>}
        />
      ) : (
        <div className="grid md:grid-cols-2 gap-3">
          {filtered.map((r) => (
            <ReportCard key={r.id} report={r} />
          ))}
        </div>
      )}
    </Layout>
  );
}

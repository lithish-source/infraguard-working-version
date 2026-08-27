import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import Layout from '../components/Layout.jsx';
import Loading from '../components/Loading.jsx';
import ReportCard from '../components/ReportCard.jsx';
import EmptyState, { ErrorState } from '../components/EmptyState.jsx';
import { reportService, adminService, referenceService } from '../services';
import {
  severityBadge, statusBadge, priorityColor, formatDate, timeAgo,
} from '../utils/helpers';

const STATUSES = ['Reported', 'Verified', 'Assigned', 'In Progress', 'Resolved', 'Rejected'];
const SEVERITIES = ['Low', 'Moderate', 'High', 'Critical'];

export default function ReportManagement() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [reports, setReports] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Admin action forms
  const [statusForm, setStatusForm] = useState({ status: '', notes: '', assigned_team: '' });
  const [severityForm, setSeverityForm] = useState({ severity: '', notes: '' });
  const [assignForm, setAssignForm] = useState({ team: '', notes: '' });

  const filters = {
    status: searchParams.get('status') || '',
    severity: searchParams.get('severity') || '',
    search: searchParams.get('search') || '',
    order_by: searchParams.get('order_by') || 'priority_desc',
  };

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 20, order_by: filters.order_by };
      if (filters.status) params.status = filters.status;
      if (filters.severity) params.severity = filters.severity;
      if (filters.search) params.search = filters.search;
      const data = await reportService.list(params);
      setReports(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load reports.');
    } finally {
      setLoading(false);
    }
  }, [page, filters.status, filters.severity, filters.search, filters.order_by]);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  const updateFilter = (key, value) => {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value); else next.delete(key);
    setSearchParams(next);
    setPage(1);
  };

  const selectReport = (r) => {
    setSelected(r);
    setStatusForm({ status: r.status, notes: '', assigned_team: r.assigned_team || '' });
    setSeverityForm({ severity: r.final_severity || r.ai_severity || '', notes: '' });
    setAssignForm({ team: r.assigned_team || '', notes: '' });
  };

  const refreshSelected = async () => {
    if (!selected) return;
    try {
      const updated = await reportService.get(selected.id);
      setSelected(updated);
    } catch { /* ignore */ }
  };

  const handleStatusChange = async (e) => {
    e.preventDefault();
    if (!selected) return;
    setActionLoading(true);
    try {
      const updated = await adminService.updateStatus(selected.id, {
        status: statusForm.status,
        notes: statusForm.notes || null,
        assigned_team: statusForm.assigned_team || null,
      });
      setSelected(updated);
      toast.success(`Status updated to "${updated.status}".`);
      fetchReports();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSeverityChange = async (e) => {
    e.preventDefault();
    if (!selected) return;
    setActionLoading(true);
    try {
      const updated = await adminService.updateSeverity(selected.id, {
        severity: severityForm.severity,
        notes: severityForm.notes || null,
      });
      setSelected(updated);
      toast.success(`Severity overridden to "${severityForm.severity}".`);
      fetchReports();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    if (!selected) return;
    setActionLoading(true);
    try {
      const updated = await adminService.assignTeam(selected.id, {
        team: assignForm.team,
        notes: assignForm.notes || null,
      });
      setSelected(updated);
      toast.success(`Assigned to "${assignForm.team}".`);
      fetchReports();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Assign failed.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && reports.length === 0) return <Layout><Loading size="lg" label="Loading reports..." /></Layout>;
  if (error) return <Layout><ErrorState message={error} onRetry={fetchReports} /></Layout>;

  return (
    <Layout>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Report Management</h2>
        <p className="text-sm text-slate-500">Verify, prioritize, assign, and resolve infrastructure damage reports.</p>
      </div>

      {/* Filters */}
      <div className="card p-4 mb-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="label text-xs">Search</label>
          <input
            type="text"
            className="input text-sm py-1.5 w-64"
            placeholder="Title, description, reference code..."
            value={filters.search}
            onChange={(e) => updateFilter('search', e.target.value)}
          />
        </div>
        <div>
          <label className="label text-xs">Status</label>
          <select className="input text-sm py-1.5" value={filters.status} onChange={(e) => updateFilter('status', e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label text-xs">Severity</label>
          <select className="input text-sm py-1.5" value={filters.severity} onChange={(e) => updateFilter('severity', e.target.value)}>
            <option value="">All</option>
            {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label text-xs">Sort</label>
          <select className="input text-sm py-1.5" value={filters.order_by} onChange={(e) => updateFilter('order_by', e.target.value)}>
            <option value="priority_desc">Priority (high first)</option>
            <option value="created_at_desc">Newest first</option>
            <option value="created_at_asc">Oldest first</option>
            <option value="severity_desc">Severity (high first)</option>
          </select>
        </div>
        <button onClick={() => setSearchParams({})} className="btn-ghost text-sm ml-auto">Clear</button>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Reports list */}
        <div className="lg:col-span-2 space-y-3">
          <div className="text-sm text-slate-500">
            {total} report{total !== 1 ? 's' : ''} found · Page {page}
          </div>
          {reports.length === 0 ? (
            <EmptyState title="No reports found" message="Try adjusting your filters." />
          ) : (
            <>
              {reports.map((r) => (
                <div
                  key={r.id}
                  onClick={() => selectReport(r)}
                  className={`cursor-pointer transition-shadow ${selected?.id === r.id ? 'ring-2 ring-brand-500' : ''}`}
                >
                  <ReportCard report={r} />
                </div>
              ))}
              {/* Pagination */}
              <div className="flex justify-center gap-2 mt-4">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-secondary text-sm"
                >
                  ← Prev
                </button>
                <span className="px-3 py-1.5 text-sm text-slate-500">
                  Page {page} of {Math.max(1, Math.ceil(total / 20))}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * 20 >= total}
                  className="btn-secondary text-sm"
                >
                  Next →
                </button>
              </div>
            </>
          )}
        </div>

        {/* Admin panel */}
        <div className="space-y-4">
          {!selected ? (
            <div className="card p-6 text-center text-sm text-slate-500">
              ← Select a report to manage it.
            </div>
          ) : (
            <>
              {/* Summary */}
              <div className="card p-5">
                <div className="text-xs text-slate-500 mb-1">{selected.reference_code}</div>
                <h3 className="font-semibold text-slate-900 dark:text-white mb-2">{selected.title}</h3>
                <div className="flex flex-wrap gap-2 mb-3">
                  {severityBadge(selected.final_severity || selected.ai_severity)}
                  {statusBadge(selected.status)}
                </div>
                <p className="text-xs text-slate-500 mb-3">{selected.description.slice(0, 150)}...</p>
                <div className="text-xs text-slate-500 space-y-1">
                  <div>Reported by: {selected.user_name || '—'}</div>
                  <div>When: {formatDate(selected.created_at)}</div>
                  <div>Verifications: {selected.verification_count}</div>
                  {selected.priority_score && (
                    <div>Priority: <span className={`font-bold ${priorityColor(selected.priority_score)}`}>{selected.priority_score.toFixed(0)}</span></div>
                  )}
                </div>
              </div>

              {/* Status update */}
              <form onSubmit={handleStatusChange} className="card p-5 space-y-3">
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm">Update Status</h3>
                <select
                  className="input text-sm"
                  value={statusForm.status}
                  onChange={(e) => setStatusForm({ ...statusForm, status: e.target.value })}
                >
                  {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                <input
                  type="text"
                  className="input text-sm"
                  placeholder="Assigned team (optional)"
                  value={statusForm.assigned_team}
                  onChange={(e) => setStatusForm({ ...statusForm, assigned_team: e.target.value })}
                />
                <textarea
                  className="input text-sm"
                  rows="2"
                  placeholder="Resolution notes..."
                  value={statusForm.notes}
                  onChange={(e) => setStatusForm({ ...statusForm, notes: e.target.value })}
                />
                <button type="submit" disabled={actionLoading} className="btn-primary w-full text-sm">
                  {actionLoading ? 'Saving...' : 'Update Status'}
                </button>
              </form>

              {/* Severity override */}
              <form onSubmit={handleSeverityChange} className="card p-5 space-y-3">
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm">Override Severity</h3>
                <select
                  className="input text-sm"
                  value={severityForm.severity}
                  onChange={(e) => setSeverityForm({ ...severityForm, severity: e.target.value })}
                >
                  <option value="">— Select severity —</option>
                  {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                <input
                  type="text"
                  className="input text-sm"
                  placeholder="Reason for override..."
                  value={severityForm.notes}
                  onChange={(e) => setSeverityForm({ ...severityForm, notes: e.target.value })}
                />
                <button type="submit" disabled={actionLoading} className="btn-secondary w-full text-sm">
                  {actionLoading ? 'Saving...' : 'Override Severity'}
                </button>
              </form>

              {/* Assign team */}
              <form onSubmit={handleAssign} className="card p-5 space-y-3">
                <h3 className="font-semibold text-slate-900 dark:text-white text-sm">Quick Assign Team</h3>
                <input
                  type="text"
                  className="input text-sm"
                  placeholder="e.g. Team Alpha"
                  value={assignForm.team}
                  onChange={(e) => setAssignForm({ ...assignForm, team: e.target.value })}
                />
                <input
                  type="text"
                  className="input text-sm"
                  placeholder="Notes..."
                  value={assignForm.notes}
                  onChange={(e) => setAssignForm({ ...assignForm, notes: e.target.value })}
                />
                <button type="submit" disabled={actionLoading} className="btn-secondary w-full text-sm">
                  {actionLoading ? 'Assigning...' : 'Assign Team'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}

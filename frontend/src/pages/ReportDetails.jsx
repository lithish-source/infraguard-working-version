import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import Layout from '../components/Layout.jsx';
import Loading from '../components/Loading.jsx';
import { ErrorState } from '../components/EmptyState.jsx';
import { PriorityRadar } from '../components/Charts.jsx';
import DamageMap from '../components/DamageMap.jsx';
import { reportService } from '../services';
import { useAuth } from '../context/AuthContext';
import {
  severityBadge, statusBadge, formatDate, timeAgo, priorityColor, SEVERITY_COLORS,
} from '../utils/helpers';

export default function ReportDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Verification form
  const [verifForm, setVerifForm] = useState({
    severity_vote: '', comment: '', is_confirmed: true,
  });
  const [verifImage, setVerifImage] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const data = await reportService.get(id);
      setReport(data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Report not found.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleVerify = async (e) => {
    e.preventDefault();
    setVerifying(true);
    try {
      const fd = new FormData();
      fd.append('severity_vote', verifForm.severity_vote || '');
      fd.append('comment', verifForm.comment || '');
      fd.append('is_confirmed', verifForm.is_confirmed);
      if (verifImage) fd.append('image', verifImage);

      const updated = await reportService.verify(id, fd);
      setReport(updated);
      toast.success('Verification submitted. Thank you!');
      setVerifForm({ severity_vote: '', comment: '', is_confirmed: true });
      setVerifImage(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Verification failed.');
    } finally {
      setVerifying(false);
    }
  };

  if (loading) return <Layout><Loading size="lg" label="Loading report..." /></Layout>;
  if (error) return <Layout><ErrorState message={error} onRetry={() => navigate('/map')} /></Layout>;
  if (!report) return null;

  const severity = report.final_severity || report.ai_severity;
  const isOwner = user?.id === report.user_id;
  const alreadyVerified = report.verifications?.some((v) => v.user_id === user?.id);

  const priorityComponents = report.priority ? {
    severity: report.priority.severity_component,
    verification: report.priority.verification_component,
    population: report.priority.population_component,
    'road_importance': report.priority.road_importance_component,
    'hospital_proximity': report.priority.hospital_proximity_component,
    'school_proximity': report.priority.school_proximity_component,
    'utility_importance': report.priority.utility_importance_component,
    'time_urgency': report.priority.time_urgency_component,
    'verification_status': report.priority.verification_status_component,
  } : null;

  return (
    <Layout>
      {/* Header */}
      <div className="mb-6">
        <Link to="/map" className="text-sm text-brand-600 hover:text-brand-700 mb-2 inline-block">
          ← Back to map
        </Link>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-xs text-slate-500 mb-1">{report.reference_code}</div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">{report.title}</h2>
            <div className="flex flex-wrap gap-2 mt-2">
              {severityBadge(severity)}
              {statusBadge(report.status)}
              {report.category_name && (
                <span className="badge bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  {report.category_name}
                </span>
              )}
              {report.district_name && (
                <span className="badge bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
                  📍 {report.district_name}
                </span>
              )}
            </div>
          </div>
          {report.priority && (
            <div className="text-right">
              <div className={`text-4xl font-bold ${priorityColor(report.priority.score)}`}>
                {report.priority.score.toFixed(0)}
              </div>
              <div className="text-xs text-slate-500 uppercase tracking-wider">Priority Score</div>
              <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 mt-1">
                {report.priority.resource_urgency} urgency
              </div>
              <div className="text-xs text-slate-500">
                Respond {report.priority.recommended_response_time}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: images + description + map */}
        <div className="lg:col-span-2 space-y-6">
          {/* Images */}
          {report.images?.length > 0 && (
            <div className="card p-4">
              <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Photos ({report.images.length})</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {report.images.map((img) => (
                  <a
                    key={img.id}
                    href={img.file_url}
                    target="_blank"
                    rel="noreferrer"
                    className="aspect-square rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800 group relative"
                  >
                    <img src={img.file_url} alt={img.caption || ''} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                    {img.is_primary && (
                      <span className="absolute top-1 left-1 bg-brand-600 text-white text-[10px] px-1.5 py-0.5 rounded">
                        Primary
                      </span>
                    )}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          <div className="card p-5">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Description</h3>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
              {report.description}
            </p>
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800 grid grid-cols-2 gap-3 text-xs text-slate-500">
              <div>
                <div className="font-medium text-slate-700 dark:text-slate-300">Address</div>
                <div>{report.address || '—'}</div>
              </div>
              <div>
                <div className="font-medium text-slate-700 dark:text-slate-300">Coordinates</div>
                <div>{report.latitude?.toFixed(4)}, {report.longitude?.toFixed(4)}</div>
              </div>
              <div>
                <div className="font-medium text-slate-700 dark:text-slate-300">Reported By</div>
                <div>{report.user_name || 'Anonymous'}</div>
              </div>
              <div>
                <div className="font-medium text-slate-700 dark:text-slate-300">Reported On</div>
                <div>{formatDate(report.created_at)}</div>
              </div>
              {report.assigned_team && (
                <div>
                  <div className="font-medium text-slate-700 dark:text-slate-300">Assigned Team</div>
                  <div>{report.assigned_team}</div>
                </div>
              )}
              {report.resolved_at && (
                <div>
                  <div className="font-medium text-slate-700 dark:text-slate-300">Resolved On</div>
                  <div>{formatDate(report.resolved_at)}</div>
                </div>
              )}
            </div>
          </div>

          {/* Map */}
          <div className="card p-4">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Location</h3>
            <DamageMap
              reports={[report]}
              center={[report.latitude, report.longitude]}
              zoom={15}
              height="300px"
            />
          </div>

          {/* Verifications list */}
          {report.verifications?.length > 0 && (
            <div className="card p-5">
              <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
                Crowd Verifications ({report.verifications.length})
              </h3>
              <div className="space-y-3">
                {report.verifications.map((v) => (
                  <div key={v.id} className="border-l-2 border-slate-200 dark:border-slate-700 pl-3 py-1">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span>{v.is_confirmed ? '✓ Confirmed' : '✗ Flagged'}</span>
                      {v.severity_vote && (
                        <span className={SEVERITY_COLORS[v.severity_vote]?.badge}>{v.severity_vote}</span>
                      )}
                      <span>· {timeAgo(v.created_at)}</span>
                    </div>
                    {v.comment && (
                      <p className="text-sm text-slate-700 dark:text-slate-300 mt-1">{v.comment}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: AI + priority + verify form */}
        <div className="space-y-6">
          {/* AI Analysis */}
          <div className="card p-5">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
              🤖 AI Analysis
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Detected Severity</span>
                <div>{severityBadge(report.ai_severity)}</div>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Damage Type</span>
                <span className="font-medium text-slate-900 dark:text-white">{report.ai_damage_type || '—'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Confidence</span>
                <span className="font-medium text-slate-900 dark:text-white">
                  {report.ai_confidence ? `${(report.ai_confidence * 100).toFixed(1)}%` : '—'}
                </span>
              </div>
              {report.final_severity && report.final_severity !== report.ai_severity && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Admin Override</span>
                  <div>{severityBadge(report.final_severity)}</div>
                </div>
              )}
            </div>
          </div>

          {/* Priority breakdown */}
          {report.priority && (
            <div className="card p-5">
              <h3 className="font-semibold text-slate-900 dark:text-white mb-1">Priority Breakdown</h3>
              <p className="text-xs text-slate-500 mb-3">Severity-based scoring with context boosters</p>
              <div className="space-y-1.5 text-xs">
                {/* Base score from severity */}
                <div className="flex items-center gap-2">
                  <span className="w-32 text-slate-500 truncate font-medium">Base Score</span>
                  <div className="flex-1 h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-600 rounded-full"
                      style={{ width: `${Math.min(100, report.priority.severity_component * 100)}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-slate-700 dark:text-slate-300 font-mono">
                    {(report.priority.severity_component * 100).toFixed(0)}
                  </span>
                </div>
                {/* Boosters */}
                <div className="border-t border-slate-200 dark:border-slate-700 mt-1 pt-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider">Context Boosters</span>
                </div>
                {[
                  ['Hospital Proximity', report.priority.hospital_proximity_component, 15],
                  ['School Proximity', report.priority.school_proximity_component, 10],
                  ['Population Impact', report.priority.population_component, 10],
                  ['Road Importance', report.priority.road_importance_component, 10],
                  ['Utility Importance', report.priority.utility_importance_component, 8],
                  ['Confirmations', report.priority.verification_component, 10],
                  ['Report Age', report.priority.time_urgency_component, 5],
                  ['Credibility', report.priority.verification_status_component, 5],
                ].map(([label, val, maxPts]) => {
                  const pts = ((val || 0) * maxPts).toFixed(1);
                  return (
                    <div key={label} className="flex items-center gap-2">
                      <span className="w-32 text-slate-500 truncate">{label}</span>
                      <div className="flex-1 h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${Math.min(100, (val || 0) * 100)}%` }}
                        />
                      </div>
                      <span className="w-14 text-right text-slate-700 dark:text-slate-300 font-mono text-[11px]">
                        +{pts} pts
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Crowd validation form */}
          {!isOwner && !alreadyVerified && report.status !== 'Resolved' && (
            <div className="card p-5">
              <h3 className="font-semibold text-slate-900 dark:text-white mb-1">Verify This Report</h3>
              <p className="text-xs text-slate-500 mb-3">
                Help build community consensus. Your vote increases report credibility.
              </p>
              <form onSubmit={handleVerify} className="space-y-3">
                <div>
                  <label className="label text-xs">Your Severity Vote (optional)</label>
                  <select
                    className="input text-sm"
                    value={verifForm.severity_vote}
                    onChange={(e) => setVerifForm({ ...verifForm, severity_vote: e.target.value })}
                  >
                    <option value="">No vote</option>
                    <option value="Low">Low</option>
                    <option value="Moderate">Moderate</option>
                    <option value="High">High</option>
                    <option value="Critical">Critical</option>
                  </select>
                </div>
                <div>
                  <label className="label text-xs">Comment (optional)</label>
                  <textarea
                    className="input text-sm"
                    rows="2"
                    placeholder="Add context..."
                    value={verifForm.comment}
                    onChange={(e) => setVerifForm({ ...verifForm, comment: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label text-xs">Additional photo (optional)</label>
                  <input
                    type="file"
                    accept="image/*"
                    className="input text-sm py-1.5"
                    onChange={(e) => setVerifImage(e.target.files?.[0] || null)}
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setVerifForm({ ...verifForm, is_confirmed: false })}
                    className={`btn-secondary flex-1 text-sm ${!verifForm.is_confirmed ? 'ring-2 ring-red-400' : ''}`}
                  >
                    ✗ Flag
                  </button>
                  <button
                    type="submit"
                    disabled={verifying}
                    className="btn-primary flex-1 text-sm"
                  >
                    {verifying ? '...' : '✓ Confirm'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {alreadyVerified && (
            <div className="card p-5 text-center text-sm text-slate-500">
              ✓ You have already verified this report. Thank you!
            </div>
          )}

          {isOwner && (
            <div className="card p-5 text-center text-sm text-slate-500">
              This is your report — others can verify it.
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

import { useEffect, useState } from 'react';
import Layout from '../components/Layout.jsx';
import Loading from '../components/Loading.jsx';
import EmptyState, { ErrorState } from '../components/EmptyState.jsx';
import {
  SeverityDoughnut, CategoryBar, MonthlyTrendLine, DistrictAnalyticsBar,
} from '../components/Charts.jsx';
import DamageMap from '../components/DamageMap.jsx';
import { adminService, reportService } from '../services';

export default function Analytics() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [responseTime, setResponseTime] = useState(null);
  const [repeatIncidents, setRepeatIncidents] = useState([]);
  const [participation, setParticipation] = useState(null);
  const [severity, setSeverity] = useState([]);
  const [category, setCategory] = useState([]);
  const [monthly, setMonthly] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [mapReports, setMapReports] = useState([]);
  const [heatmapPoints, setHeatmapPoints] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [rt, ri, pa, sev, cat, mon, dist, geojson, heat] = await Promise.all([
          adminService.responseTime(),
          adminService.repeatIncidents(),
          adminService.participation(),
          adminService.severityDist(),
          adminService.categoryDist(),
          adminService.monthlyTrend(12),
          adminService.districtAnalytics(),
          reportService.getMapData({}),
          reportService.getHeatmap({}),
        ]);
        setResponseTime(rt);
        setRepeatIncidents(ri.clusters || []);
        setParticipation(pa);
        setSeverity(sev);
        setCategory(cat);
        setMonthly(mon);
        setDistricts(dist);

        const flat = (geojson.features || []).map((f) => ({
          id: f.properties.id,
          title: f.properties.title,
          latitude: f.geometry.coordinates[1],
          longitude: f.geometry.coordinates[0],
          severity: f.properties.severity,
          ai_severity: f.properties.severity,
          final_severity: f.properties.severity,
          status: f.properties.status,
          category_name: f.properties.category,
          verification_count: f.properties.verification_count,
          priority_score: f.properties.priority_score,
          image_url: f.properties.image_url,
        }));
        setMapReports(flat);
        setHeatmapPoints(heat.points || []);
      } catch (err) {
        setError(err.response?.data?.detail || 'Could not load analytics.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <Layout><Loading size="lg" label="Loading analytics..." /></Layout>;
  if (error) return <Layout><ErrorState message={error} onRetry={() => window.location.reload()} /></Layout>;

  return (
    <Layout>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">AI Analytics</h2>
        <p className="text-sm text-slate-500">Deep-dive analytics into infrastructure vulnerability, response efficiency, and citizen participation.</p>
      </div>

      {/* Top metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card p-5">
          <div className="text-xs text-slate-500 uppercase tracking-wider">Avg Response Time</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {responseTime?.avg_hours ? `${responseTime.avg_hours}h` : '—'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Min: {responseTime?.min_hours ? `${responseTime.min_hours}h` : '—'} · Max: {responseTime?.max_hours ? `${responseTime.max_hours}h` : '—'}
          </div>
        </div>
        <div className="card p-5">
          <div className="text-xs text-slate-500 uppercase tracking-wider">Total Citizens</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {participation?.total_citizens || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">Registered users</div>
        </div>
        <div className="card p-5">
          <div className="text-xs text-slate-500 uppercase tracking-wider">Active Reporters</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {participation?.citizens_who_reported || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {participation?.total_citizens
              ? `${((participation.citizens_who_reported / participation.total_citizens) * 100).toFixed(1)}% engagement`
              : ''}
          </div>
        </div>
        <div className="card p-5">
          <div className="text-xs text-slate-500 uppercase tracking-wider">Avg Verifications</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white mt-2">
            {participation?.avg_verifications_per_report || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">Per report</div>
        </div>
      </div>

      {/* Charts grid */}
      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Severity Distribution</h3>
          <SeverityDoughnut data={severity} />
        </div>
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">12-Month Trend</h3>
          <MonthlyTrendLine data={monthly} />
        </div>
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Category Distribution</h3>
          <CategoryBar data={category} />
        </div>
        <div className="card p-5">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">District Comparison</h3>
          <DistrictAnalyticsBar data={districts} />
        </div>
      </div>

      {/* Vulnerability heatmap */}
      <div className="card p-4 mb-6">
        <div className="flex items-center justify-between mb-3 px-2">
          <h3 className="font-semibold text-slate-900 dark:text-white">🔥 Infrastructure Vulnerability Heatmap</h3>
          <span className="text-xs text-slate-500">{mapReports.length} reports</span>
        </div>
        <DamageMap
          reports={mapReports}
          heatmap={heatmapPoints}
          showHeatmap={true}
          height="450px"
          center={[18.5204, 73.8567]}
          zoom={11}
        />
      </div>

      {/* Repeat incidents */}
      <div className="card p-5 mb-6">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">🔁 Repeat Incident Detection</h3>
        {repeatIncidents.length === 0 ? (
          <EmptyState title="No repeat incidents detected" message="No clusters of repeated reports within 500m of each other." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-800 text-left text-xs text-slate-500 uppercase">
                  <th className="py-2 pr-3">Cluster</th>
                  <th className="py-2 pr-3">Center</th>
                  <th className="py-2 pr-3">Reports</th>
                  <th className="py-2 pr-3">Report IDs</th>
                </tr>
              </thead>
              <tbody>
                {repeatIncidents.map((c, i) => (
                  <tr key={i} className="border-b border-slate-100 dark:border-slate-800/50">
                    <td className="py-2 pr-3 font-medium">#{i + 1}</td>
                    <td className="py-2 pr-3 font-mono text-xs">
                      {c.center.lat.toFixed(4)}, {c.center.lng.toFixed(4)}
                    </td>
                    <td className="py-2 pr-3">
                      <span className="badge bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                        {c.count} reports
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-xs text-slate-500">
                      {c.report_ids.slice(0, 5).join(', ')}{c.report_ids.length > 5 ? ` +${c.report_ids.length - 5}` : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Citizen participation */}
      <div className="card p-5">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-4">👥 Citizen Participation Metrics</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="text-center p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
            <div className="text-2xl font-bold text-brand-600 dark:text-brand-400">{participation?.total_citizens || 0}</div>
            <div className="text-xs text-slate-500">Registered</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{participation?.citizens_who_reported || 0}</div>
            <div className="text-xs text-slate-500">Submitted Reports</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">{participation?.citizens_who_verified || 0}</div>
            <div className="text-xs text-slate-500">Verified Others</div>
          </div>
          <div className="text-center p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{participation?.avg_verifications_per_report || 0}</div>
            <div className="text-xs text-slate-500">Avg / Report</div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

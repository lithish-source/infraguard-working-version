export default function StatCard({ title, value, subtitle, icon, trend, color = 'brand' }) {
  const colorMap = {
    brand: 'bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300',
    green: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    amber: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    red: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    purple: 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    slate: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    blue: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  };

  return (
    <div className="stat-card">
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">
          {title}
        </div>
        <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">
          {value}
        </div>
        {subtitle && (
          <div className="mt-1 text-xs text-slate-500">{subtitle}</div>
        )}
        {trend !== undefined && trend !== null && (
          <div className={`mt-2 text-xs font-medium ${trend >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {trend >= 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}% vs last period
          </div>
        )}
      </div>
      {icon && (
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-xl flex-shrink-0 ${colorMap[color]}`}>
          {icon}
        </div>
      )}
    </div>
  );
}

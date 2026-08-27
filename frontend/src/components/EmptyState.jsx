export default function EmptyState({ title, message, action }) {
  return (
    <div className="card p-10 text-center">
      <div className="text-5xl mb-4 opacity-50">📭</div>
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
        {title}
      </h3>
      {message && <p className="text-sm text-slate-500 max-w-sm mx-auto">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div className="card p-10 text-center border-red-200 dark:border-red-900/50">
      <div className="text-5xl mb-4">⚠️</div>
      <h3 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-1">{title}</h3>
      {message && <p className="text-sm text-slate-500 max-w-sm mx-auto">{message}</p>}
      {onRetry && (
        <button onClick={onRetry} className="btn-primary mt-4">
          Try Again
        </button>
      )}
    </div>
  );
}

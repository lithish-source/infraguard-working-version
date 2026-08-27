export default function Loading({ size = 'md', label = 'Loading...' }) {
  const sizeClass = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }[size];

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-8">
      <div className={`${sizeClass} border-3 border-slate-200 dark:border-slate-700 border-t-brand-600 rounded-full animate-spin`} />
      {label && <p className="text-sm text-slate-500">{label}</p>}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <Loading size="lg" label="Loading page..." />
    </div>
  );
}

export function InlineLoader({ label = 'Loading...' }) {
  return <Loading size="sm" label={label} />;
}

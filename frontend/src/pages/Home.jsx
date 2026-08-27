import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Home() {
  const { isAuthenticated, isAdmin } = useAuth();
  const dashboardLink = isAuthenticated ? (isAdmin ? '/admin' : '/dashboard') : '/login';

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-950 via-brand-900 to-brand-700 text-white">
      {/* Top bar */}
      <header className="container mx-auto px-6 py-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-white/10 backdrop-blur flex items-center justify-center font-bold text-xl">
            I
          </div>
          <div>
            <div className="font-bold text-lg">InfraGuard</div>
            <div className="text-xs text-brand-200">Community Infrastructure Damage Mapping</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm font-medium hover:text-brand-200 transition-colors">
            Sign In
          </Link>
          <Link to="/register" className="btn bg-accent-500 hover:bg-accent-600 text-white">
            Get Started
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="container mx-auto px-6 py-20 lg:py-28 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur text-xs font-medium mb-6">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          AI-Powered · Real-Time · Government-Grade
        </div>
        <h1 className="text-4xl lg:text-6xl font-extrabold tracking-tight max-w-4xl mx-auto leading-tight">
          Report infrastructure damage.
          <br />
          <span className="text-accent-400">AI prioritizes what matters most.</span>
        </h1>
        <p className="mt-6 text-lg lg:text-xl text-brand-100 max-w-2xl mx-auto">
          Citizens report damaged roads, bridges, drainage, and public utilities.
          Our AI engine analyzes photos, estimates severity, and ranks incidents
          so authorities can respond faster and smarter.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row gap-3 justify-center">
          <Link to={dashboardLink} className="btn bg-accent-500 hover:bg-accent-600 text-white px-6 py-3 text-base">
            🚀 Launch Dashboard
          </Link>
          <Link to="/register" className="btn bg-white/10 backdrop-blur hover:bg-white/20 text-white px-6 py-3 text-base">
            Become a Citizen Reporter
          </Link>
        </div>

        {/* Stats */}
        <div className="mt-20 grid grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl mx-auto">
          {[
            ['10+', 'Infrastructure Categories'],
            ['4', 'AI Severity Levels'],
            ['9', 'Priority Factors'],
            ['100%', 'Transparent Scoring'],
          ].map(([n, l]) => (
            <div key={l} className="bg-white/5 backdrop-blur rounded-xl p-5 border border-white/10">
              <div className="text-3xl font-bold text-accent-400">{n}</div>
              <div className="text-sm text-brand-100 mt-1">{l}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="bg-white/5 backdrop-blur py-20">
        <div className="container mx-auto px-6">
          <h2 className="text-3xl lg:text-4xl font-bold text-center mb-4">How InfraGuard Works</h2>
          <p className="text-brand-100 text-center max-w-2xl mx-auto mb-12">
            A complete pipeline from citizen report to prioritized response — powered by computer vision and geospatial analytics.
          </p>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: '📸',
                title: '1. Citizen Reports',
                desc: 'Citizens upload photos of damaged infrastructure with GPS location and category. Reports are submitted in under 60 seconds.',
              },
              {
                icon: '🤖',
                title: '2. AI Severity Assessment',
                desc: 'OpenCV extracts edge, color, and texture features. A hybrid rule-based + ML classifier predicts damage severity with confidence scoring.',
              },
              {
                icon: '👥',
                title: '3. Crowd Validation',
                desc: 'Other citizens confirm reports, vote on severity, and add photos. Credibility scores rise with each verification.',
              },
              {
                icon: '🎯',
                title: '4. Priority Engine',
                desc: 'Nine factors — severity, population, hospitals, schools, road class, time, verifications — combine into a transparent priority score.',
              },
              {
                icon: '🗺️',
                title: '5. Geospatial Mapping',
                desc: 'Interactive Leaflet map with clustered markers, heatmaps, district boundaries, and live filtering by category and severity.',
              },
              {
                icon: '📊',
                title: '6. Admin Dashboard',
                desc: 'Authorities see real-time KPIs, monthly trends, district analytics, and resource allocation suggestions — all in one place.',
              },
            ].map((f) => (
              <div key={f.title} className="bg-white/5 backdrop-blur rounded-xl p-6 border border-white/10 hover:bg-white/10 transition-colors">
                <div className="text-4xl mb-3">{f.icon}</div>
                <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
                <p className="text-sm text-brand-100 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container mx-auto px-6 py-20 text-center">
        <h2 className="text-3xl lg:text-4xl font-bold mb-4">Ready to make your city smarter?</h2>
        <p className="text-brand-100 mb-8 max-w-xl mx-auto">
          Join InfraGuard today — every report helps authorities respond faster and keeps your community safer.
        </p>
        <Link to="/register" className="btn bg-accent-500 hover:bg-accent-600 text-white px-8 py-3 text-base">
          Create Your Free Account
        </Link>
      </section>

      <footer className="bg-brand-950 py-8 text-center text-sm text-brand-300">
        © 2026 InfraGuard · Built with FastAPI, React, OpenCV &amp; PostGIS
      </footer>
    </div>
  );
}

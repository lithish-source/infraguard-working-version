import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { PageLoader } from './components/Loading';

import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import CitizenDashboard from './pages/CitizenDashboard';
import SubmitReport from './pages/SubmitReport';
import MapView from './pages/MapView';
import ReportDetails from './pages/ReportDetails';
import MyReports from './pages/MyReports';
import AdminDashboard from './pages/AdminDashboard';
import Analytics from './pages/Analytics';
import ReportManagement from './pages/ReportManagement';
import Settings from './pages/Settings';
import Notifications from './pages/Notifications';
import NotFound from './pages/NotFound';

function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <PageLoader />;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (requireAdmin && user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <PageLoader />;
  if (user) return <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={
        <PublicRoute><Login /></PublicRoute>
      } />
      <Route path="/register" element={
        <PublicRoute><Register /></PublicRoute>
      } />

      {/* Citizen routes */}
      <Route path="/dashboard" element={
        <ProtectedRoute><CitizenDashboard /></ProtectedRoute>
      } />
      <Route path="/submit-report" element={
        <ProtectedRoute><SubmitReport /></ProtectedRoute>
      } />
      <Route path="/map" element={
        <ProtectedRoute><MapView /></ProtectedRoute>
      } />
      <Route path="/reports/:id" element={
        <ProtectedRoute><ReportDetails /></ProtectedRoute>
      } />
      <Route path="/my-reports" element={
        <ProtectedRoute><MyReports /></ProtectedRoute>
      } />
      <Route path="/notifications" element={
        <ProtectedRoute><Notifications /></ProtectedRoute>
      } />
      <Route path="/settings" element={
        <ProtectedRoute><Settings /></ProtectedRoute>
      } />

      {/* Admin routes */}
      <Route path="/admin" element={
        <ProtectedRoute requireAdmin><AdminDashboard /></ProtectedRoute>
      } />
      <Route path="/admin/analytics" element={
        <ProtectedRoute requireAdmin><Analytics /></ProtectedRoute>
      } />
      <Route path="/admin/reports" element={
        <ProtectedRoute requireAdmin><ReportManagement /></ProtectedRoute>
      } />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

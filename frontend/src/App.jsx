import { Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './stores/authStore'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import Negocios from './pages/Negocios'
import Approvals from './pages/Approvals'
import History from './pages/History'
import Settings from './pages/Settings'
import MediaBank from './pages/MediaBank'
import Billing from './pages/Billing'
import ContentAI from './pages/ContentAI'
import Contacts from './pages/Contacts'
import ContactDetail from './pages/ContactDetail'
import Funnel from './pages/Funnel'
import Ads from './pages/Ads'
import AdsOAuthCallback from './pages/AdsOAuthCallback'
import Benchmark from './pages/Benchmark'
import Landing from './pages/Landing'
import TermosDeUso from './pages/TermosDeUso'
import PoliticaPrivacidade from './pages/PoliticaPrivacidade'

function isLandingHost() {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  // Forcar landing via ?landing=1 em qualquer ambiente (util em dev)
  if (new URLSearchParams(window.location.search).has('landing')) return true
  // Landing em usinadotempo.com.br / www.usinadotempo.com.br (sem `app.`)
  return host === 'usinadotempo.com.br' || host === 'www.usinadotempo.com.br'
}

export default function App() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  // Dominio raiz serve a landing page; app.* serve a aplicacao SaaS
  if (isLandingHost()) {
    return (
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/signup"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Signup />}
      />
      <Route
        path="/forgot-password"
        element={isAuthenticated ? <Navigate to="/" replace /> : <ForgotPassword />}
      />
      <Route
        path="/reset-password"
        element={<ResetPassword />}
      />
      <Route path="/termos" element={<TermosDeUso />} />
      <Route path="/privacidade" element={<PoliticaPrivacidade />} />

      {/* Onboarding (authenticated but no layout) */}
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <Onboarding />
          </ProtectedRoute>
        }
      />

      {/* Protected routes with layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="negocios" element={<Negocios />} />
        <Route path="approvals" element={<Approvals />} />
        <Route path="media" element={<MediaBank />} />
        <Route path="history" element={<History />} />
        <Route path="content-ai" element={<ContentAI />} />
        <Route path="crm" element={<Contacts />} />
        <Route path="crm/contacts/:id" element={<ContactDetail />} />
        <Route path="crm/funnel" element={<Funnel />} />
        <Route path="ads" element={<Ads />} />
        <Route path="ads/oauth/:plataforma/callback" element={<AdsOAuthCallback />} />
        <Route path="benchmark" element={<Benchmark />} />
        <Route path="settings" element={<Settings />} />
        <Route path="settings/billing" element={<Billing />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

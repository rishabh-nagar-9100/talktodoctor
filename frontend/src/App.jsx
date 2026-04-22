/**
 * App — Main Application Component
 *
 * Root component that manages view switching between:
 * - Patient Kiosk (voice recording)
 * - Doctor Dashboard (parsed summaries)
 *
 * Uses simple state-based "routing" (no React Router needed for MVP).
 */

import { useState } from 'react';
import Header from './components/Header';
import PatientKiosk from './components/PatientKiosk';
import DoctorDashboard from './components/DoctorDashboard';
import AnalyticsDashboard from './components/AnalyticsDashboard';

export default function App() {
  // ── Active view: 'kiosk' or 'dashboard' ──
  const [activeView, setActiveView] = useState('kiosk');

  // ── Latest intake result (passed from kiosk → dashboard) ──
  const [latestIntake, setLatestIntake] = useState(null);

  /**
   * Called when the patient kiosk completes processing.
   * Stores the result so the doctor dashboard can refresh.
   */
  const handleIntakeComplete = (result) => {
    setLatestIntake(result);
  };

  return (
    <>
      <Header activeView={activeView} onViewChange={setActiveView} />

      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {activeView === 'kiosk' && <PatientKiosk onIntakeComplete={handleIntakeComplete} />}
        {activeView === 'dashboard' && <DoctorDashboard latestIntake={latestIntake} />}
        {activeView === 'analytics' && <AnalyticsDashboard />}
      </main>

      {/* ── Footer ── */}
      <footer style={{
        textAlign: 'center',
        padding: 'var(--space-lg)',
        color: 'var(--text-muted)',
        fontSize: '0.75rem',
        borderTop: '1px solid var(--border-subtle)',
      }}>
        TalkToDoctor v0.1.0 · AI assists, doctor decides · Not for clinical use without physician verification
      </footer>
    </>
  );
}

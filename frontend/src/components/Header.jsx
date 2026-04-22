/**
 * Header Component
 *
 * Sticky app header with brand logo, navigation tabs (Patient Kiosk / Doctor Dashboard),
 * and a live status indicator.
 */

import './Header.css';

export default function Header({ activeView, onViewChange }) {
  return (
    <header className="header">
      <div className="header-inner">
        {/* ── Brand ── */}
        <div className="header-brand">
          <span className="header-logo">🩺</span>
          <div>
            <div className="header-title">TalkToDoctor</div>
            <div className="header-subtitle">AI Medical Intake System</div>
          </div>
        </div>

        {/* ── Navigation Tabs ── */}
        <nav className="header-nav">
          <button
            id="nav-patient-kiosk"
            className={`nav-tab ${activeView === 'kiosk' ? 'active' : ''}`}
            onClick={() => onViewChange('kiosk')}
          >
            🎤 Patient Kiosk
          </button>
          <button
            id="nav-doctor-dashboard"
            className={`nav-tab ${activeView === 'dashboard' ? 'active' : ''}`}
            onClick={() => onViewChange('dashboard')}
          >
            👨‍⚕️ Doctor Dashboard
          </button>
          <button
            id="nav-analytics"
            className={`nav-tab ${activeView === 'analytics' ? 'active' : ''}`}
            onClick={() => onViewChange('analytics')}
          >
            📊 Analytics
          </button>
        </nav>

        {/* ── Status ── */}
        <div className="header-status">
          <span className="status-dot"></span>
          System Online
        </div>
      </div>
    </header>
  );
}

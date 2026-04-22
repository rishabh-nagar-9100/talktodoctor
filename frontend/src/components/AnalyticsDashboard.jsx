import { useState, useEffect } from 'react';
import { getAnalyticsDashboard } from '../services/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  BarChart, Bar
} from 'recharts';
import './DoctorDashboard.css';

const RISK_COLORS = {
  'High Risk': '#ef4444',     // var(--critical)
  'Moderate Risk': '#f59e0b', // var(--warning)
  'Low Risk': '#10b981'       // var(--success)
};

const SYMPTOM_COLOR = '#3b82f6'; // var(--primary)
const VOLUME_COLOR = '#8b5cf6';  // purple shade for variety

export default function AnalyticsDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchData() {
      try {
        const result = await getAnalyticsDashboard();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="dashboard-main" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ fontSize: '2rem' }}>⏳</div>
        <p>Loading analytics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-main" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ fontSize: '2rem' }}>❌</div>
        <p className="sidebar-error">{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const { system_metrics, productivity, trends } = data;

  const volumeData = trends.volume_history || [];
  const riskData = trends.risk_distribution || [];
  const symptomData = trends.top_symptoms || [];

  return (
    <div className="dashboard" style={{ padding: '2rem', maxWidth: '1440px', width: '100%', margin: '0 auto', overflowY: 'auto' }}>
      <h2 className="patient-title" style={{ marginBottom: '2rem' }}>📊 Platform Analytics</h2>

      {/* ── Top Level Stats ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem', marginBottom: '2rem', width: '100%' }}>
        <div className="glass-card" style={{ textAlign: 'center', padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--primary)', lineHeight: '1' }}>
            {system_metrics.total_intakes}
          </div>
          <div style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: '500' }}>Total Intakes</div>
        </div>
        
        <div className="glass-card" style={{ textAlign: 'center', padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--success)', lineHeight: '1' }}>
            {productivity.estimated_hours_saved}h
          </div>
          <div style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: '500' }}>Doctor Time Saved</div>
        </div>

        <div className="glass-card" style={{ textAlign: 'center', padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '3rem', fontWeight: 'bold', color: 'var(--warning)', lineHeight: '1' }}>
            {system_metrics.total_patients}
          </div>
          <div style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: '500' }}>Active Patients</div>
        </div>

        <div className="glass-card" style={{ textAlign: 'center', padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '3rem', fontWeight: 'bold', color: '#8b5cf6', lineHeight: '1' }}>
            {system_metrics.total_reports_analyzed}
          </div>
          <div style={{ color: 'var(--text-muted)', marginTop: '0.5rem', fontWeight: '500' }}>Reports Analyzed</div>
        </div>
      </div>

      {/* ── Full Width Line Chart ── */}
      <div className="glass-card" style={{ marginBottom: '2rem', padding: '1.5rem' }}>
        <h3 className="section-title" style={{ marginBottom: '1.5rem' }}>📈 Intake Volume (Last 7 Days)</h3>
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <LineChart data={volumeData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)' }} />
              <YAxis stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)' }} allowDecimals={false} />
              <RechartsTooltip 
                contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}
                itemStyle={{ color: VOLUME_COLOR, fontWeight: 'bold' }}
              />
              <Line type="monotone" dataKey="intakes" name="Intakes" stroke={VOLUME_COLOR} strokeWidth={4} dot={{ r: 6, fill: VOLUME_COLOR, strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 8 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem', width: '100%' }}>
        
        {/* ── Donut Chart for Risk ── */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <h3 className="section-title" style={{ marginBottom: '1rem' }}>⚠️ Triage Risk Distribution</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={riskData}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percent }) => percent > 0 ? `${name} (${(percent * 100).toFixed(0)}%)` : ''}
                  labelLine={false}
                >
                  {riskData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={RISK_COLORS[entry.name]} stroke="rgba(0,0,0,0)" />
                  ))}
                </Pie>
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}
                  itemStyle={{ fontWeight: 'bold', color: 'var(--text-main)' }}
                />
                <Legend verticalAlign="bottom" height={36} wrapperStyle={{ color: 'var(--text-muted)' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* ── Bar Chart for Symptoms ── */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <h3 className="section-title" style={{ marginBottom: '1rem' }}>🤒 Top Patient Symptoms</h3>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={symptomData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(255,255,255,0.1)" />
                <XAxis type="number" stroke="var(--text-muted)" allowDecimals={false} />
                <YAxis dataKey="name" type="category" stroke="var(--text-muted)" width={100} tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '8px' }}
                  itemStyle={{ color: SYMPTOM_COLOR, fontWeight: 'bold' }}
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                />
                <Bar dataKey="count" name="Cases" fill={SYMPTOM_COLOR} radius={[0, 4, 4, 0]}>
                  {symptomData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={SYMPTOM_COLOR} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}

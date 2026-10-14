import { useNavigate } from 'react-router-dom'
import { Shield, Coins, Cpu, Activity, ArrowRight, Sun, Moon, Lock, Cloud, Terminal, CheckCircle } from 'lucide-react'
import useAuthStore from '../store/authStore'

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;500;600;700;800&family=Outfit:wght@300;400;500;600;700;800&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root,
  [data-theme="dark"] {
    --lp-bg: #07090e;
    --lp-surface: #0e111a;
    --lp-surface-hover: #161b29;
    --lp-border: #1e2638;
    --lp-accent: #3b82f6;
    --lp-accent-glow: rgba(59,130,246,0.15);
    --lp-text: #f1f5f9;
    --lp-text-muted: #64748b;
    --lp-text-dim: #94a3b8;
    --lp-green: #10b981;
    --lp-purple: #8b5cf6;
  }

  [data-theme="light"] {
    --lp-bg: #f8fafc;
    --lp-surface: #ffffff;
    --lp-surface-hover: #f1f5f9;
    --lp-border: #e2e8f0;
    --lp-accent: #2563eb;
    --lp-accent-glow: rgba(37,99,235,0.08);
    --lp-text: #0f172a;
    --lp-text-muted: #8892b0;
    --lp-text-dim: #475569;
    --lp-green: #059669;
    --lp-purple: #7c3aed;
  }

  .lp-root {
    min-height: 100vh;
    background: var(--lp-bg);
    color: var(--lp-text);
    font-family: 'Outfit', sans-serif;
    overflow-x: hidden;
    position: relative;
    transition: background 0.3s ease, color 0.3s ease;
  }

  .lp-grid-bg {
    position: fixed; inset: 0; z-index: 0;
    background-image:
      linear-gradient(rgba(59,130,246,0.02) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59,130,246,0.02) 1px, transparent 1px);
    background-size: 56px 56px;
    mask-image: radial-gradient(ellipse 60% 60% at 50% 50%, black 40%, transparent 100%);
    pointer-events: none;
  }

  .lp-glow-1 {
    position: absolute; top: -10%; left: 30%;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(59,130,246,0.05) 0%, transparent 70%);
    z-index: 0; pointer-events: none;
  }
  .lp-glow-2 {
    position: absolute; top: 50%; right: -10%;
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(139,92,246,0.04) 0%, transparent 70%);
    z-index: 0; pointer-events: none;
  }

  /* HEADER */
  .lp-header {
    position: sticky; top: 0; z-index: 50;
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--lp-border);
    background: rgba(var(--lp-bg), 0.7);
    transition: all 0.3s ease;
  }
  
  .lp-nav {
    max-width: 1200px; margin: 0 auto;
    padding: 16px 24px;
    display: flex; align-items: center; justify-content: space-between;
  }

  .lp-logo {
    display: flex; align-items: center; gap: 10px;
    cursor: pointer;
  }
  .lp-logo-icon {
    width: 34px; height: 34px; border-radius: 8px;
    background: linear-gradient(135deg, var(--lp-accent) 0%, var(--lp-purple) 100%);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 16px; font-weight: 800;
    box-shadow: 0 4px 12px var(--lp-accent-glow);
  }
  .lp-logo-text {
    font-family: 'Syne', sans-serif;
    font-weight: 800; font-size: 20px;
    letter-spacing: -0.02em;
  }

  .lp-nav-actions { display: flex; align-items: center; gap: 16px; }

  /* HERO */
  .lp-hero {
    max-width: 1200px; margin: 0 auto;
    padding: 80px 24px 100px;
    text-align: center;
    position: relative; z-index: 1;
  }

  .lp-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: var(--lp-accent-glow);
    border: 1px solid var(--lp-border);
    padding: 6px 14px; border-radius: 99px;
    font-family: 'Space Mono', monospace;
    font-size: 11px; color: var(--lp-accent);
    margin-bottom: 24px;
    font-weight: 600;
  }
  .lp-badge-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--lp-accent);
    box-shadow: 0 0 8px var(--lp-accent);
  }

  .lp-title {
    font-family: 'Outfit', sans-serif;
    font-size: 58px; font-weight: 800; line-height: 1.15;
    letter-spacing: -0.03em;
    max-width: 850px; margin: 0 auto 24px;
  }
  .lp-title span {
    background: linear-gradient(135deg, var(--lp-accent) 0%, var(--lp-purple) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .lp-subtitle {
    font-size: 17px; line-height: 1.6;
    color: var(--lp-text-dim);
    max-width: 650px; margin: 0 auto 40px;
  }

  /* BUTTONS */
  .lp-btn {
    height: 38px; padding: 0 20px; border-radius: 8px;
    font-size: 14px; font-weight: 600; cursor: pointer;
    transition: all 0.2s ease;
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    font-family: inherit;
  }
  .lp-btn-primary {
    background: var(--lp-accent); color: #fff; border: none;
    box-shadow: 0 4px 20px rgba(59,130,246,0.3);
  }
  .lp-btn-primary:hover {
    opacity: 0.95; transform: translateY(-1px);
    box-shadow: 0 6px 24px rgba(59,130,246,0.4);
  }
  .lp-btn-secondary {
    background: var(--lp-surface); color: var(--lp-text);
    border: 1px solid var(--lp-border);
  }
  .lp-btn-secondary:hover {
    background: var(--lp-surface-hover); transform: translateY(-1px);
  }

  /* SHOWCASE MOCK */
  .lp-showcase {
    max-width: 1000px; margin: 0 auto 100px;
    background: var(--lp-surface);
    border: 1px solid var(--lp-border);
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.15);
    position: relative; z-index: 2;
  }
  .lp-mock-header {
    display: flex; align-items: center; gap: 6px;
    border-bottom: 1px solid var(--lp-border);
    padding-bottom: 14px; margin-bottom: 20px;
  }
  .lp-dot { width: 10px; height: 10px; border-radius: 50%; }
  .lp-dot.red { background: #ef4444; }
  .lp-dot.yellow { background: #fbbf24; }
  .lp-dot.green { background: #10b981; }

  .lp-mock-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px;
  }
  .lp-mock-card {
    background: var(--lp-bg);
    border: 1px solid var(--lp-border);
    border-radius: 8px; padding: 20px;
    text-align: left;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
  }
  .lp-mock-label { font-size: 11px; color: var(--lp-text-muted); font-family: 'Space Mono', monospace; }
  .lp-mock-val { font-size: 22px; font-weight: 700; margin-top: 4px; }
  .lp-mock-pill {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 10px; padding: 2px 8px; border-radius: 99px;
    background: rgba(16,185,129,0.1); color: var(--lp-green);
    margin-top: 8px; font-weight: 600;
  }

  /* FEATURES */
  .lp-features {
    max-width: 1200px; margin: 0 auto;
    padding: 40px 24px 100px;
    position: relative; z-index: 1;
  }
  .lp-sect-title {
    font-family: 'Syne', sans-serif;
    font-size: 36px; font-weight: 800; text-align: center;
    margin-bottom: 50px;
  }
  .lp-feat-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px;
  }
  .lp-feat-card {
    background: var(--lp-surface);
    border: 1px solid var(--lp-border);
    border-radius: 12px; padding: 30px;
    text-align: left; transition: all 0.2s ease;
  }
  .lp-feat-card:hover {
    transform: translateY(-4px);
    border-color: var(--lp-accent);
    box-shadow: 0 10px 30px rgba(59,130,246,0.05);
  }
  .lp-feat-icon {
    width: 44px; height: 44px; border-radius: 10px;
    background: var(--lp-accent-glow);
    color: var(--lp-accent);
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 20px;
  }
  .lp-feat-title { font-size: 18px; font-weight: 700; margin-bottom: 12px; }
  .lp-feat-desc { font-size: 13px; color: var(--lp-text-dim); line-height: 1.6; }

  /* CTA */
  .lp-cta {
    max-width: 1000px; margin: 0 auto 100px;
    background: linear-gradient(135deg, rgba(59,130,246,0.03) 0%, rgba(139,92,246,0.03) 100%);
    border: 1px solid var(--lp-border);
    border-radius: 16px; padding: 60px 40px;
    text-align: center; position: relative; z-index: 1;
  }
  .lp-cta-title {
    font-family: 'Syne', sans-serif;
    font-size: 32px; font-weight: 800; margin-bottom: 16px;
  }

  /* FOOTER */
  .lp-footer {
    border-top: 1px solid var(--lp-border);
    padding: 30px 24px; text-align: center;
    font-size: 12px; color: var(--lp-text-muted);
    position: relative; z-index: 1;
    background: rgba(var(--lp-bg), 0.5);
  }

  /* Responsive styling */
  @media (max-width: 768px) {
    .lp-title { font-size: 40px; }
    .lp-feat-grid { grid-template-columns: 1fr; }
    .lp-mock-grid { grid-template-columns: 1fr; }
  }
`

export default function LandingPage({ theme, toggleTheme }) {
  const navigate = useNavigate()
  const { isAuthenticated, isInitialized } = useAuthStore()

  return (
    <>
      <style>{styles}</style>

      <div className="lp-root">
        <div className="lp-grid-bg" />
        <div className="lp-glow-1" />
        <div className="lp-glow-2" />

        {/* Header */}
        <header className="lp-header">
          <div className="lp-nav">
            <div className="lp-logo" onClick={() => navigate('/')}>
              <div className="lp-logo-icon">⚡</div>
              <div>
                <div className="lp-logo-text">CloudOpt</div>
              </div>
            </div>
            <div className="lp-nav-actions">
              <button
                onClick={toggleTheme}
                style={{
                  width: 38, height: 38, borderRadius: 8,
                  background: 'var(--lp-surface)', border: '1px solid var(--lp-border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', color: 'var(--lp-text-dim)',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--lp-surface-hover)'; e.currentTarget.style.color = 'var(--lp-text)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--lp-surface)'; e.currentTarget.style.color = 'var(--lp-text-dim)' }}
              >
                {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
              </button>
              {!isInitialized ? (
                <div
                  className="lp-btn lp-btn-secondary"
                  style={{ width: 84, opacity: 0.6, pointerEvents: 'none' }}
                  role="status"
                  aria-label="Loading authentication status"
                >
                  ···
                </div>
              ) : isAuthenticated ? (
                <button className="lp-btn lp-btn-secondary" onClick={() => navigate('/dashboard')}>
                  Dashboard
                </button>
              ) : (
                <button className="lp-btn lp-btn-secondary" onClick={() => navigate('/login')}>
                  Sign In
                </button>
              )}
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <section className="lp-hero">
          <div className="lp-badge">
            <div className="lp-badge-dot" />
            AI-POWERED CLOUD MANAGEMENT
          </div>
          <h1 className="lp-title">
            Optimize your cloud.<br />
            <span>Eliminate waste</span> automatically.
          </h1>
          <p className="lp-subtitle">
            Secure, analyze, and optimize your AWS, GCP, and Azure cloud infrastructure in real-time. Powered by advanced AI agents that scan your code and credentials.
          </p>

          <div style={{ display: 'flex', gap: 14, justifyContent: 'center', marginBottom: 60 }}>
            {!isInitialized ? (
              <div
                className="lp-btn lp-btn-primary"
                style={{ width: 160, opacity: 0.6, pointerEvents: 'none' }}
                role="status"
                aria-label="Loading authentication status"
              >
                ···
              </div>
            ) : isAuthenticated ? (
              <button className="lp-btn lp-btn-primary" onClick={() => navigate('/dashboard')}>
                Go to Dashboard <ArrowRight size={15} />
              </button>
            ) : (
              <button className="lp-btn lp-btn-primary" onClick={() => navigate('/login')}>
                Get Started Free <ArrowRight size={15} />
              </button>
            )}
            <button
              className="lp-btn lp-btn-secondary"
              onClick={() => navigate(isAuthenticated ? '/security' : '/login')}
            >
              Deploy Scanner <Terminal size={14} />
            </button>
          </div>

          {/* Interactive Mock Dashboard */}
          <div className="lp-showcase">
            <div className="lp-mock-header">
              <div className="lp-dot red" />
              <div className="lp-dot yellow" />
              <div className="lp-dot green" />
              <span style={{ fontSize: 10, color: 'var(--lp-text-muted)', fontFamily: 'Space Mono', marginLeft: 10 }}>CloudOpt Workspace Dashboard</span>
            </div>
            <div className="lp-mock-grid">
              <div className="lp-mock-card">
                <span className="lp-mock-label">OVERALL SECURITY SCORE</span>
                <div className="lp-mock-val" style={{ color: 'var(--lp-accent)' }}>86%</div>
                <div className="lp-mock-pill">Excellent</div>
              </div>
              <div className="lp-mock-card">
                <span className="lp-mock-label">MONTHLY SPEND SAVINGS</span>
                <div className="lp-mock-val" style={{ color: 'var(--lp-green)' }}>$1,240</div>
                <div className="lp-mock-pill" style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--lp-green)' }}>42% savings</div>
              </div>
              <div className="lp-mock-card">
                <span className="lp-mock-label">REMEDIATION PLAYBOOKS</span>
                <div className="lp-mock-val" style={{ color: 'var(--lp-purple)' }}>CLI & Cloud</div>
                <div className="lp-mock-pill" style={{ background: 'rgba(139,92,246,0.1)', color: 'var(--lp-purple)' }}>Automated Fixes</div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="lp-features">
          <h2 className="lp-sect-title">Complete Cloud Intelligence</h2>
          <div className="lp-feat-grid">
            <div className="lp-feat-card">
              <div className="lp-feat-icon">
                <Shield size={20} />
              </div>
              <h3 className="lp-feat-title">AI Security Audit</h3>
              <p className="lp-feat-desc">
                Automatically scans repository folders and codebases recursively. Detects hardcoded secrets, misconfigurations, and vulnerabilities with high precision.
              </p>
            </div>
            <div className="lp-feat-card">
              <div className="lp-feat-icon">
                <Coins size={20} />
              </div>
              <h3 className="lp-feat-title">Cost Analysis</h3>
              <p className="lp-feat-desc">
                Gain deep visibility into your service and provider spending. Detect anomalous cost spikes (+23%) and get precise actionable recommendations.
              </p>
            </div>
            <div className="lp-feat-card">
              <div className="lp-feat-icon">
                <Cpu size={20} />
              </div>
              <h3 className="lp-feat-title">Automated Remediations</h3>
              <p className="lp-feat-desc">
                Get click-by-click instructions or copy-pasteable CLI commands to resolve security, compliance, and budget issues in seconds.
              </p>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="lp-cta">
          <h2 className="lp-cta-title">Ready to secure your cloud?</h2>
          <p className="lp-subtitle" style={{ marginBottom: 30 }}>
            Connect your cloud providers, scan your repositories, and reduce waste by up to 40% in your first month.
          </p>
          <button
            className="lp-btn lp-btn-primary"
            onClick={() => navigate(isAuthenticated ? '/dashboard' : '/login')}
          >
            {isAuthenticated ? 'Go to Dashboard' : 'Start Auditing Now'} <ArrowRight size={15} />
          </button>
        </section>

        {/* Footer */}
        <footer className="lp-footer">
          <div>© {new Date().getFullYear()} CloudOpt Inc. All rights reserved. End-to-End Encrypted · Tenant Isolated.</div>
        </footer>
      </div>
    </>
  )
}

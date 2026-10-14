import { useState, useRef, useEffect } from 'react'
import { ShieldCheck, Lock, Upload, GitBranch, X, Loader2 } from 'lucide-react'
import AlertBanner from '../components/security/AlertBanner'
import useCloudStore from '../store/cloudStore'

// ─── component ────────────────────────────────────────────────────────────────

export default function SecurityAudit() {
  const { 
    alerts: storeAlerts, 
    dismissedAlerts, 
    dismissAlert,
    scanOverall,
    scanCoverage,
    scanTime,
    repoUrl: storeRepoUrl,
    hasScanned,
    scanning,
    progress,
    scanError,
    setRepoUrl,
    startBackgroundScan,
    fetchLatestScan,
    setError
  } = useCloudStore()

  useEffect(() => {
    fetchLatestScan()
  }, [fetchLatestScan])

  const [repoUrlInput, setRepoUrlInput] = useState(storeRepoUrl || '')
  const [files, setFiles]               = useState([])
  const fileRef = useRef()

  const rawAlerts    = storeAlerts
  const activeAlerts = rawAlerts.filter(a => !dismissedAlerts.includes(a.id))

  const activeOverall = {
    ...scanOverall,
    score: scanOverall?.score ?? null,
    icon: Lock,
    color: hasScanned ? 'var(--blue)' : 'var(--text-muted)',
    status: hasScanned ? (scanOverall?.status || 'Assessment complete') : 'Not assessed',
  }

  // ── file handling ──────────────────────────────────────────────────────────

  function addFiles(incoming) {
    const next = Array.from(incoming)
    setFiles(prev => {
      const names = new Set(prev.map(f => f.name))
      return [...prev, ...next.filter(f => !names.has(f.name))]
    })
  }

  // ── scan ──────────────────────────────────────────────────────────────────

  async function startScan() {
    const url = repoUrlInput.trim()
    if (!url && files.length === 0) {
      setError('Add a repo URL or upload at least one file.')
      return
    }
    setError('')
    setRepoUrl(url)

    const filesWithContent = []
    for (const f of files) {
      try {
        const text = await f.text()
        filesWithContent.push({ name: f.name, content: text.slice(0, 3000) })
      } catch {
        setError(`Unable to read "${f.name}". Choose a different file.`)
        return
      }
    }

    startBackgroundScan(url, filesWithContent)
  }

  const OverallIcon = activeOverall.icon

  return (
    <div className="page-content">

      {/* ── Scan input ── */}
      <div className="card">
        <div className="section-header" style={{ marginBottom: 10 }}>
          <span className="card__title" style={{ margin: 0 }}>Security scan</span>
          {scanTime && (
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Last scanned {new Date(scanTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
          {/* repo url */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, flex: 1,
            border: '1px solid var(--border)', borderRadius: 8,
            padding: '0 10px', height: 36, background: 'var(--surface)',
          }}>
            <GitBranch size={14} color="var(--text-muted)" />
            <input
              type="text"
              value={repoUrlInput}
              onChange={e => setRepoUrlInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && startScan()}
              placeholder="https://github.com/owner/repo"
              style={{
                flex: 1, border: 'none', outline: 'none',
                background: 'transparent', fontSize: 13, color: 'var(--text)',
              }}
            />
          </div>

          {/* upload */}
          <button
            className="btn btn-sm btn-ghost"
            onClick={() => fileRef.current?.click()}
            style={{ display: 'flex', alignItems: 'center', gap: 5, height: 36, padding: '0 12px' }}
            title="Upload files"
          >
            <Upload size={13} />
            {files.length > 0 ? `${files.length} file${files.length > 1 ? 's' : ''}` : 'Select Folder'}
          </button>
          <input
            ref={fileRef}
            type="file"
            webkitdirectory="true"
            directory="true"
            multiple
            style={{ display: 'none' }}
            onChange={e => addFiles(e.target.files)}
          />

          {/* scan */}
          <button
            className="btn btn-sm"
            onClick={startScan}
            disabled={scanning}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              height: 36, padding: '0 14px',
              opacity: scanning ? 0.6 : 1,
              cursor: scanning ? 'not-allowed' : 'pointer',
            }}
          >
            {scanning ? <Loader2 size={13} className="spin" /> : <ShieldCheck size={13} />}
            {scanning ? 'Scanning…' : 'Scan'}
          </button>
        </div>

        <p role="note" style={{ fontSize: 11, color: 'var(--text-muted)', margin: '8px 0' }}>
          Repository scans automatically include an advisory Gemini review when
          available. Up to 12 bounded source excerpts are sent to Google after
          common secret-like values are redacted. No source is sent to OSV. AI
          findings may be incomplete and should be verified.
        </p>

        {/* file tags */}
        {files.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 6 }}>
            {files.map(f => (
              <span key={f.name} style={{
                display: 'flex', alignItems: 'center', gap: 4,
                fontSize: 11, padding: '2px 8px',
                border: '1px solid var(--border)', borderRadius: 6,
                color: 'var(--text-muted)',
              }}>
                {f.name}
                <X size={10} style={{ cursor: 'pointer' }}
                  onClick={() => setFiles(prev => prev.filter(p => p.name !== f.name))} />
              </span>
            ))}
          </div>
        )}

        {/* progress */}
        {scanning && (
          <div style={{ height: 2, background: 'var(--border)', borderRadius: 99, overflow: 'hidden', marginTop: 4 }}>
            <div style={{
              height: '100%', width: `${progress}%`,
              background: 'var(--accent)', borderRadius: 99,
              transition: 'width 0.4s ease',
            }} />
          </div>
        )}

        {scanError && <p style={{ fontSize: 11, color: 'var(--red)', marginTop: 6 }}>{scanError}</p>}
      </div>

      {/* ── Active alerts ── */}
      {activeAlerts.length > 0 && (
        <div>
          <div className="section-header">
            <span className="section-title">
              {hasScanned ? 'Scan Findings' : 'Active alerts'} ({activeAlerts.length})
            </span>
          </div>
          <div className="alerts-stack">
            {activeAlerts.map(alert => (
              <AlertBanner key={alert.id} alert={alert} onDismiss={dismissAlert} />
            ))}
          </div>
        </div>
      )}
      {hasScanned && activeAlerts.length === 0 && (
        <p role="status" style={{ color: 'var(--text-muted)' }}>
          No findings were detected by the enabled checks. This partial result is not proof that the repository is secure.
        </p>
      )}

      {/* ── Coverage and findings summary ── */}
      <div>
        <div className="section-header">
          <span className="section-title">Assessment coverage</span>
        </div>
        <div className="card" style={{ padding: '16px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <OverallIcon size={18} color={activeOverall.color} />
              <span style={{ fontSize: 15, fontWeight: 600, color: activeOverall.color }}>
                {hasScanned ? 'Partial assessment' : 'Not assessed'}
              </span>
            </div>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 10px' }}>
            {hasScanned
              ? `${activeOverall.totalFindings ?? activeAlerts.length} finding(s) in ${activeOverall.filesScanned ?? 0} scanned file(s). Rule-based checks are limited and do not prove security.`
              : 'Run a scan to see which checks were available. No overall security score is calculated.'}
          </p>
          {hasScanned && (
            <div style={{ display: 'grid', gap: 5, fontSize: 12 }}>
              {scanCoverage?.execution_mode === 'synchronous_fallback' && (
                <div role="status">
                  Scan queue unavailable; this repository was scanned synchronously without a background worker.
                </div>
              )}
              <div>Source rules: {scanCoverage?.static_analysis?.status ?? 'unavailable'} (partial by design)</div>
              {Object.entries(scanCoverage?.dependencies ?? {}).map(([ecosystem, status]) => (
                <div key={ecosystem}>
                  {ecosystem}: {status.replaceAll('_', ' ')}
                </div>
              ))}
              <div>
                Gemini advisory: {scanCoverage?.gemini?.status?.replaceAll('_', ' ') ?? 'not requested'}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Compliance ── */}
      <div className="card">
        <span className="card__title">Compliance frameworks</span>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 0 }}>
          CIS, SOC 2, ISO 27001, and PCI DSS compliance are not evaluated by this scanner.
        </p>
      </div>

    </div>
  )
}
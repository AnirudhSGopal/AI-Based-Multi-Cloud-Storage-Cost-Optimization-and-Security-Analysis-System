import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import apiClient from '../services/api'
import cloudService from '../services/cloudService'

function toAlertShape(a) {
  const type = a.severity === 'critical' ? 'critical' : a.severity === 'warning' ? 'warning' : 'info'
  
  let fixSteps = []
  if (type === 'critical') {
    fixSteps = [
      `Locate the affected resource or file: ${a.location ?? 'Unknown'}.`,
      'Identify and extract any hardcoded credentials, API keys, or JWT secrets.',
      'Configure the service to inject these values via environment variables.',
      'Rotate any exposed credentials immediately on the provider control panel.'
    ]
  } else if (type === 'warning') {
    fixSteps = [
      `Review access rules and permissions for: ${a.location ?? 'Unknown'}.`,
      'Enforce least-privilege configurations and restrict open access controls.',
      'Enable server-side validation and secure configurations.',
      'Run verification scripts to ensure that resources are not publicly queryable.'
    ]
  } else {
    fixSteps = [
      'Assess development guidelines and enforce secure header best practices.',
      'Implement missing security libraries or middleware.',
      'Set up continuous security testing in the CI/CD pipeline.'
    ]
  }

  return {
    id:       a.id,
    type,
    title:    a.message,
    impact:   a.message,
    resource: a.location ?? 'Unknown',
    owner:    'Security Team',
    time:     'just now',
    fixSteps,
  }
}

function toComplianceRow(r) {
  const status = r.status === 'pass' ? 'Pass' : 'Fail'
  const score  = r.status === 'pass' ? '>85%' : r.severity === 'high' ? '<70%' : '70–85%'
  return { framework: r.check, status, score, findings: r.detail }
}

const useCloudStore = create(
  persist(
    (set, get) => ({
      selectedProvider: 'all',
      dateRange: '30d',
      isLoading: false,
      securityScore: null,
      alerts: [],
      dismissedAlerts: [],
      scanOverall: null,
      scanCoverage: null,
      scanCompliance: null,
      scanTime: null,
      repoUrl: '',
      hasScanned: false,

      // In-memory background scan states
      scanning: false,
      progress: 0,
      scanError: '',

      // Multi-Cloud Account & Cost Optimization state
      accounts: [],
      accountsError: '',
      costData: [],
      resources: [],
      recommendations: [],
      dailyTrend: [],
      costLoading: false,
      accountsLoading: false,
      costError: '',

      setProvider:  (provider) => set({ selectedProvider: provider }),
      setDateRange: (range)    => set({ dateRange: range }),
      setLoading:   (val)      => set({ isLoading: val }),
      setRepoUrl:   (url)      => set({ repoUrl: url }),
      dismissAlert: (id)       => set((s) => ({ dismissedAlerts: [...s.dismissedAlerts, id] })),
      setError:     (err)      => set({ scanError: err }),

      // ── Cloud Accounts & Sync Actions ──────────────────────────────────
      fetchAccounts: async () => {
        set({ accountsLoading: true, accountsError: '' })
        try {
          const { data } = await cloudService.getAccounts()
          const accountsList = data.accounts || []
          set({ accounts: accountsList, accountsLoading: false, accountsError: '' })
          return accountsList
        } catch (e) {
          console.warn("Failed to fetch cloud accounts")
          set({
            accountsLoading: false,
            accountsError: e.response?.data?.error || 'Unable to load cloud accounts.',
          })
          return []
        }
      },

      testConnection: async (provider, credentials) => {
        try {
          const { data } = await cloudService.testConnection({ provider, credentials })
          return { success: true, message: data.message || "Credentials verified." }
        } catch (e) {
          const message = e.response?.data?.error || e.message || "Validation failed"
          return { success: false, error: message }
        }
      },

      addCloudAccount: async (provider, label, credentials) => {
        try {
          const { data } = await cloudService.createAccount({
            provider,
            account_label: label,
            credentials,
          })
          await get().fetchAccounts()
          await get().syncAllAccounts()
          return { success: true, message: data.message }
        } catch (e) {
          const message = e.response?.data?.error || e.message || "Failed to save account"
          return { success: false, error: message }
        }
      },

      deleteCloudAccount: async (accountId) => {
        try {
          await cloudService.deleteAccount(accountId)
          await get().fetchAccounts()
          await get().syncAllAccounts()
          return { success: true }
        } catch (e) {
          const message = e.response?.data?.error || e.message || "Failed to delete account"
          return { success: false, error: message }
        }
      },

      syncAllAccounts: async (customAccounts) => {
        const accounts = customAccounts || get().accounts
        if (!accounts || accounts.length === 0) {
          set({ costData: [], resources: [], recommendations: [], dailyTrend: [], costError: '' })
          return
        }

        set({ costLoading: true, costError: '' })

        let aggregatedCost = []
        let aggregatedResources = []
        let aggregatedRecs = []
        let latestTrend = []
        let errors = []

        for (const acc of accounts) {
          try {
            const { data } = await cloudService.syncAccount(acc.id)
            if (data.cost_data) aggregatedCost = [...aggregatedCost, ...data.cost_data]
            if (data.resources) aggregatedResources = [...aggregatedResources, ...data.resources]
            if (data.recommendations) aggregatedRecs = [...aggregatedRecs, ...data.recommendations]
            if (data.daily_trend && data.daily_trend.length > 0) latestTrend = data.daily_trend
            if (data.cost_error) errors.push(`${acc.provider.toUpperCase()}: ${data.cost_error}`)
          } catch (e) {
            const errStr = e.response?.data?.error || e.message
            errors.push(`${acc.provider.toUpperCase()}: ${errStr}`)
          }
        }

        if (!latestTrend || latestTrend.length === 0) {
          try {
            const { data: trendData } = await cloudService.getChartTrend()
            if (trendData?.trend && trendData.trend.length > 0) {
              latestTrend = trendData.trend
            }
          } catch {
            // ignore
          }
        }

        const isDemo = accounts.some(a => a.account_label?.toLowerCase().includes('demo') || (a.storage_size_gb !== undefined && a.storage_size_gb < 100))

        set({
          costData: aggregatedCost,
          resources: aggregatedResources,
          recommendations: aggregatedRecs,
          dailyTrend: latestTrend,
          costError: isDemo ? '' : errors.join(" | "),
          costLoading: false,
        })
      },

      updateScanResults: (newAlerts, score, overall, coverage, compliance, scanTime, repoUrl) => set({
        alerts: newAlerts,
        securityScore: score,
        scanOverall: overall,
        scanCoverage: coverage,
        scanCompliance: compliance,
        scanTime: scanTime,
        repoUrl: repoUrl,
        hasScanned: true,
        dismissedAlerts: []
      }),

      resetScan: () => set({
        alerts: [],
        securityScore: null,
        scanOverall: null,
        scanCoverage: null,
        scanCompliance: null,
        scanTime: null,
        repoUrl: '',
        hasScanned: false,
        dismissedAlerts: [],
        scanning: false,
        progress: 0,
        scanError: ''
      }),

      fetchLatestScan: async () => {
        try {
          const { data } = await apiClient.get('/api/v1/scan/latest')
          if (data && data.scan && data.result) {
            const rawFindings = data.findings || []
            const alerts = rawFindings.map((finding) => ({
              id: finding.id,
              severity: ['critical', 'high'].includes(finding.severity)
                ? 'critical'
                : ['medium', 'low'].includes(finding.severity) ? 'warning' : 'info',
              message: [finding.title, finding.description].filter(Boolean).join(': '),
              location: finding.file_path
                ? `${finding.file_path}${finding.line_number ? `:${finding.line_number}` : ''}`
                : 'Repository',
            }))
            set({
              alerts,
              securityScore: data.result.security_score,
              scanOverall: {
                score: data.result.security_score,
                status: 'Assessment complete',
                totalFindings: data.result.total_findings,
                filesScanned: data.result.files_scanned,
                coverage: data.result.coverage,
              },
              scanCoverage: data.result.coverage,
              scanTime: data.scan.finished_at || data.scan.created_at,
              repoUrl: data.scan.repo_url,
              hasScanned: true,
            })
          }
        } catch {
          // ignore
        }
      },

      startBackgroundScan: async (url, filesWithContent) => {
        set({ scanning: true, progress: 20, scanError: '' })
        try {
          let nextOverall
          let nextCoverage = null
          let nextScanAlerts
          let nextCompliance

          const applyAuditResult = (data, executionMode) => {
            nextOverall = {
              score: null,
              status: 'Partial assessment',
              totalFindings: data.alerts?.length ?? 0,
              filesScanned: data.files_scanned ?? filesWithContent.length,
            }
            nextCoverage = {
              ...(data.coverage ?? {}),
              ...(executionMode ? { execution_mode: executionMode } : {}),
            }
            nextScanAlerts = data.alerts || []
            nextCompliance = data.compliance ? data.compliance.map(toComplianceRow) : null
          }

          if (url && filesWithContent.length === 0) {
            let started
            try {
              const response = await apiClient.post(
                '/api/v1/scan/start',
                { repo_url: url, gemini_review: true },
              )
              started = response.data
            } catch (error) {
              const queueError = error?.response?.data?.error
              const queueUnavailable =
                error?.response?.status === 503
                && typeof queueError === 'string'
                && queueError.startsWith('Scan queue unavailable.')
              if (!queueUnavailable) throw error

              set({ progress: 50 })
              const { data } = await apiClient.post('/api/audit', {
                repoUrl: url,
                files: [],
                gemini_review: true,
              }, { timeout: 300000 })
              applyAuditResult(data, 'synchronous_fallback')
            }

            if (started) {
              const scanId = started.scan.id
              let data
              const deadline = Date.now() + 5 * 60 * 1000

              while (Date.now() < deadline) {
                await new Promise((resolve) => window.setTimeout(resolve, 1500))
                const { data: status } = await apiClient.get(`/api/v1/scan/${scanId}`)
                if (status.scan.status === 'completed') {
                  data = status
                  break
                }
                if (status.scan.status === 'failed' || status.scan.status === 'cancelled') {
                  throw new Error(status.scan.error_msg || `Scan ${status.scan.status}.`)
                }
                set({ progress: Math.min(get().progress + 5, 90) })
              }

              if (!data) throw new Error('Scan timed out while waiting for results.')
              nextCoverage = data.result.coverage ?? null
              nextOverall = {
                score: null,
                status: 'Partial assessment',
                totalFindings: data.result.total_findings,
                filesScanned: data.result.files_scanned,
                coverage: nextCoverage,
              }
              nextScanAlerts = data.findings.map((finding) => ({
                id: finding.id,
                severity: ['critical', 'high'].includes(finding.severity)
                  ? 'critical'
                  : ['medium', 'low'].includes(finding.severity) ? 'warning' : 'info',
                message: [finding.title, finding.description].filter(Boolean).join(': '),
                location: finding.file_path
                  ? `${finding.file_path}${finding.line_number ? `:${finding.line_number}` : ''}`
                  : 'Repository',
              }))
              nextCompliance = null
            }
          } else {
            set({ progress: 50 })
            const { data } = await apiClient.post('/api/audit', {
              repoUrl: url || null,
              files: filesWithContent,
            }, { timeout: 300000 })
            applyAuditResult(data)
          }

          set({ progress: 90 })

          set({
            alerts: nextScanAlerts.map(toAlertShape),
            securityScore: nextOverall?.score ?? null,
            scanOverall: nextOverall,
            scanCoverage: nextCoverage,
            scanCompliance: nextCompliance,
            scanTime: new Date().toISOString(),
            repoUrl: url,
            hasScanned: true,
            dismissedAlerts: [],
            scanning: false,
            progress: 0
          })
        } catch (e) {
          const detail = e?.response?.data?.error
            || e?.response?.data?.detail
            || e.message
            || 'Audit failed'
          set({ scanError: detail, scanning: false, progress: 0 })
          console.warn('Security audit request failed')
        }
      },

      reset: () => {
        set({
          selectedProvider: 'all',
          dateRange: '30d',
          isLoading: false,
          securityScore: null,
          alerts: [],
          dismissedAlerts: [],
          scanOverall: null,
          scanCoverage: null,
          scanCompliance: null,
          scanTime: null,
          repoUrl: '',
          hasScanned: false,
          scanning: false,
          progress: 0,
          scanError: '',
          accounts: [],
          accountsError: '',
          costData: [],
          resources: [],
          recommendations: [],
          dailyTrend: [],
          costLoading: false,
          accountsLoading: false,
          costError: '',
        })
      },
    }),
    {
      name: 'cloudopt-state-store',
      version: 3,
      migrate: (persistedState) => ({
        ...persistedState,
        alerts: [],
        dismissedAlerts: [],
        securityScore: null,
        scanOverall: null,
        scanCoverage: null,
        scanCompliance: null,
        scanTime: null,
        hasScanned: false,
      }),
      partialize: (state) => ({
        selectedProvider: state.selectedProvider,
        dateRange: state.dateRange,
        securityScore: state.securityScore,
        alerts: state.alerts,
        dismissedAlerts: state.dismissedAlerts,
        scanOverall: state.scanOverall,
        scanCoverage: state.scanCoverage,
        scanCompliance: state.scanCompliance,
        scanTime: state.scanTime,
        repoUrl: state.repoUrl,
        hasScanned: state.hasScanned,
        accounts: state.accounts,
        costData: state.costData,
        resources: state.resources,
        recommendations: state.recommendations,
      })
    }
  )
)

if (typeof window !== 'undefined') {
  window.__resetCloudStore = () => {
    useCloudStore.getState().reset?.()
  }
}

export default useCloudStore
import { memo } from 'react'
import { ShieldAlert, AlertTriangle, AlertCircle, Info } from 'lucide-react'

/**
 * SeverityBadge Component
 * Follows WCAG distinction rules: distinguishable by both color AND dedicated icon + text label.
 * Critical = Red, High = Orange, Medium = Amber, Low = Slate/Blue.
 */
function SeverityBadge({ severity = 'low', className = '', style = {} }) {
  const norm = String(severity).toLowerCase()

  const map = {
    critical: {
      label: 'CRITICAL',
      icon: ShieldAlert,
      className: 'severity-badge-critical',
    },
    high: {
      label: 'HIGH',
      icon: AlertTriangle,
      className: 'severity-badge-high',
    },
    medium: {
      label: 'MEDIUM',
      icon: AlertCircle,
      className: 'severity-badge-medium',
    },
    low: {
      label: 'LOW',
      icon: Info,
      className: 'severity-badge-low',
    },
    info: {
      label: 'INFO',
      icon: Info,
      className: 'severity-badge-low',
    },
  }

  const item = map[norm] || map.low
  const Icon = item.icon

  return (
    <span
      className={`severity-badge ${item.className} ${className}`}
      style={style}
      role="status"
      aria-label={`Severity: ${item.label}`}
    >
      <Icon size={12} aria-hidden="true" style={{ flexShrink: 0 }} />
      <span>{item.label}</span>
    </span>
  )
}

export default memo(SeverityBadge)

import { memo } from 'react'
import { Cloud } from 'lucide-react'

/**
 * ProviderChip Component
 * Displays cloud provider with explicit text label (AWS / Azure / GCP).
 * GCP uses distinct Google Teal/Cyan (#0d9488) to prevent confusion with success emerald.
 */
function ProviderChip({ provider = 'aws', className = '', style = {} }) {
  const norm = String(provider).toLowerCase()

  const config = {
    aws: {
      label: 'AWS',
      className: 'provider-chip-aws',
    },
    azure: {
      label: 'Azure',
      className: 'provider-chip-azure',
    },
    gcp: {
      label: 'GCP',
      className: 'provider-chip-gcp',
    },
    multi: {
      label: 'Multi-Cloud',
      className: '',
    },
  }

  const current = config[norm] || { label: String(provider).toUpperCase(), className: '' }

  return (
    <span
      className={`provider-chip ${current.className} ${className}`}
      style={style}
      title={`Cloud Provider: ${current.label}`}
    >
      <Cloud size={11} aria-hidden="true" style={{ flexShrink: 0 }} />
      <span>{current.label}</span>
    </span>
  )
}

export default memo(ProviderChip)

import { memo } from 'react'
import { Link } from 'react-router-dom'

/**
 * CloudOpt Brand Logo Component
 * Visually inspired directly by the project architecture:
 * 1. Top Facet: Cloud Platform Plane (AWS / Azure / GCP infrastructure)
 * 2. Left Facet: SecureVault Security Armor (Code scanning, secret detection, CVE protection)
 * 3. Right Facet: FinOps Cost Optimization (Deterministic rightsizing, anomaly reduction)
 * 4. Center Nexus: 3 Multi-Cloud nodes converging into an AI Intelligence core
 */
export function LogoIcon({ size = 32, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`cloudopt-logo-svg ${className}`}
      style={{ display: 'inline-block', verticalAlign: 'middle', flexShrink: 0 }}
      aria-label="CloudOpt Logo"
    >
      <defs>
        {/* Facet 1: Cloud Architecture Gradient */}
        <linearGradient id="copt-g-cloud" x1="7" y1="4" x2="33" y2="19" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#38BDF8" />
          <stop offset="100%" stopColor="#2563EB" />
        </linearGradient>

        {/* Facet 2: Security Vault & Armor Gradient */}
        <linearGradient id="copt-g-vault" x1="6" y1="13" x2="19" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#818CF8" />
          <stop offset="50%" stopColor="#4F46E5" />
          <stop offset="100%" stopColor="#312E81" />
        </linearGradient>

        {/* Facet 3: FinOps Cost Optimization Gradient */}
        <linearGradient id="copt-g-finops" x1="21" y1="13" x2="34" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#34D399" />
          <stop offset="60%" stopColor="#059669" />
          <stop offset="100%" stopColor="#0F766E" />
        </linearGradient>

        {/* Center Core Glow */}
        <radialGradient id="copt-core-glow" cx="20" cy="20.4" r="6" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#38BDF8" stopOpacity="0" />
        </radialGradient>

        <filter id="copt-shadow-depth" x="2" y="2" width="36" height="37" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feDropShadow dx="0" dy="1.5" stdDeviation="1.8" floodColor="#090D16" floodOpacity="0.4" />
        </filter>
      </defs>

      <g filter="url(#copt-shadow-depth)">
        {/* 1. TOP ISOMETRIC FACET: Multi-Cloud Infrastructure */}
        <path
          d="M20 4.2C20.3 4.2 20.6 4.35 20.8 4.47L33.2 11.64C33.7 11.93 33.7 12.64 33.2 12.93L20.8 20.1C20.3 20.39 19.7 20.39 19.2 20.1L6.8 12.93C6.3 12.64 6.3 11.93 6.8 11.64L19.2 4.47C19.4 4.35 19.7 4.2 20 4.2Z"
          fill="url(#copt-g-cloud)"
        />
        {/* Cloud contour inset */}
        <path
          d="M14 11.8C14 10.5 15.1 9.5 16.4 9.5C16.8 9.5 17.2 9.6 17.5 9.8C18.1 8.7 19.2 8 20.5 8C22.2 8 23.6 9.2 23.9 10.8C24.2 10.7 24.6 10.6 25 10.6C26.1 10.6 27 11.5 27 12.6C27 13.7 26.1 14.6 25 14.6H14.5C13.7 14.6 13 13.9 13 13.1C13 12.4 13.5 11.8 14 11.8Z"
          fill="#FFFFFF"
          fillOpacity="0.32"
        />

        {/* 2. LEFT ISOMETRIC FACET: SecureVault Security Armor & Keyhole */}
        <path
          d="M5.8 14.2C5.8 13.6 6.4 13.2 7 13.55L19 20.48C19.5 20.77 19.8 21.3 19.8 21.87V35.4C19.8 36.1 19 36.5 18.4 36.15L6.4 29.22C6 29 5.8 28.55 5.8 28.08V14.2Z"
          fill="url(#copt-g-vault)"
        />
        {/* Shield outline */}
        <path
          d="M12.8 20.5L16.2 22.45V27.5C16.2 29.2 14.7 30.7 12.8 31.3C10.9 30.7 9.4 29.2 9.4 27.5V22.45L12.8 20.5Z"
          fill="#0B0F19"
          fillOpacity="0.75"
        />
        {/* Vault Keyhole */}
        <path
          d="M12.8 23.2C13.5 23.2 14 23.7 14 24.4C14 24.9 13.7 25.3 13.3 25.5V27.8H12.3V25.5C11.9 25.3 11.6 24.9 11.6 24.4C11.6 23.7 12.1 23.2 12.8 23.2Z"
          fill="#A5B4FC"
        />

        {/* 3. RIGHT ISOMETRIC FACET: FinOps Cost Optimization */}
        <path
          d="M34.2 14.2V28.08C34.2 28.55 34 29 33.6 29.22L21.6 36.15C21 36.5 20.2 36.1 20.2 35.4V21.87C20.2 21.3 20.5 20.77 21 20.48L33 13.55C33.6 13.2 34.2 13.6 34.2 14.2Z"
          fill="url(#copt-g-finops)"
        />
        {/* Optimization plate */}
        <path
          d="M27.2 20.5L30.6 22.45V27.5C30.6 29.2 29.1 30.7 27.2 31.3C25.3 30.7 23.8 29.2 23.8 27.5V22.45L27.2 20.5Z"
          fill="#0B0F19"
          fillOpacity="0.75"
        />
        {/* Upward Cost Efficiency Vector */}
        <path
          d="M27.2 23.2L29.5 25.5H28V28.5H26.4V25.5H24.9L27.2 23.2Z"
          fill="#34D399"
        />

        {/* 4. CENTER MULTI-CLOUD CONVERGENCE NEXUS */}
        <circle cx="20" cy="20.4" r="5" fill="url(#copt-core-glow)" />

        {/* Cloud Providers Tri-Node: AWS (Amber), Azure (Sky), GCP (Emerald) */}
        <circle cx="20" cy="15.8" r="1.6" fill="#F59E0B" />
        <circle cx="15.8" cy="23.4" r="1.6" fill="#38BDF8" />
        <circle cx="24.2" cy="23.4" r="1.6" fill="#34D399" />

        {/* Center SecureVault AI Core */}
        <circle cx="20" cy="20.4" r="2.2" fill="#FFFFFF" />
        <circle cx="20" cy="20.4" r="1.1" fill="#2563EB" />
      </g>
    </svg>
  )
}

function Logo({
  size = 'md',
  showText = true,
  showSub = true,
  subText = 'Cost & Security Intelligence',
  to = null,
  className = '',
  onClick,
}) {
  const sizeMap = {
    sm: { icon: 22, title: '14px', sub: '9px', gap: 8 },
    md: { icon: 28, title: '16px', sub: '10px', gap: 10 },
    lg: { icon: 36, title: '20px', sub: '11px', gap: 12 },
    xl: { icon: 46, title: '26px', sub: '12px', gap: 14 },
  }

  const cfg = sizeMap[size] || sizeMap.md

  const content = (
    <div
      className={`cloudopt-logo ${className}`}
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: cfg.gap,
        textDecoration: 'none',
        userSelect: 'none',
        cursor: to || onClick ? 'pointer' : 'default',
      }}
    >
      <LogoIcon size={cfg.icon} />
      {showText && (
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
          <div
            style={{
              fontFamily: "var(--font-sans)",
              fontWeight: 800,
              fontSize: cfg.title,
              letterSpacing: '-0.035em',
              color: 'var(--text-primary, #0f172a)',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <span>Cloud</span>
            <span
              style={{
                background: 'linear-gradient(135deg, #2563eb 0%, #38bdf8 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Opt
            </span>
            <span
              style={{
                width: 5,
                height: 5,
                borderRadius: '50%',
                background: '#10b981',
                boxShadow: '0 0 6px rgba(16,185,129,0.8)',
                marginLeft: 1,
                alignSelf: 'center',
              }}
              title="Cloud Intelligence Online"
            />
          </div>
          {showSub && (
            <span
              style={{
                fontSize: cfg.sub,
                fontWeight: 600,
                color: 'var(--text-muted, #64748b)',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                marginTop: 2,
              }}
            >
              {subText}
            </span>
          )}
        </div>
      )}
    </div>
  )

  if (to) {
    return (
      <Link to={to} style={{ textDecoration: 'none' }}>
        {content}
      </Link>
    )
  }

  return content
}

export default memo(Logo)

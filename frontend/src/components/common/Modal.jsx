import { useEffect, memo } from 'react'
import { X } from 'lucide-react'

/**
 * Modal Component
 * Accessible dialog with Escape key listener, backdrop dismissal, and 12px radius elevation.
 */
function Modal({
  open = false,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  className = '',
}) {
  useEffect(() => {
    if (!open) return

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        onClose?.()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = originalOverflow
    }
  }, [open, onClose])

  if (!open) return null

  const sizeWidths = {
    sm: 380,
    md: 480,
    lg: 640,
  }

  const maxWidth = sizeWidths[size] || 480

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-dialog-title' : undefined}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(5, 8, 14, 0.65)',
        backdropFilter: 'blur(3px)',
        WebkitBackdropFilter: 'blur(3px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose?.()
        }
      }}
    >
      <div
        className={className}
        style={{
          width: '100%',
          maxWidth,
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          borderRadius: 'var(--radius-xl)',
          boxShadow: 'var(--shadow-modal)',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--color-border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          {title && (
            <h2
              id="modal-dialog-title"
              style={{
                fontSize: 'var(--text-md)',
                fontWeight: 600,
                color: 'var(--color-text-primary)',
                letterSpacing: '-0.01em',
              }}
            >
              {title}
            </h2>
          )}
          {onClose && (
            <button
              onClick={onClose}
              type="button"
              aria-label="Close dialog"
              style={{
                marginLeft: 'auto',
                width: 28,
                height: 28,
                borderRadius: 'var(--radius-sm)',
                background: 'transparent',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-bg-subtle)'
                e.currentTarget.style.color = 'var(--color-text-primary)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = 'var(--color-text-muted)'
              }}
            >
              <X size={15} />
            </button>
          )}
        </div>

        {/* Body */}
        <div style={{ padding: '20px', overflowY: 'auto' }}>{children}</div>

        {/* Footer */}
        {footer && (
          <div
            style={{
              padding: '12px 20px',
              borderTop: '1px solid var(--color-border-subtle)',
              background: 'var(--color-bg-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: 8,
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

export default memo(Modal)

import { memo } from 'react'
import { Loader2 } from 'lucide-react'

/**
 * CloudOpt Unified Button Component
 * Standard B2B instrument button with primary, secondary, ghost, and destructive variants.
 */
function Button({
  children,
  onClick,
  size = 'md',
  icon: Icon,
  variant = 'primary',
  disabled = false,
  loading = false,
  type = 'button',
  className = '',
  style = {},
  title,
  ariaLabel,
  ...rest
}) {
  const sizeClassMap = {
    xs: 'btn-xs',
    sm: 'btn-sm',
    md: 'btn-md',
    lg: 'btn-lg',
  }

  const iconSizes = {
    xs: 12,
    sm: 13,
    md: 14,
    lg: 16,
  }

  const variantClass = `btn-${variant}`
  const sizeClass = sizeClassMap[size] || 'btn-md'
  const classes = ['btn', variantClass, sizeClass, className].filter(Boolean).join(' ')

  const isDisabled = disabled || loading

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      aria-disabled={isDisabled}
      aria-busy={loading}
      aria-label={ariaLabel || title}
      title={title}
      className={classes}
      style={style}
      {...rest}
    >
      {loading ? (
        <Loader2 size={iconSizes[size] || 14} className="spin" />
      ) : (
        Icon && <Icon size={iconSizes[size] || 14} />
      )}
      {children}
    </button>
  )
}

export default memo(Button)
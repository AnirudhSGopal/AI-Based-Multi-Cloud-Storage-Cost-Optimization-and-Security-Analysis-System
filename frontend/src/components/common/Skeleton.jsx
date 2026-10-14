import { memo } from 'react'

/**
 * Skeleton Component
 * Calibrated loading placeholder for data tables and metric cards.
 * Respects prefers-reduced-motion.
 */
function Skeleton({
  width = '100%',
  height = 16,
  borderRadius = 'var(--radius-sm)',
  className = '',
  style = {},
}) {
  return (
    <div
      className={`skeleton-box ${className}`}
      style={{
        width,
        height,
        borderRadius,
        ...style,
      }}
      aria-hidden="true"
    />
  )
}

export default memo(Skeleton)

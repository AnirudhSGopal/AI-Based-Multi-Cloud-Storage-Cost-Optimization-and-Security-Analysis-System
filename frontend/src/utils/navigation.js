/**
 * Validates returnTo path to prevent open redirects.
 * Must be a same-origin relative path starting with '/' and not '//',
 * containing no protocol schemes or backslashes.
 */
export function getSafeReturnTo(target, fallback = '/dashboard') {
  if (!target || typeof target !== 'string') return fallback
  const trimmed = target.trim()
  if (!trimmed.startsWith('/') || trimmed.startsWith('//')) return fallback
  if (trimmed.includes(':') || trimmed.includes('\\')) return fallback
  return trimmed
}


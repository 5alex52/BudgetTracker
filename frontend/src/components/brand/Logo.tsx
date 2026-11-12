import { useId } from 'react'
import { cn } from '@/__shared__/utils/cn'

/**
 * BudgetTracker brand mark (a donut chart with an accent dot).
 *
 * Sources — `frontend/public/brand/logo-dark.svg` and `logo-light.svg`,
 * the same files used as favicons in `index.html`. Both versions are inlined
 * as React components (no network requests, no flicker on load);
 * theme switching is CSS-based, so the mark changes with the system theme,
 * a manual pick, and `?theme=` in the address.
 */
export function Logo({ className, size = 32 }: { className?: string; size?: number }) {
  // Gradient ids must be unique: the mark appears several times on the page
  // (header and footer), and duplicates break the fill.
  const id = useId().replace(/:/g, '')
  const darkAccent = `logoRingDark-${id}`
  const lightAccent = `logoRingLight-${id}`
  const darkBg = `logoBgDark-${id}`
  const lightBg = `logoBgLight-${id}`
  const darkRim = `logoRimDark-${id}`
  const lightRim = `logoRimLight-${id}`

  return (
    <span
      className={cn('inline-block shrink-0', className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label="BudgetTracker"
    >
      {/* Dark theme — as in `logo-dark.svg` */}
      <svg viewBox="0 0 64 64" width={size} height={size} className="hidden dark:block" aria-hidden="true">
        <defs>
          <linearGradient id={darkBg} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2A453D" />
            <stop offset="1" stopColor="#0E1815" />
          </linearGradient>
          <linearGradient id={darkRim} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fff" stopOpacity=".75" />
            <stop offset=".5" stopColor="#fff" stopOpacity=".05" />
            <stop offset="1" stopColor="#fff" stopOpacity=".25" />
          </linearGradient>
          <linearGradient id={darkAccent} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#72F2BC" />
            <stop offset="1" stopColor="#22C27C" />
          </linearGradient>
        </defs>
        <rect x="4" y="6" width="56" height="56" rx="16" fill="#000000" fillOpacity=".35" opacity=".5" />
        <rect x="4" y="4" width="56" height="56" rx="16" fill={`url(#${darkBg})`} stroke="#3B574C" />
        <rect
          x="5.5"
          y="5.5"
          width="53"
          height="53"
          rx="14.5"
          fill="none"
          stroke={`url(#${darkRim})`}
          strokeWidth="1.2"
        />
        <circle cx="32" cy="32" r="16" fill="none" stroke="#E9F6EF" strokeOpacity=".18" strokeWidth="6" />
        <circle
          cx="32"
          cy="32"
          r="16"
          fill="none"
          stroke={`url(#${darkAccent})`}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray="72 28.5"
          transform="rotate(-110 32 32)"
        />
        <circle cx="32" cy="32" r="6.5" fill={`url(#${darkAccent})`} />
        <circle cx="30" cy="30" r="2" fill="#fff" fillOpacity=".55" />
      </svg>

      {/* Light theme — as in `logo-light.svg` */}
      <svg viewBox="0 0 64 64" width={size} height={size} className="block dark:hidden" aria-hidden="true">
        <defs>
          <linearGradient id={lightBg} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#FFFFFF" />
            <stop offset="1" stopColor="#DCEFE4" />
          </linearGradient>
          <linearGradient id={lightRim} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fff" stopOpacity=".75" />
            <stop offset=".5" stopColor="#fff" stopOpacity=".05" />
            <stop offset="1" stopColor="#fff" stopOpacity=".25" />
          </linearGradient>
          <linearGradient id={lightAccent} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#2BD985" />
            <stop offset="1" stopColor="#0E9F5B" />
          </linearGradient>
        </defs>
        <rect x="4" y="6" width="56" height="56" rx="16" fill="#0B3B26" fillOpacity=".16" opacity=".5" />
        <rect x="4" y="4" width="56" height="56" rx="16" fill={`url(#${lightBg})`} stroke="#B7D3C4" />
        <rect
          x="5.5"
          y="5.5"
          width="53"
          height="53"
          rx="14.5"
          fill="none"
          stroke={`url(#${lightRim})`}
          strokeWidth="1.2"
        />
        <circle cx="32" cy="32" r="16" fill="none" stroke="#17352B" strokeOpacity=".18" strokeWidth="6" />
        <circle
          cx="32"
          cy="32"
          r="16"
          fill="none"
          stroke={`url(#${lightAccent})`}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray="72 28.5"
          transform="rotate(-110 32 32)"
        />
        <circle cx="32" cy="32" r="6.5" fill={`url(#${lightAccent})`} />
        <circle cx="30" cy="30" r="2" fill="#fff" fillOpacity=".55" />
      </svg>
    </span>
  )
}

export function Wordmark({ className, size = 32 }: { className?: string; size?: number }) {
  return (
    <span className={cn('flex items-center gap-2.5', className)}>
      <Logo size={size} />
      <span className="text-headline font-semibold tracking-snug text-fg-primary">BudgetTracker</span>
    </span>
  )
}

import { useId } from 'react'
import { cn } from '@/__shared__/utils/cn'

/**
 * Фирменный знак BudgetTracker.
 *
 * Исходники — `docs/design/Logo Dark.svg` и `Logo Light.svg`: скруглённый
 * квадрат с линией роста и точками данных. Обе версии встроены как React-
 * компоненты (без сетевых запросов и мигания при загрузке); переключение по
 * теме — на CSS, поэтому знак меняется и при системной теме, и при ручном
 * выборе, и при `?theme=` в адресе.
 */
export function Logo({ className, size = 32 }: { className?: string; size?: number }) {
  const id = useId().replace(/:/g, '')
  const darkGradient = `logoDark-${id}`
  const lightGradient = `logoLight-${id}`

  return (
    <span
      className={cn('inline-block shrink-0', className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label="BudgetTracker"
    >
      {/* Тёмная тема: глубокая плитка с неоновым свечением */}
      <svg viewBox="0 0 120 120" width={size} height={size} className="hidden dark:block" aria-hidden="true">
        <defs>
          <linearGradient id={darkGradient} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f2fe" />
            <stop offset="100%" stopColor="#3b82f6" />
          </linearGradient>
          <linearGradient id={`${darkGradient}-bg`} x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#1e293b" />
            <stop offset="100%" stopColor="#0f172a" />
          </linearGradient>
          <filter id={`${darkGradient}-glow`} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        <rect width="120" height="120" rx="28" fill={`url(#${darkGradient}-bg)`} stroke="#334155" strokeWidth="1.5" />
        <path
          d="M 24 75 L 48 50 L 72 62 L 96 32"
          fill="none"
          stroke={`url(#${darkGradient})`}
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter={`url(#${darkGradient}-glow)`}
        />
        <circle cx="24" cy="75" r="4" fill="#00f2fe" />
        <circle cx="48" cy="50" r="4" fill="#3b82f6" />
        <circle cx="72" cy="62" r="4" fill="#3b82f6" />
        <circle cx="96" cy="32" r="5" fill="#00f2fe" />
      </svg>

      {/* Светлая тема: белая плитка с мягкой тенью */}
      <svg viewBox="0 0 120 120" width={size} height={size} className="block dark:hidden" aria-hidden="true">
        <defs>
          <linearGradient id={lightGradient} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00c6ff" />
            <stop offset="100%" stopColor="#0072ff" />
          </linearGradient>
          <filter id={`${lightGradient}-shadow`} x="-10%" y="-10%" width="130%" height="130%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#0f172a" floodOpacity="0.12" />
          </filter>
        </defs>
        <rect
          width="120"
          height="120"
          rx="28"
          fill="#ffffff"
          stroke="#e2e8f0"
          strokeWidth="1.5"
          filter={`url(#${lightGradient}-shadow)`}
        />
        <path
          d="M 24 75 L 48 50 L 72 62 L 96 32"
          fill="none"
          stroke={`url(#${lightGradient})`}
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="24" cy="75" r="4" fill="#00c6ff" />
        <circle cx="48" cy="50" r="4" fill="#0072ff" />
        <circle cx="72" cy="62" r="4" fill="#0072ff" />
        <circle cx="96" cy="32" r="5" fill="#00c6ff" />
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

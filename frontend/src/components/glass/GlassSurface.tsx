import { forwardRef, useCallback, useEffect, useRef, useState, type HTMLAttributes } from 'react'
import { cn } from '@/__shared__/utils/cn'
import { supportsBackdropRefraction } from '@/__shared__/utils/feature-detect'

export type GlassVariant = 'regular' | 'clear' | 'tinted'
export type GlassLevel = 'sm' | 'md' | 'lg'

export interface GlassClassOptions {
  level?: 'sm' | 'md' | 'lg'
  variant?: 'regular' | 'clear' | 'tinted'
  opaque?: boolean
  refraction?: boolean
  glow?: boolean
  className?: string
}

/**
 * Material classes — the single place where glass is assembled.
 *
 * Components that can't wrap their markup in `GlassSurface` (Radix Content
 * requires `asChild`, buttons and toggles have their own element) take classes from here:
 * the material stays one implementation, not a copy across six files.
 */
export function glassClass({
  level = 'md',
  variant = 'regular',
  opaque = false,
  refraction = false,
  glow = false,
  className,
}: GlassClassOptions = {}) {
  return cn(
    'glass',
    level === 'sm' && 'glass--sm',
    level === 'lg' && 'glass--lg',
    variant === 'clear' && 'glass--clear',
    variant === 'tinted' && 'glass--tinted',
    opaque && 'glass--opaque',
    refraction && 'glass--refract',
    glow && 'glass--glow',
    className,
  )
}

export interface GlassSurfaceProps extends HTMLAttributes<HTMLDivElement> {
  /** Material transparency */
  variant?: GlassVariant
  /** Blur level and radius */
  level?: GlassLevel
  /** SVG refraction (Chromium only, only for elements ≤ --glass-refract-max-w) */
  refraction?: boolean
  /** Cursor-following glint (Chromium/desktop only, disabled by system settings) */
  glow?: boolean
  /** Force an opaque background (modal over modal, fallback) */
  opaque?: boolean
  as?: 'div' | 'nav' | 'aside' | 'header' | 'section'
}

const REFRACT_MAX = 800

/**
 * The single "liquid glass" material primitive.
 *
 * Level 1 — blur + saturate + border + inner glint (all browsers).
 * Level 2 — SVG refraction via backdrop-filter: url(#...), Chromium only.
 * Level 3 — press spring and cursor-following glint.
 */
export const GlassSurface = forwardRef<HTMLDivElement, GlassSurfaceProps>(function GlassSurface(
  {
    variant = 'regular',
    level = 'md',
    refraction = false,
    glow = false,
    opaque = false,
    as: Tag = 'div',
    className,
    children,
    onPointerMove,
    ...rest
  },
  ref,
) {
  const innerRef = useRef<HTMLDivElement | null>(null)
  const [allowRefraction, setAllowRefraction] = useState(false)
  const [allowGlow, setAllowGlow] = useState(false)
  const frame = useRef<number | null>(null)

  // Refraction: Chromium only (feature-detect) and only for narrow elements.
  useEffect(() => {
    if (!refraction) return
    const el = innerRef.current
    if (!el) return
    if (!supportsBackdropRefraction()) return
    const wide = el.getBoundingClientRect().width > REFRACT_MAX
    setAllowRefraction(!wide)
  }, [refraction])

  // Cursor glint: only where there's a fine pointer and motion is allowed.
  useEffect(() => {
    if (!glow) return
    const fine = window.matchMedia('(pointer: fine)').matches
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    setAllowGlow(fine && !still)
  }, [glow])

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      onPointerMove?.(event)
      if (!allowGlow) return
      const el = innerRef.current
      if (!el) return
      if (frame.current !== null) return
      const { clientX, clientY } = event
      frame.current = requestAnimationFrame(() => {
        frame.current = null
        const rect = el.getBoundingClientRect()
        el.style.setProperty('--glass-mx', `${clientX - rect.left}px`)
        el.style.setProperty('--glass-my', `${clientY - rect.top}px`)
      })
    },
    [allowGlow, onPointerMove],
  )

  useEffect(() => () => {
    if (frame.current !== null) cancelAnimationFrame(frame.current)
  }, [])

  return (
    <Tag
      ref={(node: HTMLDivElement | null) => {
        innerRef.current = node
        if (typeof ref === 'function') ref(node)
        else if (ref) (ref as React.MutableRefObject<HTMLDivElement | null>).current = node
      }}
      data-glass=""
      data-glass-variant={variant}
      data-glass-refraction={allowRefraction ? 'on' : 'off'}
      data-glass-glow={allowGlow ? 'on' : 'off'}
      onPointerMove={handlePointerMove}
      className={glassClass({ level, variant, opaque, refraction: allowRefraction, glow: allowGlow, className })}
      {...rest}
    >
      {children}
    </Tag>
  )
})

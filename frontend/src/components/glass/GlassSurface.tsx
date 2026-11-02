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
 * Классы материала — единственное место, где собирается стекло.
 *
 * Компоненты, которым нельзя обернуть разметку в `GlassSurface` (Radix Content
 * требует `asChild`, кнопки и переключатели — свой элемент), берут классы отсюда:
 * так материал остаётся одним, а не копией в шести файлах.
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
  /** Прозрачность материала */
  variant?: GlassVariant
  /** Уровень размытия и радиус */
  level?: GlassLevel
  /** SVG-рефракция (только Chromium, только для элементов ≤ --glass-refract-max-w) */
  refraction?: boolean
  /** Блик, следящий за курсором (только Chromium/desktop, отключается системными настройками) */
  glow?: boolean
  /** Принудительно непрозрачный фон (модал поверх модала, fallback) */
  opaque?: boolean
  as?: 'div' | 'nav' | 'aside' | 'header' | 'section'
}

const REFRACT_MAX = 800

/**
 * Единый примитив материала «жидкое стекло».
 *
 * Уровень 1 — blur + saturate + обводка + внутренний блик (все браузеры).
 * Уровень 2 — SVG-рефракция через backdrop-filter: url(#...), только Chromium.
 * Уровень 3 — пружина при нажатии и блик за курсором.
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

  // Рефракция: только Chromium (feature-detect) и только для нешироких элементов.
  useEffect(() => {
    if (!refraction) return
    const el = innerRef.current
    if (!el) return
    if (!supportsBackdropRefraction()) return
    const wide = el.getBoundingClientRect().width > REFRACT_MAX
    setAllowRefraction(!wide)
  }, [refraction])

  // Блик за курсором: только там, где есть точный указатель и разрешено движение.
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

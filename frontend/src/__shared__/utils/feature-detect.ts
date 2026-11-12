/**
 * Feature detection for refraction in backdrop-filter.
 *
 * Spec requirement: no UA sniffing. We check exactly what level 2 needs:
 * 1) the browser understands url(#id) as a backdrop-filter value;
 * 2) the browser honors color-interpolation-filters: sRGB (without it refraction "muddies" colors);
 * 3) the element actually gets backdrop-filter in the CSSOM.
 *
 * IMPORTANT (verified with WKWebView snapshots): WebKit accepts the url() value
 * and keeps it in the CSSOM, but does not render feDisplacementMap displacement
 * in backdrop-filter. The declaration does not break level 1 — the base blur stays,
 * so the fallback happens on its own. The function answers "does the engine
 * claim support", not "does the engine render refraction".
 *
 * The result is computed once and cached.
 */

let cached: boolean | null = null

export function supportsBackdropRefraction(): boolean {
  if (cached !== null) return cached
  if (typeof window === 'undefined' || typeof CSS === 'undefined' || !CSS.supports) {
    cached = false
    return cached
  }

  const parsesUrlBackdrop = CSS.supports('backdrop-filter', 'url(#probe)')
  const parsesSrgb = CSS.supports('color-interpolation-filters', 'sRGB')

  if (!parsesUrlBackdrop || !parsesSrgb) {
    cached = false
    return cached
  }

  // Final check: does backdrop-filter with url() apply to a live element.
  // Safari returns an empty string — the syntax is accepted but not supported.
  const probe = document.createElement('div')
  probe.style.backdropFilter = 'url(#probe)'
  probe.style.setProperty('-webkit-backdrop-filter', 'url(#probe)')
  probe.style.position = 'fixed'
  probe.style.opacity = '0'
  document.body.appendChild(probe)
  const applied =
    probe.style.backdropFilter !== '' ||
    probe.style.getPropertyValue('-webkit-backdrop-filter') !== ''
  probe.remove()

  cached = applied
  return cached
}

/** Cache reset — for tests and re-checking capabilities only. */
export function resetFeatureDetectCache(): void {
  cached = null
}

export function prefersReducedTransparency(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-transparency: reduce)').matches
}

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function prefersMoreContrast(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-contrast: more)').matches
}

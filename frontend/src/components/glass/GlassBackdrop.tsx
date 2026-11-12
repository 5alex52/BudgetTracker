/**
 * Background under the glass.
 *
 * Glass on a solid background looks like a gray fill, so saturated blurred blobs
 * always sit under the floating layer. The layer is fixed and doesn't intercept events.
 * The blobs are radial gradients (no filter: blur) — one cheap composite layer
 * that takes no part in recomputation when content scrolls.
 */
export function GlassBackdrop() {
  return (
    <div className="glass-backdrop" aria-hidden="true">
      <div className="glass-backdrop__aurora" />
      <div className="glass-backdrop__blob glass-backdrop__blob--1" />
      <div className="glass-backdrop__blob glass-backdrop__blob--2" />
      <div className="glass-backdrop__blob glass-backdrop__blob--3" />
      <div className="glass-backdrop__blob glass-backdrop__blob--4" />
      <div className="glass-backdrop__grain" />
    </div>
  )
}

/**
 * SVG filters for level 2 (refraction). Rendered once at the app root.
 * color-interpolation-filters="sRGB" is required: without it the browser interpolates
 * the displacement in linearRGB and the glass "muddies" colors.
 */
export function GlassFilters() {
  return (
    <svg className="glass-filters" aria-hidden="true" width="0" height="0" focusable="false">
      <defs>
        <filter
          id="glass-refract"
          x="0"
          y="0"
          width="100%"
          height="100%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.008 0.008"
            numOctaves="3"
            seed="17"
            result="noise"
          />
          <feGaussianBlur in="noise" stdDeviation="2" result="blur" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="blur"
            scale="14"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </defs>
    </svg>
  )
}

/**
 * Фон под стеклом.
 *
 * Стекло на однотонном фоне выглядит серой заливкой, поэтому под плавающим слоем
 * всегда лежат насыщенные размытые пятна. Слой fixed, не перехватывает события.
 * Пятна сделаны радиальными градиентами (без filter: blur) — это один дешёвый
 * композитный слой, который не участвует в пересчёте при скролле контента.
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
 * SVG-фильтры для уровня 2 (рефракция). Рендерятся один раз в корне приложения.
 * color-interpolation-filters="sRGB" обязателен: без него браузер интерполирует
 * смещение в linearRGB и стекло «грязнит» цвета.
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

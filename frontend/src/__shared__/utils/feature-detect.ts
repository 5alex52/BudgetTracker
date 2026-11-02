/**
 * Feature-detect для рефракции в backdrop-filter.
 *
 * Требование ТЗ: не UA-sniffing. Проверяем ровно то, что нужно для уровня 2:
 * 1) браузер понимает url(#id) как значение backdrop-filter;
 * 2) браузер уважает color-interpolation-filters: sRGB (без него рефракция «грязнит» цвета);
 * 3) элемент реально получает backdrop-filter в CSSOM.
 *
 * ВАЖНО (проверено снимками WKWebView): WebKit принимает значение с url() и
 * сохраняет его в CSSOM, но смещение через feDisplacementMap в backdrop-filter
 * не рисует. Объявление при этом не ломает уровень 1 — базовый blur остаётся,
 * то есть откат происходит сам собой. Функция отвечает на вопрос «движок
 * заявляет поддержку», а не «движок рисует рефракцию».
 *
 * Результат считается один раз и кешируется.
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

  // Финальная проверка: применяется ли backdrop-filter с url() к живому элементу.
  // Safari возвращает пустую строку — значит синтаксис принят, но не поддержан.
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

/** Сброс кеша — только для тестов и повторной проверки возможностей. */
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

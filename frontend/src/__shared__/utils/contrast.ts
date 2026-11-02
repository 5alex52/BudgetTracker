/**
 * Читаемый цвет текста на произвольной подложке.
 *
 * Нужен там, где фон приходит из данных (цвет счёта, метки, категории): у
 * светлых оттенков белые буквы проваливаются до 2.7:1, у тёмных — наоборот,
 * чёрные. Считаем контраст по WCAG 2.1 и выбираем вариант, который проходит
 * порог, а если не проходит ни один — берём более контрастный.
 */

type Rgb = { r: number; g: number; b: number }

function parse(input: string): Rgb | null {
  const hex = input.trim()
  const match = hex.match(/^#?([\da-f]{3}|[\da-f]{6})$/i)
  if (match) {
    const value = match[1]
    const expanded = value.length === 3 ? value.split('').map((c) => c + c).join('') : value
    return {
      r: parseInt(expanded.slice(0, 2), 16),
      g: parseInt(expanded.slice(2, 4), 16),
      b: parseInt(expanded.slice(4, 6), 16),
    }
  }
  const rgb = hex.match(/rgba?\(([^)]+)\)/)
  if (rgb) {
    const [r, g, b] = rgb[1].split(/[,/]/).map((chunk) => parseFloat(chunk.trim()))
    return { r, g, b }
  }
  return null
}

function channel(value: number): number {
  const scaled = value / 255
  return scaled <= 0.03928 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4
}

function luminance({ r, g, b }: Rgb): number {
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

export function contrastRatio(a: string, b: string): number {
  const first = parse(a)
  const second = parse(b)
  if (!first || !second) return 21
  const la = luminance(first)
  const lb = luminance(second)
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05)
}

const LIGHT_TEXT = '#ffffff'
const DARK_TEXT = '#0e1513'

/** Цвет текста поверх подложки: белый или почти чёрный, что читается лучше. */
export function readableTextOn(background: string): string {
  const white = contrastRatio(background, LIGHT_TEXT)
  const dark = contrastRatio(background, DARK_TEXT)
  return white >= dark ? LIGHT_TEXT : DARK_TEXT
}

/**
 * Цвета плашки-аватара на основе оттенка из данных.
 *
 * Оттенки приходят из макета и не все одинаково светлые: на #d94b4b ни белый,
 * ни чёрный не дают 4.5:1. Поэтому подложку при необходимости затемняем шагами
 * по 4 %, сохраняя оттенок, и только после этого выбираем цвет буквы.
 */
export function chipColors(tint: string): { backgroundColor: string; color: string } {
  const base = parse(tint)
  if (!base) return { backgroundColor: tint, color: LIGHT_TEXT }

  const toHex = (rgb: Rgb) =>
    `#${[rgb.r, rgb.g, rgb.b].map((value) => Math.round(value).toString(16).padStart(2, '0')).join('')}`
  const darken = (rgb: Rgb, amount: number): Rgb => ({
    r: rgb.r * (1 - amount),
    g: rgb.g * (1 - amount),
    b: rgb.b * (1 - amount),
  })

  // 1. Оттенок светлый — на нём лучше тёмные буквы, сам цвет не трогаем.
  if (contrastRatio(tint, LIGHT_TEXT) >= 4.5) return { backgroundColor: tint, color: LIGHT_TEXT }
  if (contrastRatio(tint, DARK_TEXT) >= 4.5) return { backgroundColor: tint, color: DARK_TEXT }

  // 2. Иначе уходим в более насыщенный оттенок шагами по 6 % — белые буквы вернутся к порогу.
  for (let step = 1; step <= 7; step += 1) {
    const background = toHex(darken(base, step * 0.06))
    if (contrastRatio(background, LIGHT_TEXT) >= 4.5) return { backgroundColor: background, color: LIGHT_TEXT }
  }

  return { backgroundColor: toHex(darken(base, 0.45)), color: LIGHT_TEXT }
}

/**
 * Цвет значка на подложке того же оттенка (`color + 22` — 13 % альфы).
 *
 * На светлой подложке сам оттенок даёт 2–3:1: значок сливается с плашкой.
 * Поэтому затемняем (в светлой теме) или осветляем (в тёмной) оттенок шагами,
 * пока он не дойдёт до порога: 4.5:1 для текста, 3:1 для графики.
 */
export function readableOnTint(color: string, options: { dark?: boolean; threshold?: number } = {}): string {
  const { dark = false, threshold = 4.5 } = options
  const base = parse(color)
  if (!base) return color

  const toHex = (rgb: Rgb) =>
    `#${[rgb.r, rgb.g, rgb.b].map((value) => Math.max(0, Math.min(255, Math.round(value))).toString(16).padStart(2, '0')).join('')}`
  const shift = (rgb: Rgb, amount: number): Rgb =>
    dark
      ? {
          r: rgb.r + (255 - rgb.r) * amount,
          g: rgb.g + (255 - rgb.g) * amount,
          b: rgb.b + (255 - rgb.b) * amount,
        }
      : { r: rgb.r * (1 - amount), g: rgb.g * (1 - amount), b: rgb.b * (1 - amount) }

  const tintBackground = (rgb: Rgb): Rgb => ({
    // подложка — тот же оттенок с альфой 13 % поверх базового фона
    r: (dark ? 24 : 255) * (1 - 0.13) + rgb.r * 0.13,
    g: (dark ? 26 : 255) * (1 - 0.13) + rgb.g * 0.13,
    b: (dark ? 24 : 255) * (1 - 0.13) + rgb.b * 0.13,
  })

  for (let step = 0; step <= 8; step += 1) {
    const candidate = shift(base, step * 0.1)
    if (contrastRatio(toHex(candidate), toHex(tintBackground(base))) >= threshold) {
      return toHex(candidate)
    }
  }
  return toHex(shift(base, 0.8))
}

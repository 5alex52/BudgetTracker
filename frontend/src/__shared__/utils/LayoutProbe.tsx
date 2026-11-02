import { useEffect, useState } from 'react'

/**
 * QA-зонд раскладки. Включается параметром `?debug=layout`.
 *
 * Показывает scrollWidth/clientWidth документа и первый элемент, который шире
 * вьюпорта. Нужен потому, что переполнение по горизонтали скриншотом не видно:
 * `overflow-hidden` на карточках режет контент, и он выглядит «просто обрезанным».
 */
export function LayoutProbe() {
  const [info, setInfo] = useState<{ scroll: number; client: number; culprit: string } | null>(null)

  useEffect(() => {
    const measure = () => {
      const doc = document.documentElement
      const viewport = doc.clientWidth
      // Ищем не «шире вьюпорта» (это режется body), а обрезанный контент:
      // элементы с overflow, у которых scrollWidth больше clientWidth.
      const clipped: string[] = []
      document.querySelectorAll<HTMLElement>('body *').forEach((node) => {
        const style = getComputedStyle(node)
        if (style.position === 'fixed') return
        if (node.scrollWidth > node.clientWidth + 1 && node.clientWidth > 0) {
          const first = node.className.toString().split(' ').slice(0, 2).join('.')
          clipped.push(`${node.tagName.toLowerCase()}.${first} sw=${node.scrollWidth} cw=${node.clientWidth}`)
        }
      })
      const culprit = clipped.slice(0, 2).join(' | ') || '—'
      setInfo({ scroll: doc.scrollWidth, client: viewport, culprit })
    }

    measure()
    const timer = setTimeout(measure, 400)
    window.addEventListener('resize', measure)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', measure)
    }
  }, [])

  if (!info) return null

  return (
    <div
      className="fixed bottom-2 left-2 z-[var(--z-toast)] max-w-[92vw] rounded-sm border border-[var(--negative)] bg-bg-base/95 px-2 py-1 font-mono text-[11px] leading-tight text-fg-primary"
      role="status"
    >
      <div>
        scroll {info.scroll} / client {info.client}{' '}
        {info.scroll > info.client ? '· ПЕРЕПОЛНЕНИЕ' : '· ок'}
      </div>
      <div>виновник: {info.culprit}</div>
    </div>
  )
}

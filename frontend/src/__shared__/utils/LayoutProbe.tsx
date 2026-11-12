import { useEffect, useState } from 'react'

/**
 * Layout QA probe. Enabled with `?debug=layout`.
 *
 * Shows the document's scrollWidth/clientWidth and the first element wider than
 * the viewport. Needed because horizontal overflow is invisible in screenshots:
 * `overflow-hidden` on cards clips content and it looks "just cut off".
 */
export function LayoutProbe() {
  const [info, setInfo] = useState<{ scroll: number; client: number; culprit: string } | null>(null)

  useEffect(() => {
    const measure = () => {
      const doc = document.documentElement
      const viewport = doc.clientWidth
      // Look not for "wider than viewport" (body clips that) but for clipped content:
      // elements with overflow where scrollWidth exceeds clientWidth.
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

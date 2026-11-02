/**
 * sync-fonts.mjs — self-host шрифтов medeo-font.
 *
 * Берёт CSS из пакета medeo-font и переносит его в src/styles/fonts.generated.css,
 * переписывая url() на стабильные пути /fonts/medeo/... (нужно для <link rel="preload">).
 * Сами woff2-файлы копируются в public/fonts/medeo/.
 *
 * Запуск: node scripts/sync-fonts.mjs   (или автоматически через npm run fonts)
 * CDN не используется: файлы раздаются с нашего origin.
 */
import { readFile, writeFile, mkdir, copyFile, readdir } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')
const pkgDist = resolve(root, 'node_modules/medeo-font/dist')
const outCssDir = resolve(root, 'src/styles')
const outFontsDir = resolve(root, 'public/fonts/medeo')

const STYLES = ['sans', 'mono'] // serif и pixel не используем

/** Убирает @font-face c font-style: italic — наклонных начертаний в UI нет. */
function dropItalic(css) {
  return css.replace(/@font-face\s*{[^}]*font-style:\s*italic[^}]*}/g, '')
}

/** url("./fonts/medeo-sans/X.woff2") → url("/fonts/medeo/medeo-sans/X.woff2") */
function rewriteUrls(css) {
  return css.replace(/url\(["']?\.\/fonts\/([^"')]+)["']?\)/g, 'url("/fonts/medeo/$1")')
}

async function main() {
  if (!existsSync(pkgDist)) {
    throw new Error('medeo-font не установлен: npm install medeo-font@1.0.0')
  }

  await mkdir(outCssDir, { recursive: true })
  await mkdir(outFontsDir, { recursive: true })

  const chunks = [
    '/* СГЕНЕРИРОВАНО scripts/sync-fonts.mjs — не редактировать вручную.\n' +
      '   Шрифт: medeo-font@1.0.0 (SIL OFL 1.1), self-host, без CDN. */\n',
  ]
  const copied = []

  for (const style of STYLES) {
    const src = join(pkgDist, `${style}.css`)
    const css = dropItalic(rewriteUrls(await readFile(src, 'utf8')))
    chunks.push(`\n/* ${style} */\n${css}`)

    const dir = join(pkgDist, 'fonts', `medeo-${style}`)
    for (const file of await readdir(dir)) {
      if (!file.endsWith('.woff2')) continue
      if (file.includes('Italic')) continue // наклонных начертаний в UI нет
      await copyFile(join(dir, file), join(outFontsDir, `medeo-${style}`, file)).catch(async () => {
        await mkdir(join(outFontsDir, `medeo-${style}`), { recursive: true })
        await copyFile(join(dir, file), join(outFontsDir, `medeo-${style}`, file))
      })
      copied.push(`medeo-${style}/${file}`)
    }
  }

  await writeFile(join(outCssDir, 'fonts.generated.css'), chunks.join(''), 'utf8')
  console.log(`fonts.generated.css: ${STYLES.join(', ')}; файлов скопировано: ${copied.length}`)
  console.log('прелоад-файлы:', copied.filter((f) => /\.(latin|cyrillic)\.woff2$/.test(f)).join(', '))
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})

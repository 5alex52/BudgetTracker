#!/usr/bin/env node
/**
 * Screenshot tool on pure CDP (no Playwright/Puppeteer): Node 22+ provides
 * a global WebSocket, that's enough.
 *
 * Why: we need not just "the whole page" but also states after clicks
 * (modal, popovers, theme, tabs) — a plain --screenshot won't capture those.
 *
 * Usage:
 *   node tools/cdp-shot.mjs --url http://127.0.0.1:5199/ --out file.png \
 *     [--width 1440] [--height 900] [--dpr 1] [--theme dark|light] \
 *     [--actions '[{"click":"text=Запись"}]'] [--full]
 *
 * Actions: {click: css}, {clickText: string}, {wait: ms}, {eval: js}
 */
import { spawn } from 'node:child_process'
import { mkdtemp, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

function arg(name, fallback = undefined) {
  const index = process.argv.indexOf(`--${name}`)
  if (index === -1) return fallback
  const value = process.argv[index + 1]
  return value === undefined || value.startsWith('--') ? true : value
}

const url = arg('url')
const out = arg('out', 'shot.png')
const width = Number(arg('width', 1440))
const height = Number(arg('height', 900))
const dpr = Number(arg('dpr', 1))
const theme = arg('theme', 'dark')
const full = arg('full', false) === true || arg('full') === 'true'
const actions = JSON.parse(arg('actions', '[]'))
const port = 9000 + Math.floor(Math.random() * 900)

if (!url) {
  console.error('--url is required')
  process.exit(1)
}

const profile = await mkdtemp(join(tmpdir(), 'cdp-profile-'))
const chrome = spawn(
  CHROME,
  [
    '--headless=new',
    '--no-sandbox',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--disable-breakpad',
    '--disable-crash-reporter',
    '--disable-features=Crashpad',
    '--force-device-scale-factor=1',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    '--window-size=1280,800',
    'about:blank',
  ],
  { stdio: 'ignore' },
)

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

async function endpoint() {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`)
      if (response.ok) {
        const data = await response.json()
        if (data.webSocketDebuggerUrl) return data.webSocketDebuggerUrl
      }
    } catch {
      /* the browser is still starting */
    }
    await sleep(200)
  }
  throw new Error('Chrome did not expose a debug endpoint')
}

const wsUrl = await endpoint()
const socket = new WebSocket(wsUrl)
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true })
  socket.addEventListener('error', reject, { once: true })
})

let messageId = 0
const pending = new Map()

socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data)
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id)
    pending.delete(message.id)
    if (message.error) reject(new Error(message.error.message))
    else resolve(message.result)
  }
})

function send(method, params = {}, sessionId = undefined) {
  messageId += 1
  const id = messageId
  const payload = { id, method, params }
  if (sessionId) payload.sessionId = sessionId
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject })
    socket.send(JSON.stringify(payload))
    setTimeout(() => {
      if (pending.has(id)) {
        pending.delete(id)
        reject(new Error(`timeout ${method}`))
      }
    }, 40000)
  })
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' })
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true })

await send('Page.enable', {}, sessionId)
await send('Runtime.enable', {}, sessionId)
await send('Emulation.setDeviceMetricsOverride', {
  width,
  height,
  deviceScaleFactor: dpr,
  mobile: width < 600,
}, sessionId)
await send('Emulation.setEmulatedMedia', {
  features: [
    { name: 'prefers-color-scheme', value: theme },
    { name: 'prefers-reduced-motion', value: 'no-preference' },
  ],
}, sessionId)

await send('Page.navigate', { url }, sessionId)
await sleep(1200)

const clickByText = (text) => `(() => {
  const nodes = [...document.querySelectorAll('button, a, [role="tab"], [role="menuitem"]')]
  const target = nodes.find((node) => node.textContent.trim().includes(${JSON.stringify(text)}))
  if (!target) return 'no target: ' + ${JSON.stringify(text)}
  target.click()
  return 'ok'
})()`

for (const action of actions) {
  if (action.wait) {
    await sleep(action.wait)
    continue
  }
  const expression =
    action.clickText !== undefined
      ? clickByText(action.clickText)
      : action.click !== undefined
        ? `(() => { const node = document.querySelector(${JSON.stringify(action.click)}); if (!node) return 'no target'; node.click(); return 'ok' })()`
        : action.eval ?? 'void 0'
  const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }, sessionId)
  if (result.exceptionDetails) {
    console.error('action error:', JSON.stringify(result.exceptionDetails.exception?.description ?? result))
  } else if (result.result?.value && result.result.value !== 'ok') {
    console.error('action:', result.result.value)
  }
  await sleep(450)
}

// Wait for web fonts, otherwise the layout shows the fallback font
await send('Runtime.evaluate', { expression: 'document.fonts.ready', awaitPromise: true }, sessionId)
await sleep(300)

let clip
if (full) {
  const metrics = await send('Page.getLayoutMetrics', {}, sessionId)
  const size = metrics.cssContentSize ?? metrics.contentSize
  clip = { x: 0, y: 0, width, height: Math.min(Math.ceil(size.height), 6000), scale: 1 }
}

const shot = await send('Page.captureScreenshot', {
  format: 'png',
  captureBeyondViewport: Boolean(full),
  ...(clip ? { clip } : {}),
}, sessionId)

await writeFile(out, Buffer.from(shot.data, 'base64'))
console.log(`OK ${out}`)

socket.close()
chrome.kill('SIGKILL')
process.exit(0)

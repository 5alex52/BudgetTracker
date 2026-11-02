#!/usr/bin/env node
/**
 * Аудит кнопок: прокликивает все <button> на каждом экране и проверяет, что
 * после нажатия что-то происходит — открывается модал/меню/поповер, меняется
 * состояние или адрес. Кнопки, после которых ничего не меняется, попадают в
 * отчёт как «мёртвые» — их и нужно дорисовать.
 *
 * Работает на чистом CDP (Node 22+ с глобальным WebSocket), без Playwright.
 *
 * Использование:
 *   node tools/audit-buttons.mjs [--base http://127.0.0.1:5199] [--json out.json]
 */
import { spawn } from 'node:child_process'
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

function arg(name, fallback = undefined) {
  const index = process.argv.indexOf(`--${name}`)
  if (index === -1) return fallback
  const value = process.argv[index + 1]
  return value === undefined || value.startsWith('--') ? true : value
}

const base = arg('base', 'http://127.0.0.1:5199')
const jsonOut = arg('json', null)

const PAGES = [
  ['/login', '/login'],
  ['/', '/'],
  ['/accounts', '/accounts'],
  ['/accounts/alfa', '/accounts/alfa'],
  ['/records', '/records'],
  ['/analytics', '/analytics'],
  ['/settings', '/settings'],
  ['/settings/currencies', '/settings/currencies'],
  ['/settings/categories', '/settings/categories'],
  ['/settings/templates', '/settings/templates'],
  ['/settings/tags', '/settings/tags'],
  ['/settings/rules', '/settings/rules'],
  ['/settings/payments', '/settings/payments'],
  ['/settings/privacy', '/settings/privacy'],
]

const port = 9000 + Math.floor(Math.random() * 900)
const profile = await mkdtemp(join(tmpdir(), 'audit-profile-'))
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
      /* ждём */
    }
    await sleep(200)
  }
  throw new Error('Chrome не отдал endpoint')
}

const socket = new WebSocket(await endpoint())
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
        reject(new Error(`таймаут ${method}`))
      }
    }, 180000)
  })
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' })
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true })
await send('Page.enable', {}, sessionId)
await send('Runtime.enable', {}, sessionId)
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId)
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'dark' }] }, sessionId)

async function evaluate(expression) {
  const result = await send(
    'Runtime.evaluate',
    { expression, awaitPromise: true, returnByValue: true },
    sessionId,
  )
  if (result.exceptionDetails) {
    return { error: result.exceptionDetails.text ?? 'ошибка выполнения' }
  }
  return { value: result.result?.value }
}

/** Собираем список кнопок страницы: подпись + видимость. */
const LIST_JS = `(() => {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
  };
  const label = (el) =>
    ((el.getAttribute('aria-label') || el.textContent || '').replace(/\\s+/g, ' ').trim() ||
      el.className.toString().slice(0, 32)).slice(0, 48);
  const seen = new Set();
  const out = [];
  [...document.querySelectorAll('button')].filter(visible).forEach((el) => {
    const name = label(el);
    if (seen.has(name)) return;
    seen.add(name);
    out.push(name);
  });
  return out;
})()`

const SIG = `(() => {
  const overlay = document.querySelectorAll('[role=dialog],[role=menu],[role=listbox],[role=tooltip],[data-radix-popper-content-wrapper]').length;
  const pressed = [...document.querySelectorAll('[aria-pressed=true],[aria-checked=true],[aria-selected=true],[aria-expanded=true]')]
    .map((el) => (el.getAttribute('aria-label') || el.textContent || '').replace(/\\s+/g, ' ').trim())
    .sort()
    .join('|');
  return [
    overlay,
    location.pathname,
    document.body.innerText.length,
    document.documentElement.className,
    pressed,
    document.querySelectorAll('[data-toast]').length,
  ].join('~');
})()`

/** Готовим нажатие: находим кнопку, запоминаем адрес центра и исходное состояние. */
const prepareJs = (label) => `(async () => {
  const label = (el) =>
    ((el.getAttribute('aria-label') || el.textContent || '').replace(/\\s+/g, ' ').trim() ||
      el.className.toString().slice(0, 32)).slice(0, 48);
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const target = [...document.querySelectorAll('button')].filter(visible).find((el) => label(el) === ${JSON.stringify(label)});
  if (!target) return null;
  target.scrollIntoView({ block: 'center', inline: 'center' });
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  const rect = target.getBoundingClientRect();
  return {
    x: Math.round(rect.left + rect.width / 2),
    y: Math.round(rect.top + rect.height / 2),
    alreadyActive:
      target.getAttribute('aria-selected') === 'true' ||
      target.getAttribute('aria-pressed') === 'true' ||
      target.getAttribute('aria-checked') === 'true',
    before: ${SIG},
  };
})()`

/** Измеряем результат уже после настоящего нажатия мышью. */
const measureJs = (before, pathBefore, alreadyActive) => `(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  await wait(500);
  const after = ${SIG};
  const opened = document.querySelectorAll('[role=dialog],[role=menu],[role=listbox],[role=tooltip],[data-radix-popper-content-wrapper]').length > 0;
  const navigated = location.pathname !== ${JSON.stringify(pathBefore)};
  const changed = after !== ${JSON.stringify(before)};
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
  await wait(80);
  return {
    status: opened
      ? 'открывает слой'
      : navigated
        ? 'переход'
        : changed
          ? 'меняет состояние'
          : ${JSON.stringify(Boolean(alreadyActive))}
            ? 'уже выбрано'
            : 'ничего не происходит',
  };
})()`

/** Ждём, пока страница реально отрендерится (React привяжет обработчики). */
async function waitForReady() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const state = await evaluate('document.readyState + "|" + (document.querySelector("header") ? "h" : "-") + "|" + document.body.innerText.length')
    if (state.value && String(state.value).startsWith('complete|h|')) {
      await sleep(350)
      return
    }
    await sleep(150)
  }
  await sleep(600)
}

const report = {}

for (const [name, path] of PAGES) {
  const url = `${base}${path}?theme=dark`
  await send('Page.navigate', { url }, sessionId)
  await waitForReady()

  const listed = await evaluate(LIST_JS)
  if (listed.error || !Array.isArray(listed.value)) {
    report[name] = [{ label: listed.error ?? 'не удалось прочитать кнопки', status: 'ошибка аудита' }]
    continue
  }

  const items = []
  for (const label of listed.value.slice(0, 24)) {
    await send('Page.navigate', { url }, sessionId)
    await waitForReady()

    const prepared = await evaluate(prepareJs(label))
    if (!prepared.value) {
      items.push({ label, status: 'кнопка не найдена' })
      continue
    }

    const { x, y, before, alreadyActive } = prepared.value
    const pathBefore = new URL(url).pathname
    // Настоящее нажатие мышью: только так срабатывают submit у форм и pointerdown у Radix
    for (const type of ['mousePressed', 'mouseReleased']) {
      await send(
        'Input.dispatchMouseEvent',
        { type, x, y, button: 'left', buttons: type === 'mousePressed' ? 1 : 0, clickCount: 1 },
        sessionId,
      )
      await sleep(60)
    }

    const outcome = await evaluate(measureJs(before, pathBefore, alreadyActive))
    items.push({ label, status: outcome.value?.status ?? outcome.error ?? 'нет ответа' })
  }

  if (path !== name) {
    await send('Page.navigate', { url }, sessionId)
    await sleep(400)
  }
  report[name] = items
}

const dead = []
for (const [page, items] of Object.entries(report)) {
  for (const item of items) {
    if (item.status === 'ничего не происходит') dead.push({ page, ...item })
  }
}

for (const [page, items] of Object.entries(report)) {
  console.log(`\n=== ${page} (${items.length} кнопок)`)
  for (const item of items) {
    const mark = item.status === 'ничего не происходит' ? '✗' : '·'
    console.log(`  ${mark} ${item.status.padEnd(18)} ${item.label}`)
  }
}

console.log(`\nИТОГО: мёртвых кнопок — ${dead.length}`)
if (jsonOut) {
  const { writeFile } = await import('node:fs/promises')
  await writeFile(jsonOut, JSON.stringify({ report, dead }, null, 2))
  console.log(`отчёт: ${jsonOut}`)
}

socket.close()
chrome.kill()
process.exit(0)

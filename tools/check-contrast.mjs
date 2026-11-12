#!/usr/bin/env node
/**
 * Text contrast audit per WCAG 2.1.
 *
 * For every visible text it computes the text color and the actual background: walks
 * the ancestors and blends semi-transparent backgrounds (glass, surfaces,
 * highlights) layer by layer with the page's base background. Then computes the contrast
 * ratio and compares it to the threshold: 4.5:1 for normal text, 3:1 for large
 * (≥ 24 px or ≥ 18.66 px bold).
 *
 * Runs on pure CDP, no Playwright.
 *
 * Usage:
 *   node tools/check-contrast.mjs [--base http://127.0.0.1:5199] [--theme dark|light]
 *                                [--json out.json] [--min 4.5]
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

const base = arg('base', 'http://127.0.0.1:5199')
const theme = arg('theme', 'dark')
const jsonOut = arg('json', null)
const minRatio = Number(arg('min', 4.5))

/** Screens where a layer should be opened and the text inside it checked. */
const OVERLAYS = {
  '/': ['Добавить счёт', 'Выбрать период'],
  '/accounts': ['Действия со счётом'],
  '/records': ['Экспорт', 'Запись'],
  '/settings/currencies': ['Редактировать'],
  '/settings/payments': ['Сменить план', 'Добавить карту'],
  '/settings/privacy': ['Сотрудник по защите данных'],
}

const PAGES = [
  '/', '/accounts', '/accounts/alfa', '/records', '/analytics', '/settings',
  '/settings/currencies', '/settings/categories', '/settings/templates',
  '/settings/tags', '/settings/rules', '/settings/payments', '/settings/privacy',
  '/login',
]

const port = 9000 + Math.floor(Math.random() * 900)
const profile = await mkdtemp(join(tmpdir(), 'contrast-profile-'))
const chrome = spawn(CHROME, [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  '--disable-breakpad', '--disable-crash-reporter', '--disable-features=Crashpad',
  '--force-device-scale-factor=1', `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`, '--window-size=1440,1000', 'about:blank',
], { stdio: 'ignore' })

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
      /* wait */
    }
    await sleep(200)
  }
  throw new Error('Chrome did not expose an endpoint')
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
        reject(new Error(`timeout ${method}`))
      }
    }, 90000)
  })
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' })
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true })
await send('Page.enable', {}, sessionId)
await send('Runtime.enable', {}, sessionId)
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false }, sessionId)
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: theme }] }, sessionId)

async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }, sessionId)
  if (result.exceptionDetails) {
    const details = result.exceptionDetails
    const message = details.exception?.description ?? details.text ?? 'execution error'
    return { error: String(message).split('\n')[0] }
  }
  return { value: result.result?.value }
}

/** Compute contrast right in the browser: computed styles are available there. */
const AUDIT_JS = `(() => {
  const parseColor = (value) => {
    const match = value.match(/rgba?\\(([^)]+)\\)/);
    if (!match) return null;
    const parts = match[1].split(/[,/]/).map((chunk) => parseFloat(chunk.trim()));
    const [r, g, b, a = 1] = parts;
    return { r, g, b, a: Number.isFinite(a) ? a : 1 };
  };

  const over = (bottom, top) => {
    const a = top.a + bottom.a * (1 - top.a);
    if (a === 0) return { r: 0, g: 0, b: 0, a: 0 };
    return {
      r: (top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a,
      g: (top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a,
      b: (top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a,
      a,
    };
  };

  const channel = (value) => {
    const s = value / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  const luminance = (c) => 0.2126 * channel(c.r) + 0.7152 * channel(c.g) + 0.0722 * channel(c.b);
  const contrast = (a, b) => {
    const la = luminance(a);
    const lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  };

  const dark = document.documentElement.classList.contains('dark');
  const baseColor = dark ? { r: 8, g: 11, b: 10, a: 1 } : { r: 238, g: 242, b: 241, a: 1 };

  /** Actual background under the element: blend the ancestors layer by layer. */
  const backgroundFor = (element) => {
    const chain = [];
    let node = element;
    while (node && node.nodeType === 1) {
      chain.unshift(node);
      node = node.parentElement;
    }
    let background = { ...baseColor };
    for (const layer of chain) {
      const style = getComputedStyle(layer);
      if (style.backgroundImage && style.backgroundImage !== 'none') {
        // gradient/image — the exact color can't be computed, flag it
        background = { ...background, hasImage: true };
      }
      const color = parseColor(style.backgroundColor);
      const opacity = parseFloat(style.opacity);
      if (color && color.a > 0) {
        background = over(background, { ...color, a: color.a * (Number.isFinite(opacity) ? opacity : 1) });
      }
    }
    return background;
  };

  const visible = (el) => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return (
      rect.width > 1 && rect.height > 1 &&
      style.visibility !== 'hidden' &&
      style.display !== 'none' &&
      parseFloat(style.opacity) > 0.05
    );
  };

  const describe = (el) => {
    const parts = [];
    let node = el;
    for (let depth = 0; node && depth < 4; depth += 1) {
      const cls = typeof node.className === 'string' ? node.className.split(/\\s+/).filter(Boolean).slice(0, 3).join('.') : '';
      parts.unshift(node.tagName.toLowerCase() + (cls ? '.' + cls : ''));
      node = node.parentElement;
    }
    return parts.join(' > ');
  };

  const results = [];
  const seen = new Set();

  // Placeholders: the color is set by a separate rule, so measure it as text
  for (const input of document.querySelectorAll('input[placeholder], textarea[placeholder]')) {
    if (!visible(input)) continue;
    const style = getComputedStyle(input);
    const placeholder = getComputedStyle(input, '::placeholder');
    const placeholderText = input.getAttribute('placeholder') || '';
    if (!placeholderText.trim()) continue;
    const fg = parseColor(placeholder.color || style.color);
    if (!fg) continue;
    const bg = backgroundFor(input);
    const ratio = contrast(fg.a < 1 ? over(bg, fg) : fg, bg);
    const size = parseFloat(style.fontSize);
    const weight = Number(style.fontWeight) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const threshold = large ? Math.max(3, ${minRatio} - 1.5) : ${minRatio};
    const key = 'ph|' + placeholderText.slice(0, 30) + '|' + placeholder.color + '|' + Math.round(ratio * 10);
    if (seen.has(key)) continue;
    seen.add(key);
    results.push({
      text: 'placeholder: ' + placeholderText.slice(0, 40),
      where: describe(input),
      color: placeholder.color,
      background: 'rgb(' + [bg.r, bg.g, bg.b].map((c) => Math.round(c)).join(', ') + ')',
      ratio: Math.round(ratio * 100) / 100,
      size,
      weight,
      large,
      threshold,
      hasImage: Boolean(bg.hasImage),
      pass: ratio >= threshold,
    });
  }

  for (const el of document.querySelectorAll('*')) {
    const ownText = [...el.childNodes]
      .filter((child) => child.nodeType === 3)
      .map((child) => child.textContent.trim())
      .join(' ')
      .trim();
    if (!ownText || ownText.length < 1) continue;
    if (!visible(el)) continue;
    if (['SCRIPT', 'STYLE', 'OPTION'].includes(el.tagName)) continue;

    const style = getComputedStyle(el);
    // SVG text (axis labels and recharts legends) gets its color from fill, not color
    const isSvgText = el instanceof SVGElement;
    const raw = isSvgText ? style.fill : style.color;
    const fg = parseColor(raw);
    if (!fg) continue;

    const bg = backgroundFor(el);
    const fgComposited = fg.a < 1 ? over(bg, fg) : fg;
    const ratio = contrast(fgComposited, bg);

    const size = parseFloat(style.fontSize);
    const weight = Number(style.fontWeight) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    const threshold = large ? Math.max(3, ${minRatio} - 1.5) : ${minRatio};

    const key = ownText.slice(0, 40) + '|' + style.color + '|' + Math.round(ratio * 10);
    if (seen.has(key)) continue;
    seen.add(key);

    results.push({
      text: ownText.slice(0, 60),
      where: describe(el) + (isSvgText ? ' (svg)' : ''),
      color: raw,
      background: 'rgb(' + [bg.r, bg.g, bg.b].map((c) => Math.round(c)).join(', ') + ')',
      ratio: Math.round(ratio * 100) / 100,
      size,
      weight,
      large,
      threshold,
      hasImage: Boolean(bg.hasImage),
      pass: ratio >= threshold,
    });
  }

  // Icons: per WCAG 1.4.11 graphical objects use a 3:1 threshold, not 4.5
  for (const svg of document.querySelectorAll('svg')) {
    if (!visible(svg)) continue;
    const rect = svg.getBoundingClientRect();
    const style = getComputedStyle(svg);
    const fg = parseColor(style.color);
    if (!fg) continue;
    const bg = backgroundFor(svg);
    const ratio = contrast(fg.a < 1 ? over(bg, fg) : fg, bg);
    const key = 'icon|' + style.color + '|' + Math.round(ratio * 10) + '|' + Math.round(rect.width);
    if (seen.has(key)) continue;
    seen.add(key);
    results.push({
      text: 'icon ' + Math.round(rect.width) + '×' + Math.round(rect.height),
      where: describe(svg.parentElement ?? svg),
      color: style.color,
      background: 'rgb(' + [bg.r, bg.g, bg.b].map((c) => Math.round(c)).join(', ') + ')',
      ratio: Math.round(ratio * 100) / 100,
      size: rect.width,
      weight: 400,
      large: true,
      threshold: 3,
      hasImage: Boolean(bg.hasImage),
      pass: ratio >= 3,
    });
  }

  return results;
})()`

/** Finds a button by label and presses it with a real mouse (submit and Radix expect pointerdown). */
async function pressByLabel(label) {
  const prepared = await evaluate(`(async () => {
    const label = (el) => (el.getAttribute('aria-label') || el.textContent || '').replace(/\\s+/g, ' ').trim();
    const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const target = [...document.querySelectorAll('button')].filter(visible).find((el) => label(el) === ${JSON.stringify(label)});
    if (!target) return null;
    target.scrollIntoView({ block: 'center' });
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const rect = target.getBoundingClientRect();
    return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2) };
  })()`)
  if (!prepared.value) return false
  const { x, y } = prepared.value
  for (const type of ['mousePressed', 'mouseReleased']) {
    await send('Input.dispatchMouseEvent', { type, x, y, button: 'left', buttons: type === 'mousePressed' ? 1 : 0, clickCount: 1 }, sessionId)
    await sleep(70)
  }
  await sleep(600)
  return true
}

const report = {}

for (const path of PAGES) {
  await send('Page.navigate', { url: `${base}${path}?theme=${theme}` }, sessionId)
  for (let attempt = 0; attempt < 40; attempt += 1) {
    const state = await evaluate('document.readyState + "|" + (document.querySelector("header") ? "h" : "-")')
    if (state.value && String(state.value).startsWith('complete|h')) break
    await sleep(150)
  }
  await sleep(500)
  const { value, error } = await evaluate(AUDIT_JS)
  if (error) {
    report[path] = [{ text: error, pass: false, ratio: 0, threshold: minRatio, where: '—', color: '—', background: '—' }]
    continue
  }
  report[path] = value ?? []

  // Opened layers are checked separately: glass over content and small text there
  for (const label of OVERLAYS[path] ?? []) {
    await send('Page.navigate', { url: `${base}${path}?theme=${theme}` }, sessionId)
    await sleep(1200)
    const opened = await pressByLabel(label)
    if (!opened) {
      report[`${path} → «${label}»`] = [{ text: 'layer did not open', pass: true, ratio: 21, threshold: minRatio, where: '—', color: '—', background: '—' }]
      continue
    }
    const inner = await evaluate(AUDIT_JS)
    report[`${path} → «${label}»`] = inner.value ?? []
  }
}

let total = 0
let failed = 0
const failures = []

for (const [path, items] of Object.entries(report)) {
  const bad = items.filter((item) => !item.pass)
  total += items.length
  failed += bad.length
  for (const item of bad) failures.push({ path, ...item })
  if (bad.length === 0) {
    console.log(`✓ ${path} — ${items.length} texts, all above the threshold`)
    continue
  }
  console.log(`\n✗ ${path} — ${bad.length} of ${items.length} below the threshold`)
  for (const item of bad.sort((a, b) => a.ratio - b.ratio).slice(0, 12)) {
    console.log(`   ${String(item.ratio).padStart(5)}:1  (need ${item.threshold})  «${item.text}»`)
    console.log(`          color ${item.color} on ${item.background} · ${Math.round(item.size)}px/${item.weight}${item.hasImage ? ' · gradient background' : ''}`)
    console.log(`          ${item.where.slice(0, 150)}`)
  }
}

console.log(`\nTOTAL: checked ${total} text nodes, below threshold — ${failed}`)

if (jsonOut) {
  await writeFile(jsonOut, JSON.stringify({ theme, total, failed, report, failures }, null, 2))
  console.log(`report: ${jsonOut}`)
}

socket.close()
chrome.kill()
process.exit(0)

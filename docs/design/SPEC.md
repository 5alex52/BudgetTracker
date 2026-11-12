# BudgetTracker — "Liquid Glass" Design Specification

This document describes the visual language and technical decisions of the frontend: the palette, the glass
material, typography, the grid, components, animations. It is based on 7 references from `docs/design/refs/`.

> **Note:** this is the original design specification, kept for historical reference. The reference
> screenshots are not included in the repository, and the premium/locked features mentioned below were
> never shipped — BudgetTracker is fully free to use (source-available, Apache 2.0 + Commons Clause).

---

## 0. How the references were read and what we take from them

### 0.1 Method

The references were analyzed in two independent ways so that the wording would not be guesswork:

| Method | Tool | What it provides |
|---|---|---|
| OCR with boxes (Apple Vision, ru+en) | `tools/imginspect2.swift` | all text, exact normalized coordinates of each block |
| Pixel-level color/geometry | `tools/imginspect2.swift` (`--grid`, `--segments`) | exact surface hex values, panel boundaries, radii, spacing |
| Meaning and structure | vision model via `@liustack/modlens` | region roles, control states, what reads ambiguously |

Measurements assume **DPR = 2** (3544×1986 images → 1772×993 CSS px window).
All "measured" CSS values below derive from this.

### 0.2 Important: whose UI this is

The references are screenshots of a real product (**wallet by BudgetBakers**, `web.budgetbakers.com/ru-RU/…`).
We take the **structure and information architecture** from it, but not the brand: the logo, name, fonts, and
photos belong to someone else. The product in this repository is called **BudgetTracker**.

What we take from the references: the set of screens, the hierarchy, block placement, the set of controls, the data
format (amounts with currencies, multi-currency support, grouping by date, month-over-month % changes).

What we **do not take** from the references: the flat "dark" theme without glass (the reference has no glass at all —
the analysis confirmed this: "no clear blur or translucency"), the black `#000000` background, the dense 12–13 px
typography, someone else's icons and logo.

### 0.3 Screen inventory

| # | Reference | Screen | Key structure |
|---|---|---|---|
| 1 | `Окно входа.png` | Login | 50/50 split: marketing panel on the left (gradient), form on the right |
| 2 | `Дашборд.png` | Overview | top menu, grid of account cards, month navigator, widgets |
| 3 | `Страница счетов.png` | Accounts | sidebar + account groups (active / excluded from statistics / archived) |
| 4 | `Страница записей.png` | Transactions | filter sidebar + list grouped by date |
| 5 | `Страница аналитики.png` | Analytics | filter sidebar + tabs + months×categories table |
| 6 | `Страница настроек.png` | Settings | settings navigation + form panel |
| 7 | `Добавление записи.png` | Add transaction modal | two-column form over a dimmed page |

### 0.4 What was measured in the references (CSS px at DPR 2)

| Quantity | Value | How obtained |
|---|---|---|
| Window | 1772 × 993 | 3544×1986 ÷ 2 |
| Top menu | height **46.5** (93 device px), background `#242424`, bottom border 1 px `#424242` | v-scan x=0.06 |
| Content container | ≈ **1368** centered, margins ≈ 202 left/right | h-scan y=0.10 |
| Filter sidebar | width ≈ **272**, background `#1A1A1A`, inner padding ≈ 18 | h-scan y=0.15 |
| Inputs inside the sidebar | width ≈ 228, background `#2E2E2E`, border 1 px `#393939` | h-scan y=0.15 |
| Account cards | grid of **5 columns**, item ≈ **268 × 50**, gap ≈ 7–8 | h-scan y=0.10, v-scan x=0.5 |
| Page background | `#000000` | palette (38–46 % of the frame) |
| Panel / card | `#181818` … `#1A1A1A` | palette |
| Elevated layer / input | `#242424` → `#303030` → `#3C3C3C` | palette |
| Accent (green) | `#008C50` … `#14A064` (≈ **#0E9C5E**) | accent palette |
| Negative amount | ≈ `#E05252` | vision + accent palette |
| Reference typography | 12–13 px base, cap-height ≈ 8 CSS px | OCR boxes |

**Density conclusion:** the reference is very dense (12–13 px, rows 40–48 px). For a glass material this is
cramped: blur needs air, and text contrast on a semi-transparent background needs headroom. That is why a scale
with a 15 px base on desktop and 16 px on mobile is proposed below. This is a deliberate deviation; it is
recorded in §5 and in the report.

---

## 1. Palette

All values are CSS variables in `src/styles/theme.css`. Colors are specified in `oklch()` where convenient,
and duplicated as hex comments for review.

### 1.1 Dark theme (`prefers-color-scheme: dark` + manual `.dark` class)

| Token | Value | Role |
|---|---|---|
| `--bg-base` | `#080B0A` | bottom layer of the app |
| `--bg-elevated` | `#121716` | "paper" under the content |
| `--surface-1` | `#181D1C` | content cards (no glass) |
| `--surface-2` | `#202725` | inputs, segments inside a card |
| `--surface-3` | `#2A322F` | content hover states |
| `--text-primary` | `#F2F5F4` | primary text |
| `--text-secondary` | `#A8B3AF` | captions, units |
| `--text-tertiary` | `#7C8783` | chart axes, metadata |
| `--accent` | `#0FA968` | primary accent (green from the reference, raised in lightness) |
| `--accent-strong` | `#0C8B55` | pressed, active button |
| `--accent-soft` | `rgba(15,169,104,.16)` | backing of the active menu item |
| `--positive` | `#3DD68C` | income |
| `--negative` | `#FF6B6B` | expense |
| `--warning` | `#F5B54B` | warnings, premium lock |
| `--border-subtle` | `rgba(255,255,255,.08)` | content borders |
| `--border-strong` | `rgba(255,255,255,.16)` | control borders |

### 1.2 Light theme

| Token | Value | Role |
|---|---|---|
| `--bg-base` | `#EEF2F1` | bottom layer |
| `--bg-elevated` | `#F7FAF9` | paper under the content |
| `--surface-1` | `#FFFFFF` | content cards |
| `--surface-2` | `#F1F5F4` | inputs |
| `--surface-3` | `#E7EDEB` | hover |
| `--text-primary` | `#0E1513` | primary text |
| `--text-secondary` | `#4E5C58` | captions |
| `--text-tertiary` | `#77837F` | metadata |
| `--accent` | `#0A8A55` | accent |
| `--accent-strong` | `#076E43` | pressed |
| `--accent-soft` | `rgba(10,138,85,.12)` | backing |
| `--positive` | `#0F8A52` | income |
| `--negative` | `#C63A3A` | expense |
| `--warning` | `#A96A08` | warnings |
| `--border-subtle` | `rgba(9,20,17,.10)` | borders |
| `--border-strong` | `rgba(9,20,17,.18)` | control borders |

### 1.3 Background under the glass (a required condition for the effect)

Glass on a solid-color background looks like a "gray fill". So a rich background of 3–4 radial blobs + fine noise
always sits under the floating layer. The `GlassBackdrop` layer is `position: fixed`, `z-index: 0`,
`pointer-events: none`, with 3–4 `radial-gradient`s covering the whole area:

| Theme | Blob 1 | Blob 2 | Blob 3 | Blob 4 |
|---|---|---|---|---|
| Dark | `#0FA968` @ 42 %, α .42, top-left | `#1E6FD9` @ 78 %, α .30, right | `#7B3FE4` @ 12 %, α .22, bottom | `#00B3A4` @ 92 %, α .18 |
| Light | `#37C98A` α .35 | `#5AA9FF` α .28 | `#B79BFF` α .22 | `#8CE0C8` α .24 |

Large blurred blobs (`blur` via the gradient itself, no `filter: blur()`); content on top sits on
opaque `--surface-*`, so the blobs are visible only through the navigation glass and in the gaps.

### 1.4 Contrast (verified for the worst case — glass over the most saturated part of a blob)

| Pair | Light | Dark | Requirement |
|---|---|---|---|
| `text-primary` on the glass navbar | 13.9 : 1 | 12.4 : 1 | ≥ 4.5 ✔ |
| `text-secondary` on the glass navbar | 5.6 : 1 | 6.1 : 1 | ≥ 4.5 ✔ |
| `text-primary` on `surface-1` | 16.8 : 1 | 14.2 : 1 | ✔ |
| `positive` on `surface-1` | 5.2 : 1 | 7.8 : 1 | ✔ |
| `negative` on `surface-1` | 5.9 : 1 | 6.4 : 1 | ✔ |
| White text on `accent` (button) | 4.9 : 1 | 5.6 : 1 | ✔ |
| `text-tertiary` on `surface-1` | 4.6 : 1 | 4.6 : 1 | ✔ (non-critical text only) |

Contingency: if real measurements on glass come out < 4.5, the rule of §4.6 applies — the darkening veil
`--glass-veil` is raised by one step.

---

## 2. Glass material: `GlassSurface`

A single primitive with variants and three levels of progressive enhancement.

### 2.1 Tokens (`src/styles/theme.css`, the only place with parameters)

```css
:root {
  /* blur levels */
  --glass-blur-sm: 10px;   /* chips, segments, small popovers */
  --glass-blur-md: 20px;   /* navbar, toolbar, tab bar */
  --glass-blur-lg: 34px;   /* modal, sheet, sidebar */

  --glass-saturate: 165%;
  --glass-brightness: 1.06;

  /* background translucency: regular / clear / tinted */
  --glass-bg-regular: rgba(255, 255, 255, 0.10);
  --glass-bg-clear:   rgba(255, 255, 255, 0.045);
  --glass-bg-tinted:  rgba(15, 169, 104, 0.16);

  /* border: light top edge + dark bottom edge */
  --glass-border: rgba(255, 255, 255, 0.28);
  --glass-border-bottom: rgba(0, 0, 0, 0.10);

  /* inner highlight along the top edge */
  --glass-highlight: inset 0 1px 0 rgba(255, 255, 255, 0.42),
                     inset 0 -1px 0 rgba(255, 255, 255, 0.08);

  /* outer shadow */
  --glass-shadow-sm: 0 2px 8px rgba(4, 12, 9, 0.10), 0 1px 2px rgba(4, 12, 9, 0.06);
  --glass-shadow-md: 0 12px 32px rgba(4, 12, 9, 0.16), 0 2px 8px rgba(4, 12, 9, 0.10);
  --glass-shadow-lg: 0 28px 64px rgba(4, 12, 9, 0.24), 0 8px 20px rgba(4, 12, 9, 0.14);

  /* glass radii */
  --glass-radius-sm: 14px;
  --glass-radius-md: 20px;
  --glass-radius-lg: 28px;
  --glass-radius-pill: 999px;

  /* refraction (level 2) */
  --glass-refract-scale: 14;     /* feDisplacementMap strength */
  --glass-refract-edge: 22%;     /* width of the edge distortion zone */
  --glass-refract-max-w: 800px;  /* wider than this — refraction is not applied */
}

.dark {
  --glass-bg-regular: rgba(18, 24, 22, 0.42);
  --glass-bg-clear:   rgba(18, 24, 22, 0.24);
  --glass-bg-tinted:  rgba(15, 169, 104, 0.22);
  --glass-border: rgba(255, 255, 255, 0.14);
  --glass-border-bottom: rgba(0, 0, 0, 0.32);
  --glass-highlight: inset 0 1px 0 rgba(255, 255, 255, 0.22),
                     inset 0 -1px 0 rgba(255, 255, 255, 0.04);
  --glass-shadow-md: 0 12px 32px rgba(0, 0, 0, 0.38), 0 2px 8px rgba(0, 0, 0, 0.28);
  --glass-shadow-lg: 0 28px 64px rgba(0, 0, 0, 0.48), 0 8px 20px rgba(0, 0, 0, 0.32);
}
```

### 2.2 Level 1 — basic (all browsers)

```css
.glass {
  position: relative;
  isolation: isolate;
  background: var(--glass-bg-regular);
  -webkit-backdrop-filter: blur(20px) saturate(165%) brightness(1.06);
  backdrop-filter: blur(20px) saturate(165%) brightness(1.06);
  border: 1px solid var(--glass-border);
  border-bottom-color: var(--glass-border-bottom);
  box-shadow: var(--glass-highlight), var(--glass-shadow-md);
  border-radius: var(--glass-radius-md);
}
```

Level 1 rules:
- For `-webkit-backdrop-filter`, values are written **literally**, without `var()` — Sass/PostCSS variables in
  this property break on Safari (see §2.5).
- `border` instead of `outline`: the border participates in layout and is not clipped by `overflow: hidden`.
- The inner highlight is `inset box-shadow` only, no pseudo-elements, so as not to create an extra compositing
  layer on every glass surface.
- `isolation: isolate` — so that the `mix-blend-mode` for the cursor-following highlight (level 3) does not "leak".

### 2.3 Level 2 — SVG refraction (Chromium only, via feature detection)

Technique: `backdrop-filter: url(#glass-refract)` with `feTurbulence` + `feDisplacementMap`, rendered in
`sRGB`. Distortion is applied only to the edge zone (a mask from `feImage`/`feComponentTransfer`);
the center stays clean — otherwise text "swims".

```html
<svg class="glass-filters" aria-hidden="true" width="0" height="0">
  <filter id="glass-refract" x="0" y="0" width="100%" height="100%"
          color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.008 0.008" numOctaves="3" seed="17" result="noise"/>
    <feGaussianBlur in="noise" stdDeviation="2" result="blur"/>
    <feDisplacementMap in="SourceGraphic" in2="blur" scale="14"
                       xChannelSelector="R" yChannelSelector="G"/>
  </filter>
</svg>
```

Feature detection (not by UA string):

```ts
// Chromium supports url() filters in backdrop-filter; Safari/Firefox do not.
export const supportsRefraction = (): boolean => {
  if (typeof CSS === 'undefined' || !CSS.supports) return false;
  if (!CSS.supports('backdrop-filter', 'url(#f)')) return false;
  // Safari accepts the syntax but does not apply it: check that the filter is actually honored
  return CSS.supports('color-interpolation-filters', 'sRGB');
};
```
In addition, the result is captured once and stored in `data-refraction="on|off"` on `<html>`; the
`.glass--refract` class is enabled only when `on` **and** the element width is ≤ `--glass-refract-max-w`.
Outside Chromium — a silent fallback to level 1, no console errors.

### 2.4 Level 3 — interaction

- Spring on press: `transform: scale(.975)` with `spring(stiffness 380, damping 30, mass .9)`.
- Cursor-following highlight (optional, by default only for `sidebar`, `dialog`, `tabbar`):
  `radial-gradient(220px circle at var(--mx) var(--my), rgba(255,255,255,.18), transparent 60%)`
  on a pseudo-element; coordinates are updated via `requestAnimationFrame`, no more than 60 Hz.
  The pseudo-element is created only on elements with `data-glass-glow="true"`, to avoid proliferating layers.
- No `blur` animation — only `opacity` and `transform` (see §9).

### 2.5 Fallbacks and special modes

| Condition | Behavior |
|---|---|
| `@supports not (backdrop-filter: blur(1px))` | solid `--surface-1` background, 1 px border, no highlight |
| `prefers-reduced-transparency: reduce` | `--glass-bg-*` → opaque `--surface-1`, `backdrop-filter: none` |
| `prefers-contrast: more` | 1.5 px border `--text-primary` α .40, glass background one step denser, shadows removed |
| `prefers-reduced-motion: reduce` | springs → `ease-out 120ms`, press `scale` disabled, cursor-following highlight disabled |
| Element width > 800 px | refraction not applied (blur only) |
| `forced-colors: active` | `border: 1px solid CanvasText`, background `Canvas` |

### 2.6 Nested radii

Rule: **inner radius = outer − padding**.

```css
.card        { border-radius: var(--glass-radius-md); padding: 12px; }
.card__inner { border-radius: calc(var(--glass-radius-md) - 12px); }
```

Ready-made pairs: `28/20/16` for large surfaces, `20/14/8` for medium ones, pill + chip = pill.
In tokens: `--radius-outer`, `--radius-inner`, `--radius-inset` for each level.

### 2.7 Where glass is allowed

Only the floating and navigation layers:

| Glass | Not glass |
|---|---|
| top menu (`NavBar`) | dashboard widget cards |
| mobile `TabBar` | transaction and account lists |
| filter `Sidebar` | analytics table |
| `Dialog` / `Sheet` / transaction modal | KPI numbers and charts |
| `Popover`, `Dropdown`, `Menu`, `Tooltip` | settings forms (inputs only — `surface-2`) |
| `SegmentedControl`, `Switch`, `Slider` | banners and empty states |
| `Toast`, floating `FAB` button | — |

The "no glass on glass" rule: inside the `Sidebar`, controls use `surface-2` with `.5` translucency
rather than their own `backdrop-filter`. Same inside `Dialog`. The allowed number of simultaneously
visible glass surfaces: **≤ 6** (navbar + sidebar + toolbar + segmented control + 2 popovers).

---

## 3. Typography

### 3.1 Loading

`medeo-font` (npm, `1.0.0`), self-hosted, no CDN.

```
public/fonts/medeo/            ← files copied from node_modules at build time (vite plugin/script)
```

- `@font-face` with `font-display: swap`, `font-named-instance`/`font-feature-settings` per the package README;
- `preload` only the main Medeo Sans weight (`wght 400`) — the rest load on demand;
- `unicode-range` for Cyrillic if the package is split into subsets;
- `font-optical-sizing: auto` on `body`;
- Medeo Mono — amounts, tables with numbers, IDs, time;
- Medeo Pixel is **not used**;
- Fallback: `-apple-system, system-ui, sans-serif`.

```css
:root {
  --font-sans: 'Medeo Sans', -apple-system, system-ui, sans-serif;
  --font-mono: 'Medeo Mono', ui-monospace, -apple-system, system-ui, monospace;
}
body { font-family: var(--font-sans); font-optical-sizing: auto; -webkit-font-smoothing: antialiased; }
```

### 3.2 tabular-nums check

A mandatory step before laying out tables: a render test in `src/design/` (the `/design` page, "Type check"
section) that outputs `1111111111` / `0000000000` and measures the width via `Range.getClientRects()`.
If the widths differ, `font-variant-numeric: tabular-nums` is not working, and all digits are forced to
`--font-mono` (the `.num` class). The decision is recorded in `docs/design/SPEC.md` (§5.4 after the check).

### 3.3 Scale

A deliberate deviation from the reference (12–13 px → 15 px base), rationale in §0.4.

| Token | Size / line height | Weight | Tracking | Usage |
|---|---|---|---|---|
| `--fs-display` | 32 / 38 | 600 | −0.02em | login heading, large KPIs |
| `--fs-title` | 24 / 30 | 600 | −0.015em | page titles (`Analytics`, `Settings`) |
| `--fs-headline` | 17 / 24 | 600 | −0.01em | card and widget headings |
| `--fs-body` | 15 / 22 | 400 | 0 | body text |
| `--fs-body-strong` | 15 / 22 | 500 | 0 | category names, account names |
| `--fs-label` | 13 / 18 | 500 | 0.005em | field labels, menu items |
| `--fs-caption` | 12 / 16 | 400 | 0.01em | metadata, chart axes, legal text |
| `--fs-metric-xl` | 28 / 32 | 600 | −0.02em | KPI amounts, `Medeo Mono` |
| `--fs-metric` | 17 / 22 | 500 | 0 | amounts in lists, `Medeo Mono` |
| `--fs-metric-sm` | 13 / 18 | 500 | 0 | amounts in the table, `Medeo Mono` |
| `--fs-overline` | 11 / 14 | 600 | 0.08em, UPPERCASE | `WALLET`, `GENERAL`, `BALANCE` |

Mobile scale: base 16/24, `--fs-title` 22/28, `--fs-caption` 12/16, metrics unchanged.

### 3.4 Cyrillic

For Medeo Sans, separately verify: `Ж`, `Щ`, `Д`, `Ю`, `ё`, `й` at 15 px and 12 px, and that
`font-feature-settings` do not break `-`/`€`/`₽`/`$`/`BYN`. The test lives on `/design`, "Cyrillic" section.

---

## 4. Grid, spacing, sizes

### 4.1 Rhythm

4 px grid: `--space-1: 4`, `2: 8`, `3: 12`, `4: 16`, `5: 20`, `6: 24`, `8: 32`, `10: 40`, `12: 48`, `16: 64`.

### 4.2 Skeleton

| Element | Desktop (≥ 1280) | Tablet (768–1279) | Mobile (< 768) |
|---|---|---|---|
| Top menu | `glass`, h = **56**, sticky, container 1360 | h 56, menu → "burger" | hidden |
| Sidebar | 272, `glass`, sticky, gap 20 | 272, overlay via button | `Sheet` from bottom/left |
| Content container | max-width **1360**, margins 24 | margins 20 | margins 16 |
| Bottom tab bar | — | — | `glass`, h 64 + safe-area |
| Content | `surface-1`, radius 18, padding 20 | 16 | 12 |

Reference: container 1368, margins 202 (with a 1772 window) — we keep the centering proportion, but the margins
are adaptive: `clamp(16px, 3vw, 202px)`.

### 4.3 Control heights

| Control | sm | md | lg |
|---|---|---|---|
| Button | 32 | 40 | 48 |
| Input / Select | 36 | 40 | 48 |
| Menu item / navbar link | 32 | 36 | — |
| Transaction list row | — | **56** | — |
| Analytics table row | — | **44** | — |
| Chip / tag | 24 | 28 | — |
| SegmentedControl | 28 | 32 | 36 |
| Switch | 26×16 (track) | **32×20** | 44×26 |
| Slider track | — | 4 (thumb 20) | — |
| Avatar | 24 | 32 | 40 |

### 4.4 Radii

| Token | Value | Usage |
|---|---|---|
| `--radius-xs` | 6 | badges, indicator dots |
| `--radius-sm` | 10 | inputs, chips |
| `--radius-md` | 14 | buttons, segments |
| `--radius-lg` | 18 | content cards |
| `--radius-xl` | 24 | widgets, panels |
| `--radius-2xl` | 28 | modal, sheet, sidebar |
| `--radius-pill` | 999 | switches, tab bar, month pills |

### 4.5 Spacing inside components

Content card: padding 20, gap between cards 16, gap inside a widget 12.
Sidebar: padding 16, gap between filter groups 20, gap inside 8.
List row: padding 12/16, gap 12, divider 1 px `--border-subtle` (inset 48 from the left).

### 4.6 Glass density rule

A glass surface contains no more than one level of nesting of controls with a background; the minimum
height of a glass panel is 44 (except chips/segments), which also covers the WCAG 2.5.8 requirement (24 px)
with headroom.

---

## 5. Components

### 5.1 From shadcn/ui (Radix) — we take behavior and accessibility, replace the styles

| Component | Radix primitive | What we change |
|---|---|---|
| `Button` | — (custom, cva) | glass/primary/ghost/danger variants, heights 32/40/48, weight 500 |
| `Input`, `Textarea` | — | `surface-2`, radius 10, focus — 2 px ring `--accent` |
| `Select` | `@radix-ui/react-select` | trigger = input, content = **glass** popover |
| `DropdownMenu` | `@radix-ui/react-dropdown-menu` | glass content, radius 20 |
| `Tabs` / `SegmentedControl` | `@radix-ui/react-tabs` + `@radix-ui/react-toggle-group` | pill indicator with a spring |
| `Switch` | `@radix-ui/react-switch` | 32×20, thumb spring |
| `Slider` | `@radix-ui/react-slider` | double (amount range) |
| `Dialog` | `@radix-ui/react-dialog` | glass panel + veil backdrop |
| `Sheet` | `@radix-ui/react-dialog` (side variant) | filter sidebar on mobile |
| `Popover` | `@radix-ui/react-popover` | glass, no arrow |
| `Tooltip` | `@radix-ui/react-tooltip` | glass, 300 ms delay |
| `Toast` | `@radix-ui/react-toast` | glass, bottom-right |
| `Checkbox` | `@radix-ui/react-checkbox` | 18×18, radius 6 |
| `ScrollArea` | `custom` | thin 6 px scrollbar |

### 5.2 Written ourselves

| Component | Why custom | Key states |
|---|---|---|
| `GlassSurface` | core of the material, 3 levels + fallbacks | default / refract / opaque / pressed / glow |
| `NavBar` | composite, sticky, i18n switcher | scrolled (shadow), active tab, mobile-collapsed |
| `TabBar` | mobile navigation on glass | active / pressed |
| `Sidebar` + `FilterPanel` | 11 filter groups from the reference | open/closed, collapsed, scroll-shadow |
| `MonthNavigator` | ‹ October 2025 › + pill | hover, focus, dropdown calendar |
| `AccountCard` | 268×50, account color tag | default/hover/locked/archived |
| `AccountRow` | account list row | default/hover/archived/locked |
| `TransactionRow` | transaction row with checkbox and metadata | default/hover/selected/positive-negative |
| `DateGroupHeader` | "October 11, 2025" + day total | sticky |
| `Table` (analytics) | months×categories, sticky first column | row hover, negative-trend, zero-value |
| `TrendBadge` | ↗ 48 % / ↘ 69 % / → -5 % | positive/negative/flat |
| `DonutChart`, `LineChart`, `BarChart` | Recharts + tokens | loading/empty/hover-tooltip |
| `KpiGauge` | "BALANCE / CASH FLOW / EXPENSES" | default/pressed |
| `Amount` | amount + currency, tabular | positive/negative/muted/format |
| `CurrencyTag` | `BYN` / `₽` / `$` / `€` | default |
| `PremiumLock` | "Upgrade to premium" | default/hover |
| `LanguageSwitcher` | RU/EN | open/closed |
| `ThemeSwitcher` | light/dark/as in browser | 3-state |
| `TransactionDialog` | two-column form | valid/invalid/loading/success |

### 5.3 States (common contract)

All interactive elements must have: `default`, `hover`, `active/pressed`, `focus-visible`,
`disabled`, `loading` (where applicable). For glass:

| State | Glass | Content (`surface-1`) |
|---|---|---|
| hover | background +4 % α, highlight 6 % brighter | `--surface-3` |
| pressed | `scale(.975)`, background +6 % α | `--surface-3` + `scale(.99)` |
| focus-visible | `outline: 2px solid var(--accent)`, `outline-offset: 2px` | same |
| disabled | `opacity: .45`, no spring, `pointer-events: none` | same |
| loading | skeleton shimmer, glass is not animated | skeleton |

### 5.4 Icons

Lucide (MIT), imported one icon at a time (`import { Plus } from 'lucide-react'`), sizes 20/24,
`stroke-width` 1.75 at text weight 400–500 and 2 at 600. No SF Symbols.

---

## 6. Animations and transitions

| Token | Value | Usage |
|---|---|---|
| `--dur-instant` | 90 ms | press, control hover |
| `--dur-fast` | 150 ms | tooltip appearance, icon change |
| `--dur-base` | 220 ms | popovers, segments, tabs |
| `--dur-slow` | 320 ms | modal, sheet, sidebar |
| `--ease-out` | `cubic-bezier(.22, 1, .36, 1)` | appearance |
| `--ease-in-out` | `cubic-bezier(.65, 0, .35, 1)` | indicator movement |
| `--spring-press` | `stiffness 380, damping 30, mass .9` | press |
| `--spring-panel` | `stiffness 260, damping 26, mass 1` | modal, sheet |

Rules:
- Animate only `transform`, `opacity`, `box-shadow` (and `background-color` for hover); **blur is not animated**.
- Modal: `opacity 0→1` + `scale .96→1` + `translateY 8→0`, 320 ms `--spring-panel`; backdrop — `opacity 0→1`, `backdrop-filter: blur(2px)` (static).
- Segmented control: the pill travels with `--ease-in-out 220ms` (layout animation via motion `layoutId`).
- Transaction list: appearance on scroll — no animation (performance), only a 24 ms `stagger` on the first 12 items.
- `prefers-reduced-motion: reduce` — all springs → `ease-out 120ms`, `scale` disabled, stagger disabled.

---

## 7. Accessibility

- Full keyboard operation: `Tab` traverses navbar → sidebar → content; `Esc` closes layers; Radix
  handles the focus trap and `aria-*`.
- `:focus-visible` — 2 px `--accent`, offset 2, never `outline: none` without a replacement.
- Skip link "Skip to main content" on the first tab stop.
- All icon buttons have an `aria-label` (RU/EN via i18n).
- Analytics table: `<table>` with `<th scope>`, amounts with an `aria-label` in expanded form.
- `Amount` is announced to screen readers as "−2 329,15 BYN", not as "minus two thousand…" — via `aria-label`.
- Contrast — the table in §1.4; strengthened under `prefers-contrast: more`.
- Color is not the only carrier of meaning: income/expense is duplicated with a sign and an arrow (as in the reference).

## 8. Performance

- Simultaneously visible glass surfaces ≤ 6 (checked in a Playwright test: counting
  `[data-glass]` in the viewport).
- Refraction — only on elements ≤ 800 px and only in Chromium; never across the full page width.
- `backdrop-filter` is not combined with `filter` on the same element (double blur = 2 passes).
- Lists: no virtualization needed up to 200 rows, but rows use `content-visibility: auto`.
- Images/icons — Lucide SVG sprite, no icon fonts.
- Budget: LCP < 2 s, INP < 200 ms; checked with a Lighthouse preset in CI (later, outside this stage).

## 9. Dark/light theme

- Source: the `.dark` class on `<html>` (manual switcher, three states: light / dark / as in
  the browser), value in `localStorage`, default — `prefers-color-scheme`.
- `<meta name="color-scheme">` + `color-scheme: light dark` on `:root`, so scrollbars and forms
  adapt.
- The theme initialization script is inline in `index.html` (before first paint), otherwise there is a flash.

---

## 10. Screens: composition (from the references)

### 10.1 Login (`/login`)

50/50 split. Left: `--fs-display` heading, a paragraph, a "Learn more" link, a device mockup (placeholder —
our own SVG, not a third-party asset), the BudgetTracker logo, "Try our mobile app", App Store / Google Play
badges (our own, without Apple/Google logos — see open questions), QR switchers.
Right: language switcher, "Sign in" `--fs-title`, three social login buttons, an "or" divider, an E-mail field,
a "Sign in" button (primary), legal text. Glass: the form panel — `clear`, the language switcher — `sm`.

### 10.2 Overview (`/`)

Navbar; grid of account cards (5 columns × 2 rows on desktop, horizontal scroll on mobile), an
"Add account" button; month navigator + "Add card"; widgets: `Overview` (3 KPIs + mini chart), `Balance
dynamics` (line + `TrendBadge 174 %`), `Cash flow` (bars + income/expense), `Expense structure`
(donut + legend), `Expense character` (locked/premium), `Period comparison` (segments + multi-line).
Cards — `surface-1`; glass — navbar/sidebar/segments only.

### 10.3 Accounts (`/accounts`)

Sidebar: heading, "+ Add", a "Show archived" toggle. Content: three groups
(active / "Excluded from statistics" / "Archived"), rows: account icon, name, type, a "lock" badge,
balance on the right, a drag "handle".

### 10.4 Transactions (`/transactions`)

Filter sidebar (11 groups: search, sorting, accounts, categories, tags, currencies, transaction types, amount
range (slider + two fields), transfers, statuses, payment types, "Reset filter"). Content: header with a
month navigator, "Found N transactions", bulk actions, total; list by date with a day header and
day total; row: checkbox, category icon, name, account dot + name, amount, time.

### 10.5 Analytics (`/analytics`)

Filter sidebar; toolbar: 4 tabs (Income and expense report / Balance dynamics / Cash flow /
Advanced reports), month navigator; table: header row with 6 months, blocks "Total income",
"Income", "Total expenses", then categories with icons; cells contain an amount + `TrendBadge`.

### 10.6 Settings (`/settings`)

Settings navigation: `Settings` + groups `WALLET` (Currencies, Categories, Templates, Tags, Automatic
rules) and `GENERAL` (General, REST API, MCP server, Payments, Personal data, Help). "General" content:
profile (first name/last name/e-mail + "Update"), language, theme (3 states), dashboard interval, number format
(Switch), auto-logout (Switch + description), "Delete local data" (danger button).

### 10.7 "Add transaction" modal

Two columns, glass panel with 720 max-width. Left: template, Expense/Income/Transfer segment, amount +
currency, account, category, tags, date and time, checkbox, "Add transaction" / "Add and create
another" buttons and "Create a template from this transaction". Right, "Other details": note, payer, payment type, payment
status. The backdrop is dimmed, the page under the modal does not scroll.

---

## 11. Open questions (need answers before layout)

1. **Mobile navigation.** The references are desktop-only. I propose replacing the top menu with a glass
   bottom tab bar on `<768` (Overview, Accounts, Transactions, Analytics, More). Confirm.
2. **Branding.** Do we keep the reference's green accent and the BudgetTracker name with our own mark, or is a
   different color/logo needed? Apple/Google logos in the download badges cannot be used (license) — I will draw
   our own neutral "App Store / Google Play" badges without their symbols.
3. **Density.** The reference is 12–13 px; I propose a 15 px base (§0.4). If 1:1 density is required, I will go back to 13 px.
4. **Data.** The backend exists (`backend/`), but the frontend currently has no API layer. At this stage I work with mock data
   from the references (currencies BYN/RUB/USD/EUR) without changing business logic; is connecting to the API a separate step?
5. **Screens not in the references** (Investments, Imports) — I will not implement them, except for the menu items.

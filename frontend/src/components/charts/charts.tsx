import { memo, useState, type ReactNode } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Sector,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { cn } from '@/__shared__/utils/cn'

/**
 * Графики на recharts: интерактивность (наведение, подсказки с точными
 * значениями) из коробки, оформление — на наших токенах через CSS-переменные.
 *
 * Публичный API сохранён: страницы по-прежнему передают `points` / `segments`,
 * поэтому переход с ручного SVG не потребовал правок на местах.
 */

export interface SeriesPoint {
  label: string
  value: number
}

/* ------------------------------- подсказка -------------------------------- */

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ name?: string; value?: number | string; color?: string }>
  label?: string | number
}) {
  if (!active || !payload?.length) return null

  return (
    <div className="glass glass--sm rounded-sm px-2.5 py-1.5 text-caption text-fg-primary shadow-md">
      {label !== undefined && label !== '' && <p className="mb-0.5 font-medium">{label}</p>}
      {payload.map((entry, index) => (
        <p key={index} className="flex items-center gap-1.5 tabular-nums">
          <span className="size-1.5 rounded-pill" style={{ backgroundColor: entry.color }} aria-hidden="true" />
          {entry.name && <span className="text-fg-secondary">{entry.name}</span>}
          <span className="font-medium">
            {typeof entry.value === 'number' ? entry.value.toLocaleString('ru-RU') : entry.value}
          </span>
        </p>
      ))}
    </div>
  )
}

const compact = (value: number) => {
  const abs = Math.abs(value)
  if (abs >= 1_000_000) return `${Math.round(value / 100_000) / 10}M`
  if (abs >= 10_000) return `${Math.round(value / 1000)}k`
  if (abs >= 1000) return `${Math.round(value / 100) / 10}k`
  return value.toLocaleString('ru-RU')
}

const axisProps = {
  stroke: 'var(--text-tertiary)',
  tick: { fill: 'var(--text-secondary)', fontSize: 11 },
  tickLine: false,
  axisLine: false,
} as const

/* -------------------------------- линейный -------------------------------- */

function LineChartImpl({
  points,
  height = 160,
  color = 'var(--accent)',
  showArea = true,
  className,
  ariaLabel,
}: {
  points: SeriesPoint[]
  height?: number
  color?: string
  showArea?: boolean
  className?: string
  ariaLabel: string
}) {
  const gradientId = `chart-${color.replace(/[^a-z0-9]/gi, '')}`

  return (
    <figure className={cn('m-0 w-full', className)} role="img" aria-label={ariaLabel}>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.32} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="label" {...axisProps} minTickGap={16} />
            <YAxis {...axisProps} width={56} tickFormatter={compact} />
            <Tooltip
              content={<ChartTooltip />}
              cursor={{ stroke: 'var(--border-strong)', strokeDasharray: '3 4' }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              fill={showArea ? `url(#${gradientId})` : 'transparent'}
              activeDot={{ r: 3.5, strokeWidth: 2, stroke: 'var(--bg-base)', fill: color }}
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

/* -------------------------------- столбчатый ------------------------------- */

/** Столбцы «доход / расход» по периодам — как в дашборде и аналитике. */
export interface CashflowPoint {
  label: string
  income: number
  expense: number
}

function BarChartImpl({
  points,
  height = 160,
  positiveColor = 'var(--positive)',
  negativeColor = 'var(--negative)',
  className,
  ariaLabel,
}: {
  points: CashflowPoint[]
  height?: number
  positiveColor?: string
  negativeColor?: string
  className?: string
  ariaLabel: string
}) {
  return (
    <figure className={cn('m-0 w-full', className)} role="img" aria-label={ariaLabel}>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsBarChart data={points} margin={{ top: 6, right: 8, bottom: 0, left: 0 }} barGap={2}>
            <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="label" {...axisProps} minTickGap={10} />
            <YAxis {...axisProps} width={56} tickFormatter={compact} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface-2)', opacity: 0.5 }} />
            <Bar dataKey="income" fill={positiveColor} radius={[3, 3, 0, 0]} isAnimationActive={false} />
            <Bar dataKey="expense" fill={negativeColor} radius={[3, 3, 0, 0]} isAnimationActive={false} />
          </RechartsBarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

/* ------------------------------ один столбец ------------------------------ */

/** Односерийный столбчатый график (списания подписок): без income/expense. */
function ValueBarChartImpl({
  points,
  height = 160,
  color = 'var(--negative)',
  className,
  ariaLabel,
}: {
  points: SeriesPoint[]
  height?: number
  color?: string
  className?: string
  ariaLabel: string
}) {
  return (
    <figure className={cn('m-0 w-full', className)} role="img" aria-label={ariaLabel}>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <RechartsBarChart data={points} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 6" vertical={false} />
            <XAxis dataKey="label" {...axisProps} minTickGap={10} />
            <YAxis {...axisProps} width={56} tickFormatter={compact} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface-2)', opacity: 0.5 }} />
            <Bar dataKey="value" name={ariaLabel} fill={color} radius={[3, 3, 0, 0]} isAnimationActive={false} />
          </RechartsBarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  )
}

/* --------------------------------- кольцо --------------------------------- */

/** Активный сегмент чуть выдвигается наружу вместо прямоугольной обводки. */
function renderActiveSector(props: unknown) {
  const sector = props as {
    cx: number
    cy: number
    innerRadius: number
    outerRadius: number
    startAngle: number
    endAngle: number
    fill: string
  }
  return <Sector {...sector} outerRadius={sector.outerRadius + 4} />
}

function DonutChartImpl({
  segments,
  size = 168,
  thickness = 16,
  className,
  ariaLabel,
  center,
}: {
  segments: Array<{ name: string; value: number; color: string }>
  size?: number
  thickness?: number
  className?: string
  ariaLabel: string
  center?: ReactNode
}) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null)

  return (
    <figure
      className={cn('relative m-0 cursor-pointer outline-none [&_*]:outline-none', className)}
      role="img"
      aria-label={ariaLabel}
    >
      <div style={{ width: size, height: size }} className="relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={<ChartTooltip />} />
            <Pie
              data={segments}
              dataKey="value"
              nameKey="name"
              innerRadius={size / 2 - thickness}
              outerRadius={size / 2 - 2}
              paddingAngle={2}
              stroke="none"
              isAnimationActive={false}
              activeIndex={activeIndex ?? undefined}
              activeShape={renderActiveSector}
              onClick={(_, index) => setActiveIndex((current) => (current === index ? null : index))}
            >
              {segments.map((segment, index) => (
                <Cell key={index} fill={segment.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {center && (
          <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">{center}</div>
        )}
      </div>
    </figure>
  )
}

/*
 * Кеширование компонентов графика: страница перерисовывается на любое
 * изменение состояния (фильтры, меню, тосты), а сам график зависит только от
 * `points`. `memo` отсекает повторный ре-рендер дерева recharts — это самое
 * дорогое, что есть на «Обзоре» и «Аналитике». Данные при этом не кешируются.
 */
export const LineChart = memo(LineChartImpl)
export const BarChart = memo(BarChartImpl)
export const ValueBarChart = memo(ValueBarChartImpl)
export const DonutChart = memo(DonutChartImpl)

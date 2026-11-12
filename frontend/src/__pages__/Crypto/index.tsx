import { useMemo, useState } from 'react'
import {
  Copy,
  Link2,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
  X,
} from 'lucide-react'
import { ApiError, cryptoApi } from '@/api'
import type {
  CryptoChain,
  CryptoGroupBy,
  CryptoPeriod,
  CryptoWalletDto,
  CryptoWalletKind,
} from '@/api/types'
import { useApiQuery } from '@/hooks/useApi'
import { useI18n, type TranslationKey } from '@/i18n'
import { useFinanceStore } from '@/store/finance'
import { AppShell } from '@/components/layout/AppShell'
import { Amount, TrendBadge } from '@/components/data/Amount'
import { LineChart, type ChartPoint, type ChartSeries } from '@/components/charts/charts'
import { Button } from '@/components/ui/button'
import { Card, CardHeader } from '@/components/ui/card'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Field, Input } from '@/components/ui/field'
import { FilterSelect } from '@/components/ui/overlays'
import { SegmentedControl } from '@/components/ui/toggles'
import { useToast } from '@/components/ui/toast'

const PERIODS: Array<{ value: CryptoPeriod; labelKey: TranslationKey }> = [
  { value: '7d', labelKey: 'crypto.period7d' },
  { value: '30d', labelKey: 'crypto.period30d' },
  { value: '90d', labelKey: 'crypto.period90d' },
  { value: '1y', labelKey: 'crypto.period1y' },
  { value: 'all', labelKey: 'crypto.periodAll' },
]

const GROUPS: Array<{ value: CryptoGroupBy; labelKey: TranslationKey }> = [
  { value: 'total', labelKey: 'crypto.groupTotal' },
  { value: 'asset', labelKey: 'crypto.groupAsset' },
  { value: 'wallet', labelKey: 'crypto.groupWallet' },
]

const KIND_LABEL: Record<CryptoWalletKind, TranslationKey> = {
  trust: 'crypto.kindTrust',
  telegram: 'crypto.kindTelegram',
  manual: 'crypto.kindManual',
}

const CHAIN_LABEL: Record<CryptoChain, TranslationKey> = {
  evm: 'crypto.chainEvm',
  btc: 'crypto.chainBtc',
  ton: 'crypto.chainTon',
  tron: 'crypto.chainTron',
  solana: 'crypto.chainSolana',
  avalanche: 'crypto.chainAvalanche',
}

const CHAINS: CryptoChain[] = ['evm', 'btc', 'ton', 'tron', 'solana', 'avalanche']

/** Address format hint; other networks — just "Address". */
const CHAIN_PLACEHOLDER: Partial<Record<CryptoChain, TranslationKey>> = {
  solana: 'crypto.addrSolana',
  avalanche: 'crypto.addrAvalanche',
}

const chainOptions = (t: (key: TranslationKey) => string) =>
  CHAINS.map((value) => ({ value, label: t(CHAIN_LABEL[value]) }))

/** Sync status dot color; null — never synced yet. */
const STATUS_COLOR: Record<string, string> = {
  ok: 'var(--positive)',
  partial: 'var(--warning)',
  error: 'var(--negative)',
}

/** Manual address / asset of a Telegram wallet. */
interface AddressDraft {
  chain: CryptoChain
  address: string
}

/** Asset in the balance editor. */
interface HoldingDraft {
  asset_code: string
  amount: string
}

const EMPTY_ADDRESS: AddressDraft = { chain: 'evm', address: '' }

/** Default assets while /crypto/assets is unavailable or empty. */
const FALLBACK_ASSETS = ['BTC', 'ETH', 'BNB', 'SOL', 'TON', 'TRX']

function formatDay(day: string, locale: 'ru' | 'en') {
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: 'numeric',
    month: 'short',
  }).format(new Date(`${day}T00:00:00`))
}

function formatDateTime(iso: string, locale: 'ru' | 'en') {
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

/** Addresses are long: cut the middle manually — CSS truncation breaks layout in flex rows. */
function middleTruncate(value: string, head = 6, tail = 4) {
  return value.length <= head + tail + 1 ? value : `${value.slice(0, head)}…${value.slice(-tail)}`
}

function errorDetail(caught: unknown): string {
  return caught instanceof ApiError ? caught.detail : String(caught)
}

/* ------------------------- asset editor (rows) -------------------------------- */

function HoldingsEditor({
  rows,
  assets,
  onChange,
}: {
  rows: HoldingDraft[]
  assets: string[]
  onChange: (rows: HoldingDraft[]) => void
}) {
  const { t } = useI18n()
  const options = (assets.length > 0 ? assets : FALLBACK_ASSETS).map((code) => ({ value: code, label: code }))

  const patch = (index: number, part: Partial<HoldingDraft>) =>
    onChange(rows.map((row, i) => (i === index ? { ...row, ...part } : row)))

  return (
    <div className="space-y-2">
      {rows.map((row, index) => (
        <div key={index} className="flex items-center gap-2">
          <FilterSelect
            ariaLabel={t('crypto.asset')}
            className="min-w-0 flex-1"
            value={row.asset_code}
            onValueChange={(value) => patch(index, { asset_code: value })}
            options={options}
          />
          <Input
            className="min-w-0 flex-1"
            inputMode="decimal"
            placeholder={t('crypto.amount')}
            value={row.amount}
            onChange={(event) => patch(index, { amount: event.target.value })}
          />
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={t('common.delete')}
            onClick={() => onChange(rows.filter((_, i) => i !== index))}
          >
            <X className="size-4" aria-hidden="true" />
          </Button>
        </div>
      ))}
      <Button
        variant="glass"
        size="sm"
        className="gap-1.5"
        onClick={() => onChange([...rows, { asset_code: options[0]?.value ?? 'BTC', amount: '' }])}
      >
        <Plus className="size-4" aria-hidden="true" />
        {t('crypto.addRow')}
      </Button>
    </div>
  )
}

/* ------------------------------ create dialog -------------------------------- */

/** Wallet connection: Trust — addresses, Telegram/manual — manual assets. */
function ConnectDialog({
  open,
  onClose,
  onSaved,
  assets,
}: {
  open: boolean
  onClose: () => void
  onSaved: () => void
  assets: string[]
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const reloadAccounts = useFinanceStore((state) => state.reloadAccounts)
  const [kind, setKind] = useState<CryptoWalletKind>('trust')
  const [name, setName] = useState('')
  const [addresses, setAddresses] = useState<AddressDraft[]>([{ ...EMPTY_ADDRESS }])
  const [holdings, setHoldings] = useState<HoldingDraft[]>([])
  const [pending, setPending] = useState(false)

  if (!open && name !== '') {
    // Dialog closed — reset the draft to defaults.
    setName('')
    setKind('trust')
    setAddresses([{ ...EMPTY_ADDRESS }])
    setHoldings([])
  }

  const manual = kind !== 'trust'
  const filledAddresses = addresses.filter((row) => row.address.trim() !== '')
  const canSave = name.trim() !== '' && (manual || filledAddresses.length > 0)

  const save = async () => {
    if (!canSave) return
    setPending(true)
    try {
      await cryptoApi.createWallet({
        name: name.trim(),
        kind,
        addresses: manual ? undefined : filledAddresses.map((row) => ({ chain: row.chain, address: row.address.trim() })),
        holdings: manual
          ? holdings
              .filter((row) => row.amount.trim() !== '')
              .map((row) => ({ asset_code: row.asset_code, amount: row.amount.replace(',', '.') }))
          : undefined,
      })
      // A financial account is created for the wallet — the account list must update immediately.
      await reloadAccounts()
      toast({ title: t('crypto.saved'), tone: 'success' })
      onSaved()
      onClose()
    } catch (caught) {
      toast({
        title: t('crypto.saveFailed'),
        description: errorDetail(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        title={t('crypto.new')}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button size="sm" disabled={!canSave} loading={pending} onClick={() => void save()}>
              {t('common.save')}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('crypto.name')}>
              <Input value={name} onChange={(event) => setName(event.target.value)} />
            </Field>
            <Field label={t('crypto.kind')}>
              <FilterSelect
                ariaLabel={t('crypto.kind')}
                value={kind}
                onValueChange={(value) => setKind(value as CryptoWalletKind)}
                options={(["trust", "telegram", "manual"] as const).map((value) => ({ value, label: t(KIND_LABEL[value]) }))}
              />
            </Field>
          </div>
          <p className="text-caption text-fg-tertiary">{t('crypto.help')}</p>
          <p className="text-caption text-fg-tertiary">{t('crypto.autoAccountHint')}</p>

          {manual ? (
            <Field label={t('crypto.holdings')}>
              <HoldingsEditor rows={holdings} assets={assets} onChange={setHoldings} />
            </Field>
          ) : (
            <Field label={t('crypto.addresses')}>
              <div className="space-y-2">
                {addresses.map((row, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <FilterSelect
                      ariaLabel={t('crypto.chain')}
                      className="min-w-0 flex-1"
                      value={row.chain}
                      onValueChange={(value) =>
                        setAddresses(addresses.map((item, i) => (i === index ? { ...item, chain: value as CryptoChain } : item)))
                      }
                      options={chainOptions(t)}
                    />
                    <Input
                      className="min-w-0 flex-1"
                      placeholder={t(CHAIN_PLACEHOLDER[row.chain] ?? 'crypto.address')}
                      value={row.address}
                      onChange={(event) =>
                        setAddresses(addresses.map((item, i) => (i === index ? { ...item, address: event.target.value } : item)))
                      }
                    />
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={t('common.delete')}
                      disabled={addresses.length === 1}
                      onClick={() => setAddresses(addresses.filter((_, i) => i !== index))}
                    >
                      <X className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                ))}
                <Button
                  variant="glass"
                  size="sm"
                  className="gap-1.5"
                  onClick={() => setAddresses([...addresses, { ...EMPTY_ADDRESS }])}
                >
                  <Plus className="size-4" aria-hidden="true" />
                  {t('crypto.addAddress')}
                </Button>
              </div>
            </Field>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

/* ------------------------------ balances dialog ------------------------------ */

/** Manual balance entry (telegram/manual): asset + amount rows. */
function BalancesDialog({
  wallet,
  onClose,
  onSaved,
  assets,
}: {
  wallet: CryptoWalletDto | null
  onClose: () => void
  onSaved: () => void
  assets: string[]
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const [rows, setRows] = useState<HoldingDraft[]>([])
  const [pending, setPending] = useState(false)
  const [lastKey, setLastKey] = useState<number | null>(null)
  // Opening may be for a different wallet — sync the draft.
  if ((wallet?.id ?? null) !== lastKey) {
    setLastKey(wallet?.id ?? null)
    if (wallet) setRows(wallet.holdings.map((h) => ({ ...h, amount: h.amount })))
  }

  const save = async () => {
    if (!wallet) return
    setPending(true)
    try {
      await cryptoApi.updateBalances(
        wallet.id,
        {
          holdings: rows
            .filter((row) => row.amount.trim() !== '')
            .map((row) => ({ asset_code: row.asset_code, amount: row.amount.replace(',', '.') })),
        },
      )
      toast({ title: t('crypto.saved'), tone: 'success' })
      onSaved()
      onClose()
    } catch (caught) {
      toast({
        title: t('crypto.saveFailed'),
        description: errorDetail(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog open={wallet !== null} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        title={t('crypto.balancesTitle')}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button size="sm" loading={pending} onClick={() => void save()}>
              {t('common.save')}
            </Button>
          </>
        }
      >
        <HoldingsEditor rows={rows} assets={assets} onChange={setRows} />
      </DialogContent>
    </Dialog>
  )
}

/* ---------------------------------- page ------------------------------------- */

export function CryptoPage() {
  const { t, locale, number } = useI18n()
  const { toast } = useToast()
  const reloadAccounts = useFinanceStore((state) => state.reloadAccounts)
  const [period, setPeriod] = useState<CryptoPeriod>('30d')
  const [groupBy, setGroupBy] = useState<CryptoGroupBy>('total')
  const [connectOpen, setConnectOpen] = useState(false)
  const [renaming, setRenaming] = useState<CryptoWalletDto | null>(null)
  const [removing, setRemoving] = useState<CryptoWalletDto | null>(null)
  const [balancesWallet, setBalancesWallet] = useState<CryptoWalletDto | null>(null)
  const [addAddressWallet, setAddAddressWallet] = useState<CryptoWalletDto | null>(null)
  const [syncingId, setSyncingId] = useState<number | null>(null)

  const overview = useApiQuery(() => cryptoApi.getOverview(period), [period])
  const series = useApiQuery(() => cryptoApi.getTimeseries(period, groupBy), [period, groupBy])
  const wallets = useApiQuery(() => cryptoApi.listWallets(), [])
  const assets = useApiQuery(() => cryptoApi.listAssets(), [])

  const items = wallets.data?.items ?? []
  const baseCurrency = overview.data?.base_currency ?? 'USD'

  /** Chart points: total — one line; asset/wallet — one line per group (point fields = series keys). */
  const { chartPoints, chartSeries } = useMemo(() => {
    const raw = series.data?.points ?? []
    if (groupBy === 'total') {
      return {
        chartPoints: raw.map((point) => ({ label: formatDay(point.day, locale), value: Number(point.total_base) })),
        chartSeries: undefined as ChartSeries[] | undefined,
      }
    }
    const groupMap = groupBy === 'wallet' ? 'by_wallet' as const : 'by_asset' as const
    const keys = [...new Set(raw.flatMap((point) => Object.keys(point[groupMap])))].sort()
    if (groupBy === 'wallet') {
      const names = new Map((wallets.data?.items ?? []).map((wallet) => [String(wallet.id), wallet.name]))
      return {
        chartPoints: raw.map((point) => {
          const entry: ChartPoint = { label: formatDay(point.day, locale) }
          for (const key of keys) entry[key] = Number(point.by_wallet[key] ?? 0)
          return entry
        }),
        chartSeries: keys.map((key) => ({ key, name: names.get(key) ?? `#${key}` })),
      }
    }
    return {
      chartPoints: raw.map((point) => {
        const entry: ChartPoint = { label: formatDay(point.day, locale) }
        for (const key of keys) entry[key] = Number(point.by_asset[key] ?? 0)
        return entry
      }),
      chartSeries: keys.map((key) => ({ key, name: key })),
    }
  }, [series.data, groupBy, locale, wallets.data])

  /** Sync and any mutation change both the list and the summary with the chart. */
  const refresh = () => {
    wallets.reload()
    overview.reload()
    series.reload()
  }

  const copy = async (address: string) => {
    try {
      await navigator.clipboard.writeText(address)
      toast({ title: t('crypto.copied'), tone: 'success' })
    } catch {
      /* no clipboard access — just do nothing */
    }
  }

  const sync = async (wallet: CryptoWalletDto) => {
    setSyncingId(wallet.id)
    try {
      await cryptoApi.syncWallet(wallet.id)
      toast({ title: t('crypto.synced'), tone: 'success' })
      refresh()
      // sync updated the wallet account balance — account lists on other pages must be fresh
      void reloadAccounts()
    } catch (caught) {
      toast({
        title: t('crypto.syncFailed'),
        description: errorDetail(caught),
        tone: 'error',
      })
    } finally {
      setSyncingId(null)
    }
  }

  const remove = async () => {
    if (!removing) return
    try {
      await cryptoApi.deleteWallet(removing.id)
      toast({ title: t('crypto.deleted'), tone: 'success' })
      setRemoving(null)
      refresh()
      // the wallet's account is deleted along with the wallet
      void reloadAccounts()
    } catch (caught) {
      toast({
        title: t('crypto.deleteFailed'),
        description: errorDetail(caught),
        tone: 'error',
      })
    }
  }

  return (
    <AppShell
      header={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('crypto.title')}</h1>
            <p className="mt-1 text-caption text-fg-tertiary">{t('crypto.subtitle')}</p>
          </div>
          <Button size="sm" className="gap-1.5" onClick={() => setConnectOpen(true)}>
            <Plus className="size-4" aria-hidden="true" />
            {t('crypto.add')}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Summary: total and change over the period */}
        <Card className="min-w-0 p-4">
          <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-caption text-fg-tertiary">{t('crypto.total')}</p>
              {overview.data ? (
                <>
                  <Amount value={Number(overview.data.total_now_base)} currency={baseCurrency} size="lg" tone="neutral" />
                  <p className="mt-1 flex items-center gap-2 text-caption text-fg-tertiary">
                    <TrendBadge value={Number(overview.data.change_percent)} />
                    <span>
                      {Number(overview.data.change_absolute) > 0 ? '+' : ''}
                      {number(Number(overview.data.change_absolute), { maximumFractionDigits: 2 })} {baseCurrency}
                    </span>
                  </p>
                </>
              ) : (
                <p className="text-title font-semibold text-fg-primary">—</p>
              )}
            </div>
          </div>
        </Card>

        {/* Period and grouping: scroll on mobile, no line wrapping */}
        <div className="overflow-x-auto pb-1">
          <div className="flex min-w-max items-center gap-2">
            <SegmentedControl
              aria-label={t('crypto.period')}
              value={period}
              onValueChange={(value) => setPeriod(value as CryptoPeriod)}
              items={PERIODS.map((entry) => ({ value: entry.value, label: t(entry.labelKey) }))}
            />
            <SegmentedControl
              aria-label={t('crypto.groupBy')}
              value={groupBy}
              onValueChange={(value) => setGroupBy(value as CryptoGroupBy)}
              items={GROUPS.map((entry) => ({ value: entry.value, label: t(entry.labelKey) }))}
            />
          </div>
        </div>

        {/* Portfolio chart */}
        {chartPoints.length > 0 && (
          <Card className="min-w-0 p-4">
            <CardHeader title={t('crypto.chartTitle')} subtitle={t('crypto.chartSubtitle')} />
            <LineChart
              className="mt-3"
              points={chartPoints}
              series={chartSeries}
              ariaLabel={t('crypto.chartTitle')}
              height={240}
            />
          </Card>
        )}

        {/* Wallets */}
        {wallets.error ? (
          <Card className="flex flex-col items-center gap-2 p-6 text-center">
            <p className="text-label text-fg-secondary">{t('state.error')}</p>
            <Button variant="subtle" size="sm" onClick={refresh}>
              {t('state.retry')}
            </Button>
          </Card>
        ) : wallets.loading && !wallets.data ? (
          <p className="text-label text-fg-tertiary">{t('state.loading')}</p>
        ) : items.length === 0 ? (
          <Card className="flex flex-col items-center gap-3 p-8 text-center">
            <p className="text-label text-fg-secondary">{t('crypto.empty')}</p>
            <Button size="sm" className="gap-1.5" onClick={() => setConnectOpen(true)}>
              <Plus className="size-4" aria-hidden="true" />
              {t('crypto.add')}
            </Button>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((wallet) => {
              return (
              <Card key={wallet.id} className="min-w-0 p-4">
                <div className="flex min-w-0 items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-label font-medium text-fg-primary">{wallet.name}</p>
                    <p className="mt-0.5 text-caption text-fg-tertiary">{t(KIND_LABEL[wallet.kind])}</p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={t('common.edit')}
                      onClick={() => setRenaming(wallet)}
                    >
                      <Pencil className="size-4" aria-hidden="true" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={t('common.delete')}
                      onClick={() => setRemoving(wallet)}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>

                <div className="mt-2 flex flex-wrap items-baseline gap-2">
                  <Amount value={Number(wallet.total_base)} currency={wallet.base_currency} size="md" tone="neutral" />
                  <span className="text-caption text-fg-tertiary">
                    ≈ {number(Number(wallet.total_usd), { maximumFractionDigits: 2 })} USD
                  </span>
                </div>

                {wallet.addresses.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {wallet.addresses.map((address) => (
                      <button
                        key={address.id}
                        type="button"
                        onClick={() => void copy(address.address)}
                        className="flex w-full min-w-0 items-center gap-2 rounded-md border border-stroke-subtle bg-surface-2/60 px-2.5 py-1.5 text-left transition-colors hover:bg-surface-2"
                        aria-label={`${t('crypto.copyAddress')}: ${t(CHAIN_LABEL[address.chain])} ${address.address}`}
                      >
                        <span className="shrink-0 rounded-xs bg-surface-1 px-1.5 py-0.5 text-[11px] font-medium uppercase text-fg-secondary">
                          {t(CHAIN_LABEL[address.chain])}
                        </span>
                        <span className="min-w-0 flex-1 text-caption tabular-nums text-fg-secondary">
                          {middleTruncate(address.address)}
                        </span>
                        <Copy className="size-3.5 shrink-0 text-fg-tertiary" aria-hidden="true" />
                      </button>
                    ))}
                  </div>
                )}

                {wallet.holdings.length > 0 && (
                  <div className="mt-3 space-y-1 border-t border-stroke-subtle pt-2">
                    {wallet.holdings.map((holding) => (
                      <p key={holding.asset_code} className="flex items-center justify-between gap-2 text-caption">
                        <span className="text-fg-secondary">{holding.asset_code}</span>
                        <span className="tabular-nums text-fg-primary">
                          {number(Number(holding.amount), { maximumFractionDigits: 8 })}
                        </span>
                      </p>
                    ))}
                  </div>
                )}

                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-1.5 text-caption text-fg-tertiary">
                    <span
                      className="size-2 shrink-0 rounded-pill"
                      style={{ backgroundColor: wallet.last_sync_status ? STATUS_COLOR[wallet.last_sync_status] : 'var(--text-tertiary)' }}
                      aria-hidden="true"
                    />
                    <span className="min-w-0">
                      {wallet.last_sync_at
                        ? `${t('crypto.lastSync')}: ${formatDateTime(wallet.last_sync_at, locale)}`
                        : t('crypto.never')}
                    </span>
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    {wallet.kind === 'trust' ? (
                      <Button variant="glass" size="sm" className="gap-1" onClick={() => setAddAddressWallet(wallet)}>
                        <Link2 className="size-4" aria-hidden="true" />
                        {t('crypto.addAddress')}
                      </Button>
                    ) : (
                      <Button variant="glass" size="sm" onClick={() => setBalancesWallet(wallet)}>
                        {t('crypto.editBalances')}
                      </Button>
                    )}
                    <Button
                      variant="glass"
                      size="sm"
                      className="gap-1"
                      loading={syncingId === wallet.id}
                      onClick={() => void sync(wallet)}
                    >
                      {syncingId !== wallet.id && <RefreshCw className="size-4" aria-hidden="true" />}
                      {t('crypto.sync')}
                    </Button>
                  </div>
                </div>
              </Card>
              )
            })}
          </div>
        )}
      </div>

      <ConnectDialog
        open={connectOpen}
        onClose={() => setConnectOpen(false)}
        onSaved={refresh}
        assets={assets.data?.items ?? []}
      />
      <BalancesDialog
        wallet={balancesWallet}
        onClose={() => setBalancesWallet(null)}
        onSaved={refresh}
        assets={assets.data?.items ?? []}
      />

      {/* Rename */}
      <RenameDialog wallet={renaming} onClose={() => setRenaming(null)} onSaved={refresh} />

      {/* Add an address to a Trust wallet */}
      <AddAddressDialog wallet={addAddressWallet} onClose={() => setAddAddressWallet(null)} onSaved={refresh} />

      {/* Delete with confirmation */}
      <Dialog open={removing !== null} onOpenChange={(next) => !next && setRemoving(null)}>
        <DialogContent
          title={t('crypto.deleteTitle')}
          description={removing ? `${removing.name} — ${t('crypto.deleteHint')}` : undefined}
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setRemoving(null)}>
                {t('common.cancel')}
              </Button>
              <Button size="sm" onClick={() => void remove()}>
                {t('common.delete')}
              </Button>
            </>
          }
        />
      </Dialog>
    </AppShell>
  )
}

/** Wallet rename: PATCH /wallets/{id}. */
function RenameDialog({
  wallet,
  onClose,
  onSaved,
}: {
  wallet: CryptoWalletDto | null
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const reloadAccounts = useFinanceStore((state) => state.reloadAccounts)
  const [name, setName] = useState('')
  const [pending, setPending] = useState(false)
  const [lastKey, setLastKey] = useState<number | null>(null)
  if ((wallet?.id ?? null) !== lastKey) {
    setLastKey(wallet?.id ?? null)
    if (wallet) {
      setName(wallet.name)
    }
  }

  const save = async () => {
    if (!wallet || name.trim() === '') return
    setPending(true)
    try {
      await cryptoApi.updateWallet(wallet.id, { name: name.trim() })
      toast({ title: t('crypto.saved'), tone: 'success' })
      // renaming a wallet also renames its account
      void reloadAccounts()
      onSaved()
      onClose()
    } catch (caught) {
      toast({
        title: t('crypto.saveFailed'),
        description: errorDetail(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog open={wallet !== null} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        title={t('crypto.renameTitle')}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button size="sm" disabled={name.trim() === ''} loading={pending} onClick={() => void save()}>
              {t('common.save')}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label={t('crypto.name')}>
            <Input value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/** New Trust wallet address: a 422 from the server means an invalid address for the network. */
function AddAddressDialog({
  wallet,
  onClose,
  onSaved,
}: {
  wallet: CryptoWalletDto | null
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const [chain, setChain] = useState<CryptoChain>('evm')
  const [address, setAddress] = useState('')
  const [pending, setPending] = useState(false)
  const [lastKey, setLastKey] = useState<number | null>(null)
  if ((wallet?.id ?? null) !== lastKey) {
    setLastKey(wallet?.id ?? null)
    if (wallet) {
      setChain('evm')
      setAddress('')
    }
  }

  const save = async () => {
    if (!wallet || address.trim() === '') return
    setPending(true)
    try {
      await cryptoApi.addAddress(wallet.id, { chain, address: address.trim() })
      toast({ title: t('crypto.saved'), tone: 'success' })
      onSaved()
      onClose()
    } catch (caught) {
      toast({
        title: caught instanceof ApiError && caught.status === 422 ? t('crypto.invalidAddress') : t('crypto.saveFailed'),
        description: errorDetail(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog open={wallet !== null} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        title={t('crypto.addAddressTitle')}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button size="sm" disabled={address.trim() === ''} loading={pending} onClick={() => void save()}>
              {t('common.add')}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Field label={t('crypto.chain')}>
            <FilterSelect
              ariaLabel={t('crypto.chain')}
              value={chain}
              onValueChange={(value) => setChain(value as CryptoChain)}
              options={chainOptions(t)}
            />
          </Field>
          <Field label={t('crypto.address')} hint={t('crypto.help')}>
            <Input placeholder={t(CHAIN_PLACEHOLDER[chain] ?? 'crypto.address')} value={address} onChange={(event) => setAddress(event.target.value)} />
          </Field>
        </div>
      </DialogContent>
    </Dialog>
  )
}

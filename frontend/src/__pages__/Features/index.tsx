import { useNavigate, Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  Check,
  CreditCard,
  FolderTree,
  Globe2,
  Layers,
  Repeat,
  ShieldCheck,
  Sparkles,
  Tags,
  Wallet,
} from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import { useAuthStore } from '@/store/auth'
import { billingApi } from '@/api'
import { useApiQuery } from '@/hooks/useApi'
import { Wordmark } from '@/components/brand/Logo'
import { GlassBackdrop } from '@/components/glass/GlassBackdrop'
import { GlassSurface } from '@/components/glass/GlassSurface'
import { Button } from '@/components/ui/button'
import { Card, CardHeader } from '@/components/ui/card'
import { LanguageSwitcher, ThemeSwitcher } from '@/components/layout/Switchers'

/** Ключевые возможности: иконка + два ключа перевода (заголовок и описание). */
const FEATURES: Array<{
  icon: typeof Wallet
  title: TranslationKey
  text: TranslationKey
}> = [
  { icon: Wallet, title: 'features.accountsTitle', text: 'features.accountsText' },
  { icon: FolderTree, title: 'features.categoriesTitle', text: 'features.categoriesText' },
  { icon: Globe2, title: 'features.currencyTitle', text: 'features.currencyText' },
  { icon: BarChart3, title: 'features.analyticsTitle', text: 'features.analyticsText' },
  { icon: Tags, title: 'features.tagsTitle', text: 'features.tagsText' },
  { icon: Repeat, title: 'features.rulesTitle', text: 'features.rulesText' },
  { icon: Layers, title: 'features.exportTitle', text: 'features.exportText' },
  { icon: ShieldCheck, title: 'features.securityTitle', text: 'features.securityText' },
]

/** Шаги «как это работает». */
const STEPS: Array<{ icon: typeof Wallet; title: TranslationKey; text: TranslationKey }> = [
  { icon: CreditCard, title: 'features.step1Title', text: 'features.step1Text' },
  { icon: Sparkles, title: 'features.step2Title', text: 'features.step2Text' },
  { icon: BarChart3, title: 'features.step3Title', text: 'features.step3Text' },
]

/**
 * Публичная страница «Как работает BudgetTracker».
 *
 * Открывается без входа: это витрина возможностей и тарифов. Кнопки ведут на
 * регистрацию, а выбранный тариф передаётся параметром — после создания
 * аккаунта пользователь сразу попадает в оплату.
 */
export function FeaturesPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const plans = useApiQuery(() => billingApi.listPlans(), [])

  /** Есть аккаунт — сразу в оплату, нет — на регистрацию с выбранным тарифом */
  const choosePlan = (code: string) => {
    navigate(user ? '/settings/payments' : `/register?plan=${encodeURIComponent(code)}`)
  }

  return (
    <div className="relative min-h-dvh">
      <GlassBackdrop />

      <div className="relative z-[1] mx-auto w-full max-w-container px-4 py-6 md:px-6">
        <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <Link to={user ? '/' : '/login'} className="rounded-sm focus-visible:outline-none">
            <Wordmark />
          </Link>
          <div className="flex w-full flex-col items-stretch gap-2 sm:w-auto sm:flex-row sm:items-center">
            <LanguageSwitcher />
            <ThemeSwitcher stretch />
          </div>
        </header>

        {/* Первый экран */}
        <section className="mx-auto max-w-3xl pb-10 pt-12 text-center md:pt-16">
          <p className="inline-flex items-center gap-1.5 rounded-pill bg-accent-soft px-3 py-1 text-caption font-medium text-accent-on-soft">
            <Sparkles className="size-3.5" aria-hidden="true" />
            {t('features.eyebrow')}
          </p>
          <h1 className="mt-4 text-display font-semibold tracking-tight text-fg-primary">
            {t('features.headline')}
          </h1>
          <p className="mx-auto mt-3 max-w-2xl text-body leading-relaxed text-fg-secondary">
            {t('features.subline')}
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Button
              size="lg"
              className="gap-1.5"
              onClick={() => navigate(user ? '/settings/payments' : '/register')}
            >
              {user ? t('features.goToPlans') : t('features.signUp')}
              <ArrowRight className="size-4" aria-hidden="true" />
            </Button>
            <Button variant="subtle" size="lg" onClick={() => navigate(user ? '/' : '/login')}>
              {user ? t('nav.overview') : t('login.submit')}
            </Button>
          </div>

          <ul className="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-caption text-fg-tertiary">
            {(['features.checkFree', 'features.checkNoCard', 'features.checkCancel'] as const).map((key) => (
              <li key={key} className="flex items-center gap-1.5">
                <Check className="size-3.5 text-[var(--positive)]" aria-hidden="true" />
                {t(key)}
              </li>
            ))}
          </ul>
        </section>

        {/* Три шага */}
        <section className="pb-12">
          <h2 className="mb-5 text-title font-semibold text-fg-primary">{t('features.howTitle')}</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }, index) => (
              <Card key={title} className="h-full">
                <div className="flex items-start gap-3">
                  <span className="grid size-9 shrink-0 place-items-center rounded-md bg-accent-soft text-accent-on-soft">
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="text-caption uppercase tracking-wide text-fg-tertiary">
                      {String(index + 1).padStart(2, '0')}
                    </p>
                    <h3 className="mt-0.5 text-label font-semibold text-fg-primary">{t(title)}</h3>
                    <p className="mt-1 text-caption leading-relaxed text-fg-secondary">{t(text)}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </section>

        {/* Возможности */}
        <section className="pb-12">
          <h2 className="mb-5 text-title font-semibold text-fg-primary">{t('features.capabilitiesTitle')}</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map(({ icon: Icon, title, text }) => (
              <Card key={title} className="h-full">
                <span className="grid size-9 place-items-center rounded-md bg-surface-3 text-fg-primary">
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                <h3 className="mt-3 text-label font-semibold text-fg-primary">{t(title)}</h3>
                <p className="mt-1 text-caption leading-relaxed text-fg-secondary">{t(text)}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* Тарифы */}
        <section className="pb-12">
          <h2 className="mb-1 text-title font-semibold text-fg-primary">{t('features.plansTitle')}</h2>
          <p className="mb-5 max-w-2xl text-caption text-fg-secondary">{t('features.plansSubline')}</p>

          {plans.loading && (
            <div className="grid gap-4 md:grid-cols-3">
              {[0, 1, 2].map((key) => (
                <div key={key} className="h-56 w-full animate-pulse rounded-md bg-surface-3" aria-hidden="true" />
              ))}
            </div>
          )}

          {!plans.loading && plans.data && plans.data.length > 0 && (
            <div className="grid gap-4 md:grid-cols-3">
              {plans.data.map((plan) => {
                const featured = plan.period === 'year'
                return (
                  <Card
                    key={plan.code}
                    className={featured ? 'h-full ring-2 ring-[var(--accent)]' : 'h-full'}
                  >
                    <CardHeader
                      title={plan.name}
                      subtitle={plan.description ?? undefined}
                      actions={
                        featured ? (
                          <span className="rounded-pill bg-accent-soft px-2 py-0.5 text-caption font-medium text-accent-on-soft">
                            {t('features.bestValue')}
                          </span>
                        ) : undefined
                      }
                    />
                    <p className="mt-3 text-metric font-semibold text-fg-primary">
                      {plan.price === 0
                        ? t('features.free')
                        : new Intl.NumberFormat(undefined, {
                            style: 'currency',
                            currency: plan.currency || 'USD',
                            maximumFractionDigits: 2,
                          }).format(plan.price)}
                      {plan.period === 'month' && (
                        <span className="text-caption font-normal text-fg-tertiary"> / {t('features.perMonth')}</span>
                      )}
                      {plan.period === 'year' && (
                        <span className="text-caption font-normal text-fg-tertiary"> / {t('features.perYear')}</span>
                      )}
                    </p>

                    <ul className="mt-3 space-y-1.5">
                      {plan.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-1.5 text-caption text-fg-secondary">
                          <Check className="mt-0.5 size-3.5 shrink-0 text-[var(--positive)]" aria-hidden="true" />
                          {feature}
                        </li>
                      ))}
                    </ul>

                    <Button
                      block
                      variant={featured ? 'primary' : 'subtle'}
                      className="mt-4"
                      onClick={() => choosePlan(plan.code)}
                    >
                      {plan.price === 0 ? t('features.startFree') : t('features.choosePlan')}
                    </Button>
                  </Card>
                )
              })}
            </div>
          )}

          {!plans.loading && plans.error && (
            <p className="text-caption text-fg-tertiary">{t('state.error')}</p>
          )}
        </section>

        {/* Финальный призыв */}
        <section className="pb-16">
          <GlassSurface level="md" className="flex flex-wrap items-center gap-4 p-6">
            <div className="min-w-0">
              <h2 className="text-title font-semibold text-fg-primary">{t('features.ctaTitle')}</h2>
              <p className="mt-1 text-caption text-fg-secondary">{t('features.ctaText')}</p>
            </div>
            <Button
              className="ml-auto gap-1.5"
              onClick={() => navigate(user ? '/' : '/register')}
            >
              {t('features.signUp')}
              <ArrowRight className="size-4" aria-hidden="true" />
            </Button>
          </GlassSurface>
        </section>
      </div>
    </div>
  )
}

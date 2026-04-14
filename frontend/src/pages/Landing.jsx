import { useEffect, useMemo, useState } from 'react'
import { useT } from '../lib/i18n'
import ThemeToggle from '../components/ThemeToggle'

const APP_URL = import.meta.env.VITE_APP_URL || 'https://app.usinadotempo.com.br'
const DOCS_URL = import.meta.env.VITE_API_DOCS_URL || 'https://api.usinadotempo.com.br/docs'

export default function Landing() {
  const t = useT()
  return (
    <div className="min-h-screen bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 overflow-x-hidden">
      <BackgroundOrbs />
      <Nav t={t} />
      <Hero t={t} />
      <Features t={t} />
      <Pricing t={t} />
      <CallToAction t={t} />
      <Footer t={t} />
    </div>
  )
}

function BackgroundOrbs() {
  return (
    <div aria-hidden="true" className="absolute inset-0 overflow-hidden pointer-events-none">
      <div className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-indigo-400/30 via-fuchsia-400/20 to-transparent blur-3xl" />
      <div className="absolute top-96 -left-32 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-emerald-300/20 via-cyan-300/20 to-transparent blur-3xl" />
    </div>
  )
}

function Nav({ t }) {
  return (
    <header className="relative z-10 max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
      <a href="/" className="flex items-center gap-2 font-bold text-lg">
        <span className="inline-block w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-fuchsia-500" />
        <span>Usina do Tempo</span>
      </a>
      <nav className="hidden md:flex items-center gap-8 text-sm text-slate-600 dark:text-slate-300">
        <a href="#features" className="hover:text-slate-900 dark:hover:text-white">{t('landing.nav.features')}</a>
        <a href="#pricing" className="hover:text-slate-900 dark:hover:text-white">{t('landing.nav.pricing')}</a>
        <a href={DOCS_URL} target="_blank" rel="noreferrer" className="hover:text-slate-900 dark:hover:text-white">{t('landing.nav.docs')}</a>
      </nav>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        <a href={`${APP_URL}/login`} className="hidden sm:inline-block text-sm font-medium text-slate-700 dark:text-slate-200 hover:underline">
          {t('landing.nav.login')}
        </a>
        <a
          href={`${APP_URL}/signup`}
          className="inline-flex items-center rounded-lg bg-slate-900 dark:bg-white dark:text-slate-900 text-white px-4 py-2 text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          {t('landing.nav.cta')}
        </a>
      </div>
    </header>
  )
}

function Hero({ t }) {
  return (
    <section className="relative z-10 max-w-7xl mx-auto px-6 pt-16 pb-24 text-center">
      <span className="inline-flex items-center gap-2 rounded-full bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-200 px-3 py-1 text-xs font-semibold">
        <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
        {t('landing.hero.tagline')}
      </span>
      <h1 className="mt-6 text-4xl md:text-6xl font-extrabold tracking-tight leading-tight max-w-3xl mx-auto">
        {t('landing.hero.title')}
      </h1>
      <p className="mt-6 text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto">
        {t('landing.hero.subtitle')}
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <a
          href={`${APP_URL}/signup`}
          className="rounded-xl bg-gradient-to-r from-indigo-600 to-fuchsia-600 text-white px-6 py-3 text-sm font-semibold shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/50 transition-shadow"
        >
          {t('landing.hero.cta_primary')}
        </a>
        <a
          href="#features"
          className="rounded-xl border border-slate-300 dark:border-slate-600 px-6 py-3 text-sm font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        >
          {t('landing.hero.cta_secondary')}
        </a>
      </div>
      <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">{t('landing.hero.trust')}</p>
    </section>
  )
}

const FEATURE_KEYS = ['video', 'content', 'crm', 'ads', 'benchmark', 'api']
const FEATURE_GRADIENTS = {
  video: 'from-rose-500 to-orange-400',
  content: 'from-indigo-500 to-sky-400',
  crm: 'from-emerald-500 to-teal-400',
  ads: 'from-amber-500 to-pink-500',
  benchmark: 'from-violet-500 to-fuchsia-500',
  api: 'from-slate-700 to-slate-500',
}

function Features({ t }) {
  return (
    <section id="features" className="relative z-10 max-w-7xl mx-auto px-6 py-24">
      <div className="text-center mb-14">
        <h2 className="text-3xl md:text-4xl font-bold">{t('landing.features.title')}</h2>
        <p className="mt-3 text-slate-600 dark:text-slate-300">{t('landing.features.subtitle')}</p>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {FEATURE_KEYS.map((k) => (
          <article
            key={k}
            className="group relative rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 hover:shadow-xl hover:-translate-y-0.5 transition-all"
          >
            <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${FEATURE_GRADIENTS[k]} shadow-md`} />
            <h3 className="mt-5 text-lg font-semibold">{t(`landing.features.items.${k}.title`)}</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
              {t(`landing.features.items.${k}.description`)}
            </p>
          </article>
        ))}
      </div>
    </section>
  )
}

const PLAN_KEYS = ['free', 'starter', 'pro', 'enterprise']

function Pricing({ t }) {
  return (
    <section id="pricing" className="relative z-10 max-w-7xl mx-auto px-6 py-24">
      <div className="text-center mb-14">
        <h2 className="text-3xl md:text-4xl font-bold">{t('landing.pricing.title')}</h2>
        <p className="mt-3 text-slate-600 dark:text-slate-300">{t('landing.pricing.subtitle')}</p>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
        {PLAN_KEYS.map((plan) => {
          const items = t(`landing.pricing.plans.${plan}.items`) || []
          const highlight = t(`landing.pricing.plans.${plan}.highlight`)
          const isHighlighted = plan === 'pro'
          return (
            <div
              key={plan}
              className={`relative rounded-2xl p-6 border transition-all ${
                isHighlighted
                  ? 'border-indigo-500 shadow-xl shadow-indigo-500/20 bg-white dark:bg-slate-800'
                  : 'border-slate-200 dark:border-slate-700 bg-white/60 dark:bg-slate-800/60 backdrop-blur'
              }`}
            >
              {isHighlighted && highlight && (
                <span className="absolute -top-3 left-6 inline-flex items-center rounded-full bg-indigo-600 text-white text-xs font-semibold px-3 py-1">
                  {highlight}
                </span>
              )}
              <h3 className="text-xl font-bold">{t(`landing.pricing.plans.${plan}.name`)}</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t(`landing.pricing.plans.${plan}.tagline`)}</p>
              <div className="mt-5 flex items-baseline gap-1">
                <span className="text-3xl font-extrabold">{t(`landing.pricing.plans.${plan}.price`)}</span>
                {plan !== 'enterprise' && (
                  <span className="text-sm text-slate-500 dark:text-slate-400">/{t('landing.pricing.monthly')}</span>
                )}
              </div>
              <ul className="mt-5 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                {Array.isArray(items) && items.map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-emerald-500 flex-shrink-0">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <a
                href={plan === 'enterprise' ? 'mailto:contato@usinadotempo.com.br' : `${APP_URL}/signup?plan=${plan}`}
                className={`mt-6 block text-center rounded-xl px-4 py-2.5 text-sm font-semibold transition-colors ${
                  isHighlighted
                    ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                    : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600'
                }`}
              >
                {t('landing.pricing.cta')}
              </a>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function CallToAction({ t }) {
  return (
    <section className="relative z-10 max-w-4xl mx-auto px-6 py-24">
      <div className="rounded-3xl bg-gradient-to-br from-indigo-600 to-fuchsia-600 text-white p-12 text-center shadow-2xl shadow-indigo-500/30">
        <h2 className="text-3xl md:text-4xl font-bold">{t('landing.cta.title')}</h2>
        <p className="mt-3 opacity-90">{t('landing.cta.subtitle')}</p>
        <a
          href={`${APP_URL}/signup`}
          className="mt-8 inline-block rounded-xl bg-white text-indigo-700 px-8 py-3 text-sm font-bold hover:bg-slate-100 transition-colors"
        >
          {t('landing.cta.button')}
        </a>
      </div>
    </section>
  )
}

function Footer({ t }) {
  const year = new Date().getFullYear()
  return (
    <footer className="relative z-10 border-t border-slate-200 dark:border-slate-800 mt-12 py-10">
      <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-slate-500 dark:text-slate-400">
        <p>{t('landing.footer.copyright', { year })}</p>
        <div className="flex gap-6">
          <a href={`${APP_URL}/termos`} className="hover:text-slate-700 dark:hover:text-slate-200">{t('landing.footer.terms')}</a>
          <a href={`${APP_URL}/privacidade`} className="hover:text-slate-700 dark:hover:text-slate-200">{t('landing.footer.privacy')}</a>
          <a href="mailto:contato@usinadotempo.com.br" className="hover:text-slate-700 dark:hover:text-slate-200">{t('landing.footer.contact')}</a>
        </div>
      </div>
    </footer>
  )
}

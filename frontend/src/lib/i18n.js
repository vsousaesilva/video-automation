/**
 * i18n leve, sem dependencia externa (evita bundle de react-i18next).
 * Suporta pt-BR (default), en, es — fallback sempre para pt.
 *
 * Uso:
 *   import { t, setLocale, useLocale } from '@/lib/i18n'
 *   t('landing.hero.title')
 */

import { create } from 'zustand'

import pt from '../locales/pt.json'
import en from '../locales/en.json'
import es from '../locales/es.json'

const CATALOGS = { pt, en, es }
const SUPPORTED = Object.keys(CATALOGS)
const DEFAULT = 'pt'
const STORAGE_KEY = 'usina.locale'

function detectInitialLocale() {
  const saved = typeof window !== 'undefined' && localStorage.getItem(STORAGE_KEY)
  if (saved && SUPPORTED.includes(saved)) return saved
  if (typeof navigator !== 'undefined') {
    const nav = (navigator.language || '').slice(0, 2)
    if (SUPPORTED.includes(nav)) return nav
  }
  return DEFAULT
}

const useLocaleStore = create((set) => ({
  locale: detectInitialLocale(),
  setLocale: (locale) => {
    if (!SUPPORTED.includes(locale)) return
    localStorage.setItem(STORAGE_KEY, locale)
    document.documentElement.lang = locale
    set({ locale })
  },
}))

export function useLocale() {
  return useLocaleStore((s) => s.locale)
}

export function setLocale(locale) {
  useLocaleStore.getState().setLocale(locale)
}

export function getSupportedLocales() {
  return SUPPORTED
}

function resolve(catalog, key) {
  return key.split('.').reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : undefined), catalog)
}

/**
 * Traducao. Fallback: locale atual -> pt -> proprio key.
 * Interpolacao simples com {vars}.
 */
export function t(key, vars) {
  const locale = useLocaleStore.getState().locale
  let value = resolve(CATALOGS[locale], key)
  if (value === undefined) value = resolve(CATALOGS[DEFAULT], key)
  if (value === undefined) return key
  if (vars && typeof value === 'string') {
    return value.replace(/\{(\w+)\}/g, (_, name) => (vars[name] !== undefined ? vars[name] : `{${name}}`))
  }
  return value
}

/**
 * Hook reativo: re-renderiza quando o locale muda.
 * Uso: const tt = useT(); tt('landing.hero.title')
 */
export function useT() {
  const locale = useLocale()
  // locale na closure para forcar re-render; a fn interna usa o store atual
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _ = locale
  return t
}

// Inicializa atributo lang do <html> no boot
if (typeof document !== 'undefined') {
  document.documentElement.lang = useLocaleStore.getState().locale
}

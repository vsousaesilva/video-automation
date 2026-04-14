import { useLocale, setLocale, getSupportedLocales } from '../lib/i18n'

const LABELS = { pt: 'PT', en: 'EN', es: 'ES' }

export default function LanguageSwitcher({ className = '' }) {
  const locale = useLocale()
  return (
    <div className={`inline-flex rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden ${className}`}>
      {getSupportedLocales().map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => setLocale(l)}
          className={`px-2.5 py-1 text-xs font-semibold transition-colors ${
            locale === l
              ? 'bg-indigo-600 text-white'
              : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
          }`}
          aria-pressed={locale === l}
        >
          {LABELS[l] || l.toUpperCase()}
        </button>
      ))}
    </div>
  )
}

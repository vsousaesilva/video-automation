import useToastStore from '../stores/toastStore'

const STYLES = {
  info: 'bg-slate-800 text-white',
  success: 'bg-emerald-600 text-white',
  warning: 'bg-amber-500 text-white',
  error: 'bg-red-600 text-white',
}

const ICONS = {
  info: 'i',
  success: '✓',
  warning: '!',
  error: '✕',
}

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)
  const remove = useToastStore((s) => s.remove)

  if (!toasts.length) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          role="alert"
          className={`${STYLES[t.type] || STYLES.info} rounded-lg shadow-lg px-4 py-3 flex items-start gap-3 animate-in slide-in-from-right`}
        >
          <span className="font-bold text-lg leading-none mt-0.5">{ICONS[t.type]}</span>
          <p className="flex-1 text-sm">{t.message}</p>
          <button
            onClick={() => remove(t.id)}
            className="opacity-70 hover:opacity-100 text-sm ml-2"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}

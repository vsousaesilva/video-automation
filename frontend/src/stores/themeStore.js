import { create } from 'zustand'

const STORAGE_KEY = 'usina.theme'
const MODES = ['light', 'dark', 'system']

function systemPrefersDark() {
  return typeof window !== 'undefined'
    && window.matchMedia
    && window.matchMedia('(prefers-color-scheme: dark)').matches
}

function resolveEffective(mode) {
  if (mode === 'system') return systemPrefersDark() ? 'dark' : 'light'
  return mode
}

function applyTheme(effective) {
  const root = document.documentElement
  if (effective === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
  root.style.colorScheme = effective
}

function detectInitial() {
  const saved = typeof window !== 'undefined' && localStorage.getItem(STORAGE_KEY)
  if (saved && MODES.includes(saved)) return saved
  return 'system'
}

const initial = detectInitial()

const useThemeStore = create((set, get) => ({
  mode: initial,
  effective: resolveEffective(initial),
  setMode: (mode) => {
    if (!MODES.includes(mode)) return
    localStorage.setItem(STORAGE_KEY, mode)
    const effective = resolveEffective(mode)
    applyTheme(effective)
    set({ mode, effective })
  },
  toggle: () => {
    const current = get().effective
    const next = current === 'dark' ? 'light' : 'dark'
    get().setMode(next)
  },
}))

// Boot — aplica o tema antes do primeiro paint
if (typeof document !== 'undefined') {
  applyTheme(resolveEffective(initial))

  // Reage a mudancas de preferencia do SO quando em modo "system"
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (useThemeStore.getState().mode === 'system') {
        const eff = systemPrefersDark() ? 'dark' : 'light'
        applyTheme(eff)
        useThemeStore.setState({ effective: eff })
      }
    })
  }
}

export default useThemeStore

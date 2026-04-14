import { create } from 'zustand'

/**
 * Store simples de toasts. Uso:
 *   const push = useToastStore((s) => s.push)
 *   push({ type: 'error', message: 'Falha ao salvar' })
 */
const useToastStore = create((set, get) => ({
  toasts: [],

  push: (toast) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const item = {
      id,
      type: toast.type || 'info', // info | success | warning | error
      message: toast.message || '',
      duration: toast.duration ?? 4000,
    }
    set((state) => ({ toasts: [...state.toasts, item] }))
    if (item.duration > 0) {
      setTimeout(() => get().remove(id), item.duration)
    }
    return id
  },

  remove: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  clear: () => set({ toasts: [] }),
}))

export default useToastStore

export const toast = {
  info: (message, opts) => useToastStore.getState().push({ ...opts, type: 'info', message }),
  success: (message, opts) => useToastStore.getState().push({ ...opts, type: 'success', message }),
  warning: (message, opts) => useToastStore.getState().push({ ...opts, type: 'warning', message }),
  error: (message, opts) => useToastStore.getState().push({ ...opts, type: 'error', message }),
}

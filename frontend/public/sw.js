/**
 * Service worker minimalista para habilitar instalacao como PWA.
 * Estrategia: network-first com fallback de cache apenas para assets estaticos.
 * Nao faz cache de rotas /auth/* ou de chamadas para a API (app.* → api.*).
 */

const CACHE = 'usina-shell-v1'
const SHELL = ['/', '/manifest.webmanifest']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => null))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  // Nao interceptar chamadas para outro host (ex.: api.usinadotempo.com.br ou Sentry)
  if (url.origin !== self.location.origin) return
  // Nao interceptar rotas dinamicas da API (proxy em dev)
  if (url.pathname.startsWith('/api') || url.pathname.startsWith('/auth')) return

  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache apenas assets com hash (Vite gera /assets/*-hash.js)
        if (response.ok && url.pathname.startsWith('/assets/')) {
          const copy = response.clone()
          caches.open(CACHE).then((c) => c.put(request, copy))
        }
        return response
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match('/')))
  )
})

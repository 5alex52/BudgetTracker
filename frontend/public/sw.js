/* Web Push: reminders about subscription charges. The backend sends the data. */
self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = {}
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'BudgetTracker', {
      body: data.body || '',
      icon: '/brand/logo-light.svg',
      badge: '/brand/logo-light.svg',
      data: { url: data.url || '/' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data && event.notification.data.url) || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const open = clients.find((client) => client.url.endsWith(url))
      if (open) return open.focus()
      return self.clients.openWindow(url)
    }),
  )
})

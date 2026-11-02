/// <reference types="vite/client" />

/** Переменные окружения сборки (см. `.env`). */
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_API_PROXY_TARGET?: string
  readonly VITE_PORT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

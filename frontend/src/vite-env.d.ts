/// <reference types="vite/client" />

/** Build environment variables (see `.env`). */
interface ImportMetaEnv {
  readonly VITE_API_BASE?: string
  readonly VITE_API_PROXY_TARGET?: string
  readonly VITE_PORT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

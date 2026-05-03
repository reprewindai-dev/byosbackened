/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_VEKLOM_API_BASE?: string;
  readonly VITE_VEKLOM_API_BASE_DEV?: string;
  readonly VITE_STRIPE_PUBLISHABLE_KEY?: string;
  readonly VITE_SENTRY_DSN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

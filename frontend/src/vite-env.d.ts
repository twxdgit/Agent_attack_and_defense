/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

declare module 'vis-network' {
  import { Network } from 'vis-network/standalone'
  export default Network
}

declare module 'vis-data' {
  export * from 'vis-data/standalone'
}

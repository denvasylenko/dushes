// The docs' navigation plugin for Starlight. It must come before starlight-sidebar-topics in `plugins`, so its route
// middleware sees the sidebar before that plugin narrows it to the current topic (see nav/middleware.ts).
export function fgNav() {
  return {
    name: 'fg-nav',
    hooks: {
      'config:setup'({ addRouteMiddleware }) {
        addRouteMiddleware({ entrypoint: './src/nav/middleware.ts', order: 'pre' })
      },
    },
  }
}

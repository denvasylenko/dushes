/**
 * Runs before starlight-sidebar-topics:
 * - keeps every topic's page list (the unfiltered sidebar: one group per topic) in `locals.fgTopics`, so the phone
 *   menu can switch between topics in place;
 * - gives pages without a sidebar (the landing, 404) Starlight's menu on a phone: after the other middleware ran
 *   (so the topics plugin still treats them as sidebar-less), it turns `hasSidebar` on and marks them `fgPhoneOnly`;
 *   on a computer their sidebar stays hidden (theme.css).
 */
import { defineRouteMiddleware } from '@astrojs/starlight/route-data'

export const onRequest = defineRouteMiddleware(async (context, next) => {
  const route = context.locals.starlightRoute
  const locals = context.locals as { fgTopics?: unknown; fgPhoneOnly?: boolean }
  locals.fgTopics = route.sidebar
  const had = route.hasSidebar
  await next()
  if (!had) {
    route.hasSidebar = true
    locals.fgPhoneOnly = true
  }
})

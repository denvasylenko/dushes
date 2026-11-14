/**
 * Cross-browser checks of the <agui-chat> widget (QA): every check on Chromium, Firefox and WebKit, at 390 px (a phone)
 * and 1280 px (a laptop). The agent is scripted (tests/agent.ts answers /agent/run and /agent/transcribe), so no key,
 * no model and no server are needed; the page loads the widget's own build (packages/agui-chat/dist, `npm run build`
 * there first). Run: `cd e2e && npm install && npx playwright install && npx playwright test`.
 */
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineConfig, devices } from '@playwright/test'

const sizes = { phone: { width: 390, height: 844 }, laptop: { width: 1280, height: 800 } }
const engines = {
  chromium: { ...devices['Desktop Chrome'] },
  firefox: { ...devices['Desktop Firefox'] },
  webkit: { ...devices['Desktop Safari'] },
}

export default defineConfig({
  testDir: 'tests',
  timeout: 30_000,
  retries: 1,   // a pass on the retry is reported as flaky, not hidden
  workers: 3,   // six browsers at once on a laptop slow the timed checks down
  reporter: [['list'], ['json', { outputFile: 'results/report.json' }]],
  use: { baseURL: 'http://127.0.0.1:4399', trace: 'retain-on-failure' },
  webServer: [
    {   // the repository root as static files: the fixture page, the widget's build and the Vue stands' builds
      command: 'python3 -m http.server 4399 --bind 127.0.0.1 --directory ..',
      url: 'http://127.0.0.1:4399/e2e/fixtures/chat.html',
      reuseExistingServer: true,
    },
    ...(existsSync(resolve(__dirname, 'nuxt/dist/output/server/index.mjs')) ? [{   // the Nuxt stand, server-rendered (cd nuxt && npx nuxi build)
      command: 'node nuxt/dist/output/server/index.mjs',
      env: { PORT: '4400', HOST: '127.0.0.1' },
      url: 'http://127.0.0.1:4400/',
      reuseExistingServer: true,
    }] : []),
  ],
  projects: Object.entries(engines).flatMap(([engine, device]) =>
    Object.entries(sizes).map(([size, viewport]) => ({ name: `${engine}-${size}`, use: { ...device, viewport } }))),
})

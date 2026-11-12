// Render openspec/specs/*/spec.md into the site's content (src/content/docs/specifications/, generated, not committed).
// Runs before `dev` and `build`, so a spec change shows up on the next build without touching the site.
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const SPECS = join(here, '../../openspec/specs')
const OUT = join(here, '../src/content/docs/specifications')
const REPO = 'https://github.com/denvasylenko/dushes/blob/main/openspec/specs'

const yaml = (s) => JSON.stringify(s)   // a JSON string is a valid YAML scalar
const names = readdirSync(SPECS).filter((n) => existsSync(join(SPECS, n, 'spec.md'))).sort()

rmSync(OUT, { recursive: true, force: true })
mkdirSync(OUT, { recursive: true })

const index = []
for (const name of names) {
  const src = readFileSync(join(SPECS, name, 'spec.md'), 'utf8')
  const purpose = (src.match(/## Purpose\n+([\s\S]*?)\n+## /) ?? [])[1]?.trim().replace(/\n+/g, ' ') ?? ''
  const reqs = (src.match(/^### Requirement: /gm) ?? []).length
  const scen = (src.match(/^#### Scenario: /gm) ?? []).length
  let body = src
    .replace(/^# .*\n+/, '')
    .replace(/## Purpose\n+[\s\S]*?\n+(?=## )/, '')
    .replace(/^## Requirements\n+/m, '')
    .replace(/^### Requirement: (.*)$/gm, '## $1')
    .replace(/^#### Scenario: (.*)$/gm, '### Scenario: $1')
  const title = name
  writeFileSync(join(OUT, `${name}.md`), `---
title: ${yaml(title)}
description: ${yaml(purpose || `Behaviour contract for ${name}.`)}
tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 2 }
editUrl: ${yaml(`${REPO.replace('/blob/', '/edit/')}/${name}/spec.md`)}
---

${purpose ? `${purpose}\n\n` : ''}<p class="spec-meta">${reqs} requirements · ${scen} scenarios · <a href="${REPO}/${name}/spec.md">source</a></p>

${body.trim()}
`)
  index.push({ name, purpose, reqs, scen })
}

const total = index.reduce((a, s) => a + s.reqs, 0)
writeFileSync(join(OUT, 'index.mdx'), `---
title: Specifications
description: Behaviour contracts, one per capability, generated from openspec/specs/ on every build.
sidebar: { order: 0, label: All capabilities }
---
import { LinkCard, CardGrid } from '@astrojs/starlight/components';

Every capability of formguide has a contract in [OpenSpec](https://github.com/Fission-AI/OpenSpec) format: requirements use SHALL, each with at least one WHEN / THEN scenario. These pages are generated from \`openspec/specs/\` at build time: **${index.length} capabilities, ${total} requirements**.

<CardGrid>
${index.map((s) => `  <LinkCard title=${yaml(s.name)} description=${yaml(`${s.purpose} (${s.reqs} requirements)`)} href=${yaml(`${s.name}/`)} />`).join('\n')}
</CardGrid>
`)
console.log(`specs: ${index.length} pages`)

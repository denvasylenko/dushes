import { describe, expect, it } from 'vitest'
import { md } from '../src/dom'

describe('md: fenced code blocks', () => {
  it('renders a fenced block with its language and a copy button, escaped', () => {
    const html = md('Use this:\n\n```yaml\nmodel: "openai:gpt-5"\n<tag>\n```\n\nDone.', { copy: 'Copy' })
    expect(html).toContain('<div class="code" part="code" data-lang="yaml">')
    expect(html).toContain('data-copy')
    expect(html).toContain('model: &quot;openai:gpt-5&quot;\n&lt;tag&gt;')
    expect(html).toMatch(/<p>Done\.<\/p>$/)
  })

  it('keeps list markers and blank lines inside code', () => {
    const html = md('```\n- not a list\n\nstill code\n```')
    expect(html).not.toContain('<ul>')
    expect(html).toContain('- not a list\n\nstill code')
  })

  it('shows an unclosed fence (still streaming) as code', () => {
    expect(md('```bash\nformguide serve')).toContain('<code>formguide serve</code>')
  })
})

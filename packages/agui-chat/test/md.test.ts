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

  it('reads a fence with a title, and the blocks after it stay apart', () => {
    const html = md('```yaml title="formguide.yaml"\nmodels: {}\n```\n\nIn Python:\n\n```python\nguide = 1\n```')
    expect(html).toContain('data-lang="formguide.yaml"')
    expect(html).toContain('<code>models: {}</code>')
    expect(html).toContain('<p>In Python:</p>')
    expect(html).toContain('<code>guide = 1</code>')
  })

  it('draws a table: a header, right-aligned columns from the dashes row, inline marks in cells, in its own scrolling box', () => {
    const html = md('**Pick:**\n\n| Model | Torque | Price |\n|---|---:|---:|\n| DD-1840 | 105 Nm | \u20ac219 |\n| **DD-1860** | 130 Nm | \u20ac289 |\n\nDone.')
    const box = document.createElement('div'); box.innerHTML = html
    const table = box.querySelector('.tbl table')!
    expect([...table.querySelectorAll('th')].map((x) => x.textContent)).toEqual(['Model', 'Torque', 'Price'])
    expect([...table.querySelectorAll('tr')].length).toBe(3)                       // the dashes row is not a row
    expect(table.querySelectorAll('td')[1].getAttribute('style')).toBe('text-align:right')
    expect(table.querySelector('td b')!.textContent).toBe('DD-1860')
    expect(box.textContent).not.toContain('|')                                     // no raw pipes left
    expect(box.querySelectorAll('p').length).toBe(2)                               // the text around it stays text
    expect(md('a | b is not a table\nnext line')).not.toContain('<table')         // a pipe alone does not make one
    expect(md('| x | <img src=y onerror=1> |\n|---|---|\n| 1 | 2 |')).not.toContain('<img')   // cells are escaped
  })
})

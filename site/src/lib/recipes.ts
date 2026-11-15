/**
 * A recipe's files and its measured result, read once for the page (components/recipe/*) and for the Markdown
 * exports (lib/markdown.ts), so the page, the .md export and llms-full.txt show the same code and the same number.
 */
import recipes from '../data/recipes.json'
import { ageDays, longDate } from './bench'

const ALL = import.meta.glob('../../../backend/demo/recipes/**/*.{yaml,md,py}', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const ROOT = '../../../backend/demo/recipes/'

export interface RecipeFile { path: string; code: string; lang: 'yaml' | 'md' | 'python' }

/** The recipe folder's files: formguide.yaml first, then other YAML, skills, tool code. */
export function recipeFiles(name: string): RecipeFile[] {
  const prefix = `${ROOT}${name}/`
  const rank = (p: string) => (p === 'formguide.yaml' ? 0 : p.endsWith('.yaml') ? 1 : p.endsWith('.md') ? 2 : 3)
  const files = Object.entries(ALL)
    .filter(([p]) => p.startsWith(prefix) && !p.includes('__pycache__'))
    .map(([p, code]) => {
      const path = p.slice(prefix.length)
      return { path, code: code.replace(/\s+$/, ''), lang: path.endsWith('.py') ? 'python' : path.endsWith('.md') ? 'md' : 'yaml' } as RecipeFile
    })
    .sort((a, b) => rank(a.path) - rank(b.path) || a.path.localeCompare(b.path))
  if (!files.length) throw new Error(`recipe: no files in backend/demo/recipes/${name}/`)
  return files
}

export interface RecipeResult { runs: number; hits: number; scenarios: number; tool: string; model: string; date: string; report: string }
const MODELS: Record<string, string> = { 'claude-haiku-5-5': 'Claude Haiku 5.5', 'claude-sonnet-5-5': 'Claude Sonnet 5.5', 'claude-opus-5-5': 'Claude Opus 5.5' }
export const SCENARIOS_URL = 'https://github.com/denvasylenko/dushes/tree/main/backend/evals/recipes'

export const recipeResult = (name: string): RecipeResult | undefined => (recipes as Record<string, RecipeResult>)[name]
export const modelName = (id: string) => MODELS[id] ?? id
export const recipeAge = (r: RecipeResult) => ageDays(r.date)

/** The files as Markdown fences, each titled with its path. */
export const recipeFilesMarkdown = (name: string) =>
  recipeFiles(name).map((f) => `\`\`\`${f.lang} title="${f.path}"\n${f.code}\n\`\`\``).join('\n\n')

/** "How well it works" as one line, the same figure the page's tile shows. */
export function recipeResultMarkdown(name: string): string {
  const r = recipeResult(name)
  if (!r) return 'Not measured yet.'
  const days = recipeAge(r)
  return `**${r.hits} of ${r.runs}** runs went as expected (${r.scenarios} scenario${r.scenarios === 1 ? '' : 's'}; ${modelName(r.model)}, ${longDate(r.date)}; [scenarios](${SCENARIOS_URL}))`
    + (r.tool ? `. Expected in every run: \`${r.tool}\`.` : '.') + (days > 14 ? ` This measurement is ${days} days old.` : '')
}

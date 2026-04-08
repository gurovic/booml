import MarkdownIt from 'markdown-it'
import markdownKatex from '@/utils/markdownKatex'

export const STATEMENT_COLOR_PRESETS = [
  { label: 'Синий', color: '#2563eb' },
  { label: 'Зелёный', color: '#16a34a' },
  { label: 'Красный', color: '#dc2626' },
  { label: 'Оранжевый', color: '#ea580c' },
  { label: 'Фиолетовый', color: '#9333ea' },
  { label: 'Серый', color: '#475569' },
  { label: 'Чёрный', color: '#111827' },
]

const NAMED_COLORS = {
  red: '#dc2626',
  green: '#16a34a',
  blue: '#2563eb',
  orange: '#ea580c',
  purple: '#9333ea',
  gray: '#475569',
  grey: '#475569',
  black: '#111827',
  white: '#ffffff',
}

const HEX_COLOR_RE = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i
const COLOR_PREFIX = '{color:'

export function normalizeStatementColor(rawColor) {
  if (typeof rawColor !== 'string') return null
  const color = rawColor.trim().toLowerCase()
  if (!color) return null
  if (HEX_COLOR_RE.test(color)) return color
  return NAMED_COLORS[color] || null
}

function statementColor(md) {
  const parseColorInline = (state, silent) => {
    const start = state.pos
    if (!state.src.startsWith(COLOR_PREFIX, start)) return false

    const colorStart = start + COLOR_PREFIX.length
    const colorSeparator = state.src.indexOf('|', colorStart)
    if (colorSeparator === -1) return false

    const closePos = state.src.indexOf('}', colorSeparator + 1)
    if (closePos === -1) return false

    const color = normalizeStatementColor(state.src.slice(colorStart, colorSeparator))
    const content = state.src.slice(colorSeparator + 1, closePos)

    if (!color || !content.trim()) return false

    if (!silent) {
      const token = state.push('statement_color_inline', '', 0)
      token.meta = { color }
      token.content = content
    }

    state.pos = closePos + 1
    return true
  }

  md.inline.ruler.before('escape', 'statement_color_inline', parseColorInline)

  md.renderer.rules.statement_color_inline = (tokens, idx, options, env, self) => {
    const token = tokens[idx]
    const color = normalizeStatementColor(token?.meta?.color || '')
    if (!color) return md.utils.escapeHtml(token?.content || '')

    const children = []
    md.inline.parse(token.content || '', md, env, children)
    const innerHtml = self.render(children, options, env)

    return `<span class="statement-color" style="color:${color};">${innerHtml}</span>`
  }
}

const markdown = new MarkdownIt({
  html: false,
  breaks: false,
  linkify: true,
})
  .use(markdownKatex, { throwOnError: false })
  .use(statementColor)

function stripLeadingH1(statement) {
  if (typeof statement !== 'string' || !statement) return ''

  const lines = statement.replace(/\r\n?/g, '\n').split('\n')
  let firstContentLine = 0

  while (firstContentLine < lines.length && !lines[firstContentLine].trim()) {
    firstContentLine += 1
  }

  if (firstContentLine >= lines.length) return statement
  if (!/^#\s+/.test(lines[firstContentLine])) return statement

  lines.splice(firstContentLine, 1)
  while (firstContentLine < lines.length && !lines[firstContentLine].trim()) {
    lines.splice(firstContentLine, 1)
  }

  return lines.join('\n')
}

export function renderProblemStatement(statement) {
  return markdown.render(stripLeadingH1(statement || ''))
}

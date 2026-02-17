import katex from 'katex'

function isEscaped(text, pos) {
  let slashCount = 0
  for (let idx = pos - 1; idx >= 0 && text[idx] === '\\'; idx -= 1) {
    slashCount += 1
  }
  return slashCount % 2 === 1
}

function findUnescapedDelimiter(text, delimiter, fromIndex = 0) {
  let idx = fromIndex
  while ((idx = text.indexOf(delimiter, idx)) !== -1) {
    if (!isEscaped(text, idx)) return idx
    idx += delimiter.length
  }
  return -1
}

function replaceDelimitedMath(text, open, close, formatContent) {
  if (!text || !text.includes(open)) return text

  let cursor = 0
  let output = ''

  while (cursor < text.length) {
    const openPos = findUnescapedDelimiter(text, open, cursor)
    if (openPos === -1) {
      output += text.slice(cursor)
      break
    }

    const contentStart = openPos + open.length
    const closePos = findUnescapedDelimiter(text, close, contentStart)
    if (closePos === -1) {
      output += text.slice(cursor)
      break
    }

    const content = text.slice(contentStart, closePos)
    const replacement = formatContent(content)

    output += text.slice(cursor, openPos)
    output += replacement == null ? text.slice(openPos, closePos + close.length) : replacement
    cursor = closePos + close.length
  }

  return output
}

function normalizeMathDelimiters(text) {
  if (typeof text !== 'string' || !text) return text

  let normalized = text

  normalized = replaceDelimitedMath(normalized, '\\[', '\\]', content => {
    const trimmed = content.trim()
    return trimmed ? `\n$$\n${trimmed}\n$$\n` : null
  })

  normalized = replaceDelimitedMath(normalized, '\\(', '\\)', content => {
    const trimmed = content.trim()
    return trimmed ? `$${trimmed}$` : null
  })

  return normalized
}

function isValidDelim(state, pos) {
  const max = state.posMax
  const prevChar = pos > 0 ? state.src.charCodeAt(pos - 1) : -1
  const nextChar = pos + 1 <= max ? state.src.charCodeAt(pos + 1) : -1

  let canOpen = true
  let canClose = true

  if (
    prevChar === 0x20 ||
    prevChar === 0x09 ||
    (nextChar >= 0x30 && nextChar <= 0x39)
  ) {
    canClose = false
  }
  if (nextChar === 0x20 || nextChar === 0x09) {
    canOpen = false
  }

  return { canOpen, canClose }
}

function mathInline(state, silent) {
  if (state.src[state.pos] !== '$') return false

  const open = isValidDelim(state, state.pos)
  if (!open.canOpen) {
    if (!silent) state.pending += '$'
    state.pos += 1
    return true
  }

  const start = state.pos + 1
  let match = start

  while ((match = state.src.indexOf('$', match)) !== -1) {
    let pos = match - 1
    while (state.src[pos] === '\\') pos -= 1
    if ((match - pos) % 2 === 1) break
    match += 1
  }

  if (match === -1) {
    if (!silent) state.pending += '$'
    state.pos = start
    return true
  }

  if (match - start === 0) {
    if (!silent) state.pending += '$$'
    state.pos = start + 1
    return true
  }

  const close = isValidDelim(state, match)
  if (!close.canClose) {
    if (!silent) state.pending += '$'
    state.pos = start
    return true
  }

  if (!silent) {
    const token = state.push('math_inline', 'math', 0)
    token.markup = '$'
    token.content = state.src.slice(start, match)
  }

  state.pos = match + 1
  return true
}

function mathBlock(state, start, end, silent) {
  let pos = state.bMarks[start] + state.tShift[start]
  let max = state.eMarks[start]
  if (pos + 2 > max) return false
  if (state.src.slice(pos, pos + 2) !== '$$') return false

  pos += 2
  let firstLine = state.src.slice(pos, max)
  let lastLine = ''
  let next = start
  let lastPos = 0
  let found = false

  if (silent) return true

  if (firstLine.trim().slice(-2) === '$$') {
    firstLine = firstLine.trim().slice(0, -2)
    found = true
  }

  while (!found) {
    next += 1
    if (next >= end) break

    pos = state.bMarks[next] + state.tShift[next]
    max = state.eMarks[next]

    if (pos < max && state.tShift[next] < state.blkIndent) break

    if (state.src.slice(pos, max).trim().slice(-2) === '$$') {
      lastPos = state.src.slice(0, max).lastIndexOf('$$')
      lastLine = state.src.slice(pos, lastPos)
      found = true
    }
  }

  state.line = next + 1

  const token = state.push('math_block', 'math', 0)
  token.block = true
  token.content =
    (firstLine && firstLine.trim() ? `${firstLine}\n` : '') +
    state.getLines(start + 1, next, state.tShift[start], true) +
    (lastLine && lastLine.trim() ? lastLine : '')
  token.map = [start, state.line]
  token.markup = '$$'
  return true
}

function renderMath(latex, displayMode, options) {
  try {
    return katex.renderToString(latex, {
      ...options,
      displayMode,
      output: 'htmlAndMathml',
      strict: 'ignore',
      trust: false,
    })
  } catch (error) {
    if (options.throwOnError) {
      console.error(error)
    }
    return latex
  }
}

export default function markdownKatex(md, options = {}) {
  md.core.ruler.before('normalize', 'normalize_math_delimiters', state => {
    state.src = normalizeMathDelimiters(state.src)
  })

  md.inline.ruler.after('escape', 'math_inline', mathInline)
  md.block.ruler.after('blockquote', 'math_block', mathBlock, {
    alt: ['paragraph', 'reference', 'blockquote', 'list'],
  })

  md.renderer.rules.math_inline = (tokens, idx) =>
    renderMath(tokens[idx].content, false, options)

  md.renderer.rules.math_block = (tokens, idx) => {
    const html = renderMath(tokens[idx].content, true, options)
    return `<div class="math-block">${html}</div>\n`
  }

  const defaultLinkOpen =
    md.renderer.rules.link_open ||
    ((tokens, idx, renderOptions, env, self) => self.renderToken(tokens, idx, renderOptions))

  md.renderer.rules.link_open = (tokens, idx, renderOptions, env, self) => {
    const token = tokens[idx]
    const hrefIndex = token.attrIndex('href')
    const href = hrefIndex >= 0 ? token.attrs[hrefIndex][1] : ''

    if (/^https?:\/\//i.test(href)) {
      token.attrSet('target', '_blank')
      token.attrSet('rel', 'noopener noreferrer')
    }

    return defaultLinkOpen(tokens, idx, renderOptions, env, self)
  }
}

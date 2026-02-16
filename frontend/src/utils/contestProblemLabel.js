export function toContestProblemLabel(index) {
  if (!Number.isInteger(index) || index < 0) {
    throw new Error('index must be a non-negative integer')
  }

  let current = index
  const letters = []

  let done = false
  while (!done) {
    const remainder = current % 26
    letters.push(String.fromCharCode(65 + remainder))
    current = Math.floor(current / 26)
    if (current === 0) {
      done = true
    } else {
      current -= 1
    }
  }

  return letters.reverse().join('')
}

export function normalizeContestProblemLabel(value) {
  const normalized = String(value ?? '').trim().toUpperCase()
  return /^[A-Z]+$/.test(normalized) ? normalized : ''
}

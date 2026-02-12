// Move an item inside an array and return a new array.
// `toIndex` is the desired index in the resulting array (0-based).
export function arrayMove(list, fromIndex, toIndex) {
  const arr = Array.isArray(list) ? [...list] : []
  const from = Number(fromIndex)
  const to = Number(toIndex)

  if (!Number.isInteger(from) || !Number.isInteger(to)) return arr
  if (from < 0 || from >= arr.length) return arr

  const clampedTo = Math.max(0, Math.min(to, arr.length - 1))
  if (from === clampedTo) return arr

  const [item] = arr.splice(from, 1)
  arr.splice(clampedTo, 0, item)
  return arr
}


const TZ_MOSCOW = 'Europe/Moscow'

const _fmtDateTimeMsk = new Intl.DateTimeFormat('ru-RU', {
  timeZone: TZ_MOSCOW,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
})

const _fmtTimeMsk = new Intl.DateTimeFormat('ru-RU', {
  timeZone: TZ_MOSCOW,
  hour: '2-digit',
  minute: '2-digit',
})

export function formatDateTimeMsk(isoString) {
  if (!isoString) return '-'
  const d = new Date(isoString)
  if (Number.isNaN(d.getTime())) return String(isoString)
  return _fmtDateTimeMsk.format(d)
}

export function formatTimeMsk(isoString) {
  if (!isoString) return '-'
  const d = new Date(isoString)
  if (Number.isNaN(d.getTime())) return String(isoString)
  return _fmtTimeMsk.format(d)
}

export function toTimestamp(isoString) {
  if (!isoString) return null
  const d = new Date(isoString)
  if (Number.isNaN(d.getTime())) return null
  return d.getTime()
}

const pad2 = (value) => String(Math.max(0, Number(value) || 0)).padStart(2, '0')

export function formatCountdown(totalSeconds) {
  const normalized = Math.max(0, Number.isFinite(totalSeconds) ? Math.floor(totalSeconds) : 0)
  const days = Math.floor(normalized / 86400)
  const hours = Math.floor((normalized % 86400) / 3600)
  const minutes = Math.floor((normalized % 3600) / 60)
  const seconds = normalized % 60

  if (days > 0) {
    return `${days}д ${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)}`
  }
  return `${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)}`
}

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


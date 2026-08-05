import type { ActivityEntry, Dataset, DateRange, RangeMode } from './types'

const day = (date: Date) => date.toISOString().slice(0, 10)
const parse = (iso: string) => new Date(`${iso}T12:00:00`)

export function formatMoney(value: number, digits = 0) {
  return new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: digits, minimumFractionDigits: digits }).format(value)
}

export function rangeFor(mode: RangeMode, anchor: string, custom?: { from: string; to: string }): DateRange {
  const current = parse(anchor)
  if (mode === 'all') return { from: '2000-01-01', to: '2100-12-31', label: 'All activity' }
  if (mode === 'custom') return { from: custom?.from || anchor, to: custom?.to || anchor, label: `${custom?.from || anchor} to ${custom?.to || anchor}` }
  let from = new Date(current), to = new Date(current)
  if (mode === 'week') { const shift = (current.getDay() + 6) % 7; from.setDate(current.getDate() - shift); to = new Date(from); to.setDate(from.getDate() + 6) }
  if (mode === 'month') { from = new Date(current.getFullYear(), current.getMonth(), 1); to = new Date(current.getFullYear(), current.getMonth() + 1, 0) }
  if (mode === 'year') { from = new Date(current.getFullYear(), 0, 1); to = new Date(current.getFullYear(), 11, 31) }
  const label = mode === 'day' ? current.toLocaleDateString('en-CA', { weekday: 'short', month: 'long', day: 'numeric', year: 'numeric' }) : mode === 'week' ? `${from.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' })} – ${to.toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })}` : mode === 'month' ? current.toLocaleDateString('en-CA', { month: 'long', year: 'numeric' }) : String(current.getFullYear())
  return { from: day(from), to: day(to), label }
}

export function shiftAnchor(mode: RangeMode, anchor: string, direction: number) {
  const next = parse(anchor)
  if (mode === 'day') next.setDate(next.getDate() + direction)
  else if (mode === 'week') next.setDate(next.getDate() + 7 * direction)
  else if (mode === 'month') next.setMonth(next.getMonth() + direction)
  else if (mode === 'year') next.setFullYear(next.getFullYear() + direction)
  return day(next)
}

export function activityFor(data: Dataset, range: DateRange): ActivityEntry[] {
  const inside = (date: string) => date >= range.from && date <= range.to
  const expenses = data.transactions.filter(row => inside(row.date)).map((row, index) => ({ id: `imported-${index}-${row.date}-${row.merchant}`, source: 'imported' as const, entry_type: 'expense' as const, date: row.date, amount: Number(row.amount), name: row.merchant, category: row.category || 'Other', account: row.account || 'Card' }))
  const income = data.chequing.filter(row => row.is_income && inside(row.date)).map((row, index) => ({ id: `chequing-${index}-${row.date}-${row.desc}`, source: 'chequing' as const, entry_type: 'income' as const, date: row.date, amount: Math.abs(Number(row.amount)), name: row.desc || 'Deposit', category: row.dep_type === 'interest' ? 'Interest' : 'Deposits', account: row.account || 'Chequing' }))
  const manual = data.manual.filter(row => inside(row.date)).map(row => ({ id: row.id, source: 'manual' as const, entry_type: row.entry_type, date: row.date, amount: Number(row.amount), name: row.name, category: row.category, account: row.account, note: row.note }))
  return [...expenses, ...income, ...manual].sort((a, b) => b.date.localeCompare(a.date) || b.amount - a.amount)
}

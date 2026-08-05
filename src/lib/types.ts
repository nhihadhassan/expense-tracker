export type EntryType = 'expense' | 'income'

export type Transaction = {
  date: string
  merchant: string
  raw?: string
  amount: number
  category: string
  account?: string
  account_type?: string
}

export type ChequingEntry = {
  date: string
  desc: string
  amount: number
  account?: string
  dep_type?: string
  is_income?: boolean
}

export type ManualEntry = {
  id: string
  entry_type: EntryType
  date: string
  amount: number
  name: string
  category: string
  account: string
  note: string
  currency?: string
  created_at: string
  updated_at: string
}

export type ActivityEntry = {
  id: string
  source: 'imported' | 'manual' | 'chequing'
  entry_type: EntryType
  date: string
  amount: number
  name: string
  category: string
  account: string
  note?: string
}

export type Dataset = {
  transactions: Transaction[]
  chequing: ChequingEntry[]
  manual: ManualEntry[]
}

export type RangeMode = 'day' | 'week' | 'month' | 'year' | 'all' | 'custom'

export type DateRange = { from: string; to: string; label: string }

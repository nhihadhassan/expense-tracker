import { describe, expect, it } from 'vitest'
import { activityFor, rangeFor } from './finance'
import type { Dataset } from './types'

const fixture: Dataset = {
  transactions: [
    { date: '2026-08-03', merchant: 'Market', amount: 41.25, category: 'Food', account: 'Card' },
    { date: '2026-08-04', merchant: 'Train', amount: 12, category: 'Transport', account: 'Card' },
  ],
  chequing: [{ date: '2026-08-01', desc: 'Payroll', amount: 2100, is_income: true, account: 'Chequing' }],
  manual: [{ id: 'income', entry_type: 'income', date: '2026-08-02', amount: 100, name: 'Refund', category: 'Refund', account: 'Manual', note: '', created_at: '', updated_at: '' }],
}

describe('cash-flow aggregation', () => {
  it('includes imported chequing and manual income without making card charges income', () => {
    const rows = activityFor(fixture, rangeFor('month', '2026-08-05'))
    expect(rows.filter(row => row.entry_type === 'income').reduce((sum, row) => sum + row.amount, 0)).toBe(2200)
    expect(rows.filter(row => row.entry_type === 'expense').reduce((sum, row) => sum + row.amount, 0)).toBe(53.25)
  })

  it('uses calendar week boundaries', () => {
    const range = rangeFor('week', '2026-08-05')
    expect(range.from).toBe('2026-08-03')
    expect(range.to).toBe('2026-08-09')
  })
})

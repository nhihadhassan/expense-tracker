import { createClient } from '@supabase/supabase-js'
import type { Dataset, ManualEntry } from './types'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://zgafubhzhxikuknihmnu.supabase.co'
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || 'sb_publishable_HMICK42AzL2W_Tpb6VutDQ_HawfnbWM'
export const supabase = createClient(supabaseUrl, supabaseKey)

async function localData(): Promise<Dataset> {
  const [transactions, chequing, manual] = await Promise.all([
    fetch('/api/transactions').then(r => r.ok ? r.json() : Promise.reject(r)),
    fetch('/api/chequing').then(r => r.ok ? r.json() : []),
    fetch('/api/manual-entries').then(r => r.ok ? r.json() : []),
  ])
  return { transactions, chequing, manual }
}

export async function loadData(): Promise<Dataset> {
  try { return await localData() } catch {
    const [transactions, chequing, manual] = await Promise.all([
      supabase.from('exp_transactions').select('date,merchant,raw,amount,category,account,account_type').order('date'),
      supabase.from('exp_chequing').select('date,descr,amount,account,dep_type,is_income').order('date'),
      supabase.from('exp_manual_entries').select('id,entry_type,date,amount,name,category,account,note,currency,created_at,updated_at').order('date', { ascending: false }),
    ])
    if (transactions.error || chequing.error || manual.error) throw transactions.error || chequing.error || manual.error
    return { transactions: transactions.data || [], chequing: (chequing.data || []).map(row => ({ ...row, desc: row.descr })), manual: manual.data || [] }
  }
}

export async function saveEntry(entry: ManualEntry) {
  try {
    const method = entry.created_at === entry.updated_at ? 'POST' : 'PATCH'
    const url = method === 'POST' ? '/api/manual-entries' : `/api/manual-entries/${encodeURIComponent(entry.id)}`
    const response = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(entry) })
    if (!response.ok) throw new Error((await response.json()).error || 'Could not save entry')
    return await response.json() as ManualEntry
  } catch {
    const { data, error } = await supabase.from('exp_manual_entries').upsert(entry).select().single()
    if (error) throw error
    return data as ManualEntry
  }
}

export async function removeEntry(id: string) {
  try {
    const response = await fetch(`/api/manual-entries/${encodeURIComponent(id)}`, { method: 'DELETE' })
    if (!response.ok) throw new Error('Could not delete entry')
  } catch {
    const { error } = await supabase.from('exp_manual_entries').delete().eq('id', id)
    if (error) throw error
  }
}

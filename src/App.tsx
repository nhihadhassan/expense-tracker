import { useEffect, useMemo, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Bank, CalendarBlank, ChartDonut, ChartPieSlice, CheckCircle, CurrencyDollar, DotsThree, ForkKnife, ListBullets, Minus, PencilSimple, Plus, Receipt, Target, TrendDown, TrendUp, UploadSimple, Wallet } from '@phosphor-icons/react'
import { Pie, PieChart, ResponsiveContainer, Cell, Tooltip } from 'recharts'
import { EXPENSE_CATEGORIES, INCOME_CATEGORIES, categoryColors } from './lib/constants'
import { activityFor, formatMoney, rangeFor, shiftAnchor } from './lib/finance'
import { loadData, removeEntry, saveEntry, supabase } from './lib/client'
import type { ActivityEntry, Dataset, EntryType, ManualEntry, RangeMode } from './lib/types'

const modes: RangeMode[] = ['day', 'week', 'month', 'year', 'all', 'custom']
const today = new Date().toISOString().slice(0, 10)

function useLedger(enabled: boolean) {
  const [data, setData] = useState<Dataset>({ transactions: [], chequing: [], manual: [] })
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState('')
  const refresh = async () => { setStatus('loading'); try { setData(await loadData()); setStatus('ready') } catch (issue) { setError(issue instanceof Error ? issue.message : 'Could not load financial data.'); setStatus('error') } }
  useEffect(() => { if (enabled) void refresh() }, [enabled])
  return { data, setData, status, error, refresh }
}

function App() {
  const auth = useHostedAuth()
  const ledger = useLedger(auth === 'signed-in')
  const [composer, setComposer] = useState<{ type: EntryType; entry?: ManualEntry } | null>(null)
  if (auth === 'checking') return <div className="auth-shell"><div className="auth-card">Checking your secure workspace…</div></div>
  if (auth === 'signed-out') return <Login />
  return <AppShell onAdd={type => setComposer({ type })}>
    <Routes>
      <Route path="/" element={<Overview {...ledger} />} />
      <Route path="/cash-flow" element={<CashFlow {...ledger} onAdd={(type, entry) => setComposer({ type, entry })} />} />
      <Route path="/activity" element={<Activity {...ledger} onEdit={entry => setComposer({ type: entry.entry_type, entry })} />} />
      <Route path="/plans" element={<Plans data={ledger.data} />} />
      <Route path="/more" element={<More />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    {composer && <EntryComposer type={composer.type} entry={composer.entry} onClose={() => setComposer(null)} onSaved={entry => { ledger.setData(current => ({ ...current, manual: current.manual.some(row => row.id === entry.id) ? current.manual.map(row => row.id === entry.id ? entry : row) : [entry, ...current.manual] })); setComposer(null) }} onDeleted={id => { ledger.setData(current => ({ ...current, manual: current.manual.filter(row => row.id !== id) })); setComposer(null) }} />}
  </AppShell>
}

function useHostedAuth() {
  const local = window.location.hostname === 'localhost' && window.location.port === '8765'
  const [state, setState] = useState<'checking' | 'signed-in' | 'signed-out'>(local ? 'signed-in' : 'checking')
  useEffect(() => {
    if (local) return
    void supabase.auth.getSession().then(({ data }) => setState(data.session ? 'signed-in' : 'signed-out'))
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => setState(session ? 'signed-in' : 'signed-out'))
    return () => listener.subscription.unsubscribe()
  }, [local])
  return state
}

function Login() {
  const [email, setEmail] = useState(''); const [sent, setSent] = useState(false); const [error, setError] = useState('')
  const submit = async (event: React.FormEvent) => { event.preventDefault(); setError(''); const { error: issue } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.origin } }); if (issue) setError(issue.message); else setSent(true) }
  return <main className="auth-shell"><form className="auth-card" onSubmit={submit}><span className="brand-mark"><Wallet size={22} weight="duotone" /></span><p className="eyebrow">Private workspace</p><h1>Open your ledger.</h1>{sent ? <p className="auth-copy">Check your inbox for a secure sign-in link.</p> : <><label>Email address<input type="email" required value={email} onChange={event => setEmail(event.target.value)} placeholder="you@example.com" /></label>{error && <p className="form-error">{error}</p>}<button className="save-button income" type="submit">Send secure link</button></>}</form></main>
}

function AppShell({ children, onAdd }: { children: React.ReactNode; onAdd: (type: EntryType) => void }) {
  const location = useLocation()
  const nav = [{ to: '/', label: 'Overview', icon: ChartPieSlice }, { to: '/activity', label: 'Activity', icon: ListBullets }, { to: '/plans', label: 'Plans', icon: Target }, { to: '/more', label: 'More', icon: DotsThree }]
  return <div className="app-shell"><aside className="sidebar"><div className="brand"><span className="brand-mark"><Wallet size={22} weight="duotone" /></span><span>Ledger</span></div><p className="side-kicker">Personal finance</p><nav>{nav.map(item => <NavItem key={item.to} item={item} />)}<NavItem item={{ to: '/cash-flow', label: 'Cash flow', icon: ChartDonut }} /></nav><div className="side-foot"><button onClick={() => onAdd('expense')} className="quick expense"><Minus size={18} /> Expense</button><button onClick={() => onAdd('income')} className="quick income"><Plus size={18} /> Income</button></div></aside><main className="main-content">{children}</main><div className="money-dock"><button onClick={() => onAdd('expense')} className="money-action expense"><Minus size={22} weight="bold" /><span>Add expense</span></button><button onClick={() => onAdd('income')} className="money-action income"><Plus size={22} weight="bold" /><span>Add income</span></button></div><nav className="bottom-nav">{nav.map(item => <NavItem key={item.to} item={item} compact />)}</nav>{location.pathname === '/cash-flow' && <div className="cash-route-indicator" aria-hidden="true" />}</div>
}

function NavItem({ item, compact = false }: { item: { to: string; label: string; icon: typeof ChartPieSlice }; compact?: boolean }) { const Icon = item.icon; return <NavLink end={item.to === '/'} to={item.to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}${compact ? ' compact' : ''}`}><Icon size={compact ? 21 : 20} weight="duotone" /><span>{item.label}</span></NavLink> }

function Screen({ title, eyebrow, children, action }: { title: string; eyebrow: string; children: React.ReactNode; action?: React.ReactNode }) { return <section className="screen"><header className="screen-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1></div>{action}</header>{children}</section> }

function Overview({ data, status, error }: ReturnType<typeof useLedger>) {
  const latest = useMemo(() => [...data.transactions.map(row => row.date), ...data.manual.map(row => row.date), ...data.chequing.map(row => row.date)].sort().at(-1) || today, [data])
  const range = rangeFor('month', latest); const entries = activityFor(data, range); const inTotal = entries.filter(row => row.entry_type === 'income').reduce((sum, row) => sum + row.amount, 0); const outTotal = entries.filter(row => row.entry_type === 'expense').reduce((sum, row) => sum + row.amount, 0); const net = inTotal - outTotal
  return <Screen eyebrow="Overview" title="Your money, clearly." action={<NavLink className="quiet-action" to="/cash-flow">Open cash flow <ArrowRight size={18} /></NavLink>}><LoadState status={status} error={error}><div className="overview-period"><CalendarBlank size={18} /><span>{range.label}</span></div><section className="hero-ledger"><div><span>Cash in</span><strong className="income-value">{formatMoney(inTotal)}</strong></div><div><span>Cash out</span><strong className="expense-value">{formatMoney(outTotal)}</strong></div><div className="net-row"><span>Net</span><strong className={net >= 0 ? 'income-value' : 'expense-value'}>{net < 0 ? '−' : ''}{formatMoney(Math.abs(net))}</strong></div></section><section className="overview-grid"><NavLink to="/cash-flow" className="overview-link"><ChartDonut size={26} weight="duotone" /><span><b>Explore categories</b><small>See every dollar behind this period</small></span><ArrowRight size={18} /></NavLink><section className="recent"><div className="section-title"><h2>Recent activity</h2><NavLink to="/activity">View all</NavLink></div>{entries.slice(0, 5).map(row => <ActivityRow key={row.id} row={row} />)}{entries.length === 0 && <Empty message="Import a statement or add your first entry to begin." />}</section></section></LoadState></Screen>
}

function CashFlow({ data, status, error, onAdd }: ReturnType<typeof useLedger> & { onAdd: (type: EntryType, entry?: ManualEntry) => void }) {
  const [mode, setMode] = useState<RangeMode>('month'); const [anchor, setAnchor] = useState(today); const [custom, setCustom] = useState({ from: today, to: today }); const [selected, setSelected] = useState<string | null>(null)
  useEffect(() => {
    const dates = [...data.transactions.map(row => row.date), ...data.chequing.map(row => row.date), ...data.manual.map(row => row.date)].filter(Boolean).sort()
    if (!dates.length) return
    const currentMonth = today.slice(0, 7)
    const currentHasData = dates.some(date => date.startsWith(currentMonth))
    if (!currentHasData) setAnchor(dates.at(-1)!)
  }, [data])
  const range = rangeFor(mode, anchor, custom); const entries = activityFor(data, range); const expenses = entries.filter(row => row.entry_type === 'expense'); const income = entries.filter(row => row.entry_type === 'income'); const cashOut = expenses.reduce((sum, row) => sum + row.amount, 0); const cashIn = income.reduce((sum, row) => sum + row.amount, 0); const categories = Object.entries(expenses.reduce<Record<string, { amount: number; count: number; rows: ActivityEntry[] }>>((all, row) => { const item = all[row.category] || { amount: 0, count: 0, rows: [] }; item.amount += row.amount; item.count += 1; item.rows.push(row); all[row.category] = item; return all }, {})).sort(([, a], [, b]) => b.amount - a.amount)
  const selectedData = selected ? categories.find(([name]) => name === selected)?.[1] : undefined
  return <Screen eyebrow="Cash flow" title="Where your money went." action={<button className="quiet-action" onClick={() => onAdd('expense')}><Plus size={18} /> Add entry</button>}><LoadState status={status} error={error}><section className="period-control"><div className="mode-row">{modes.map(item => <button key={item} className={mode === item ? 'selected' : ''} onClick={() => { setMode(item); setSelected(null) }}>{item === 'all' ? 'All' : item}</button>)}</div>{mode === 'custom' ? <div className="custom-dates"><label>From<input type="date" value={custom.from} onChange={event => setCustom(value => ({ ...value, from: event.target.value }))} /></label><label>To<input type="date" value={custom.to} onChange={event => setCustom(value => ({ ...value, to: event.target.value }))} /></label></div> : <div className="range-nav"><button aria-label="Previous period" disabled={mode === 'all'} onClick={() => setAnchor(shiftAnchor(mode, anchor, -1))}><ArrowLeft size={18} /></button><span>{range.label}</span><button aria-label="Next period" disabled={mode === 'all'} onClick={() => setAnchor(shiftAnchor(mode, anchor, 1))}><ArrowRight size={18} /></button></div>}</section><section className="cashflow-grid"><div className="donut-panel"><div className="donut-wrap"><ResponsiveContainer><PieChart><Pie data={categories.map(([name, value]) => ({ name, value: value.amount }))} dataKey="value" nameKey="name" innerRadius="64%" outerRadius="92%" paddingAngle={2} stroke="none" onClick={segment => setSelected(typeof segment.name === 'string' ? segment.name : null)}>{categories.map(([name]) => <Cell key={name} fill={categoryColors[name] || '#9aa8b8'} />)}</Pie><Tooltip formatter={value => formatMoney(Number(value), 2)} /></PieChart></ResponsiveContainer><div className="donut-center"><span>Cash in <b className="income-value">{formatMoney(cashIn)}</b></span><span>Cash out <b className="expense-value">{formatMoney(cashOut)}</b></span><hr /><span>Net <b className={cashIn - cashOut >= 0 ? 'income-value' : 'expense-value'}>{cashIn - cashOut < 0 ? '−' : ''}{formatMoney(Math.abs(cashIn - cashOut))}</b></span></div></div><p className="chart-hint">Tap a category to see its share of income.</p></div><div className="category-focus">{selectedData ? <><p className="eyebrow">Selected category</p><h2>{selected}</h2><strong>{formatMoney(selectedData.amount, 2)}</strong><p>{(selectedData.amount / (cashOut || 1) * 100).toFixed(1)}% of expenses · {selectedData.count} transaction{selectedData.count === 1 ? '' : 's'}</p><p>{cashIn ? `${(selectedData.amount / cashIn * 100).toFixed(1)}% of recorded income` : 'No income recorded'}</p></> : <><ChartPieSlice size={32} weight="duotone" /><h2>Category detail</h2><p>Select a segment or row to inspect the underlying transactions.</p></>}</div></section><section className="category-list">{categories.map(([name, value]) => <details key={name} open={selected === name} onToggle={event => { if ((event.target as HTMLDetailsElement).open) setSelected(name) }}><summary><span className="category-dot" style={{ backgroundColor: categoryColors[name] || '#9aa8b8' }} /><span><b>{name}</b><small>{(value.amount / (cashOut || 1) * 100).toFixed(0)}% of expenses · {value.count} transaction{value.count === 1 ? '' : 's'}</small></span><strong>{formatMoney(value.amount, 2)}</strong></summary><div className="detail-transactions">{value.rows.map(row => <ActivityRow key={row.id} row={row} />)}</div></details>)}{categories.length === 0 && <Empty message="There are no expenses in this period." />}</section></LoadState></Screen>
}

function Activity({ data, status, error, onEdit }: ReturnType<typeof useLedger> & { onEdit: (entry: ManualEntry) => void }) {
  const entries = activityFor(data, rangeFor('all', today)); const [query, setQuery] = useState('')
  const visible = entries.filter(row => `${row.name} ${row.category} ${row.account}`.toLowerCase().includes(query.toLowerCase()))
  return <Screen eyebrow="Activity" title="Every entry, traceable." action={<label className="search"><Receipt size={17} /><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search activity" /></label>}><LoadState status={status} error={error}><section className="activity-list">{visible.map(row => <ActivityRow key={row.id} row={row} onClick={row.source === 'manual' ? () => { const entry = data.manual.find(item => item.id === row.id); if (entry) onEdit(entry) } : undefined} />)}{visible.length === 0 && <Empty message="No entries match this search." />}</section></LoadState></Screen>
}

function Plans({ data }: { data: Dataset }) {
  const expenses = data.transactions.filter(row => row.amount > 0)
  const spentByCategory = expenses.reduce<Record<string, number>>((all, row) => { all[row.category] = (all[row.category] || 0) + row.amount; return all }, {})
  const defaults = { Food: 800, Subscriptions: 150, Transport: 300, Entertainment: 450, Shopping: 650 }
  const savedBudgets = readJson<Record<string, number>>('expense-budgets-v1', {})
  const budgets = Object.entries({ ...defaults, ...savedBudgets }).filter(([, limit]) => Number(limit) > 0).map(([category, limit]) => ({ category, limit: Number(limit), spent: spentByCategory[category] || 0 })).sort((a, b) => b.spent - a.spent)
  const savedGoals = readJson<Array<{ name: string; target: number; saved: number }>>('expense-goals-v1', [])
  const goals = savedGoals.length ? savedGoals : [{ name: 'Emergency Fund', target: 20000, saved: 15000 }, { name: 'Japan Trip', target: 5000, saved: 1500 }, { name: 'New Car Downpayment', target: 8000, saved: 800 }]
  const totalSpent = budgets.reduce((sum, item) => sum + item.spent, 0)
  const totalBudget = budgets.reduce((sum, item) => sum + item.limit, 0)
  const health = totalBudget ? Math.min(100, totalSpent / totalBudget * 100) : 0
  return <Screen eyebrow="Plans" title="Budgets & Goals" action={<button className="quiet-action plans-month"><CalendarBlank size={18} /> {new Date().toLocaleDateString('en-CA', { month: 'long', year: 'numeric' })}</button>}>
    <p className="plans-intro">Track spending and progress towards your financial targets.</p>
    <section className="plans-hero-grid">
      <article className="budget-health"><div className="plans-card-heading"><h2>Budget Health</h2><CheckCircle size={24} weight="duotone" /></div><div className="health-total"><span>Total spent</span><strong>{formatMoney(totalSpent)}</strong><small>of {formatMoney(totalBudget)} budget</small></div><div className="health-track"><i style={{ width: `${health}%` }} /></div><div className="health-meta"><span>{Math.max(0, Math.round(100 - health))}% remaining</span><b className={health <= 85 ? 'income-value' : 'expense-value'}>{health <= 85 ? 'On Track' : 'Review'}</b></div></article>
      <article className="active-budgets"><div className="plans-card-heading"><h2>Active Budgets</h2><a className="plans-add" href="/legacy.html#tab-budgets">+ New budget</a></div><div className="budget-card-grid">{budgets.slice(0, 3).map(item => <BudgetCard key={item.category} {...item} />)}<a className="create-budget" href="/legacy.html#tab-budgets"><Plus size={22} /><b>Create new</b></a></div></article>
    </section>
    <section className="savings-panel"><div className="plans-card-heading"><h2>Savings Goals</h2><div className="goal-arrows"><button aria-label="Previous goals">‹</button><button aria-label="Next goals">›</button></div></div><div className="goal-grid">{goals.slice(0, 3).map(goal => <GoalCard key={goal.name} {...goal} />)}</div></section>
    <section className="plans-analysis"><div className="section-title"><div><p className="eyebrow">Deeper analysis</p><h2>Keep the detail below the plan.</h2></div><a href="/legacy.html#tab-analytics" className="quiet-action">Open analytics <ArrowRight size={17} /></a></div><div className="analysis-links"><a href="/legacy.html#tab-analytics">Monthly variance <small>Compare actual spend with targets</small><ArrowRight size={17} /></a><a href="/legacy.html#tab-analytics">Cash-flow projection <small>See the next six months</small><ArrowRight size={17} /></a><a href="/legacy.html#tab-analytics">Spending trends <small>Find categories moving fastest</small><ArrowRight size={17} /></a></div></section>
  </Screen>
}

function BudgetCard({ category, limit, spent }: { category: string; limit: number; spent: number }) { const pct = Math.min(100, limit ? spent / limit * 100 : 0); const over = spent > limit; return <article className="budget-card"><span className="budget-icon"><Wallet size={21} weight="duotone" /></span><div className="budget-copy"><b>{category}</b><small>{formatMoney(limit, 0)} limit</small></div><div className="budget-amount"><strong>{formatMoney(spent, 0)}</strong><small className={over ? 'expense-value' : 'income-value'}>{over ? 'over' : 'spent'}</small></div><div className="budget-progress"><i className={over ? 'over' : ''} style={{ width: `${pct}%` }} /></div><small className="budget-remaining">{formatMoney(Math.max(0, limit - spent), 0)} remaining</small></article> }

function GoalCard({ name, target, saved }: { name: string; target: number; saved: number }) { const pct = target ? Math.min(100, saved / target * 100) : 0; return <article className="goal-card"><div className="goal-ring" style={{ '--goal-pct': `${pct * 3.6}deg` } as React.CSSProperties}><strong>{pct.toFixed(0)}%</strong></div><b>{name}</b><span>{formatMoney(saved, 0)} / {formatMoney(target, 0)}</span></article> }

function readJson<T>(key: string, fallback: T): T { try { const value = JSON.parse(localStorage.getItem(key) || 'null'); return value ?? fallback } catch { return fallback } }

function More() { return <Screen eyebrow="More" title="Tools and settings."><section className="tool-list"><a href="/legacy.html#tab-admin"><UploadSimple size={22} weight="duotone" /><span><b>Statement imports</b><small>Preview, map, and commit your monthly statements.</small></span><ArrowRight size={18} /></a><a href="/legacy.html#tab-analytics"><TrendUp size={22} weight="duotone" /><span><b>Deeper analytics</b><small>Forecasts, anomalies, subscriptions, and account insights.</small></span><ArrowRight size={18} /></a><a href="/legacy.html#tab-rules"><Bank size={22} weight="duotone" /><span><b>Category rules</b><small>Keep future statement transactions consistent.</small></span><ArrowRight size={18} /></a></section></Screen> }

function ActivityRow({ row, onClick }: { row: ActivityEntry; onClick?: () => void }) { const incoming = row.entry_type === 'income'; return <article className={`activity-row${onClick ? ' interactive' : ''}`} onClick={onClick} tabIndex={onClick ? 0 : undefined} onKeyDown={event => { if (onClick && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onClick() } }}><span className="row-icon" style={{ color: categoryColors[row.category] || '#9aa8b8' }}>{incoming ? <TrendUp size={20} weight="duotone" /> : <TrendDown size={20} weight="duotone" />}</span><span className="row-copy"><b>{row.name}</b><small>{row.category} · {new Date(`${row.date}T12:00:00`).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' })} · {row.account}</small></span><strong className={incoming ? 'income-value' : 'expense-value'}>{incoming ? '+' : '−'}{formatMoney(row.amount, 2)}</strong>{onClick && <PencilSimple size={16} className="edit-icon" />}</article> }

function EntryComposer({ type, entry, onClose, onSaved, onDeleted }: { type: EntryType; entry?: ManualEntry; onClose: () => void; onSaved: (entry: ManualEntry) => void; onDeleted: (id: string) => void }) {
  const [amount, setAmount] = useState(String(entry?.amount || '0')); const [date, setDate] = useState(entry?.date || today); const [name, setName] = useState(entry?.name || ''); const [category, setCategory] = useState(entry?.category || (type === 'income' ? 'Deposits' : 'Other')); const [account, setAccount] = useState(entry?.account || 'Manual'); const [note, setNote] = useState(entry?.note || ''); const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const choices = type === 'income' ? INCOME_CATEGORIES : EXPENSE_CATEGORIES
  const press = (key: string) => setAmount(current => key === 'back' ? current.length > 1 ? current.slice(0, -1) : '0' : key === '.' && current.includes('.') ? current : current === '0' && key !== '.' ? key : current + key)
  const save = async () => { const value = Number(amount); if (!value || value <= 0 || !name.trim()) { setError('Enter a positive amount and a name or source.'); return } setBusy(true); setError(''); const now = new Date().toISOString(); const next: ManualEntry = { id: entry?.id || crypto.randomUUID(), entry_type: type, date, amount: Math.round(value * 100) / 100, name: name.trim(), category, account: account.trim() || 'Manual', note: note.trim(), currency: 'CAD', created_at: entry?.created_at || now, updated_at: now }; try { onSaved(await saveEntry(next)) } catch (issue) { setError(issue instanceof Error ? issue.message : 'Could not save entry. Your change was not applied.') } finally { setBusy(false) } }
  const remove = async () => { if (!entry || !window.confirm('Delete this manual entry?')) return; setBusy(true); try { await removeEntry(entry.id); onDeleted(entry.id) } catch (issue) { setError(issue instanceof Error ? issue.message : 'Could not delete entry.') } finally { setBusy(false) } }
  return <div className="composer-backdrop" role="presentation"><section className="composer" role="dialog" aria-modal="true" aria-labelledby="composer-title"><header><div><p className="eyebrow">Manual entry</p><h2 id="composer-title">{entry ? 'Edit' : 'Add'} {type}</h2></div><button aria-label="Close composer" onClick={onClose}>×</button></header><div className={`amount-display ${type}`}><span>{type === 'income' ? 'Income' : 'Expense'}</span><strong>{formatMoney(Number(amount) || 0, 2)}</strong></div><div className="calculator">{'123456789.0'.split('').map(key => <button key={key} onClick={() => press(key)}>{key}</button>)}<button aria-label="Backspace" onClick={() => press('back')}>←</button></div><div className="form-fields"><label>Date<input type="date" value={date} onChange={event => setDate(event.target.value)} /></label><label>{type === 'income' ? 'Source' : 'Name'}<input value={name} onChange={event => setName(event.target.value)} placeholder={type === 'income' ? 'Salary, refund, deposit' : 'Merchant or expense'} autoFocus /></label><label>Account<input value={account} onChange={event => setAccount(event.target.value)} placeholder="Manual" /></label><label>Note <span className="optional">optional</span><textarea value={note} onChange={event => setNote(event.target.value)} rows={2} /></label></div><fieldset><legend>Category</legend><div className="category-picker">{choices.map(item => <button key={item} className={category === item ? 'chosen' : ''} onClick={() => setCategory(item)}>{item}</button>)}</div></fieldset>{error && <p className="form-error">{error}</p>}<footer>{entry && <button className="delete-button" disabled={busy} onClick={remove}>Delete</button>}<button className={`save-button ${type}`} disabled={busy} onClick={save}>{busy ? 'Saving…' : `Save ${type}`}</button></footer></section></div>
}

function LoadState({ status, error, children }: { status: 'loading' | 'ready' | 'error'; error: string; children: React.ReactNode }) { if (status === 'loading') return <div className="loading-ledger"><span /><span /><span /></div>; if (status === 'error') return <div className="error-state"><h2>Data could not load</h2><p>{error}</p><p>Start the local tracker server, or sign in to the hosted workspace.</p></div>; return <>{children}</> }
function Empty({ message }: { message: string }) { return <div className="empty"><CheckCircle size={24} weight="duotone" /><p>{message}</p></div> }

export default App

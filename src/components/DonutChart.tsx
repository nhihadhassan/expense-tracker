import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { categoryColors } from '../lib/constants'
import { formatMoney } from '../lib/finance'
import type { ActivityEntry } from '../lib/types'

type Category = [string, { amount: number; count: number; rows: ActivityEntry[] }]

export default function DonutChart({ categories, onSelect }: { categories: Category[]; onSelect: (name: string) => void }) {
  return <div className="chart-graphic" aria-hidden="true">
    <ResponsiveContainer>
      <PieChart>
        <Pie
          data={categories.map(([name, value]) => ({ name, value: value.amount }))}
          dataKey="value"
          nameKey="name"
          innerRadius="64%"
          outerRadius="92%"
          paddingAngle={2}
          stroke="none"
          onClick={segment => { if (typeof segment.name === 'string') onSelect(segment.name) }}
        >
          {categories.map(([name]) => <Cell key={name} fill={categoryColors[name] || '#9aa8b8'} />)}
        </Pie>
        <Tooltip formatter={value => formatMoney(Number(value), 2)} />
      </PieChart>
    </ResponsiveContainer>
  </div>
}

export const EXPENSE_CATEGORIES = [
  'Car', 'Clothes', 'Communication', 'Eating out', 'Entertainment', 'Food',
  'Gifts', 'Health', 'Miscellaneous', 'School', 'Sports', 'Toiletry',
  'Transport', 'Travel', 'Uber', 'Shopping', 'Subscriptions', 'Fees & Interest',
  'Giving', 'Other',
] as const

export const INCOME_CATEGORIES = [
  'Deposits', 'Salary', 'Savings', 'Interest', 'Refund', 'Other income',
] as const

export const categoryColors: Record<string, string> = {
  Travel: '#5ac996', Shopping: '#ffa647', 'Eating out': '#72bcd9', Food: '#f47d87',
  Transport: '#ff8d84', Uber: '#dfac36', Clothes: '#b47bd4', Entertainment: '#efbf54',
  Health: '#ec7375', Gifts: '#c7a8b8', Car: '#8c9bb5', Communication: '#b993c7',
  Miscellaneous: '#c7a937', School: '#70aee5', Sports: '#71c2ae', Toiletry: '#8c9bb5',
  Subscriptions: '#9077d5', 'Fees & Interest': '#ef9589', Giving: '#b7a1b7', Other: '#9aa8b8',
  Deposits: '#53d69d', Salary: '#53d69d', Savings: '#87cda9', Interest: '#83cbb1',
  Refund: '#78d7b3', 'Other income': '#79caa8',
}

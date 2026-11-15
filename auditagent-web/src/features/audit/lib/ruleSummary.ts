import type { ContractRule } from '@/api/types'
import { formatDate } from '@/shared/lib/dates'
import { formatPercent, formatPkr } from '@/shared/lib/money'

/** One plain sentence for a rule that Agent 1 read from the contract. */
export function ruleSummary(rule: ContractRule): string {
  switch (rule.clause_type) {
    case 'late_penalty': {
      const grace = rule.grace_days > 0 ? `, first ${rule.grace_days} days free` : ''
      const date = formatDate(rule.deadline)
      if (rule.mode === 'flat_percent') {
        return `${formatPercent(rule.percent)} once if delivery is after ${date}${grace}`
      }
      const cap = rule.cap_percent ? `, up to ${formatPercent(rule.cap_percent)}` : ''
      return `${formatPercent(rule.percent)} per day after ${date}${cap}${grace}`
    }
    case 'volume_discount':
      return `${formatPercent(rule.discount_percent)} discount from ${rule.min_quantity} units`
    case 'payment_terms':
      return `Net ${rule.net_days} days from the invoice date`
    case 'unit_price':
      return `${rule.item_name} at ${formatPkr(rule.agreed_unit_price)} per unit`
  }
}
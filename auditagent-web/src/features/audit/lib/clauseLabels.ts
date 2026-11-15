import type { ClauseType } from '@/api/types'

export const clauseLabels: Record<ClauseType, string> = {
  late_penalty: 'Late delivery penalty',
  volume_discount: 'Volume discount',
  payment_terms: 'Payment terms',
  unit_price: 'Agreed unit price',
}

/** "delivery_date" -> "Delivery date"; a clause type gets its proper label. */
export function fieldLabel(field: string): string {
  if (field in clauseLabels) return clauseLabels[field as ClauseType]
  const text = field.replaceAll('_', ' ').trim()
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : ''
}
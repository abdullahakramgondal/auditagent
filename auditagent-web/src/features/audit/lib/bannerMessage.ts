import Decimal from 'decimal.js'
import type { AuditStatus } from '@/api/types'
import { formatPkr } from '@/shared/lib/money'

/** One sentence per status, built from the fields of the result. No amount is calculated here. */
export function bannerMessage(status: AuditStatus, totalDifference: string | null): string {
  if (status === 'COMPLIANT') return 'The invoice matches the contract.'
  if (status === 'NEEDS_REVIEW') {
    return 'Some values could not be proven. Check the reasons below before paying.'
  }
  if (totalDifference !== null && !new Decimal(totalDifference).isZero()) {
    return `The invoice is ${formatPkr(totalDifference)} above what the contract allows.`
  }
  return 'The invoice breaks a contract rule that has no amount, for example the payment terms.'
}
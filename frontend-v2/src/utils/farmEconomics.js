import { formatCurrency } from '@/utils/formatters';

export function recommendationLabel(row) {
  if (row.recommendation === 'direct_accepted') return 'OFFER ACCEPTED';
  if (row.recommendation === 'apmc_accepted') return 'APMC ACCEPTED';
  if (row.recommendation === 'switch_to_direct') return 'SWITCH TO DIRECT';
  return 'STAY APMC';
}

export function recommendationStyle(row) {
  if (row.recommendation === 'direct_accepted' || row.recommendation === 'apmc_accepted') {
    return {
      color: 'var(--green-ok)',
      border: '1px solid var(--green-ok)',
      background: 'rgba(76, 175, 80, 0.08)',
    };
  }
  if (row.recommendation === 'switch_to_direct') {
    return {
      color: 'var(--accent)',
      border: '1px solid var(--accent)',
      background: 'var(--orange-selected)',
    };
  }
  return {
    color: 'var(--green-ok)',
    border: '1px solid var(--border)',
    background: 'transparent',
  };
}

export function formatMarginDelta(delta) {
  if (delta == null || Number.isNaN(Number(delta))) return '--';
  const n = Number(delta);
  const prefix = n >= 0 ? '+' : '';
  return `${prefix}${formatCurrency(n)} vs APMC`;
}

export function formatMarginBreakdown(revenue, logistics, spoilage, net) {
  return `${formatCurrency(revenue)} − ${formatCurrency(logistics)} − ${formatCurrency(spoilage)} = ${formatCurrency(net)}`;
}

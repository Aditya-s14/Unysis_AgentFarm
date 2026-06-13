import { useMemo, useState } from 'react';
import { DEMO_FARMS } from '@/utils/demoFixtures';
import { listEligibleFarms } from '@/utils/commitmentEligibility';
import { formatCurrency, formatKg } from '@/utils/formatters';
import { formatPremiumPct, formatPricePerKg } from '@/utils/priceDiscovery';
import usePriceAcceptance from '@/hooks/usePriceAcceptance';
import { SECTION } from '@/utils/uiChars';

function QuoteRow({
  quote,
  isAccepted,
  acceptance,
  accepting,
  onAccept,
  compact,
}) {
  const [confirming, setConfirming] = useState(false);

  const handleAccept = async () => {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    await onAccept(quote);
    setConfirming(false);
  };

  const payout = quote.estimated_payout_inr
    ?? Math.round(quote.private_offer_per_kg * quote.tonnage_kg);

  return (
    <div
      className="px-4 py-4"
      style={{ borderTop: '1px solid var(--border)' }}
    >
      <div className="mb-3">
        <p className="font-syne font-bold text-paper" style={{ fontSize: compact ? '12px' : '13px' }}>
          {quote.farm_name}
        </p>
        <p className="font-mono text-muted mt-0.5" style={{ fontSize: '10px' }}>
          {quote.crop_type}
          {' · '}
          {formatKg(quote.tonnage_kg)}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div
          className="p-3"
          style={{
            border: '1px solid var(--border)',
            borderRadius: '4px',
            background: 'var(--bg)',
          }}
        >
          <p className="font-mono uppercase text-muted" style={{ fontSize: '9px', letterSpacing: '0.14em' }}>
            APMC mandi
          </p>
          <p className="font-mono mt-1" style={{ fontSize: '10px', color: 'var(--text)' }}>
            {quote.apmc_name}
          </p>
          <p className="font-syne font-bold mt-2" style={{ fontSize: '18px', color: 'var(--text)' }}>
            {formatPricePerKg(quote.apmc_price_per_kg)}
          </p>
          <p className="font-mono text-muted mt-1" style={{ fontSize: '9px' }}>
            Auction floor price
          </p>
        </div>

        <div
          className="p-3"
          style={{
            border: '1px solid var(--accent)',
            borderRadius: '4px',
            background: 'rgba(245, 166, 35, 0.06)',
          }}
        >
          <p className="font-mono uppercase" style={{ fontSize: '9px', letterSpacing: '0.14em', color: 'var(--accent)' }}>
            Private buyer offer
          </p>
          <p className="font-mono mt-1" style={{ fontSize: '10px', color: 'var(--text)' }}>
            {quote.private_buyer_name}
          </p>
          <p className="font-syne font-bold mt-2 flex items-baseline gap-2 flex-wrap" style={{ fontSize: '18px', color: 'var(--accent)' }}>
            {formatPricePerKg(quote.private_offer_per_kg)}
            <span className="font-mono" style={{ fontSize: '11px' }}>
              {formatPremiumPct(quote.premium_vs_apmc_pct)}
            </span>
          </p>
          {isAccepted ? (
            <div className="mt-2">
              <span
                className="font-mono uppercase tracking-wider px-2 py-1 inline-block"
                style={{
                  fontSize: '9px',
                  color: 'var(--green-ok)',
                  border: '1px solid var(--green-ok)',
                  borderRadius: '2px',
                  background: 'rgba(76, 175, 80, 0.08)',
                }}
              >
                Accepted
              </span>
              {acceptance?.accepted_at && (
                <p className="font-mono text-muted mt-1" style={{ fontSize: '9px' }}>
                  {new Date(acceptance.accepted_at).toLocaleString()}
                </p>
              )}
            </div>
          ) : (
            <div className="mt-2 space-y-2">
              {confirming && (
                <p className="font-mono" style={{ fontSize: '10px', color: 'var(--text)', lineHeight: 1.5 }}>
                  Accept {formatPricePerKg(quote.private_offer_per_kg)} for {formatKg(quote.tonnage_kg)}
                  {' → '}
                  est. {formatCurrency(payout)}
                </p>
              )}
              <button
                type="button"
                disabled={accepting}
                onClick={handleAccept}
                className="font-mono uppercase tracking-wider px-3 py-1.5 w-full sm:w-auto"
                style={{
                  fontSize: '9px',
                  border: `1px solid ${confirming ? 'var(--green-ok)' : 'var(--accent)'}`,
                  color: confirming ? 'var(--green-ok)' : 'var(--accent)',
                  borderRadius: '2px',
                  background: confirming ? 'rgba(76, 175, 80, 0.08)' : 'transparent',
                  opacity: accepting ? 0.6 : 1,
                }}
              >
                {accepting ? 'Accepting…' : confirming ? 'Confirm accept' : 'Accept offer'}
              </button>
              {confirming && (
                <button
                  type="button"
                  onClick={() => setConfirming(false)}
                  className="font-mono text-muted ml-2"
                  style={{ fontSize: '9px' }}
                >
                  Cancel
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Side-by-side APMC vs private buyer prices with digital accept (D1).
 * Pass `farmId` on the farmer role dashboard to show only that farm.
 */
export default function PriceDiscoveryBoard({ compact = false, farmId = null }) {
  const {
    quotes,
    loading,
    error,
    acceptingId,
    isAccepted,
    getAcceptance,
    acceptOffer,
  } = usePriceAcceptance();

  const eligibleIds = useMemo(
    () => new Set(listEligibleFarms(DEMO_FARMS).map((f) => f.id)),
    [],
  );

  const visibleQuotes = useMemo(() => {
    let filtered = quotes.filter((q) => eligibleIds.has(q.farm_id));
    if (farmId) filtered = filtered.filter((q) => q.farm_id === farmId);
    return filtered;
  }, [quotes, eligibleIds, farmId]);

  if (loading && visibleQuotes.length === 0) {
    return (
      <div className="font-mono text-muted mt-4" style={{ fontSize: '11px' }}>
        Loading price board…
      </div>
    );
  }

  if (error && visibleQuotes.length === 0) {
    return (
      <div className="font-mono text-muted mt-4" style={{ fontSize: '11px' }}>
        Price board unavailable: {error}
      </div>
    );
  }

  if (visibleQuotes.length === 0) {
    return (
      <div
        className={compact ? 'mt-4' : 'mt-6'}
        style={{
          border: '1px solid var(--border)',
          borderRadius: '4px',
          padding: '12px 16px',
        }}
      >
        <p className="font-mono text-muted" style={{ fontSize: '11px' }}>
          {farmId
            ? 'No price quotes for your farm in the next 7-day harvest window.'
            : 'No harvest-eligible farms in the next 7 days for price discovery.'}
        </p>
      </div>
    );
  }

  return (
    <div
      className={compact ? 'mt-4' : 'mt-6'}
      style={{
        border: '1px solid var(--border)',
        borderTop: '3px solid var(--accent)',
        borderRadius: '4px',
        overflow: 'hidden',
        background: 'var(--bg-card)',
      }}
    >
      <div className="px-5 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <h2
          className="font-syne font-bold uppercase text-paper tracking-wider-2"
          style={{ fontSize: compact ? '12px' : '14px' }}
        >
          {`${SECTION} Real-Time Price Discovery`}
        </h2>
        <p className="font-mono text-muted mt-1" style={{ fontSize: '10px', lineHeight: 1.5 }}>
          Compare nearest APMC auction floor vs direct private buyer offer — accept digitally to bypass middleman margin.
        </p>
      </div>

      <div>
        {visibleQuotes.map((quote) => (
          <QuoteRow
            key={quote.farm_id}
            quote={quote}
            compact={compact}
            isAccepted={isAccepted(quote.farm_id)}
            acceptance={getAcceptance(quote.farm_id)}
            accepting={acceptingId === quote.farm_id}
            onAccept={acceptOffer}
          />
        ))}
      </div>
    </div>
  );
}

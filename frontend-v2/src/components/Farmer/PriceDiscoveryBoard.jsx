import { useMemo, useState } from 'react';
import { DEMO_FARMS } from '@/utils/demoFixtures';
import { listEligibleFarms } from '@/utils/commitmentEligibility';
import { formatCurrency, formatKg } from '@/utils/formatters';
import { formatPremiumPct, formatPricePerKg } from '@/utils/priceDiscovery';
import usePriceAcceptance from '@/hooks/usePriceAcceptance';
import { SECTION } from '@/utils/uiChars';

function acceptedChannel(acceptance) {
  return acceptance?.channel || 'private';
}

/** Return apmc | private when one price is strictly higher; null on tie. */
function betterPriceChannel(quote) {
  const apmc = Number(quote.apmc_price_per_kg);
  const priv = Number(quote.private_offer_per_kg);
  if (priv > apmc) return 'private';
  if (apmc > priv) return 'apmc';
  return null;
}

function OfferColumn({
  channel,
  label,
  venue,
  pricePerKg,
  priceColor,
  priceSuffix,
  footnote,
  quote,
  acceptance,
  accepting,
  onAccept,
  highlighted = false,
}) {
  const [confirming, setConfirming] = useState(false);
  const isThisAccepted = acceptance && acceptedChannel(acceptance) === channel;
  const otherAccepted = acceptance && acceptedChannel(acceptance) !== channel;
  const acceptingThis = accepting === `${quote.farm_id}:${channel}`;

  const payout = Math.round(pricePerKg * quote.tonnage_kg);

  const handleAccept = async () => {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    await onAccept(quote, channel);
    setConfirming(false);
  };

  return (
    <div
      className="p-3 flex flex-col h-full"
      style={{
        border: isThisAccepted
          ? '2px solid var(--green-ok)'
          : highlighted
            ? '1px solid var(--accent)'
            : '1px solid var(--border)',
        borderRadius: '4px',
        background: isThisAccepted
          ? 'rgba(34, 160, 107, 0.06)'
          : highlighted
            ? 'var(--orange-selected)'
            : 'var(--bg)',
        opacity: otherAccepted ? 0.55 : 1,
      }}
    >
      <p
        className="font-mono uppercase"
        style={{
          fontSize: '9px',
          letterSpacing: '0.14em',
          color: highlighted ? 'var(--accent)' : 'var(--muted)',
        }}
      >
        {label}
      </p>
      <p className="font-mono mt-1" style={{ fontSize: '10px', color: 'var(--text)' }}>
        {venue}
      </p>
      <p
        className="font-syne font-bold mt-2 flex items-baseline gap-2 flex-wrap"
        style={{ fontSize: '18px', color: priceColor }}
      >
        {formatPricePerKg(pricePerKg)}
        {priceSuffix}
      </p>
      <p className="font-mono text-muted mt-1" style={{ fontSize: '9px' }}>
        {footnote}
      </p>

      <div className="mt-auto pt-3">
        {isThisAccepted ? (
          <div>
            <span
              className="font-mono uppercase tracking-wider px-2 py-1 inline-block"
              style={{
                fontSize: '9px',
                color: 'var(--green-ok)',
                border: '1px solid var(--green-ok)',
                borderRadius: '2px',
                background: 'rgba(34, 160, 107, 0.08)',
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
        ) : otherAccepted ? (
          <p className="font-mono text-muted" style={{ fontSize: '9px' }}>
            Other channel selected
          </p>
        ) : (
          <div className="space-y-2">
            {confirming && (
              <p className="font-mono" style={{ fontSize: '10px', color: 'var(--text)', lineHeight: 1.5 }}>
                Accept {formatPricePerKg(pricePerKg)} for {formatKg(quote.tonnage_kg)}
                {' → '}
                est. {formatCurrency(payout)}
              </p>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={acceptingThis}
                onClick={handleAccept}
                className="font-mono uppercase tracking-wider px-3 py-1.5"
                style={{
                  fontSize: '9px',
                  border: `1px solid ${confirming ? 'var(--green-ok)' : highlighted ? 'var(--accent)' : 'var(--border)'}`,
                  color: confirming ? 'var(--green-ok)' : highlighted ? 'var(--accent)' : 'var(--text)',
                  borderRadius: '2px',
                  background: confirming ? 'rgba(34, 160, 107, 0.08)' : 'transparent',
                  opacity: acceptingThis ? 0.6 : 1,
                }}
              >
                {acceptingThis ? 'Accepting…' : confirming ? 'Confirm accept' : 'Accept offer'}
              </button>
              {confirming && (
                <button
                  type="button"
                  onClick={() => setConfirming(false)}
                  className="font-mono text-muted"
                  style={{ fontSize: '9px' }}
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function QuoteRow({
  quote,
  acceptance,
  accepting,
  onAccept,
  compact,
}) {
  const bestChannel = betterPriceChannel(quote);

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

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-stretch">
        <OfferColumn
          channel="apmc"
          label="APMC mandi"
          venue={quote.apmc_name}
          pricePerKg={quote.apmc_price_per_kg}
          priceColor={bestChannel === 'apmc' ? 'var(--accent)' : 'var(--text)'}
          footnote="Auction floor price"
          quote={quote}
          acceptance={acceptance}
          accepting={accepting}
          onAccept={onAccept}
          highlighted={bestChannel === 'apmc'}
        />
        <OfferColumn
          channel="private"
          label="Private buyer offer"
          venue={quote.private_buyer_name}
          pricePerKg={quote.private_offer_per_kg}
          priceColor={bestChannel === 'private' ? 'var(--accent)' : 'var(--text)'}
          priceSuffix={(
            <span className="font-mono" style={{ fontSize: '11px' }}>
              {formatPremiumPct(quote.premium_vs_apmc_pct)}
            </span>
          )}
          footnote="Direct buyer price"
          quote={quote}
          acceptance={acceptance}
          accepting={accepting}
          onAccept={onAccept}
          highlighted={bestChannel === 'private'}
        />
      </div>
    </div>
  );
}

/**
 * Side-by-side APMC vs private buyer prices with digital accept (D1).
 * Pass `farmId` on the farmer role dashboard to show only that farm.
 */
export default function PriceDiscoveryBoard({ compact = false, embedded = false, farmId = null }) {
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
        className={embedded ? undefined : (compact ? 'mt-4' : 'mt-6')}
        style={embedded ? undefined : {
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
      className={embedded ? undefined : (compact ? 'mt-4' : 'mt-6')}
      style={embedded ? undefined : {
        border: '1px solid var(--border)',
        borderTop: '3px solid var(--accent)',
        borderRadius: '4px',
        overflow: 'hidden',
        background: 'var(--bg-card)',
      }}
    >
      {!embedded && (
      <div className="px-5 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <h2
          className="font-syne font-bold uppercase text-paper tracking-wider-2"
          style={{ fontSize: compact ? '12px' : '14px' }}
        >
          {`${SECTION} Real-Time Price Discovery`}
        </h2>
        <p className="font-mono text-muted mt-1" style={{ fontSize: '10px', lineHeight: 1.5 }}>
          Compare APMC auction floor vs direct private buyer offer — accept either channel digitally.
        </p>
      </div>
      )}

      <div>
        {visibleQuotes.map((quote) => (
          <QuoteRow
            key={quote.farm_id}
            quote={quote}
            compact={compact}
            acceptance={isAccepted(quote.farm_id) ? getAcceptance(quote.farm_id) : null}
            accepting={acceptingId}
            onAccept={acceptOffer}
          />
        ))}
      </div>
    </div>
  );
}

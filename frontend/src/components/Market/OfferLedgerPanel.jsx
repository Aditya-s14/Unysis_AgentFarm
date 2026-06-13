import { useMemo, useState } from 'react';
import { DEMO_DEMAND_POINTS, DEMO_FARMS } from '@/utils/demoFixtures';
import { formatCurrency, formatKg } from '@/utils/formatters';
import useMarketOffers from '@/hooks/useMarketOffers';
import useFarmerCommitments from '@/hooks/useFarmerCommitments';

const CROP_OPTIONS = ['tomato', 'onion', 'banana', 'mango'];
const PRIVATE_DPS = DEMO_DEMAND_POINTS.filter((d) => d.point_type === 'private');

function dpLabel(dpId) {
  return PRIVATE_DPS.find((d) => d.id === dpId)?.name || dpId;
}

function farmLabel(farmId) {
  return DEMO_FARMS.find((f) => f.id === farmId)?.name || farmId;
}

function OfferRow({ offer, onAccept, accepting, acceptFarmId, setAcceptFarmId }) {
  const isBid = offer.side === 'bid';
  const canAccept = offer.status === 'open';
  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center gap-3 py-3 px-4"
      style={{ borderTop: '1px solid var(--border)' }}
    >
      <div className="flex-1 min-w-0">
        <p className="font-syne font-bold text-paper flex items-center gap-2 flex-wrap" style={{ fontSize: '13px' }}>
          <span
            className="font-mono uppercase"
            style={{
              fontSize: '9px',
              letterSpacing: '0.12em',
              padding: '2px 8px',
              border: `1px solid ${isBid ? 'var(--accent)' : 'var(--green-ok)'}`,
              color: isBid ? 'var(--accent)' : 'var(--green-ok)',
              borderRadius: '2px',
            }}
          >
            {offer.side}
          </span>
          {isBid ? offer.buyer_name : farmLabel(offer.farm_id)}
          {offer.status !== 'open' && (
            <span className="font-mono text-muted uppercase" style={{ fontSize: '9px' }}>
              {offer.status}
            </span>
          )}
        </p>
        <p className="font-mono text-muted mt-0.5" style={{ fontSize: '10px' }}>
          {offer.crop_type}
          {' · '}
          {formatKg(offer.quantity_kg)}
          {' @ '}
          {formatCurrency(offer.price_per_kg)}
          /kg
        </p>
        <p className="font-mono text-muted mt-0.5" style={{ fontSize: '9px' }}>
          → {dpLabel(offer.demand_point_id)}
        </p>
      </div>
      {canAccept && (
        <div className="flex flex-col gap-2 shrink-0">
          {isBid && (
            <select
              value={acceptFarmId}
              onChange={(e) => setAcceptFarmId(e.target.value)}
              className="font-mono text-paper px-2 py-1"
              style={{
                fontSize: '10px',
                border: '1px solid var(--border)',
                background: 'var(--card)',
                borderRadius: '2px',
              }}
            >
              <option value="">Select farm…</option>
              {DEMO_FARMS.filter((f) => f.crop_type === offer.crop_type).map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
          )}
          <button
            type="button"
            disabled={accepting || (isBid && !acceptFarmId)}
            onClick={() => onAccept(offer.id, isBid ? acceptFarmId : undefined)}
            className="font-mono uppercase tracking-wider px-3 py-1.5"
            style={{
              fontSize: '9px',
              border: '1px solid var(--accent)',
              color: 'var(--accent)',
              borderRadius: '2px',
              background: 'rgba(245, 166, 35, 0.05)',
            }}
          >
            {accepting ? 'Accepting…' : 'Accept'}
          </button>
        </div>
      )}
    </div>
  );
}

function CommitmentRow({ commitment }) {
  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center gap-2 py-3 px-4"
      style={{ borderTop: '1px solid var(--border)' }}
    >
      <div className="flex-1">
        <p className="font-syne font-bold text-paper" style={{ fontSize: '13px' }}>
          {farmLabel(commitment.farm_id)}
        </p>
        <p className="font-mono text-muted mt-0.5" style={{ fontSize: '10px' }}>
          {commitment.crop_type}
          {' · '}
          {formatKg(commitment.quantity_kg)}
          {' @ '}
          {formatCurrency(commitment.price_per_kg)}
          /kg
        </p>
        <p className="font-mono text-accent mt-0.5" style={{ fontSize: '9px' }}>
          Guaranteed → {dpLabel(commitment.demand_point_id)}
        </p>
      </div>
    </div>
  );
}

/**
 * D4 — unified bid/ask offer ledger with accept → guaranteed pickup.
 */
export default function OfferLedgerPanel() {
  const { lockCommitment } = useFarmerCommitments();
  const {
    offers,
    commitments,
    loading,
    error,
    acceptingId,
    posting,
    postOffer,
    acceptOffer,
    refresh,
  } = useMarketOffers({
    onAcceptCommitment: (farmId, tonnageKg, demandPointId) => {
      lockCommitment(farmId, { tonnage_kg: tonnageKg, demand_point_id: demandPointId });
    },
  });

  const [side, setSide] = useState('ask');
  const [farmId, setFarmId] = useState(DEMO_FARMS[0]?.id || '');
  const [buyerName, setBuyerName] = useState('');
  const [demandPointId, setDemandPointId] = useState(PRIVATE_DPS[0]?.id || '');
  const [cropType, setCropType] = useState('tomato');
  const [quantityKg, setQuantityKg] = useState('800');
  const [pricePerKg, setPricePerKg] = useState('22');
  const [acceptFarmByOffer, setAcceptFarmByOffer] = useState({});

  const openOffers = useMemo(
    () => offers.filter((o) => o.status === 'open'),
    [offers],
  );
  const acceptedOffers = useMemo(
    () => offers.filter((o) => o.status === 'accepted'),
    [offers],
  );

  const handlePost = async (e) => {
    e.preventDefault();
    const body = {
      side,
      role: side === 'ask' ? 'farmer' : 'buyer',
      demand_point_id: demandPointId,
      crop_type: cropType,
      quantity_kg: Number(quantityKg),
      price_per_kg: Number(pricePerKg),
      ...(side === 'ask' ? { farm_id: farmId } : { buyer_name: buyerName.trim() || 'Direct Buyer' }),
    };
    await postOffer(body);
    await refresh();
  };

  const handleAccept = async (offerId, farmForBid) => {
    await acceptOffer(offerId, farmForBid || null);
    await refresh();
  };

  return (
    <div className="space-y-6">
      <div
        className="p-4"
        style={{
          background: 'rgba(245, 166, 35, 0.03)',
          border: '1px solid var(--border)',
          borderRadius: '4px',
        }}
      >
        <p className="font-mono text-muted text-[11px] leading-relaxed">
          Accepted offers override VRP routing — guaranteed pickup to the committed private DC.
          All offers are append-only with audit timestamps.
        </p>
      </div>

      {error && (
        <div
          className="font-mono text-[12px] p-3"
          style={{
            color: 'var(--red-risk)',
            border: '1px solid var(--red-risk)',
            background: 'rgba(255, 68, 68, 0.05)',
            borderRadius: '2px',
          }}
        >
          {error}
        </div>
      )}

      <div
        className="bg-card"
        style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
      >
        <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <p className="font-mono uppercase text-accent" style={{ fontSize: '0.65rem', letterSpacing: '0.15em' }}>
            ▸ Post Offer
          </p>
        </div>
        <form onSubmit={handlePost} className="p-5 space-y-4">
          <div className="flex gap-2">
            {['ask', 'bid'].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setSide(s)}
                className="font-mono uppercase px-4 py-2"
                style={{
                  fontSize: '10px',
                  letterSpacing: '0.1em',
                  border: `1px solid ${side === s ? 'var(--accent)' : 'var(--border)'}`,
                  color: side === s ? 'var(--accent)' : 'var(--muted)',
                  background: side === s ? 'rgba(245, 166, 35, 0.08)' : 'transparent',
                  borderRadius: '2px',
                }}
              >
                {s}
              </button>
            ))}
          </div>
          {side === 'ask' ? (
            <select
              value={farmId}
              onChange={(e) => setFarmId(e.target.value)}
              className="w-full font-mono px-3 py-2 text-paper"
              style={{ fontSize: '12px', border: '1px solid var(--border)', background: 'var(--card)' }}
            >
              {DEMO_FARMS.map((f) => (
                <option key={f.id} value={f.id}>{f.name} ({f.crop_type})</option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              placeholder="Buyer name"
              value={buyerName}
              onChange={(e) => setBuyerName(e.target.value)}
              className="w-full font-mono px-3 py-2 text-paper"
              style={{ fontSize: '12px', border: '1px solid var(--border)', background: 'var(--card)' }}
            />
          )}
          <div className="grid grid-cols-2 gap-3">
            <select
              value={demandPointId}
              onChange={(e) => setDemandPointId(e.target.value)}
              className="font-mono px-3 py-2 text-paper"
              style={{ fontSize: '12px', border: '1px solid var(--border)', background: 'var(--card)' }}
            >
              {PRIVATE_DPS.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
            <select
              value={cropType}
              onChange={(e) => setCropType(e.target.value)}
              className="font-mono px-3 py-2 text-paper"
              style={{ fontSize: '12px', border: '1px solid var(--border)', background: 'var(--card)' }}
            >
              {CROP_OPTIONS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="number"
              min="1"
              value={quantityKg}
              onChange={(e) => setQuantityKg(e.target.value)}
              placeholder="Qty (kg)"
              className="font-mono px-3 py-2 text-paper"
              style={{ fontSize: '12px', border: '1px solid var(--border)', background: 'var(--card)' }}
            />
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={pricePerKg}
              onChange={(e) => setPricePerKg(e.target.value)}
              placeholder="Price/kg"
              className="font-mono px-3 py-2 text-paper"
              style={{ fontSize: '12px', border: '1px solid var(--border)', background: 'var(--card)' }}
            />
          </div>
          <button
            type="submit"
            disabled={posting}
            className="w-full py-2 font-mono uppercase tracking-wider"
            style={{
              fontSize: '11px',
              background: 'var(--accent)',
              color: '#0D1F0F',
              borderRadius: '2px',
            }}
          >
            {posting ? 'Posting…' : 'Post Offer'}
          </button>
        </form>
      </div>

      <div
        className="bg-card"
        style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
      >
        <div className="px-5 py-4 flex justify-between items-center" style={{ borderBottom: '1px solid var(--border)' }}>
          <p className="font-mono uppercase text-accent" style={{ fontSize: '0.65rem', letterSpacing: '0.15em' }}>
            ▸ Open Offers
          </p>
          <span className="font-mono text-muted" style={{ fontSize: '10px' }}>
            {loading ? '…' : openOffers.length}
          </span>
        </div>
        {openOffers.length === 0 ? (
          <p className="px-5 py-6 font-mono text-muted text-[12px]">No open offers.</p>
        ) : (
          openOffers.map((o) => (
            <OfferRow
              key={o.id}
              offer={o}
              accepting={acceptingId === o.id}
              acceptFarmId={acceptFarmByOffer[o.id] || ''}
              setAcceptFarmId={(val) => setAcceptFarmByOffer((prev) => ({ ...prev, [o.id]: val }))}
              onAccept={handleAccept}
            />
          ))
        )}
      </div>

      <div
        className="bg-card"
        style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
      >
        <div className="px-5 py-4 flex justify-between items-center" style={{ borderBottom: '1px solid var(--border)' }}>
          <p className="font-mono uppercase text-accent" style={{ fontSize: '0.65rem', letterSpacing: '0.15em' }}>
            ▸ Accepted Commitments
          </p>
          <span className="font-mono text-muted" style={{ fontSize: '10px' }}>
            {commitments.length}
          </span>
        </div>
        {commitments.length === 0 ? (
          <p className="px-5 py-6 font-mono text-muted text-[12px]">
            No accepted commitments yet — accept an offer to guarantee pickup.
          </p>
        ) : (
          commitments.map((c) => <CommitmentRow key={c.offer_id} commitment={c} />)
        )}
      </div>

      {acceptedOffers.length > 0 && (
        <div
          className="bg-card opacity-80"
          style={{ border: '1px solid var(--border)', borderRadius: '4px' }}
        >
          <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
            <p className="font-mono uppercase text-muted" style={{ fontSize: '0.65rem', letterSpacing: '0.15em' }}>
              ▸ Ledger (accepted offers)
            </p>
          </div>
          {acceptedOffers.map((o) => (
            <div key={o.id} className="px-5 py-3 font-mono text-muted" style={{ fontSize: '10px', borderTop: '1px solid var(--border)' }}>
              {o.id}
              {o.accepted_at ? ` · accepted ${new Date(o.accepted_at).toLocaleString()}` : ''}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

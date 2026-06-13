import { useMemo, useState } from 'react';
import { DEMO_DEMAND_POINTS } from '@/utils/demoFixtures';
import { formatCurrency, formatKg } from '@/utils/formatters';
import useBuyerDemands from '@/hooks/useBuyerDemands';

const BUYER_TYPES = [
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'supermarket', label: 'Supermarket' },
  { value: 'exporter', label: 'Exporter' },
];

const CROP_OPTIONS = ['tomato', 'onion', 'banana', 'mango'];

const PRIVATE_DPS = DEMO_DEMAND_POINTS.filter((d) => d.point_type === 'private');

function dpLabel(dpId) {
  return PRIVATE_DPS.find((d) => d.id === dpId)?.name || dpId;
}

function PostRow({ post, onRemove, removing }) {
  const total = Math.round(post.quantity_kg * post.price_per_kg);
  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center gap-3 py-3 px-4"
      style={{ borderTop: '1px solid var(--border)' }}
    >
      <div className="flex-1 min-w-0">
        <p className="font-syne font-bold text-paper truncate" style={{ fontSize: '13px' }}>
          {post.buyer_name}
        </p>
        <p className="font-mono text-muted mt-0.5" style={{ fontSize: '10px' }}>
          {post.buyer_type}
          {' · '}
          {post.crop_type}
          {' · '}
          {formatKg(post.quantity_kg)}
          {' @ '}
          {formatCurrency(post.price_per_kg)}
          /kg
        </p>
        <p className="font-mono text-muted mt-0.5" style={{ fontSize: '9px' }}>
          → {dpLabel(post.demand_point_id)}
        </p>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="font-mono text-accent" style={{ fontSize: '11px' }}>
          {formatCurrency(total)}
        </span>
        <button
          type="button"
          disabled={removing}
          onClick={() => onRemove(post.id)}
          className="font-mono uppercase tracking-wider px-3 py-1.5"
          style={{
            fontSize: '9px',
            border: '1px solid var(--red-risk)',
            color: 'var(--red-risk)',
            borderRadius: '2px',
            background: 'rgba(255, 68, 68, 0.05)',
          }}
        >
          Remove
        </button>
      </div>
    </div>
  );
}

/**
 * Buyer role UI — post crop demand (qty + price) on private DCs.
 */
export default function BuyerDemandPanel({ compact = false }) {
  const { posts, syncing, postDemand, removePost } = useBuyerDemands();
  const [buyerName, setBuyerName] = useState('');
  const [buyerType, setBuyerType] = useState('restaurant');
  const [demandPointId, setDemandPointId] = useState(PRIVATE_DPS[0]?.id || '');
  const [cropType, setCropType] = useState('tomato');
  const [quantityKg, setQuantityKg] = useState('800');
  const [pricePerKg, setPricePerKg] = useState('22');
  const [submitting, setSubmitting] = useState(false);
  const [removingId, setRemovingId] = useState(null);
  const [error, setError] = useState(null);

  const estimatedTotal = useMemo(() => {
    const qty = Number(quantityKg) || 0;
    const price = Number(pricePerKg) || 0;
    return Math.round(qty * price);
  }, [quantityKg, pricePerKg]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await postDemand({
        demand_point_id: demandPointId,
        buyer_name: buyerName.trim() || 'Direct Buyer',
        buyer_type: buyerType,
        crop_type: cropType,
        quantity_kg: Number(quantityKg),
        price_per_kg: Number(pricePerKg),
      });
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Post failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRemove = async (postId) => {
    setRemovingId(postId);
    await removePost(postId);
    setRemovingId(null);
  };

  const inputStyle = {
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: '2px',
    color: 'var(--text)',
    fontSize: compact ? '10px' : '11px',
  };

  return (
    <div
      className="bg-card"
      style={{
        border: '1px solid var(--border)',
        borderRadius: '4px',
      }}
    >
      <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <p
          className="font-mono uppercase"
          style={{ color: 'var(--accent)', fontSize: '0.65rem', letterSpacing: '0.15em' }}
        >
          ▸ Direct Buyer Demand
        </p>
        <p className="font-mono text-muted mt-1" style={{ fontSize: compact ? '10px' : '11px' }}>
          Post quantity and price at a private DC — routes prioritize direct buyers before APMC.
          {syncing ? ' Syncing…' : ''}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="px-4 py-4 space-y-3">
        <div className={`grid gap-3 ${compact ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2'}`}>
          <label className="block">
            <span className="font-mono text-muted uppercase" style={{ fontSize: '9px' }}>Buyer name</span>
            <input
              type="text"
              value={buyerName}
              onChange={(e) => setBuyerName(e.target.value)}
              placeholder="e.g. Taj West End Kitchen"
              className="font-mono w-full mt-1 px-2 py-1.5"
              style={inputStyle}
            />
          </label>
          <label className="block">
            <span className="font-mono text-muted uppercase" style={{ fontSize: '9px' }}>Buyer type</span>
            <select
              value={buyerType}
              onChange={(e) => setBuyerType(e.target.value)}
              className="font-mono w-full mt-1 px-2 py-1.5"
              style={inputStyle}
            >
              {BUYER_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="font-mono text-muted uppercase" style={{ fontSize: '9px' }}>Private DC</span>
            <select
              value={demandPointId}
              onChange={(e) => setDemandPointId(e.target.value)}
              className="font-mono w-full mt-1 px-2 py-1.5"
              style={inputStyle}
            >
              {PRIVATE_DPS.map((d) => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="font-mono text-muted uppercase" style={{ fontSize: '9px' }}>Crop</span>
            <select
              value={cropType}
              onChange={(e) => setCropType(e.target.value)}
              className="font-mono w-full mt-1 px-2 py-1.5"
              style={inputStyle}
            >
              {CROP_OPTIONS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="font-mono text-muted uppercase" style={{ fontSize: '9px' }}>Quantity (kg)</span>
            <input
              type="number"
              min="1"
              step="1"
              value={quantityKg}
              onChange={(e) => setQuantityKg(e.target.value)}
              className="font-mono w-full mt-1 px-2 py-1.5"
              style={inputStyle}
              required
            />
          </label>
          <label className="block">
            <span className="font-mono text-muted uppercase" style={{ fontSize: '9px' }}>Price (₹/kg)</span>
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={pricePerKg}
              onChange={(e) => setPricePerKg(e.target.value)}
              className="font-mono w-full mt-1 px-2 py-1.5"
              style={inputStyle}
              required
            />
          </label>
        </div>

        <p className="font-mono text-muted" style={{ fontSize: '10px' }}>
          Est. order value:{' '}
          <span className="text-accent">{formatCurrency(estimatedTotal)}</span>
        </p>

        {error && (
          <p className="font-mono text-[11px]" style={{ color: 'var(--red-risk)' }}>{error}</p>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="font-mono uppercase tracking-wider px-4 py-2 transition disabled:opacity-50"
          style={{
            fontSize: '10px',
            background: 'var(--accent)',
            color: '#0D1F0F',
            borderRadius: '2px',
            letterSpacing: '0.12em',
          }}
        >
          {submitting ? 'Posting…' : 'Post demand'}
        </button>
      </form>

      <div>
        <p
          className="font-mono uppercase px-4 py-2 text-muted"
          style={{ fontSize: '9px', letterSpacing: '0.12em', borderTop: '1px solid var(--border)' }}
        >
          Active posts ({posts.length})
        </p>
        {posts.length === 0 ? (
          <p className="px-4 py-4 font-mono text-muted text-[11px]">No buyer demand posted yet.</p>
        ) : (
          posts.map((post) => (
            <PostRow
              key={post.id}
              post={post}
              onRemove={handleRemove}
              removing={removingId === post.id}
            />
          ))
        )}
      </div>
    </div>
  );
}

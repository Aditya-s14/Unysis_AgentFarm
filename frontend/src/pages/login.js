import Head from 'next/head';
import { useRouter } from 'next/router';
import { useState } from 'react';
import { requestOtp, verifyOtp } from '@/api/client';
import { useAppContext } from '@/context/AppContext';

const DEMO_ACCOUNTS = [
  { phone: '+919800000001', label: 'FPO Admin' },
  { phone: '+919800000002', label: 'Farmer' },
  { phone: '+919800000003', label: 'Driver' },
  { phone: '+919800000004', label: 'Mandi' },
];

// Mirrors ROLE_HOME in src/middleware.js.
const ROLE_HOME = {
  fpo: '/dashboard',
  farmer: '/farmer',
  driver: '/driver',
  mandi: '/mandi',
};

/**
 * Login — phone → OTP → JWT (T1).
 * With the mock OTP provider the code is echoed back (dev_otp) and shown
 * inline so the demo needs no SMS infrastructure.
 */
export default function LoginPage() {
  const router = useRouter();
  const { login } = useAppContext();

  const [step, setStep] = useState('phone'); // 'phone' | 'code'
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [devOtp, setDevOtp] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submitPhone = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const resp = await requestOtp(phone);
      setDevOtp(resp.dev_otp || null);
      setStep('code');
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const submitCode = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const resp = await verifyOtp(phone, code);
      login(resp.access_token, resp.expires_in);
      // Hard navigation, not router.push: a tab opened before a frontend
      // rebuild holds a stale bundle whose client-side route transition can
      // fail silently — leaving a signed-in user stranded on this form,
      // where re-pressing Verify burns the (single-use) code into 401s.
      // A full page load always goes through middleware with the fresh
      // cookie and always loads the current bundle. Button stays disabled
      // (busy) on success for the same reason.
      window.location.assign(ROLE_HOME[resp.role] || '/dashboard');
    } catch (err) {
      setError(err?.response?.data?.detail || err.message);
      setBusy(false);
    }
  };

  return (
    <>
      <Head><title>Sign in | AgentFarm</title></Head>
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="glass-card-static p-8 w-full max-w-md">
          <div className="flex items-center gap-3 mb-6">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center"
              style={{ background: 'var(--navy)', color: '#fff' }}
            >
              <span className="text-xs font-bold">AF</span>
            </div>
            <div>
              <p className="text-sm font-bold tracking-tight" style={{ color: 'var(--navy)' }}>
                AgentFarm
              </p>
              <p className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                Sign in with your phone
              </p>
            </div>
          </div>

          {step === 'phone' && (
            <form onSubmit={submitPhone} className="space-y-4">
              <div>
                <label className="section-label block mb-2" htmlFor="phone">Phone number</label>
                <input
                  id="phone"
                  type="tel"
                  required
                  placeholder="+91 98XXXXXXXX"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm rounded-xl focus:outline-none"
                  style={{
                    background: 'var(--bg-subtle)',
                    color: 'var(--text)',
                    border: '1px solid var(--border)',
                  }}
                />
              </div>
              <button type="submit" disabled={busy} className="btn-primary w-full justify-center disabled:opacity-50">
                {busy ? 'Sending…' : 'Send OTP'}
              </button>

              <div className="pt-2">
                <p className="section-label mb-2">Demo accounts</p>
                <div className="flex flex-wrap gap-2">
                  {DEMO_ACCOUNTS.map((a) => (
                    <button
                      key={a.phone}
                      type="button"
                      onClick={() => setPhone(a.phone)}
                      className="text-xs px-3 py-1.5 rounded-full transition-colors"
                      style={{
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border)',
                        background: 'rgba(235,240,245,0.5)',
                        cursor: 'pointer',
                      }}
                    >
                      {a.label}
                    </button>
                  ))}
                </div>
              </div>
            </form>
          )}

          {step === 'code' && (
            <form onSubmit={submitCode} className="space-y-4">
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Code sent to <strong style={{ color: 'var(--navy)' }}>{phone}</strong>
              </p>
              {devOtp && (
                <p
                  className="text-xs px-3 py-2 rounded-lg"
                  style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}
                >
                  Dev mode — your OTP is <strong>{devOtp}</strong>
                </p>
              )}
              <div>
                <label className="section-label block mb-2" htmlFor="otp">One-time code</label>
                <input
                  id="otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  required
                  placeholder="6-digit code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="w-full px-4 py-2.5 text-sm rounded-xl focus:outline-none tracking-[0.3em]"
                  style={{
                    background: 'var(--bg-subtle)',
                    color: 'var(--text)',
                    border: '1px solid var(--border)',
                  }}
                />
              </div>
              <button type="submit" disabled={busy} className="btn-primary w-full justify-center disabled:opacity-50">
                {busy ? 'Verifying…' : 'Verify & Sign in'}
              </button>
              <button
                type="button"
                className="btn-secondary w-full justify-center"
                onClick={() => { setStep('phone'); setCode(''); setDevOtp(null); setError(null); }}
              >
                Use a different number
              </button>
            </form>
          )}

          {error && (
            <p
              className="mt-4 text-xs px-3 py-2 rounded-lg"
              style={{ background: 'var(--red-muted)', color: 'var(--red-risk)' }}
            >
              {error}
            </p>
          )}
        </div>
      </div>
    </>
  );
}

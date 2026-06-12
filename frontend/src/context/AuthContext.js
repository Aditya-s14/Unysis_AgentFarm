import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'agentfarm_user';

export const DEMO_ACCOUNTS = [
  // FPO
  { role: 'fpo',    entity_id: 'fpo-001',     name: 'Priya Sharma',         label: 'FPO Admin',              region: 'Karnataka & Maharashtra' },
  // Farmers
  { role: 'farmer', entity_id: 'farm-001',    name: 'Ravi Kumar',           label: 'Nandi Valley Tomatoes',  region: 'Karnataka' },
  { role: 'farmer', entity_id: 'farm-006',    name: 'Arvind Patil',         label: 'Nasik Hills Onion Growers', region: 'Maharashtra' },
  { role: 'farmer', entity_id: 'farm-011',    name: 'Deepa Gowda',          label: 'Chikmagalur Robusta Banana', region: 'Karnataka' },
  // Drivers
  { role: 'driver', entity_id: 'tr-001',      name: 'Suresh Naik',          label: 'Truck T1 (1-ton)',       region: 'Karnataka' },
  { role: 'driver', entity_id: 'tr-004',      name: 'Ramesh Yadav',         label: 'Truck T4 (3-ton)',       region: 'Karnataka' },
  { role: 'driver', entity_id: 'tr-008',      name: 'Kumar Singh',          label: 'Truck T8 (5-ton)',       region: 'Maharashtra' },
  // Mandi operators
  { role: 'mandi',  entity_id: 'dp-apmc-01', name: 'Shyam Iyer',           label: 'Yeshwanthpur APMC',      region: 'Bengaluru' },
  { role: 'mandi',  entity_id: 'dp-apmc-04', name: 'Ganesh More',          label: 'Nashik Wholesale APMC',  region: 'Maharashtra' },
  { role: 'mandi',  entity_id: 'dp-priv-01', name: 'Anita Desai',          label: 'Reliance Fresh DC Pune', region: 'Maharashtra' },
];

export const ROLE_LABELS = {
  fpo:    'FPO Admin',
  farmer: 'Farmer',
  driver: 'Driver',
  mandi:  'Mandi Operator',
};

export const ROLE_COLORS = {
  fpo:    { bg: '#1e3a5f', text: '#fff' },
  farmer: { bg: '#166534', text: '#fff' },
  driver: { bg: '#92400e', text: '#fff' },
  mandi:  { bg: '#581c87', text: '#fff' },
};

const AuthContext = createContext(null);

export function AuthContextProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setUser(JSON.parse(stored));
    } catch {
      // ignore bad stored value
    }
    setLoading(false);
  }, []);

  const login = useCallback((account) => {
    const u = { role: account.role, entity_id: account.entity_id, name: account.name, label: account.label };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthContextProvider');
  return ctx;
}

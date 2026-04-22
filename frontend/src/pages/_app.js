import '@/styles/globals.css';
import { AppContextProvider } from '@/context/AppContext';

/**
 * Next.js custom App — wraps every page with the AgentFarm context provider
 * and imports global styles (including Tailwind and Leaflet CSS).
 */
export default function MyApp({ Component, pageProps }) {
  return (
    <AppContextProvider>
      <Component {...pageProps} />
    </AppContextProvider>
  );
}

import '@/styles/globals.css';
import { AppContextProvider } from '@/context/AppContext';
import { AuthContextProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';

export default function MyApp({ Component, pageProps }) {
  return (
    <ThemeProvider>
      <AuthContextProvider>
        <AppContextProvider>
          <Component {...pageProps} />
        </AppContextProvider>
      </AuthContextProvider>
    </ThemeProvider>
  );
}

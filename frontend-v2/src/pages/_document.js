import { Html, Head, Main, NextScript } from 'next/document';

/** Custom Document — sets the document language and boilerplate head tags. */
export default function Document() {
  return (
    <Html lang="en" suppressHydrationWarning>
      <Head>
        <meta charSet="utf-8" />
        <meta name="description" content="AgentFarm Optimizer — agentic AI for Indian agri supply chains" />
        <link rel="icon" href="/favicon.ico" />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('agentfarm_theme');if(t!=='dark'&&t!=='light'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}document.documentElement.setAttribute('data-theme',t||'light');document.documentElement.style.colorScheme=t||'light';}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`,
          }}
        />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}

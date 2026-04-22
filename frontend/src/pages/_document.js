import { Html, Head, Main, NextScript } from 'next/document';

/** Custom Document — sets the document language and boilerplate head tags. */
export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <meta charSet="utf-8" />
        <meta name="description" content="AgentFarm Optimizer — agentic AI for Indian agri supply chains" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}

import Head from 'next/head';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import ChatInterface from '@/components/Advisor/ChatInterface';

/**
 * Advisor page — hosts the conversational Farmer Advisor UI.
 * The underlying Advisor Agent is a decoupled service (see CLAUDE.md).
 */
export default function AdvisorPage() {
  return (
    <>
      <Head>
        <title>Advisor | AgentFarm</title>
      </Head>
      <DashboardLayout title="Farmer Advisor">
        <div className="max-w-3xl">
          <ChatInterface />
        </div>
      </DashboardLayout>
    </>
  );
}

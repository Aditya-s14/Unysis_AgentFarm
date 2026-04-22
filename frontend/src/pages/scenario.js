import Head from 'next/head';
import { useState } from 'react';
import DashboardLayout from '@/components/Dashboard/DashboardLayout';
import ScenarioForm from '@/components/ScenarioBuilder/ScenarioForm';
import MapView from '@/components/Map/MapView';

/**
 * Scenario page — lets the user build and run a disruption scenario,
 * and previews farms/mandis/routes on a map of India.
 */
export default function ScenarioPage() {
  // TODO: replace with real fetched seed data from GET /api/farms etc.
  const [preview] = useState({
    farms: [
      { id: 'F1', name: 'Farm 1', crop_type: 'tomato', location: { lat: 15.3173, lng: 75.7139 } },
      { id: 'F2', name: 'Farm 2', crop_type: 'onion', location: { lat: 18.5204, lng: 73.8567 } },
      { id: 'F3', name: 'Farm 3', crop_type: 'mango', location: { lat: 12.9716, lng: 77.5946 } },
    ],
    demandPoints: [
      { id: 'M1', name: 'Yeshwanthpur Mandi', type: 'APMC', location: { lat: 13.0285, lng: 77.5547 } },
      { id: 'M2', name: 'Vashi Mandi', type: 'APMC', location: { lat: 19.0760, lng: 72.8777 } },
    ],
    routes: [],
  });

  return (
    <>
      <Head>
        <title>Scenario | AgentFarm</title>
      </Head>
      <DashboardLayout title="Run a Scenario">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <ScenarioForm />
          </div>
          <div className="lg:col-span-2">
            <MapView
              farms={preview.farms}
              demandPoints={preview.demandPoints}
              routes={preview.routes}
            />
          </div>
        </div>
      </DashboardLayout>
    </>
  );
}

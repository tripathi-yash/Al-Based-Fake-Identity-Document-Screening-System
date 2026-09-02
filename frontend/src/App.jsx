import React from "react";
import UploadForm from "./components/UploadForm";
import RiskDashboard from "./components/RiskDashboard";
import TamperHeatmap from "./components/TamperHeatmap";
import LedgerView from "./components/LedgerView";

// TODO: wire these together - upload calls POST /screen, response feeds
// RiskDashboard + TamperHeatmap; LedgerView calls GET /ledger separately.
export default function App() {
  return (
    <div>
      <h1>AI-Based Fake Identity & Document Screening System</h1>
      <UploadForm />
      <RiskDashboard />
      <TamperHeatmap />
      <LedgerView />
    </div>
  );
}

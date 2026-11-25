import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import Landing from "./pages/Landing";
import AppShell from "./pages/AppShell";
import OverviewPage from "./pages/Overview";
import AccountsPage from "./pages/Accounts";
import AccountDetailPage from "./pages/AccountDetail";
import ReviewPage from "./pages/Review";
import PipelinePage from "./pages/Pipeline";
import PlaygroundPage from "./pages/Playground";
import ComparePage from "./pages/Compare";
import NotFound from "./pages/NotFound";
import DemoPage from "./pages/Demo";
import MethodologyPage from "./pages/Methodology";
import { DemoProvider } from "./demo/DemoContext";
import { Loading } from "./components/ui";

const AnalyticsPage = lazy(() => import("./pages/Analytics"));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <DemoProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/app" element={<AppShell />}>
          <Route index element={<OverviewPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="accounts/:id" element={<AccountDetailPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="methodology" element={<MethodologyPage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="pipeline" element={<PipelinePage />} />
          <Route path="analytics" element={<Suspense fallback={<Loading />}><AnalyticsPage /></Suspense>} />
          <Route path="playground" element={<PlaygroundPage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
      </DemoProvider>
    </BrowserRouter>
  </StrictMode>,
);

import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Fleet } from "./pages/Fleet";
import { EngineDetail } from "./pages/EngineDetail";
import { WorkOrders } from "./pages/WorkOrders";
import { Models } from "./pages/Models";
import { About } from "./pages/About";

function NotFound() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-center">
      <p className="text-4xl font-semibold text-zinc-700">404</p>
      <p className="text-sm text-zinc-400">That page does not exist.</p>
      <a href="/" className="text-xs font-medium text-amber-300 hover:underline">
        Back to the fleet
      </a>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Fleet />} />
          <Route path="engines/:id" element={<EngineDetail />} />
          <Route path="work-orders" element={<WorkOrders />} />
          <Route path="models" element={<Models />} />
          <Route path="about" element={<About />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

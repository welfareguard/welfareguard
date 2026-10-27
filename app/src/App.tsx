import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { DataContext, type Bench } from "@/lib/data";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import Playground from "@/pages/Playground";
import Replay from "@/pages/Replay";
import Results from "@/pages/Results";
import Scenarios from "@/pages/Scenarios";
import Learn from "@/pages/Learn";

export default function App() {
  const [data, setData] = useState<Bench | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch(import.meta.env.BASE_URL + "data.json", { cache: "no-cache" })
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status} while loading data.json`); return r.json(); })
      .then((d: Bench) => { if (!d.guards || !d.samples || !d.scenarios) throw new Error("data.json is missing guards, samples or scenarios"); setData(d); })
      .catch((e: Error) => setError(e.message));
  }, []);
  return (
    <BrowserRouter>
      <DataContext.Provider value={data}>
        <Layout loading={!data && !error} error={error}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/try" element={<Playground />} />
            <Route path="/replay" element={<Replay />} />
            <Route path="/results" element={<Results />} />
            <Route path="/scenarios" element={<Scenarios />} />
            <Route path="/learn" element={<Learn />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </Layout>
      </DataContext.Provider>
    </BrowserRouter>
  );
}

import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell.jsx";
import HomePage from "./pages/HomePage.jsx";
import LyricsPage from "./pages/LyricsPage.jsx";
import VersesPage from "./pages/VersesPage.jsx";
import { getOptions } from "./lib/api.js";

function App() {
  const [options, setOptions] = useState({
    books: [],
    bible_versions: [],
    defaults: {},
    app: {},
    output_directory: "",
  });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [loadingLabel, setLoadingLabel] = useState("Checking backend connection...");

  useEffect(() => {
    let active = true;

    async function loadAppOptions() {
      try {
        if (active) {
          setLoadingLabel("Loading backend options...");
        }
        const payload = await getOptions();
        if (active) {
          setOptions(payload);
          setLoadError("");
          setLoadingLabel("Backend connected.");
        }
      } catch (error) {
        if (active) {
          setLoadError(error.message);
          setLoadingLabel("Backend connection failed.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadAppOptions();

    return () => {
      active = false;
    };
  }, []);

  return (
    <BrowserRouter>
      <AppShell options={options} loading={loading} loadingLabel={loadingLabel} loadError={loadError}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lyrics" element={<LyricsPage options={options} />} />
          <Route path="/verses" element={<VersesPage options={options} />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

export default App;

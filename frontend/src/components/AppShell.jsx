import { NavLink, useLocation } from "react-router-dom";
import ProgressBar from "./ProgressBar.jsx";

function AppShell({ options, loading, loadingLabel, loadError, children }) {
  const verseLookupReady = options.app?.verse_lookup_ready;
  const location = useLocation();
  const hideWorkspaceHero = location.pathname === "/verses" || location.pathname === "/lyrics";

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <div className="brand-block">
          <p className="brand-kicker">SlideGen</p>
          <h1>Automation Hub</h1>
          <p className="brand-copy">
            Build sermon slides and lyric decks with a polished web app and a Python backend that is
            ready to be shared.
          </p>
        </div>

        <nav className="nav-stack">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "nav-card active" : "nav-card")}>
            <span className="nav-title">Overview</span>
            <span className="nav-caption">Project home and quick jump-off</span>
          </NavLink>
          <NavLink to="/lyrics" className={({ isActive }) => (isActive ? "nav-card active" : "nav-card")}>
            <span className="nav-title">Lyrics Module</span>
            <span className="nav-caption">Compose songs, validate slides, export PPTX</span>
          </NavLink>
          <NavLink to="/verses" className={({ isActive }) => (isActive ? "nav-card active" : "nav-card")}>
            <span className="nav-title">Verses Module</span>
            <span className="nav-caption">Fetch chapter text, compare versions, export PPTX</span>
          </NavLink>
        </nav>

        <div className="sidebar-card">
          <p className="sidebar-label">Backend Output</p>
          <p className="sidebar-value">{options.output_directory || "Loading output folder..."}</p>
        </div>

        <div className="sidebar-card">
          <p className="sidebar-label">Status</p>
          <p className="sidebar-value">
            {loading
              ? "Loading defaults from FastAPI..."
              : loadError || (verseLookupReady ? "Connected and ready for verse lookup." : "Connected. Verse lookup needs server setup.")}
          </p>
        </div>
      </aside>

      <div className="workspace">
        {!hideWorkspaceHero ? (
          <header className="workspace-header">
            <div>
              <p className="page-kicker">React + FastAPI</p>
              <h2>Modern workflow for your slide automation</h2>
            </div>
            <div className="workspace-pills">
              <span>FastAPI backend</span>
              <span>PPTX export ready</span>
            </div>
          </header>
        ) : null}

        <ProgressBar active={loading} label={loadingLabel} accent="teal" />
        {loadError ? <div className="global-banner error">Backend options failed: {loadError}</div> : null}
        {children}
      </div>
    </div>
  );
}

export default AppShell;

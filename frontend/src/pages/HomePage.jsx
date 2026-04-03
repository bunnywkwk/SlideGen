import { Link } from "react-router-dom";

function HomePage() {
  return (
    <main className="page-grid">
      <section className="hero-panel">
        <div className="hero-copy-block">
          <p className="page-kicker">Separate Modules</p>
          <h3>Turn one long page into a real app flow.</h3>
          <p>
            The web app now has dedicated screens for lyrics and verses so each workflow can grow
            independently without turning the UI into one giant form.
          </p>
        </div>

        <div className="hero-stats">
          <div className="stat-card">
            <span className="stat-value">2</span>
            <span className="stat-label">Dedicated tools</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">1</span>
            <span className="stat-label">Shared API backend</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">24/7</span>
            <span className="stat-label">Portable generation flow</span>
          </div>
        </div>
      </section>

      <section className="module-grid">
        <article className="feature-panel feature-panel-warm">
          <p className="feature-kicker">Lyrics</p>
          <h3>Song drafting and slide planning</h3>
          <p>
            Paste songs, preview validation warnings, inspect draft chunks, and export a ready-made
            PowerPoint deck.
          </p>
          <Link to="/lyrics" className="feature-link">
            Open Lyrics Module
          </Link>
        </article>

        <article className="feature-panel feature-panel-cool">
          <p className="feature-kicker">Verses</p>
          <h3>Chapter lookup and dual-version slides</h3>
          <p>
            Choose book and chapter, preview matching verses, compare two Bible versions, and
            download the sermon deck.
          </p>
          <Link to="/verses" className="feature-link">
            Open Verses Module
          </Link>
        </article>
      </section>
    </main>
  );
}

export default HomePage;

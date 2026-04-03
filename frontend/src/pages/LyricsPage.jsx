import { useEffect, useState } from "react";
import ProgressBar from "../components/ProgressBar.jsx";
import StatusBanner from "../components/StatusBanner.jsx";
import { downloadPptWithProgress, generatePreviewWithProgress, saveBlobFile } from "../lib/api.js";

const createEmptySong = () => ({
  title: "",
  lyrics: "",
});

function LyricsPage({ options }) {
  const [form, setForm] = useState({
    include_welcome_slide: false,
    include_verse_labels: false,
    songs: [createEmptySong(), createEmptySong(), createEmptySong()],
  });
  const [preview, setPreview] = useState(null);
  const [busyLabel, setBusyLabel] = useState("");
  const [busyProgress, setBusyProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");

  function applyProgress(status) {
    setBusyLabel(status.message || "Working...");
    setBusyProgress(status.progress ?? 0);
  }

  useEffect(() => {
    const desiredSlots = Math.max(1, Math.min(options.defaults?.lyrics_song_slots || 3, 4));
    setForm((current) => {
      if (current.songs.length === desiredSlots) {
        return current;
      }

      const nextSongs = [...current.songs];
      while (nextSongs.length < desiredSlots) {
        nextSongs.push(createEmptySong());
      }
      return {
        ...current,
        songs: nextSongs.slice(0, desiredSlots),
      };
    });
  }, [options.defaults]);

  function updateSong(index, field, value) {
    setForm((current) => {
      const nextSongs = [...current.songs];
      nextSongs[index] = {
        ...nextSongs[index],
        [field]: value,
      };
      return {
        ...current,
        songs: nextSongs,
      };
    });
  }

  function addSong() {
    setForm((current) => {
      if (current.songs.length >= 4) {
        return current;
      }
      return {
        ...current,
        songs: [...current.songs, createEmptySong()],
      };
    });
  }

  function removeSong() {
    setForm((current) => {
      if (current.songs.length <= 1) {
        return current;
      }
      return {
        ...current,
        songs: current.songs.slice(0, -1),
      };
    });
  }

  function buildPayload() {
    const songs = form.songs
      .map((song) => ({
        title: song.title.trim(),
        lyrics: song.lyrics.trim(),
      }))
      .filter((song) => song.title || song.lyrics);

    if (songs.length === 0) {
      throw new Error("Add at least one song before generating a preview.");
    }

    for (const song of songs) {
      if (!song.title || !song.lyrics) {
        throw new Error("Each song needs both a title and lyrics.");
      }
    }

    return {
      job_type: "lyrics",
      template_path: null,
      include_welcome_slide: form.include_welcome_slide,
      include_verse_labels: form.include_verse_labels,
      songs,
    };
  }

  async function handlePreview() {
    try {
      setBusyLabel("Starting lyrics preview...");
      setBusyProgress(4);
      setErrorMessage("");
      const payload = buildPayload();
      const data = await generatePreviewWithProgress(payload, applyProgress);
      setPreview(data.lyrics_preview);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setBusyLabel("");
      setBusyProgress(0);
    }
  }

  async function handleDownload() {
    try {
      setBusyLabel("Starting lyrics export...");
      setBusyProgress(4);
      setErrorMessage("");
      const payload = buildPayload();
      const file = await downloadPptWithProgress(payload, applyProgress);
      saveBlobFile(file.blob, file.filename);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setBusyLabel("");
      setBusyProgress(0);
    }
  }

  return (
    <main className="page-grid">
      <section className="page-intro">
        <div>
          <p className="page-kicker">Lyrics Module</p>
          <h3>Build worship-song decks with a cleaner editorial workspace.</h3>
        </div>
        <div className="page-actions">
          <button type="button" className="ghost-button" onClick={addSong}>
            Add Song
          </button>
          <button type="button" className="ghost-button" onClick={removeSong}>
            Remove Song
          </button>
        </div>
      </section>

      <ProgressBar active={Boolean(busyLabel)} label={busyLabel} accent="orange" progressValue={busyProgress} />
      <StatusBanner tone="error">{errorMessage}</StatusBanner>

      <section className="module-layout">
        <div className="module-main">
          <article className="panel">
            <div className="panel-header">
              <div>
                <p className="feature-kicker">Deck Settings</p>
                <h4>Keep the workflow simple</h4>
              </div>
            </div>

            <div className="toggle-row">
              <label className="toggle-card compact">
                <input
                  type="checkbox"
                  checked={form.include_welcome_slide}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      include_welcome_slide: event.target.checked,
                    }))
                  }
                />
                <div>
                  <strong>Keep welcome slide</strong>
                  <p>Add a cover slide before the song slides.</p>
                </div>
              </label>

              <label className="toggle-card compact">
                <input
                  type="checkbox"
                  checked={form.include_verse_labels}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      include_verse_labels: event.target.checked,
                    }))
                  }
                />
                <div>
                  <strong>Show section labels</strong>
                  <p>Add section cues like `VERSE:` and `CHORUS:` to the slides.</p>
                </div>
              </label>
            </div>
          </article>

          <article className="panel">
            <div className="panel-header">
              <div>
                <p className="feature-kicker">Song Editor</p>
                <h4>Paste and organize lyrics</h4>
              </div>
              <span className="pill">{form.songs.length} song slot(s)</span>
            </div>

            <div className="stack-list">
              {form.songs.map((song, index) => (
                <div className="editor-card" key={`lyrics-song-${index}`}>
                  <div className="editor-heading">
                    <h5>Song {index + 1}</h5>
                    <span className="mini-pill">
                      {song.lyrics.trim() ? `${song.lyrics.trim().split(/\n+/).length} lines` : "Empty"}
                    </span>
                  </div>

                  <label className="field">
                    <span>Title</span>
                    <input
                      value={song.title}
                      onChange={(event) => updateSong(index, "title", event.target.value)}
                      placeholder="Enter the song title"
                    />
                  </label>

                  <label className="field">
                    <span>Lyrics</span>
                    <textarea
                      rows="10"
                      value={song.lyrics}
                      onChange={(event) => updateSong(index, "lyrics", event.target.value)}
                      placeholder="Paste lyrics here. You can use [Verse], [Chorus], [Bridge], and --- for manual slide breaks."
                    />
                  </label>
                </div>
              ))}
            </div>

            <div className="button-row">
              <button type="button" className="primary-button" onClick={handlePreview}>
                Preview Lyrics
              </button>
              <button type="button" className="secondary-button strong" onClick={handleDownload}>
                Download PPTX
              </button>
            </div>
          </article>
        </div>

        <aside className="module-sidebar">
          <article className="panel panel-sticky">
            <div className="panel-header">
              <div>
                <p className="feature-kicker">Preview</p>
                <h4>Slide planning</h4>
              </div>
            </div>

            {preview ? (
              <div className="preview-stack">
                <div className="info-card">
                  <span>Total slides</span>
                  <strong>{preview.total_slide_count}</strong>
                </div>
                <div className="info-card">
                  <span>Presentation mode</span>
                  <strong>{preview.presentation_mode}</strong>
                </div>

                {preview.songs.map((song) => (
                  <article key={song.title} className="preview-note">
                    <div className="preview-note-header">
                      <h5>{song.title}</h5>
                      <span>{song.slide_count} slides</span>
                    </div>

                    {song.warnings.length > 0 ? (
                      <p className="tone-warning">{song.warnings.join(" | ")}</p>
                    ) : (
                      <p className="tone-success">No validation warnings.</p>
                    )}

                    <pre>{song.draft_text}</pre>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <h5>No preview yet</h5>
                <p>Generate a lyrics preview to inspect the draft text and estimated slide count.</p>
              </div>
            )}
          </article>
        </aside>
      </section>
    </main>
  );
}

export default LyricsPage;

import { useEffect, useState } from "react";
import ProgressBar from "../components/ProgressBar.jsx";
import StatusBanner from "../components/StatusBanner.jsx";
import { downloadPptWithProgress, generatePreviewWithProgress, saveBlobFile } from "../lib/api.js";

const BASE_SONG_SLOTS = 4;
const MAX_SONG_SLOTS = 8;

const createEmptySong = () => ({
  title: "",
  lyrics: "",
});

function LyricsPage({ options }) {
  const [form, setForm] = useState({
    include_welcome_slide: false,
    include_verse_labels: false,
    songs: Array.from({ length: BASE_SONG_SLOTS }, createEmptySong),
  });
  const [preview, setPreview] = useState(null);
  const [busyLabel, setBusyLabel] = useState("");
  const [busyProgress, setBusyProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const desiredSlots = Math.max(
      BASE_SONG_SLOTS,
      Math.min(options.defaults?.lyrics_song_slots || BASE_SONG_SLOTS, MAX_SONG_SLOTS),
    );

    setForm((current) => {
      if (current.songs.length >= desiredSlots) {
        return current;
      }

      const nextSongs = [...current.songs];
      while (nextSongs.length < desiredSlots) {
        nextSongs.push(createEmptySong());
      }

      return {
        ...current,
        songs: nextSongs,
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

  function clearSong(index) {
    setForm((current) => {
      const nextSongs = [...current.songs];
      nextSongs[index] = createEmptySong();
      return {
        ...current,
        songs: nextSongs,
      };
    });
  }

  function removeSong(index) {
    setForm((current) => {
      if (current.songs.length <= BASE_SONG_SLOTS) {
        return current;
      }
      return {
        ...current,
        songs: current.songs.filter((_, songIndex) => songIndex !== index),
      };
    });
  }

  function addSong() {
    setForm((current) => {
      if (current.songs.length >= MAX_SONG_SLOTS) {
        return current;
      }
      return {
        ...current,
        songs: [...current.songs, createEmptySong()],
      };
    });
  }

  function applyProgress(status) {
    setBusyLabel(status.message || "Working...");
    setBusyProgress(status.progress ?? 0);
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

  const populatedSongs = form.songs.filter((song) => song.title.trim() || song.lyrics.trim()).length;
  const canAddSong = form.songs.length < MAX_SONG_SLOTS;

  return (
    <main className="page-grid">
      <section className="lyrics-mini-header">
        <div className="lyrics-mini-copy">
          <p className="page-kicker">Lyrics Module</p>
          <h3>Song editor</h3>
        </div>
        <div className="lyrics-mini-pills">
          <span className="pill">{form.songs.length} song slots</span>
          <span className="pill">{populatedSongs} ready</span>
        </div>
      </section>

      <ProgressBar active={Boolean(busyLabel)} label={busyLabel} accent="orange" progressValue={busyProgress} />
      <StatusBanner tone="error">{errorMessage}</StatusBanner>

      <section className="panel lyrics-controls-panel">
        <div className="toolbar-heading">
          <p className="feature-kicker">Lyrics Workflow</p>
        </div>

        <div className="lyrics-toolbar">
          <div className="lyrics-stat-card">
            <span>Default setup</span>
            <strong>4 songs ready to edit</strong>
            <p>Add extra slots only when you need them.</p>
          </div>

          <div className="toggle-row lyrics-toggle-row">
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
                <p>Add cues like `VERSE:` and `CHORUS:` on the slides.</p>
              </div>
            </label>
          </div>
        </div>

        <div className="lyrics-action-strip">
          <div className="lyrics-inline-actions">
            <button type="button" className="ghost-button" onClick={addSong} disabled={!canAddSong}>
              Add Song Slot
            </button>
            <span className="helper-chip">{canAddSong ? `Up to ${MAX_SONG_SLOTS} songs per deck` : "Maximum song slots reached"}</span>
          </div>

          <div className="button-row lyrics-button-row">
            <button type="button" className="primary-button verse-action-button" onClick={handlePreview}>
              Preview Lyrics
            </button>
            <button type="button" className="secondary-button strong verse-action-button" onClick={handleDownload}>
              Download PowerPoint
            </button>
          </div>
        </div>
      </section>

      <section className="lyrics-editor-surface">
        <div className="lyrics-surface-header">
          <div>
            <p className="feature-kicker">Song Editor</p>
            <h4>Paste each song into its own card</h4>
          </div>
          <span className="pill">{form.songs.length} visible cards</span>
        </div>

        <div className="lyrics-editor-grid">
          {form.songs.map((song, index) => {
            const canRemove = form.songs.length > BASE_SONG_SLOTS;
            const hasContent = song.title.trim() || song.lyrics.trim();

            return (
              <article className="editor-card lyrics-editor-card" key={`lyrics-song-${index}`}>
                <div className="editor-heading">
                  <div className="lyrics-editor-heading-copy">
                    <h5>Song {index + 1}</h5>
                    <span className="mini-pill">
                      {hasContent ? `${song.lyrics.trim().split(/\n+/).filter(Boolean).length} lines` : "Waiting for lyrics"}
                    </span>
                  </div>
                  <div className="editor-card-actions">
                    <button type="button" className="ghost-button lyrics-inline-button" onClick={() => clearSong(index)}>
                      Clear
                    </button>
                    {canRemove && index >= BASE_SONG_SLOTS ? (
                      <button
                        type="button"
                        className="ghost-button lyrics-inline-button lyrics-remove-button"
                        onClick={() => removeSong(index)}
                      >
                        Remove
                      </button>
                    ) : null}
                  </div>
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
                    rows="11"
                    value={song.lyrics}
                    onChange={(event) => updateSong(index, "lyrics", event.target.value)}
                    placeholder="Paste lyrics here. Use [Verse], [Chorus], [Bridge], and --- for manual slide breaks."
                  />
                </label>
              </article>
            );
          })}
        </div>
      </section>

      <section className="lyrics-preview-surface">
        {preview ? (
          <>
            <div className="summary-grid lyrics-summary-grid">
              <div className="info-card">
                <span>Total slides</span>
                <strong>{preview.total_slide_count}</strong>
              </div>
              <div className="info-card">
                <span>Presentation mode</span>
                <strong>{preview.presentation_mode}</strong>
              </div>
              <div className="info-card">
                <span>Song count</span>
                <strong>{preview.songs.length}</strong>
              </div>
            </div>

            <div className="lyrics-preview-grid">
              {preview.songs.map((song, index) => (
                <article key={`${song.title}-${index}`} className="preview-note lyrics-preview-song">
                  <div className="preview-note-header">
                    <div>
                      <h5>{song.title}</h5>
                      <span>{song.slide_count} slides planned</span>
                    </div>
                    <span className="mini-pill">{song.chunks.length} chunks</span>
                  </div>

                  {song.warnings.length > 0 ? (
                    <p className="tone-warning">{song.warnings.join(" | ")}</p>
                  ) : (
                    <p className="tone-success">Ready for export.</p>
                  )}

                  <div className="lyrics-chunk-list">
                    {song.chunks.map((chunk, chunkIndex) => (
                      <div key={`${song.title}-${chunkIndex}`} className="lyrics-chunk-card">
                        <div className="lyrics-chunk-header">
                          <strong>{chunk.section_label || chunk.section_name}</strong>
                          <span>{chunk.lines.length} lines</span>
                        </div>
                        <div className="lyrics-chunk-lines">
                          {chunk.lines.map((line, lineIndex) => (
                            <p key={`${song.title}-${chunkIndex}-${lineIndex}`}>{line}</p>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-state verse-empty-state">
            <h5>No preview yet</h5>
            <p>Use the song editor above, then load a lyrics preview. Clean slide chunks will appear here.</p>
          </div>
        )}
      </section>
    </main>
  );
}

export default LyricsPage;

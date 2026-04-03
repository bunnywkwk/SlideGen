import { useEffect, useState } from "react";
import CustomSelect from "../components/CustomSelect.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import StatusBanner from "../components/StatusBanner.jsx";
import { downloadVersePptWithProgress, generatePreviewWithProgress, saveBlobFile } from "../lib/api.js";

const FONT_OPTIONS = [
  "Arial Black",
  "Aptos",
  "Calibri",
  "Georgia",
  "Helvetica",
  "Tahoma",
  "Times New Roman",
  "Trebuchet MS",
  "Verdana",
];

const COLOR_OPTIONS = [
  { value: "#FFFFFF", label: "White", color: "#FFFFFF" },
  { value: "#F9E7B5", label: "Warm Cream", color: "#F9E7B5" },
  { value: "#CFFAFE", label: "Soft Cyan", color: "#CFFAFE" },
  { value: "#FFD6A5", label: "Peach Glow", color: "#FFD6A5" },
  { value: "#FBCFE8", label: "Rose Mist", color: "#FBCFE8" },
  { value: "#D9F99D", label: "Lime Light", color: "#D9F99D" },
];

function VersesPage({ options }) {
  const [form, setForm] = useState({
    book: "Romans",
    chapter: 8,
    start_verse: 1,
    end_verse: "",
    left_version: "NIV11",
    right_version: "APD",
    header_font_name: "Arial Black",
    verse_font_name: "Times New Roman",
    header_font_color: "#FFFFFF",
    verse_font_color: "#FFFFFF",
  });
  const [styleMode, setStyleMode] = useState("default");
  const [styleFile, setStyleFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busyLabel, setBusyLabel] = useState("");
  const [busyProgress, setBusyProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");

  const serverHasVerseLookup = Boolean(options.app?.verse_lookup_ready);
  const canRunVerseLookup = serverHasVerseLookup;

  useEffect(() => {
    setForm((current) => ({
      ...current,
      book: current.book || options.books[0] || "Romans",
      left_version: current.left_version || options.defaults?.left_version || "NIV11",
      right_version: current.right_version || options.defaults?.right_version || "APD",
    }));
  }, [options.books, options.defaults]);

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function handleStyleModeChange(nextMode) {
    setStyleMode(nextMode);
    setStyleFile(null);
  }

  function applyProgress(status) {
    setBusyLabel(status.message || "Working...");
    setBusyProgress(status.progress ?? 0);
  }

  function buildPayload() {
    if (!serverHasVerseLookup) {
      throw new Error("Verse lookup is not configured on this server yet. Add SLIDEGEN_YOUVERSION_API_KEY in the backend.");
    }

    if (styleMode !== "default" && !styleFile) {
      throw new Error("Choose a style file before downloading the PowerPoint.");
    }

    return {
      job_type: "verses",
      template_path: null,
      book: form.book,
      chapter: Number(form.chapter),
      start_verse: Number(form.start_verse),
      end_verse: form.end_verse === "" ? null : Number(form.end_verse),
      left_version: form.left_version.trim(),
      right_version: form.right_version.trim(),
      header_font_name: styleMode === "background" ? form.header_font_name : null,
      verse_font_name: styleMode === "background" ? form.verse_font_name : null,
      header_font_color: styleMode === "background" ? form.header_font_color : null,
      verse_font_color: styleMode === "background" ? form.verse_font_color : null,
      api_key: null,
    };
  }

  async function handlePreview() {
    try {
      setBusyLabel("Starting verses preview...");
      setBusyProgress(4);
      setErrorMessage("");
      const payload = buildPayload();
      const data = await generatePreviewWithProgress(payload, applyProgress);
      setPreview(data.verses_preview);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setBusyLabel("");
      setBusyProgress(0);
    }
  }

  async function handleDownload() {
    try {
      setBusyLabel("Starting verses export...");
      setBusyProgress(4);
      setErrorMessage("");
      const payload = buildPayload();
      const file = await downloadVersePptWithProgress(payload, styleMode === "default" ? null : styleFile, applyProgress);
      saveBlobFile(file.blob, file.filename);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setBusyLabel("");
      setBusyProgress(0);
    }
  }

  const styleAccept = ".png,.jpg,.jpeg,.webp";
  const selectedStyleLabel = styleFile ? styleFile.name : "No file selected";
  const bookOptions = options.books.map((book) => ({ value: book, label: book }));
  const versionOptions = (options.bible_versions ?? []).map((version) => ({ value: version, label: version }));
  const fontOptions = FONT_OPTIONS.map((font) => ({ value: font, label: font }));

  return (
    <main className="page-grid">
      <section className="verse-mini-header">
        <div className="verse-mini-copy">
          <p className="page-kicker">Verses Module</p>
          <h3>Verse generator</h3>
        </div>
        <div className="verse-mini-pills">
          <span className="pill">{options.books.length || 0} books</span>
          <span className="pill">{serverHasVerseLookup ? "Server key ready" : "Server key missing"}</span>
        </div>
      </section>

      <ProgressBar active={Boolean(busyLabel)} label={busyLabel} accent="teal" progressValue={busyProgress} />
      <StatusBanner tone="error">{errorMessage}</StatusBanner>
      {!serverHasVerseLookup ? (
        <StatusBanner tone="warning">
          Verse generation is disabled because the backend is missing SLIDEGEN_YOUVERSION_API_KEY.
        </StatusBanner>
      ) : null}

      <section className="panel verse-controls-panel">
        <div className="toolbar-heading">
          <p className="feature-kicker">Verse Lookup</p>
        </div>

        <div className="verse-toolbar verse-toolbar-inline">
            <div className="verse-toolbar-field">
              <CustomSelect
                label="Book"
                value={form.book}
                options={bookOptions}
                searchable
                onChange={(value) => updateField("book", value)}
              />
            </div>

            <label className="field verse-toolbar-field">
              <span>Chapter</span>
              <input
                type="number"
                min="1"
                value={form.chapter}
                onChange={(event) => updateField("chapter", event.target.value)}
              />
            </label>

            <label className="field verse-toolbar-field">
              <span>Start</span>
              <input
                type="number"
                min="1"
                value={form.start_verse}
                onChange={(event) => updateField("start_verse", event.target.value)}
              />
            </label>

            <label className="field verse-toolbar-field">
              <span>End</span>
              <input
                type="number"
                min="1"
                value={form.end_verse}
                onChange={(event) => updateField("end_verse", event.target.value)}
                placeholder="Optional"
              />
            </label>

            <div className="verse-toolbar-field">
              <CustomSelect
                label="Left"
                value={form.left_version}
                options={versionOptions}
                onChange={(value) => updateField("left_version", value)}
              />
            </div>

            <div className="verse-toolbar-field">
              <CustomSelect
                label="Right"
                value={form.right_version}
                options={versionOptions}
                onChange={(value) => updateField("right_version", value)}
              />
            </div>

        </div>

        <div className="verse-style-strip">
          <div className="verse-style-header">
            <p className="feature-kicker">Output Style</p>
          </div>

          <div className="choice-grid choice-grid-tight">
              <button
                type="button"
                className={styleMode === "default" ? "choice-card active" : "choice-card"}
                onClick={() => handleStyleModeChange("default")}
              >
                <strong>Default</strong>
                <span>Bundled verse template or fallback theme.</span>
              </button>
              <button
                type="button"
                className={styleMode === "background" ? "choice-card active" : "choice-card"}
                onClick={() => handleStyleModeChange("background")}
              >
                <strong>Background</strong>
                <span>Upload an image for the verse slides.</span>
              </button>
          </div>

          {styleMode === "background" ? (
            <div className="upload-card compact verse-style-upload">
              <label className="field">
                <span>Background Image</span>
                <input
                  type="file"
                  accept={styleAccept}
                  onChange={(event) => setStyleFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <p className="helper-copy">Selected file: {selectedStyleLabel}</p>

              <div className="verse-font-grid">
                <CustomSelect
                  label="Header Font"
                  value={form.header_font_name}
                  options={fontOptions}
                  onChange={(value) => updateField("header_font_name", value)}
                />

                <CustomSelect
                  label="Verse Font"
                  value={form.verse_font_name}
                  options={fontOptions}
                  onChange={(value) => updateField("verse_font_name", value)}
                />

                <CustomSelect
                  label="Header Color"
                  value={form.header_font_color}
                  options={COLOR_OPTIONS}
                  onChange={(value) => updateField("header_font_color", value)}
                />

                <CustomSelect
                  label="Verse Color"
                  value={form.verse_font_color}
                  options={COLOR_OPTIONS}
                  onChange={(value) => updateField("verse_font_color", value)}
                />
              </div>
            </div>
          ) : null}

          <div className="button-row verse-action-row">
            <button type="button" className="primary-button verse-action-button" onClick={handlePreview} disabled={!canRunVerseLookup}>
              Load Verse Preview
            </button>
            <button
              type="button"
              className="secondary-button strong verse-action-button"
              onClick={handleDownload}
              disabled={!canRunVerseLookup}
            >
              Download PowerPoint
            </button>
          </div>
        </div>
      </section>

      <section className="verse-preview-surface">
        {preview ? (
          <>
            <div className="summary-grid verse-summary-grid">
              <div className="info-card">
                <span>Reference</span>
                <strong>
                  {preview.book} {preview.chapter}
                </strong>
              </div>
              <div className="info-card">
                <span>Verse count</span>
                <strong>{preview.verse_count}</strong>
              </div>
              <div className="info-card">
                <span>Presentation mode</span>
                <strong>{preview.presentation_mode}</strong>
              </div>
            </div>

            <div className="verse-card-grid">
              {preview.verses.map((verse) => (
                <article key={verse.verse_number} className="preview-note verse-preview-card">
                  <div className="preview-note-header">
                    <h5>Verse {verse.verse_number}</h5>
                    <span>
                      {preview.left_version} / {preview.right_version}
                    </span>
                  </div>
                  <p>
                    <strong>{preview.left_version}:</strong> {verse.left_text}
                  </p>
                  <p>
                    <strong>{preview.right_version}:</strong> {verse.right_text}
                  </p>
                </article>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-state verse-empty-state">
            <h5>No preview yet</h5>
            <p>
              {canRunVerseLookup
                ? "Use the top lookup bar, then load the verses. The preview cards will appear here."
                : "This module will work after the backend server key is configured."}
            </p>
          </div>
        )}
      </section>
    </main>
  );
}

export default VersesPage;

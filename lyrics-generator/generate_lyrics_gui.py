import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import generate_lyrics_ppt as core


class DraftReviewWindow(tk.Toplevel):
    def __init__(self, parent, song_payloads):
        super().__init__(parent)
        self.parent = parent
        self.song_payloads = song_payloads
        self.title("Review Slide Drafts")
        self.geometry("980x760")
        self.minsize(820, 620)
        self.transient(parent)
        self.grab_set()
        self.editors = []

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        intro = (
            "Review the proposed slide draft for each song. "
            "Use section headers like [Verse] and put --- anywhere you want an exact new slide."
        )
        ttk.Label(container, text=intro, wraplength=900, foreground="#444").pack(anchor="w")

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True, pady=(10, 10))

        for payload in song_payloads:
            song = core.parse_song_text(payload["lyrics"], source_name=payload["slot_name"], title_hint=payload["title"])
            draft_text = core.song_to_draft_text(song)

            frame = ttk.Frame(notebook, padding=10)
            notebook.add(frame, text=payload["slot_name"])

            ttk.Label(frame, text=f"Title: {song.title}").pack(anchor="w")
            ttk.Label(
                frame,
                text="Edit the draft below. Every --- line becomes a new slide during generation.",
                foreground="#666",
            ).pack(anchor="w", pady=(4, 8))

            editor = ScrolledText(frame, width=100, height=28, wrap="word", font=("Segoe UI", 10))
            editor.pack(fill="both", expand=True)
            editor.insert("1.0", draft_text)
            self.editors.append((payload, editor))

        buttons = ttk.Frame(container)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Apply To Main Form", command=self._apply).pack(side="right")
        ttk.Button(buttons, text="Close", command=self.destroy).pack(side="right", padx=(0, 8))

    def _apply(self) -> None:
        updates = []
        for payload, editor in self.editors:
            updates.append(
                {
                    "panel_index": payload["panel_index"],
                    "title": payload["title"],
                    "lyrics": editor.get("1.0", "end").strip(),
                }
            )
        self.parent.apply_review_updates(updates)
        self.destroy()


class SongPanel:
    def __init__(self, parent, slot_index: int) -> None:
        self.slot_index = slot_index
        self.enabled_var = tk.BooleanVar(value=slot_index < 3)
        self.title_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Waiting for lyrics.")
        self.frame = ttk.LabelFrame(parent, text=self._frame_title(), padding=10)

        top = ttk.Frame(self.frame)
        top.pack(fill="x")

        self.enabled_check = ttk.Checkbutton(top, text="Use This Song", variable=self.enabled_var, command=self.refresh_enabled_state)
        self.enabled_check.pack(side="left")

        ttk.Label(top, text="Title").pack(side="left", padx=(14, 6))
        self.title_entry = ttk.Entry(top, textvariable=self.title_var, width=34)
        self.title_entry.pack(side="left", fill="x", expand=True)

        self.text = ScrolledText(self.frame, width=92, height=10, wrap="word", font=("Segoe UI", 10))
        self.text.pack(fill="both", expand=True, pady=(10, 8))

        tip = "Paste lyrics here. Use [Verse], [Chorus], [Bridge] and --- for exact slide breaks."
        ttk.Label(self.frame, text=tip, foreground="#666").pack(anchor="w")
        ttk.Label(self.frame, textvariable=self.status_var, foreground="#0b5").pack(anchor="w", pady=(6, 0))

        self.title_entry.bind("<KeyRelease>", self._on_change)
        self.text.bind("<<Modified>>", self._on_text_modified)
        self.refresh_enabled_state()

    def _frame_title(self) -> str:
        labels = ["1st Song", "2nd Song", "3rd Song", "4th Song"]
        return labels[self.slot_index]

    def refresh_enabled_state(self) -> None:
        state = "normal" if self.enabled_var.get() else "disabled"
        self.title_entry.configure(state=state)
        self.text.configure(state=state)
        if not self.enabled_var.get():
            self.status_var.set("Optional slot disabled.")
        else:
            self._update_status()

    def _on_change(self, _event=None) -> None:
        if self.enabled_var.get():
            self._update_status()

    def _on_text_modified(self, _event=None) -> None:
        if self.text.edit_modified():
            self.text.edit_modified(False)
            if self.enabled_var.get():
                self._update_status()

    def _update_status(self) -> None:
        body = self.text.get("1.0", "end").strip()
        if not body:
            self.status_var.set("Paste lyrics to validate this song.")
            return
        warnings = core.validate_song_text(body, self.title_var.get().strip() or None)
        if warnings:
            self.status_var.set("Check: " + "; ".join(warnings[:2]))
        else:
            try:
                song = core.parse_song_text(body, source_name=self._frame_title(), title_hint=self.title_var.get().strip() or None)
                slides = 1 + len(core.build_song_chunks(song))
                self.status_var.set(f"Ready: {song.title} ({slides} slide(s))")
            except Exception as err:
                self.status_var.set(f"Check: {err}")

    def get_payload(self):
        return {
            "enabled": self.enabled_var.get(),
            "title": self.title_var.get().strip(),
            "lyrics": self.text.get("1.0", "end").strip(),
        }

    def set_payload(self, payload) -> None:
        self.enabled_var.set(payload["enabled"])
        self.title_var.set(payload["title"])
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", payload["lyrics"])
        self.text.edit_modified(False)
        self.refresh_enabled_state()


class LyricsPPTGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Lyricsify")
        self.geometry("1060x980")
        self.minsize(960, 860)

        self.base_dir = Path(__file__).resolve().parent
        self.samples_dir = self.base_dir / "samples-ppt"
        self.default_template = core.resolve_template(None, self.samples_dir)

        self.template_var = tk.StringVar(value=str(self.default_template))
        self.out_dir_var = tk.StringVar(value=str(self.base_dir / "generated-ppt"))
        self.include_welcome_var = tk.BooleanVar(value=False)
        self.include_verse_labels_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready.")
        self.output_file_var = tk.StringVar(value="")
        self.datetime_var = tk.StringVar(value="")
        self._pending_songs = []
        self._loading = False
        self._loading_start = 0.0
        self._loading_dots = 0
        self._busy_base_text = "Working"

        self.song_panels = []
        self._build_ui()
        self._tick_datetime()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        container = ttk.Frame(canvas, padding=14)

        container.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas_window = canvas.create_window((0, 0), window=container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _resize_container(event):
            canvas.itemconfigure(canvas_window, width=event.width)

        canvas.bind("<Configure>", _resize_container)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._bind_mousewheel(canvas)

        top = ttk.Frame(container)
        top.pack(fill="x")
        ttk.Label(top, text="Date/Time").pack(side="left")
        ttk.Label(top, textvariable=self.datetime_var).pack(side="left", padx=(8, 0))

        config = ttk.LabelFrame(container, text="Presentation Settings", padding=10)
        config.pack(fill="x", pady=(12, 10))

        self._path_row(config, 0, "Template PPTX", self.template_var, self._pick_template)
        self._path_row(config, 1, "Output Folder", self.out_dir_var, self._pick_out_dir)
        ttk.Checkbutton(config, text="Keep sample WELCOME slide", variable=self.include_welcome_var).grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Checkbutton(config, text="Show VERSE: labels", variable=self.include_verse_labels_var).grid(row=2, column=1, sticky="w", pady=(6, 0))

        actions = ttk.Frame(config)
        actions.grid(row=2, column=2, sticky="e", pady=(6, 0))
        ttk.Button(actions, text="Load Sample Songs", command=self._load_sample_songs).pack(side="left")
        ttk.Button(actions, text="Clear Songs", command=self._clear_songs).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Review Slides", command=self._open_review_window).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Preview Validation", command=self._preview_validation).pack(side="left")
        ttk.Button(actions, text="Generate PPT", command=self._generate_clicked).pack(side="left", padx=(8, 0))

        for col in range(3):
            config.grid_columnconfigure(col, weight=1 if col == 1 else 0)

        order_bar = ttk.LabelFrame(container, text="Song Order", padding=10)
        order_bar.pack(fill="x", pady=(0, 10))
        ttk.Label(order_bar, text="Songs appear in the PPT from top to bottom. Use the move buttons to reorder.").pack(side="left")
        ttk.Button(order_bar, text="Move 1st Down", command=lambda: self._move_song(0, 1)).pack(side="left", padx=(16, 6))
        ttk.Button(order_bar, text="Move 2nd Up", command=lambda: self._move_song(1, -1)).pack(side="left", padx=6)
        ttk.Button(order_bar, text="Move 2nd Down", command=lambda: self._move_song(1, 1)).pack(side="left", padx=6)
        ttk.Button(order_bar, text="Move 3rd Up", command=lambda: self._move_song(2, -1)).pack(side="left", padx=6)
        ttk.Button(order_bar, text="Move 3rd Down", command=lambda: self._move_song(2, 1)).pack(side="left", padx=6)
        ttk.Button(order_bar, text="Move 4th Up", command=lambda: self._move_song(3, -1)).pack(side="left", padx=6)

        songs_container = ttk.Frame(container)
        songs_container.pack(fill="both", expand=True)

        for index in range(4):
            panel = SongPanel(songs_container, index)
            panel.frame.pack(fill="both", expand=True, pady=(0 if index == 0 else 8, 0))
            self.song_panels.append(panel)

        status_frame = ttk.LabelFrame(container, text="Status", padding=10)
        status_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(status_frame, textvariable=self.status_var, foreground="#0b5").pack(anchor="w")
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=420)
        self.progress.pack(anchor="w", pady=(8, 8))
        ttk.Label(status_frame, text="Last Output").pack(anchor="w")
        ttk.Entry(status_frame, textvariable=self.output_file_var, width=120, state="readonly").pack(fill="x", pady=(4, 0))

    def _bind_mousewheel(self, canvas: tk.Canvas) -> None:
        def _on_mousewheel(event):
            delta = 0
            if hasattr(event, "delta") and event.delta:
                delta = int(-event.delta / 120)
            elif getattr(event, "num", None) == 4:
                delta = -1
            elif getattr(event, "num", None) == 5:
                delta = 1
            if delta:
                canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel)
        canvas.bind_all("<Button-5>", _on_mousewheel)

    def _path_row(self, parent, row, label, var, pick_cmd) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=var, width=88).grid(row=row, column=1, sticky="we", pady=6, padx=(8, 8))
        ttk.Button(parent, text="Browse", command=pick_cmd).grid(row=row, column=2, sticky="e", pady=6)

    def _pick_template(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose sample PPTX",
            filetypes=[("PowerPoint files", "*.pptx"), ("All files", "*.*")],
            initialdir=str(self.samples_dir),
        )
        if path:
            self.template_var.set(path)

    def _pick_out_dir(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder", initialdir=str(self.base_dir))
        if path:
            self.out_dir_var.set(path)

    def _tick_datetime(self) -> None:
        self.datetime_var.set(datetime.now().strftime("%B %d, %Y %I:%M:%S %p"))
        self.after(1000, self._tick_datetime)

    def _set_busy(self, busy: bool, message: str) -> None:
        self._loading = busy
        if busy:
            self._loading_start = time.time()
            self._loading_dots = 0
            self._busy_base_text = message.rstrip(".")
            self.status_var.set(message)
            self.progress.start(10)
            self._animate_loading()
        else:
            self.progress.stop()
            self.status_var.set(message)

    def _animate_loading(self) -> None:
        if not self._loading:
            return
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        elapsed = int(time.time() - self._loading_start)
        self.status_var.set(f"{self._busy_base_text}{dots} ({elapsed}s)")
        self.after(300, self._animate_loading)

    def _move_song(self, index: int, direction: int) -> None:
        other = index + direction
        if other < 0 or other >= len(self.song_panels):
            return
        payload_a = self.song_panels[index].get_payload()
        payload_b = self.song_panels[other].get_payload()
        self.song_panels[index].set_payload(payload_b)
        self.song_panels[other].set_payload(payload_a)
        self.status_var.set(f"Moved song slot {index + 1} {'down' if direction > 0 else 'up'}.")

    def _slot_name(self, idx: int) -> str:
        return ["1st Song", "2nd Song", "3rd Song", "4th Song"][idx - 1]

    def _clear_songs(self) -> None:
        for idx, panel in enumerate(self.song_panels):
            panel.set_payload({"enabled": idx < 3, "title": "", "lyrics": ""})
        self.status_var.set("Cleared all song panels.")

    def _load_sample_songs(self) -> None:
        sample_files = list(core.iter_song_files(self.base_dir / "txt-lyrics"))[:4]
        if len(sample_files) < 3:
            messagebox.showerror("Not Enough Samples", "Add at least 3 sample .txt songs in txt-lyrics first.")
            return

        self._clear_songs()
        for idx, path in enumerate(sample_files):
            try:
                song = core.parse_song_file(path)
                lyrics = path.read_text(encoding="utf-8").strip()
            except Exception as err:
                messagebox.showerror("Sample Load Failed", f"Could not load {path.name}: {err}")
                return

            self.song_panels[idx].set_payload(
                {
                    "enabled": True,
                    "title": song.title,
                    "lyrics": lyrics,
                }
            )

        self.status_var.set(f"Loaded {len(sample_files)} sample song(s) from txt-lyrics.")

    def _selected_payloads_for_review(self):
        payloads = []
        for idx, panel in enumerate(self.song_panels, start=1):
            payload = panel.get_payload()
            if not payload["enabled"]:
                continue
            if not payload["title"] and not payload["lyrics"]:
                continue
            if not payload["title"]:
                raise ValueError(f"{self._slot_name(idx)} title is required.")
            if not payload["lyrics"]:
                raise ValueError(f"{self._slot_name(idx)} lyrics are required.")
            payloads.append(
                {
                    "panel_index": idx - 1,
                    "slot_name": self._slot_name(idx),
                    "title": payload["title"],
                    "lyrics": payload["lyrics"],
                }
            )
        return payloads

    def _open_review_window(self) -> None:
        try:
            payloads = self._selected_payloads_for_review()
            if len(payloads) < 1:
                raise ValueError("Add at least one song before reviewing slide drafts.")
            DraftReviewWindow(self, payloads)
        except Exception as err:
            messagebox.showerror("Review Error", str(err))

    def apply_review_updates(self, updates) -> None:
        for update in updates:
            panel = self.song_panels[update["panel_index"]]
            payload = panel.get_payload()
            payload["title"] = update["title"]
            payload["lyrics"] = update["lyrics"]
            panel.set_payload(payload)
        self.status_var.set("Applied reviewed slide drafts to the main form.")

    def _collect_songs(self):
        songs = []
        warnings = []
        for idx, panel in enumerate(self.song_panels, start=1):
            payload = panel.get_payload()
            if not payload["enabled"]:
                continue
            if not payload["title"] and not payload["lyrics"]:
                continue
            if not payload["title"]:
                raise ValueError(f"{self._slot_name(idx)} title is required.")
            if not payload["lyrics"]:
                raise ValueError(f"{self._slot_name(idx)} lyrics are required.")
            song = core.parse_song_text(payload["lyrics"], source_name=f"Song {idx}", title_hint=payload["title"])
            songs.append(song)
            issues = core.validate_song_text(payload["lyrics"], payload["title"])
            if issues:
                warnings.append(f"{song.title}: " + "; ".join(issues))
        return songs, warnings

    def _preview_validation(self) -> None:
        try:
            songs, warnings = self._collect_songs()
            if len(songs) < 3 or len(songs) > 4:
                raise ValueError("Enter exactly 3 or 4 songs.")
            lines = []
            for song in songs:
                slide_total = 1 + len(core.build_song_chunks(song, include_verse_labels=self.include_verse_labels_var.get()))
                lines.append(f"{song.title}: {slide_total} slide(s)")
            if warnings:
                lines.append("")
                lines.append("Warnings:")
                lines.extend(warnings)
            messagebox.showinfo("Validation Preview", "\n".join(lines))
        except Exception as err:
            messagebox.showerror("Validation Error", str(err))

    def _generate_clicked(self) -> None:
        try:
            songs, warnings = self._collect_songs()
            if len(songs) < 3 or len(songs) > 4:
                raise ValueError("Enter exactly 3 or 4 songs.")
            template = Path(self.template_var.get().strip())
            if not template.exists():
                raise ValueError("Choose a valid template PPTX.")
            out_dir = Path(self.out_dir_var.get().strip())
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as err:
            messagebox.showerror("Invalid Input", str(err))
            return

        if warnings:
            proceed = messagebox.askyesno("Warnings Detected", "Some songs have warnings.\n\n" + "\n".join(warnings[:6]) + "\n\nGenerate anyway?")
            if not proceed:
                return

        self._pending_songs = songs
        self._set_busy(True, "Generating slides...")
        threading.Thread(target=self._generate_worker, daemon=True).start()

    def _generate_worker(self) -> None:
        try:
            output_path = core.unique_output_path(Path(self.out_dir_var.get().strip()), 1)
            core.create_presentation(
                template_path=Path(self.template_var.get().strip()),
                output_path=output_path,
                songs=self._pending_songs,
                include_welcome_slide=self.include_welcome_var.get(),
                include_verse_labels=self.include_verse_labels_var.get(),
            )
            self.after(0, lambda: self._handle_success(output_path))
        except Exception as err:
            self.after(0, lambda msg=str(err): self._handle_failure(msg))

    def _handle_success(self, output_path: Path) -> None:
        self._set_busy(False, "Lyrics PPT generated.")
        self.output_file_var.set(str(output_path))

    def _handle_failure(self, message: str) -> None:
        self._set_busy(False, f"Generation failed: {message}")
        messagebox.showerror("Generation Failed", message)


def main() -> None:
    app = LyricsPPTGui()
    app.mainloop()


if __name__ == "__main__":
    main()

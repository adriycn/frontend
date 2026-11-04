# CReaper

Windows desktop app (PyQt6) for downloading, trimming and AI-clipping videos, plus a FastAPI backend
(Railway) that handles accounts, tokens and AI calls.

## Layout

| Path | What it is |
|---|---|
| `desktop/` | The app. Entry point `desktop/main.py`. Run all desktop commands from this folder (imports are `services.*`, `ui.*`, `utils.*`). |
| `backend/` | FastAPI server (`backend/main.py`, ~26 routes under `/api/...`; most logic is in `services.py`). **A separate git repo** (`github.com/adriycn/backend`), nested inside this one. Commit there separately. |
| `bootstrapper/` | `CReaperBootstrapper.exe`: installs and updates the app and launches it. |
| `Website/` | Web client and docs. |
| `build.py`, `CReaper*.spec` | Release build: PyInstaller → `Releases/CReaper-<ver>.zip`. Version is read from `AppSettings.APP_VERSION` in `desktop/utils/settings.py`. |
| `patch*.py` (root), `backend/append_*.py`, `backend/patch_*.py` | One-off source-rewriting scripts from earlier work. They are not part of the app, so don't run them. |
| `build/`, `dist/`, `Releases/`, `desktop/build`, `desktop/dist`, `desktop/obfuscated` | Build output. Don't edit or search these. They contain stale copies of the source. |
| `legacy_caption_aligners/`, `scratch/` | Old or experimental code. Not imported by the app. |

## Commands

```powershell
# Desktop tests (~514): run from desktop/
cd desktop; python -m pytest -q
python -m pytest tests/test_realtime_preview.py -q     # one file

# Backend tests (~604): run from backend/
cd backend; python -m pytest -q

# Run the app from source: frozen-only checks (bootstrapper handoff) are skipped when not frozen
cd desktop; python main.py

# Release build
python build.py
```

Python 3.14 is installed locally; the backend Docker image uses 3.12.

## Testing rules

- `desktop/tests/conftest.py` fakes a signed-in session and gives every test its own `%LOCALAPPDATA%`. Use
  `@pytest.mark.signed_out` to opt out.
- `backend/conftest.py` strips every AI/DB credential and sets `CREAPER_NO_DOTENV=1`, so a missed mock fails
  instead of spending quota. **Never run evals or tests against production AI keys** (`backend/.env`): this
  once drained the Groq quota and broke real users' clipper jobs. `backend/eval/` harnesses must use isolated keys.

## Desktop architecture

`MainWindow` (`ui/main_window.py`) is a thin shell. Each feature is a `*Manager` that holds a reference to the
window (`self.mw`) and puts its widgets on it as attributes (e.g. `mw.ced_player`, `mw.ced_caption_y`). Widgets
are mostly built in `ui/main_window_ui.py` (`MainWindowUI`, ~2900 lines).

| Feature | UI | Services |
|---|---|---|
| Standard Trim (local file or URL) | `ui/main_window_editor.py` (`EditorManager`), `ui/components/trim_timeline.py`, `ui/components/video_preview.py` | `trim_service.py`, `preview_stream.py`, `preview_proxy.py` |
| Auto Clipper ("AI Clipper") | `ui/main_window_clipper.py` (`ClipperManager`) | `clipper_service.py` (`ClipperPipelineThread`), `reframer.py`, `caption_timeline.py`, `clip_effects.py`, `backgrounds.py`, `output_format.py`, `preview_service.py`, `preview_fast.py` |
| Clip editor ("Edit Clip", opened from Auto Clipper results) | `ui/clip_editor.py` (`ClipEditorManager`) | `clip_project.py` |
| AI Best Moments / highlights | `ui/main_window_workflow.py`, `ui/main_window_highlights.py`, `ui/components/ai_card.py` | `ai_service.py`, `moment_scout.py`, `moment_discovery.py`, `highlight_service.py` |
| Downloader / convert | `ui/main_window_downloader.py` | `downloader_service.py`, `media_convert_service.py` |
| Account (Discord OAuth), tokens, settings, storage | `main_window_account.py`, `main_window_settings.py`, `main_window_storage.py` | `auth_service.py`, `utils/session.py` (DPAPI-encrypted refresh token), `storage_service.py` |

Conventions:
- **All slow work runs in a `QThread` subclass** with `progress`/`done`/`failed` signals and a cooperative
  cancel (`cancel_check` callables passed down into FFmpeg runners). Never block the UI thread. On close,
  `MainWindow.closeEvent` interrupts and waits on running threads. New long-running threads must be added there.
- FFmpeg/ffprobe come from `utils/ffmpeg_locator.py` (bundled `desktop/bin/`). Spawn them with `NO_WINDOW` and
  pass arguments as a list, never through a shell.
- User data goes through `utils/app_paths.user_data_dir` (see "Install location" below; by default
  `%LOCALAPPDATA%\CReaper`). Settings are in `settings.json` via `AppSettings.get_value/set_value`. Logs go to
  `debug.log` there. `sys.excepthook` logs exceptions raised in signal handlers instead of letting PyQt6 abort the
  process.
- Theme colours come from one table in `ui/styles.py` (`theme_colors`). Dialogs use
  `ui/components/app_dialog.py` (`ask`/`inform`), not `QMessageBox`.
- Module docstrings explain the design and the *why* (past bugs, platform quirks). Read them before changing a
  module, and keep them current.

### Install location (any drive)
CReaper can live on any drive (a full C: was the reason). `%LOCALAPPDATA%\CReaper` is the **anchor**: it always
holds `location.json` (`{"install_root", "data_root"}`, absent = everything in the anchor, the layout of every older
install), `settings.json`, `session.dat`, `device_id.json`, `debug.log` and `.bootstrapper_handoff`.
- `install_root` = `CReaperBootstrapper.exe`, `state.json`, `versions\<ver>\`, `staging\`, `downloads\`.
  `data_root` (`<install_root>\data`) = `install_location.BULK_DIRS`: `models`, `projects`, `cache`,
  `preview_cache`, `music`, `tmp`.
- Shared logic: `desktop/utils/install_location.py` (app) and a copy inside `bootstrapper/main.py` (it ships as one
  exe). `tests/test_install_location.py` keeps the two in agreement. Change both together.
- Always go through `app_paths.user_data_dir(...)` (or `install_location.data_path`). Never build
  `%LOCALAPPDATA%\CReaper\<bulky folder>` by hand. A bulky folder that exists only in the anchor is still used (data
  not yet carried over), so a failed move never hides projects.
- `main.py` calls `install_location.apply_temp_dir()` first: TEMP/TMP point at `<data_root>\tmp`, so FFmpeg and
  download work files follow the drive too.
- The chosen folder is always a dedicated `...\CReaper` folder (`dedicated_folder`), because the launcher's cleanup
  deletes leftovers inside the install root. Never relax that.
- Launcher options: `--install-dir <folder>` (no dialog; also moves an existing install), `--change-location`
  (dialog, used by Settings > Storage > "Change location"), env `CREAPER_NO_SHORTCUTS=1` (scripted installs and
  tests must set it: shortcuts are made in the real profile, whatever LOCALAPPDATA says).
- A move copies first and deletes last (`migrate_install`); an install on a drive that is gone shows an error with
  "Choose another folder" and is never silently re-created on C:.
- Test a launcher change with the real frozen exe: build it with the flags from `build.py` into a scratch folder
  (not `Releases/`), use a throwaway `LOCALAPPDATA`, and `--install-dir` on another drive.

### Video preview pipeline
- `VideoPreview` wraps Qt Multimedia `QMediaPlayer` + `QVideoWidget` (Qt's FFmpeg backend decodes on its own
  threads), or with `graphics=True` a `QGraphicsVideoItem` on the clip editor's `EditCanvas`. Text and handles
  can't be drawn over a `QVideoWidget`, because it is a native window.
- Smooth playback depends mostly on the UI thread. Position updates are coalesced to 30 Hz, scrub seeks to one
  per 45 ms (the newest one wins), and the full-window `AnimatedBackground` pauses while any preview plays
  (`VideoPreview.add_activity_listener`) and otherwise repaints at most 15 fps.
- The player must be created **before** its video surface. Qt destroys children in creation order, and a
  `QGraphicsVideoItem` destroyed while its player still feeds it frames deadlocked at teardown.
- Hardware decoding is off by default because some drivers show a solid green picture. It can be turned on with
  the Settings toggle (`preview_hw_decoding`), which Qt reads once per process. A green first frame turns it off
  again (`looks_like_failed_hw_frame`).
- Standard Trim plays a demanding video (`preview_proxy.is_demanding`: 4K, 1440p60) at once, then hot-swaps to a
  720p copy built in the background.
- AV1 has no software decoder in Qt's backend, so `preview_proxy.py` makes a 480p H.264 proxy (PyAV) cached in
  `preview_cache/`. Online videos stream ≤720p through `preview_stream.py` (a loopback HLS master playlist).
  **Exports always use the original source.**
- YouTube auto-dubs videos into many audio languages. Every audio pick ranks the ORIGINAL track first
  (`preview_stream._language_rank`), as yt-dlp's `bestaudio` does for exports. A plain bitrate `max()` used to play
  a Hindi/Arabic dub in Standard Trim and AI Best Moments previews.
- The Auto Clipper settings preview is a still image. `preview_service.py` grabs one frame with FFmpeg, and
  `preview_fast.py` re-applies look changes in numpy, mirroring FFmpeg's filter maths. Captions and the hook are
  pre-rendered from the same ASS as the export, so preview and export match.
- The clip editor preview is a **text-free** half-size render (`render(..., proxy=True, burn_text=False)`).
  Captions, the headline and texts are drawn live on `ui/components/edit_canvas.py` from `services/clip_overlay.py`,
  which uses the same numbers as the export. Only changes to `clip_project.render_key(edit)` (anything except
  `TEXT_KEYS`) start a new render. The old preview keeps playing meanwhile, with `preview_a.mp4` and
  `preview_b.mp4` used in turn.
- Canvas items report one `itemChanged` per drag release, which is one undo step. Their geometry is stored in the
  edit (`caption_x/_y/_scale/_rot`, `hook_x/_y/_scale/_rot`, `texts[i].x/y/scale/rot`) and exported as ASS
  `\pos`, `\fs` and `\frz`.

### Output layout, framing and hook headline
- `services/output_format.py` is the single source of layout truth: `layout(name, src_w, src_h, framing)` →
  `canvas`, `pic` (the rectangle where the footage is drawn), `fit`, `caption_y`, `caption_range`, `hook_top`,
  `hook_scale`. Canvases: 9:16 1080×1920, 16:9 1920×1080, 1:1 1080×1080, 4:5 1080×1350.
- Framing values are `"fill"` (the default: crop around the speaker) and `"fit"` (labelled "Square close-up"):
  a zoomed square picture tracked on the speaker, centred, with a background from `backgrounds.py` above and
  below (`output_format.fit_shape`; 9:16 → 1080² at y=420).
  - "Fit" is never the whole source frame shrunk. It used to be, as "Show entire video", and users rejected the
    tiny strip.
  - Fill never falls back to fit, not even for very wide sources. Saved values must stay `fill`/`fit` for compatibility. A `fit` saved before the speaker-framing
  change is reset to fill once (`main_window_clipper.saved_framing`, flag `clipper_framing_fill_reset`).
- Speaker reframing is `services/reframer.py`:
  - `plan_reframe(..., pic=(w, h))` plans in the picture's real shape. The pipeline (`_reframe_video`) renders
    `plan.crop_w × crop_h` at `centers_x/y`.
  - One zoom per clip comes from the face size (`zoom_for`: the face is about 20% of the height, from 1.12×
    up to `max_zoom`). Clips without faces aren't zoomed.
  - The Auto Clipper still preview uses `frame_crop`, which applies the same rules to one frame
    (`preview_fast.load_picture(reframe=True)`).
  - The editor's `picture.mp4` is already reframed, so preview, editor and export share one crop.
  - Tests: `tests/test_speaker_reframing.py` (white squares stand in for faces).
- The `"9:16 square"` legacy layout (1080² picture at y=420, hook in the band above) exists only so old editor
  projects re-render unchanged. Don't remove it.
- Hook headline placement lives in `services/hook_placement.py` (`place` / `place_for_layout`):
  - "band": a picture with free space above it gets the headline bottom-anchored just above the picture, sized to
    fit, never over the footage.
  - "card": a picture that fills the frame (or a band too thin) gets bold white text with a heavy dark outline,
    slightly below the middle and clear of the captions. There is no box behind it: the white rounded card was
    removed because users disliked it. The name "card" stays for the placement.
  - Wrapping is `hook_layout(max_chars=...)`.
  - Everything goes through `clipper_service.ass_layout_args(lay)` / `emoji_place(lay, caption_y, override)`, so
    the pipeline, the Auto Clipper preview, the emoji and the editor canvas share one calculation.
  - Legacy square projects keep their fixed `y=310` headline until it is moved.
- The framing UI labels are "Fill screen (crop edges)" and "Square close-up" (`ui/components/framing_tile.py`).

### Captions and fonts
- Captions are short subtitle lines, TikTok style: one or two lines, a few words each, with the spoken word
  optionally highlighted. All layout is in `services/caption_layout.py`:
  - `group` wraps the words, `place_lines` positions the lines, `ass_events` writes the export/preview ASS (one
    Dialogue per line, with `\fn<full name>\b0`), and `canvas_spec` produces the editor canvas items.
  - Line widths come from the font's own metrics (`fonts.Face.width`, within ~2% of libass), so lines never run
    past the frame and the canvas matches the export.
  - Word display times come from `CaptionTimeline.display_words()`, or `clip_project.display_words(edit)` in the
    editor.
- Styles are `word_highlight` (the default: words shown together, the spoken word lit word by word),
  `tiktok`, `box_highlight` (the spoken word on a coloured box), `pop` (the original one-word coloured captions,
  in any font), `bold_highlight`, `subtitle` and `minimal`.
  - The user's changes go in `edit["caption_look"]` (`LOOK_KEYS`): font, weight, size, text, outline, shadow,
    highlight and box colours, highlight text/box, alignment, spacing and capitals. Sizes are cap heights, so
    changing fonts keeps the size.
  - The same controls (`ui/components/caption_style_ui.CaptionLookPanel`) are on the AI Clipper page (step 5,
    `size_in_look`) and in the clip editor's Captions tab.
  - The old one-word styles `classic`/`clean`/`boxed`/`big` are LEGACY: old projects keep rendering through the
    old path in `export_ass`.
  - The last look chosen in the editor is saved (`caption_layout.saved`/`remember`, settings keys
    `caption_style`/`caption_look`). New Auto Clipper clips and the Auto Clipper preview use it.
- Fonts are 26 static TTFs (14 families, OFL/Apache, ~5.7 MB) in `desktop/assets/fonts/`. Licences are in
  `licenses/`, the sources in `SOURCES.md`, and the dev-only download script is `fetch_fonts.py`.
  - The folder is flat because libass `fontsdir` doesn't search subfolders.
  - They must be static fonts: libass can't select a weight inside a variable font.
  - **Every ASS burn must use `fonts.ass_filter(path)`**, which adds `fontsdir`. Qt registers a font file lazily
    (`fonts.qt_family`), and `edit_canvas.bundled_font` sizes it the way libass does.
  - `build.py` ships `assets/fonts`.
- Players: `VideoPreview.release_all()` stops every player before teardown (on `aboutToQuit`, and from
  `tests/conftest.py` at session end). A player still loaded at Python exit hung the process at 0% CPU (the
  "QFFmpeg::AudioRenderer" thread).

### Clip editor screen (`ui/clip_editor.py`)
- The header shows "Editing clip N of M", the clip's headline, and Previous/Next clip buttons. Switching saves
  first.
- The side tabs are Captions, Headline, Text, Sound and Background. The Background tab is `mw.ced_bg_tab`
  (`ced_bg_tab_index`); don't use tab indexes.
- Captions uses `CaptionLookPanel` with folded `Section`s: Outline & shadow, Layout, then the editor's Position
  and "Fix a word" via `panel.add_section`.
- Headline has the text, "Use the AI's headline", a size slider (`hook_scale`) and a position reset.
- Folds use `caption_style_ui.Section` / `_chevron`, never the ▸/▾ text glyphs, which the UI font lacks.

### Clip editor projects
`clip_project.py` stores each Auto Clipper clip as `%LOCALAPPDATA%/CReaper/projects/<id>/` (`picture.mp4`,
`audio.m4a`, `project.json` with the plan, words, layout and **edit state**). The editor only changes the edit
dict through pure functions (`split`, `trim_segment`, `set_field`, `edit_caption_line`, …). Undo/redo is a
stack of edit-dict snapshots (max 100). Export always writes a new file. The original AI MP4 is never modified.

## Backend notes
- Hook headlines are in `backend/hook_headline.py`. The ranking call writes a draft (`HOOK_GUIDE`).
  - After the final clips are fixed, `services.apply_hooks` makes ONE dedicated call (`write_hooks`, system
    prompt `HOOK_WRITER`) with each clip's exact transcript.
  - `check_hook` rejects descriptions ("a man talks about…"), filler, invented numbers, meme tone on serious
    clips, and repeated hooks or openers. One retry is told what was wrong; `finalize_hook` then cleans the line.
  - Capitals are kept, on both the backend and the desktop (`caption_timeline.clean_hook_text`).
  - Tests that count AI calls must exclude the `HOOK_WRITER` call.
- AI provider routing goes through `services.request_ai_evaluation` / `chat_complete`. The order is configurable
  (`AI_PROVIDER_ORDER`; default Groq → Gemini → OpenRouter → Litepod, with Cloudflare Workers AI when its
  credentials are set). Settings are documented in `backend/.env.example`.
  - `GEMINI_MODEL` and `OPENROUTER_MODEL` take comma-separated backup lists.
    - Gemini (`services.gemini_with_backup`): a failing model is skipped for a while (2 min, or 30 min if
      missing) and the next model answers in the same call.
    - OpenRouter: the list is sent as its native `models` fallback.
    - Read Gemini models only through `services.gemini_model()`, never `os.getenv("GEMINI_MODEL")`.
  - Shared provider health (`best_moments_engine.PROVIDER_HEALTH`) is used by Best Moments AND Auto Clipper:
    - A bad key or a used-up quota blocks a provider for longer.
    - A call that timed out or failed with 5xx blocks it for 120 s (`AI_OUTAGE_BLOCK_SEC`), cleared by its next
      success.
    - A timeout is never re-sent to the same provider.
  - `python provider_check.py` (from `backend/`) tests every configured key/model with one tiny real request
    each (auth + generation through CReaper's own call path). It spends real quota: run it by hand, never from
    tests.
- **Users never see provider details.** Every AI availability failure shows exactly `AI_BUSY_MESSAGE`
  ("AI is currently busy. Please try again shortly.").
  - Job errors and HTTP details go through `services.public_error`; the app re-filters with
    `desktop/utils/user_errors.friendly_error`.
  - The real error and its kind go to the server log and to the clipper job's `diagnostics.internal_error`.
    The status endpoint drops `diagnostics`; never put internal detail on a job dict that it returns.
  - Log records are redacted of secret env values (`services._install_log_redaction`).
- AI Best Moments "Related Moments" (optional, off by default; `backend/related_moments.py`): finds hook → main
  body pairs.
  - After the normal results, ONE extra AI call runs over the job's own moments. Pairs are validated, and their
    times come from the moments, never from the model.
  - Its price is the `related_moments` entry in `PRICING` (an add-on, not in `OPERATIONS`).
  - It is charged as a separate best_moments debit (`<job>:related`, idempotency key `<key>:related`). That debit
    is settled together with the main one when the result is read, and refunded on its own when no pair is found
    or the step fails.
  - Desktop: the toggle is `ai_related_toggle`, the results show `ui/components/pair_card.py`, and a pair is made
    into a clip with `ClipperManager.start_pair` → `ClipperPipelineThread(preset_plan=…)`, segments
    `keep_order`, no AI plan and no charge.
- Tokens/billing: `token_system.py`. SQL migrations: `backend/migrations/` (Supabase/Postgres). Clipper jobs
  persist through `job_store.py`. For memory/crash investigations, see the job-record RSS/heartbeat fields and the
  `RESOURCES` log line.
- The desktop app calls `AppSettings.API_BASE_URL` (Railway public domain), and the backend enforces a minimum
  client version (`enforce_version`). Bump `APP_VERSION` for releases.

## Performance limits (Settings > Performance)
- `desktop/utils/resources.py` enforces them. The UI is `ui/components/performance_panel.py` (presets + painted
  `GaugeSlider`s). Settings keys: `perf_preset`, `perf_cpu_pct`, `perf_ram_gb`. Auto (the default) changes
  nothing.
- `main.py` installs a `subprocess.Popen` hook first thing, before yt-dlp is imported, because yt-dlp subclasses
  Popen when it's imported. Every FFmpeg process:
  - gets `-threads`/`-filter_threads`;
  - waits for a slot (`max_parallel` from the RAM budget). Slots are re-entrant per thread, and the GUI thread
    never waits;
  - joins one Windows job object with a hard CPU rate cap (below-normal priority on Low).
- In-process engines use `resources.threads()`/`in_process_threads()`: Whisper `cpu_threads`, OpenCV, the PyAV
  preview-copy encoder. New heavy in-process work must do the same.
- RAM is NOT a hard cap: fewer parallel tasks, admission control on their working sets, fewer threads. A job
  memory limit would kill FFmpeg mid-export instead.

## AI evaluation completeness
- Every shortlisted candidate ends evaluated or explicitly `not_evaluated`, never silently dropped:
  - Vision judge: a quick 5xx gets one retry; failures are shared through `PROVIDER_HEALTH`; the words-only
    judge evaluates the remaining candidates.
  - Transcript chunks and Best Moments batches: one retry pass.
- Too little evaluated (less than half, or fewer than the clips asked for) fails the job as busy, refunded. A
  partial result says so in its notice.
- Progress counts candidates with a valid answer only: "(n/m evaluated)".

## Gotchas
- `MainWindow.nativeEvent` must not call `super().nativeEvent()`, because PyQt6 crashes with an access violation
  on Windows (custom frameless title bar in `ui/components/window_chrome.py`).
- `main.py` sets `KMP_DUPLICATE_LIB_OK`/`OMP_NUM_THREADS=1` and disables OpenCV OpenCL before other imports, to
  avoid OpenMP runtime collisions between onnxruntime/ctranslate2/cv2.
- A frozen build refuses to start unless it was launched by the bootstrapper (handoff token file).
- The repo path is under OneDrive, which can lock files during builds (`build.py` retries).

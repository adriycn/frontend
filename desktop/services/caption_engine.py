"""
CReaper caption engine: word-level speech-to-text on the FINAL clip audio.

The words and their timestamps come from the exact audio that ends up in the rendered video
(finalized_edit.mp4, whose audio starts at t=0 and is stream-copied into the final file), so:
  * every word comes from the audio itself (no transcript/clip mismatch; YouTube and local files
    behave the same; no clip offsets to apply);
  * timestamps are already final-video times (trimming/reframing/rendering cannot shift them);
  * nothing is synthesized: words without acoustic timestamps are never invented.

Engines, in order:
  1. CReaper server: the clip audio (~300 KB) is sent to /api/ai/transcribe with word_timestamps=1,
     which runs Groq whisper-large-v3-turbo. No model download, no local RAM/CPU load.
  2. Offline fallback: faster-whisper (CTranslate2 int8, CPU) - ONLY if a model is already bundled
     with the app or installed in %LOCALAPPDATA%/CReaper/models/whisper. Never auto-downloaded.
     Model name via CREAPER_WHISPER_MODEL (default "small.en").
"""
import os
import re
import sys
import subprocess
import threading
from typing import Callable, Dict, List, Optional

import numpy as np

from utils.ffmpeg_locator import find_ffmpeg, NO_WINDOW

SAMPLE_RATE = 16000
DEFAULT_MODEL = "small.en"
MODEL_SIZES_MB = {"tiny.en": 75, "base.en": 145, "small.en": 484, "tiny": 75, "base": 145, "small": 484}

_MODEL_LOCK = threading.Lock()
_CACHED_MODEL = None
_CACHED_MODEL_NAME = None


class CaptionEngineError(RuntimeError):
    """User-presentable caption failure."""


def _log(msg: str):
    try:
        from services.caption_timeline import _timeline_debug_log
        _timeline_debug_log(f"[caption_engine] {msg}")
    except Exception:
        pass


def get_model_name() -> str:
    return (os.environ.get("CREAPER_WHISPER_MODEL") or DEFAULT_MODEL).strip()


def get_bundled_models_dir() -> Optional[str]:
    """Models shipped inside the app build (<app>/_internal/models/whisper), if any."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "models", "whisper")
        if os.path.isdir(bundled):
            return bundled
    return None


def get_models_dir() -> str:
    """Writable per-user model cache: <models>/whisper under the data location (%LOCALAPPDATA%/CReaper by default,
    the drive chosen in the installer otherwise). Downloads go here."""
    from utils.app_paths import user_data_dir
    return user_data_dir("models", "whisper")


def find_local_model(name: Optional[str] = None) -> Optional[str]:
    """
    Directory of a complete model (model.bin + config.json), or None. The copy bundled with the
    app is preferred, so captions work offline on the first clip; the user cache is the fallback.
    """
    name = name or get_model_name()
    candidates = []
    bundled = get_bundled_models_dir()
    if bundled:
        candidates.append(os.path.join(bundled, name))
    root = get_models_dir()
    candidates.append(os.path.join(root, name))
    snap_root = os.path.join(root, f"models--Systran--faster-whisper-{name}", "snapshots")
    if os.path.isdir(snap_root):
        candidates += [os.path.join(snap_root, d) for d in os.listdir(snap_root)]
    for c in candidates:
        if os.path.isfile(os.path.join(c, "model.bin")) and os.path.isfile(os.path.join(c, "config.json")):
            return c
    return None


def is_engine_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


MODEL_FILES = ["config.json", "tokenizer.json", "vocabulary.txt", "model.bin"]
_HF_URL = "https://huggingface.co/Systran/faster-whisper-{name}/resolve/main/{file}"
_CONNECT_TIMEOUT = 15
_READ_TIMEOUT = 45          # no bytes for this long = stalled connection -> retry with resume
_MAX_RETRIES = 6


def _download_file(url: str, dest: str, label: str, progress: Callable[[str], None],
                   cancel_check: Callable[[], bool]) -> None:
    """
    Resumable HTTPS download with stall detection and progress. Partial data is kept in
    '<dest>.part', so an interrupted download (or app restart) continues where it stopped.
    """
    import time
    import requests

    part = dest + ".part"
    total = None
    last_report = 0.0
    for attempt in range(1, _MAX_RETRIES + 1):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = {"Range": f"bytes={have}-"} if have else {}
        try:
            with requests.get(url, stream=True, headers=headers,
                              timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT), allow_redirects=True) as r:
                if r.status_code == 416:            # already complete
                    break
                if r.status_code == 200 and have:   # server ignored Range: start over
                    have = 0
                    open(part, "wb").close()
                if r.status_code not in (200, 206):
                    raise IOError(f"HTTP {r.status_code}")
                length = int(r.headers.get("Content-Length") or 0)
                total = have + length if length else total
                t0, got0 = time.time(), have
                with open(part, "ab") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        if cancel_check():
                            raise CaptionEngineError("Cancelled while downloading the speech model.")
                        if not chunk:
                            continue
                        f.write(chunk)
                        have += len(chunk)
                        now = time.time()
                        if now - last_report >= 0.5:
                            last_report = now
                            speed = (have - got0) / max(0.001, now - t0) / 1e6
                            if total:
                                progress(f"Downloading speech model ({label}): {have / 1e6:.0f} / {total / 1e6:.0f} MB "
                                         f"({100 * have / total:.0f}%) · {speed:.1f} MB/s")
                            else:
                                progress(f"Downloading speech model ({label}): {have / 1e6:.0f} MB · {speed:.1f} MB/s")
            if total is None or have >= total:
                break
        except CaptionEngineError:
            raise
        except Exception as e:
            _log(f"Download of {label} interrupted (attempt {attempt}/{_MAX_RETRIES}): {type(e).__name__}: {e}")
            if attempt == _MAX_RETRIES:
                raise CaptionEngineError(
                    "The speech model download keeps stalling. Check your internet connection and try again; "
                    "it will resume where it stopped.")
            progress(f"Connection interrupted, resuming download ({attempt}/{_MAX_RETRIES - 1})...")
            time.sleep(min(10, 2 * attempt))

    size = os.path.getsize(part) if os.path.exists(part) else 0
    if total and size != total:
        raise CaptionEngineError(f"The speech model download is incomplete ({size} of {total} bytes). Please retry.")
    os.replace(part, dest)


def download_speech_model(name: str, progress: Callable[[str], None],
                          cancel_check: Callable[[], bool] = lambda: False) -> str:
    """
    Downloads the CTranslate2 Whisper model files into <models>/whisper/<name>/ with our own
    resumable downloader. (huggingface_hub's chunked 'Xet' transfer stalled after the first
    10 MiB on this setup with no progress or timeout, leaving the app stuck.)
    """
    target = os.path.join(get_models_dir(), name)
    os.makedirs(target, exist_ok=True)
    for file in MODEL_FILES:
        dest = os.path.join(target, file)
        if os.path.isfile(dest) and os.path.getsize(dest) > 0:
            continue
        _download_file(_HF_URL.format(name=name, file=file), dest, file, progress, cancel_check)
    if not find_local_model(name):
        raise CaptionEngineError("The speech model download did not produce a usable model.")
    return target


def _load_model(progress: Callable[[str], None], cancel_check: Callable[[], bool] = lambda: False):
    global _CACHED_MODEL, _CACHED_MODEL_NAME
    from utils.resources import in_process_threads
    threads = in_process_threads(max(1, min(4, (os.cpu_count() or 2))))     # Settings > Performance
    name = get_model_name()
    with _MODEL_LOCK:
        # (the thread count is part of the cache key: a changed CPU limit reloads the model with it)
        if _CACHED_MODEL is not None and _CACHED_MODEL_NAME == (name, threads):
            return _CACHED_MODEL
        try:
            from faster_whisper import WhisperModel
        except Exception as e:
            raise CaptionEngineError(
                f"The speech-recognition engine is not available in this build ({type(e).__name__}).")

        model_dir = find_local_model(name)
        if not model_dir:
            # Never downloaded automatically (hundreds of MB). Only used if bundled/installed.
            raise CaptionEngineError("No offline speech model is installed on this PC.")

        progress("Loading speech model...")
        try:
            # int8 on CPU: ~4x less RAM than float32 and fastest on older CPUs without AVX-512/GPU
            _CACHED_MODEL = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=threads)
        except Exception as e:
            raise CaptionEngineError(f"Could not load the speech model ({type(e).__name__}: {e}).")
        _CACHED_MODEL_NAME = (name, threads)
        _log(f"Loaded faster-whisper '{name}' from {model_dir} (int8, {threads} threads)")
        return _CACHED_MODEL


def release_model():
    """Frees the model's memory (~0.6-1 GB for small.en)."""
    global _CACHED_MODEL, _CACHED_MODEL_NAME
    with _MODEL_LOCK:
        _CACHED_MODEL = None
        _CACHED_MODEL_NAME = None


def load_clip_audio(path: str) -> np.ndarray:
    """Decodes the clip's audio to 16 kHz mono float32 with the bundled FFmpeg (sample 0 = video t=0)."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise CaptionEngineError("FFmpeg is missing, so the clip audio cannot be read.")
    try:
        proc = subprocess.run(
            [ffmpeg, "-nostdin", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
             "-f", "f32le", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW, timeout=300,
        )
    except subprocess.TimeoutExpired:
        raise CaptionEngineError("Reading the clip audio timed out.")
    if proc.returncode != 0 or not proc.stdout:
        raise CaptionEngineError("The clip has no readable audio track.")
    return np.frombuffer(proc.stdout, dtype=np.float32).copy()


def _hotwords_from_text(text: str, limit: int = 40) -> str:
    """Rare/proper words from the source transcript, used only as a recognition hint (never as timing)."""
    seen, out = set(), []
    for tok in re.findall(r"[A-Za-z][A-Za-z'\-]{2,}", text or ""):
        if tok[0].isupper() or "-" in tok:
            key = tok.lower()
            if key not in seen:
                seen.add(key)
                out.append(tok)
        if len(out) >= limit:
            break
    return " ".join(out)


def refine_onsets_with_vad(audio: np.ndarray, words: List[Dict]) -> int:
    """
    Whisper derives word boundaries from attention (DTW), not acoustics: consecutive words are
    contiguous, so after a pause the next word's start lands inside the silence and its caption
    appears before it is spoken. Silero VAD (bundled with faster-whisper) locates where speech
    actually resumes; a word whose start lies in a non-speech gap is moved to that speech onset,
    never beyond the word's own end. Words that start inside speech are not touched.
    Returns how many onsets were moved.
    """
    if not words or audio.size == 0:
        return 0
    try:
        from faster_whisper.vad import get_speech_timestamps, VadOptions
        regions = get_speech_timestamps(
            audio, VadOptions(min_silence_duration_ms=120, speech_pad_ms=30, min_speech_duration_ms=60))
    except Exception as e:
        _log(f"VAD onset refinement unavailable: {type(e).__name__}: {e}")
        return 0
    spans = [(r["start"] / SAMPLE_RATE, r["end"] / SAMPLE_RATE) for r in regions]
    if not spans:
        return 0
    durations = sorted(max(0.0, w["end"] - w["start"]) for w in words)
    typical = durations[len(durations) // 2] if durations else 0.3
    moved = 0
    prev_start = 0.0
    for w in words:
        s, e = w["start"], w["end"]
        inside = any(a <= s < b for a, b in spans)
        if not inside:
            # Start lies in a pause: the word begins where speech resumes
            onset = next((a for a, _b in spans if a > s), None)
            if onset is not None and onset < e:
                w["start"] = round(max(onset, prev_start), 3)
                moved += 1
        elif (e - s) > max(1.0, 3.0 * typical):
            # DTW glitch: one word stretched across a pause (seen: "I" stamped 13.14-15.44 s while
            # spoken at ~15.4 s). A word is spoken in one breath, so it starts at the last speech
            # onset inside its span.
            onsets = [a for a, _b in spans if s < a < e - 0.05]
            if onsets:
                w["start"] = round(max(onsets[-1], prev_start), 3)
                moved += 1
        prev_start = w["start"]
    return moved


def _norm_word(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", (w or "").lower().replace("\u2019", "'"))


def correct_spellings_from_transcript(words: List[Dict], reference_text: str) -> List[str]:
    """
    Fixes near-miss misrecognitions (e.g. "throughtle" -> "throttle") using the clip's transcript,
    keeping Whisper's timestamps. Conservative: only 1:1 word substitutions in an otherwise aligned
    sequence, both words >= 6 letters, high character similarity, and Whisper's spelling absent from
    the transcript. Returns the corrections made.
    """
    import difflib
    ref = [t for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9'\u2019\-]*", reference_text or "")]
    if not ref or not words:
        return []
    ref_norm = [_norm_word(t) for t in ref]
    ref_set = set(ref_norm)
    hyp_norm = [_norm_word(w["word"]) for w in words]
    fixes = []
    sm = difflib.SequenceMatcher(a=hyp_norm, b=ref_norm, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "replace" or (i2 - i1) != (j2 - j1):
            continue
        for k in range(i2 - i1):
            h, r = hyp_norm[i1 + k], ref_norm[j1 + k]
            # >= 6 letters: leaves short homophones (their/there, your/you're) to Whisper
            if len(h) < 6 or len(r) < 6 or h == r or h in ref_set or abs(len(h) - len(r)) > 3:
                continue
            if difflib.SequenceMatcher(None, h, r).ratio() < 0.75:
                continue
            original = words[i1 + k]["word"]
            m = re.match(r"^(\W*)(.*?)(\W*)$", original)
            lead, core, trail = (m.group(1), m.group(2), m.group(3)) if m else ("", original, "")
            new_core = ref[j1 + k]
            if core[:1].isupper():
                new_core = new_core[:1].upper() + new_core[1:]
            words[i1 + k]["word"] = f"{lead}{new_core}{trail}"
            fixes.append(f"{original}->{words[i1 + k]['word']}")
    return fixes


def _encode_upload_audio(audio_path: str, out_path: str) -> None:
    """
    Mono 16 kHz FLAC of the clip audio (~1-1.5 MB for 45 s). Lossless and sample-exact: unlike MP3,
    FLAC has no encoder delay/padding that a server-side decoder might not trim, which would shift
    every returned timestamp.
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise CaptionEngineError("FFmpeg is missing, so the clip audio cannot be read.")
    res = subprocess.run(
        [ffmpeg, "-y", "-nostdin", "-v", "error", "-i", audio_path, "-vn", "-ac", "1",
         "-ar", str(SAMPLE_RATE), "-c:a", "flac", out_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=NO_WINDOW, timeout=120,
    )
    if res.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) < 500:
        raise CaptionEngineError("Could not prepare the clip audio for transcription.")


def _transcribe_server(audio_path: str, hint_text: str, progress: Callable[[str], None]) -> List[Dict]:
    """
    Word timestamps from the CReaper backend (Groq whisper-large-v3-turbo). Only the clip's audio
    (a few hundred KB) is uploaded; nothing is installed or downloaded on this PC.
    """
    import tempfile
    import requests
    from utils.settings import AppSettings
    from utils.hardware import get_machine_id
    from services.local_transcription import error_text

    from utils.session import auth_headers, NotSignedIn
    try:
        headers = auth_headers()
    except NotSignedIn:
        raise CaptionEngineError("Please sign in with Discord to use caption transcription.")
    except requests.RequestException:
        raise CaptionEngineError("The CReaper server can't be reached for caption transcription.")

    tmp_dir = tempfile.mkdtemp(prefix="creaper_captions_")
    mp3 = os.path.join(tmp_dir, "clip_audio.flac")
    try:
        _encode_upload_audio(audio_path, mp3)
        progress("Transcribing clip audio (word timestamps)...")
        try:
            with open(mp3, "rb") as f:
                resp = requests.post(
                    f"{AppSettings.API_BASE_URL}/api/ai/transcribe",
                    data={
                        "machine_id": get_machine_id(),
                        "word_timestamps": "1",
                        # No Whisper prompt: Whisper treats a prompt as text spoken BEFORE the audio,
                        # so passing the clip's own transcript made it skip what it "already heard"
                        # (measured: 63 words without vs. 5 words with, timestamps past the clip end).
                        # Spellings are fixed afterwards from the transcript instead.
                    },
                    files={"file": ("clip_audio.flac", f, "audio/flac")},
                    headers=headers,
                    timeout=(15, 120),
                )
        except requests.exceptions.Timeout:
            raise CaptionEngineError("The caption transcription service took too long to respond.")
        except requests.RequestException:
            raise CaptionEngineError("Could not reach the CReaper caption transcription service.")
        if resp.status_code != 200:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text or f"HTTP {resp.status_code}"
            raise CaptionEngineError(f"Caption transcription failed: {error_text(detail)}")
        try:
            data = resp.json()
        except ValueError:
            raise CaptionEngineError("The caption transcription service returned an invalid response.")
        if "words" not in data:
            # An older server ignores word_timestamps: never fall back to segment-level timing
            raise CaptionEngineError("The CReaper server does not support word-level captions yet (deploy the updated backend).")
        words = []
        for w in data.get("words") or []:
            text = str(w.get("word", "")).strip()
            if not text:
                continue
            start = float(w.get("start", 0.0))
            words.append({"word": text, "start": start, "end": max(start, float(w.get("end", start))),
                          "probability": float(w.get("probability", 1.0) or 1.0)})
        return words
    finally:
        try:
            if os.path.exists(mp3):
                os.remove(mp3)
            os.rmdir(tmp_dir)
        except OSError:
            pass


def _transcribe_local(audio: np.ndarray, hint_text: str, language: str,
                      progress: Callable[[str], None], cancel_check: Callable[[], bool]) -> List[Dict]:
    """faster-whisper on this PC; only when a model is already bundled/installed (no downloads)."""
    model = _load_model(progress, cancel_check)
    progress("Transcribing clip audio offline (word timestamps)...")
    lang = None if get_model_name().endswith(".en") else (language or None)
    try:
        segments, _info = model.transcribe(
            audio,
            language=lang,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 400, "speech_pad_ms": 200},
            condition_on_previous_text=False,
            hallucination_silence_threshold=2.0,
            hotwords=_hotwords_from_text(hint_text) or None,
        )
        words: List[Dict] = []
        for seg in segments:
            # Whisper's standard "no speech" test: likely hallucination over silence/music
            if getattr(seg, "no_speech_prob", 0.0) > 0.6 and getattr(seg, "avg_logprob", 0.0) < -1.0:
                _log(f"Skipped likely non-speech segment {seg.start:.2f}-{seg.end:.2f}: {seg.text!r}")
                continue
            for w in (seg.words or []):
                text = (w.word or "").strip()
                if text:
                    words.append({"word": text, "start": float(w.start), "end": float(w.end),
                                  "probability": float(getattr(w, "probability", 1.0) or 0.0)})
        return words
    except CaptionEngineError:
        raise
    except Exception as e:
        raise CaptionEngineError(f"Speech recognition failed ({type(e).__name__}: {e}).")


def transcribe_clip_words(
    audio_path: str,
    hint_text: str = "",
    language: str = "en",
    progress_cb: Optional[Callable[[str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> List[Dict]:
    """
    Returns the spoken words of the clip with acoustic timestamps in clip time:
        [{"word", "start", "end", "probability"}]
    1. CReaper server: Groq whisper-large-v3-turbo word timestamps (no local download or RAM use).
    2. Fallback: faster-whisper on this PC, only if a model is already bundled/installed.
    Raises CaptionEngineError on failure.
    """
    def progress(msg: str):
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    audio = load_clip_audio(audio_path)
    duration = len(audio) / SAMPLE_RATE
    if duration < 0.3:
        return []

    source = "server"
    try:
        words = _transcribe_server(audio_path, hint_text, progress)
    except CaptionEngineError as server_err:
        if not (is_engine_available() and find_local_model()):
            raise
        _log(f"Server captions failed ({server_err}); using the installed offline model.")
        source = "offline"
        words = _transcribe_local(audio, hint_text, language, progress, cancel_check or (lambda: False))

    # Clamp to the clip, then keep Whisper's word order non-decreasing in time without moving
    # anything by more than the overlap itself (equal/overlapping starts happen).
    for w in words:
        w["start"] = round(max(0.0, min(w["start"], duration)), 3)
        w["end"] = round(max(w["start"], min(w["end"], duration)), 3)
    for i in range(1, len(words)):
        if words[i]["start"] < words[i - 1]["start"]:
            words[i]["start"] = words[i - 1]["start"]
        if words[i]["end"] < words[i]["start"]:
            words[i]["end"] = words[i]["start"]

    moved = refine_onsets_with_vad(audio, words)
    fixed = correct_spellings_from_transcript(words, hint_text)
    _log(f"Transcribed {len(words)} words over {duration:.2f}s via {source}"
         + (f" | {moved} onsets moved out of silence" if moved else "")
         + (f" | spelling fixed: {fixed[:10]}" if fixed else ""))
    return words


def words_to_cues(words: List[Dict], max_gap: float = 0.7, max_words: int = 12) -> List[Dict]:
    """
    Groups timed words into caption cues for CaptionTimeline (clip-relative times).
    Grouping only affects bookkeeping; every word keeps its own acoustic timestamp.
    """
    from services.clipper_service import clean_pure_word

    cues: List[Dict] = []
    current: List[Dict] = []

    def flush():
        if current:
            cues.append({
                "start": current[0]["start"],
                "end": max(w["end"] for w in current),
                "text": " ".join(w["word"] for w in current),
                "words": list(current),
                "relative": True,
                "words_relative": True,
                "deduped": True,
            })

    for w in words:
        clean = clean_pure_word(w["word"])
        if not clean:
            continue
        item = {
            "word": clean,
            "start": w["start"],
            "end": max(w["end"], w["start"] + 0.04),
            "confidence": w.get("probability", 1.0),
            "clip_relative": True,
            "source": "faster_whisper",
        }
        if current and (item["start"] - current[-1]["end"] > max_gap or len(current) >= max_words):
            flush()
            current = []
        current.append(item)
    flush()
    return cues

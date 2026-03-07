"""
AI Transcript  — app.py
A clean, modular Streamlit application supporting:
  1. Audio / Video File Transcription
  2. YouTube Video Transcription
  3. Real-time Audio Recording + Transcription
"""

import os
import io
import re
import time
import tempfile

import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Transcription Tool",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Base ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .block-container {
        padding-top: 4rem;
        padding-bottom: 4rem;
        max-width: 1100px;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: #141414;
        border-right: 1px solid #2a2a2a;
    }

    section[data-testid="stSidebar"] .stRadio label {
        font-size: 15px;
        padding: 6px 0;
    }

    /* ── Hero ── */
    .hero-title {
        font-size: 52px;
        font-weight: 700;
        text-align: center;
        background: linear-gradient(135deg, #ffffff 0%, #a0a0a0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        line-height: 1.2;
    }

    .hero-subtitle {
        text-align: center;
        color: #888;
        font-size: 17px;
        margin-bottom: 48px;
        font-weight: 400;
    }

    /* ── Feature Cards ── */
    .card-grid {
        display: flex;
        gap: 24px;
    }

    .feat-card {
        flex: 1;
        background: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 16px;
        padding: 32px 24px;
        text-align: center;
        transition: border-color 0.25s ease, transform 0.25s ease;
        cursor: default;
    }

    .feat-card:hover {
        border-color: #4ade80;
        transform: translateY(-4px);
    }

    .feat-icon {
        font-size: 40px;
        margin-bottom: 16px;
        display: block;
    }

    .feat-title {
        font-size: 18px;
        font-weight: 600;
        color: #f0f0f0;
        margin-bottom: 10px;
    }

    .feat-desc {
        font-size: 14px;
        color: #888;
        line-height: 1.6;
    }

    /* ── Section Header ── */
    .section-header {
        font-size: 28px;
        font-weight: 700;
        color: #f0f0f0;
        margin-bottom: 6px;
    }

    .section-sub {
        color: #777;
        font-size: 14px;
        margin-bottom: 28px;
    }

    /* ── Transcript Box ── */
    .transcript-box {
        background: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 12px;
        padding: 24px;
        font-size: 15px;
        line-height: 1.8;
        color: #d4d4d4;
        white-space: pre-wrap;
        max-height: 420px;
        overflow-y: auto;
        font-family: 'Inter', sans-serif;
    }

    /* ── Divider ── */
    hr.custom-divider {
        border: none;
        border-top: 1px solid #2a2a2a;
        margin: 32px 0;
    }

    /* ── Badge ── */
    .badge {
        display: inline-block;
        background: #4ade8022;
        color: #4ade80;
        border: 1px solid #4ade8044;
        border-radius: 100px;
        padding: 3px 12px;
        font-size: 12px;
        font-weight: 500;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def load_model():
    """Load Faster-Whisper model once and cache it for the session lifetime."""
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    return model


def transcribe_audio(audio_path: str, language: str | None = None) -> tuple[str, str]:
    """
    Transcribe an audio file using Faster-Whisper.

    Args:
        audio_path: Absolute path to the audio file.
        language:   ISO 639-1 language code (e.g. 'en'). None = auto-detect.

    Returns:
        (plain_transcript, srt_content) — both as strings.
    """
    model = load_model()
    segments, _ = model.transcribe(
        audio_path,
        language=language if language and language != "Auto-detect" else None,
        beam_size=5,
    )

    segments = list(segments)  # materialise the generator

    plain_lines = []
    srt_blocks = []

    for idx, seg in enumerate(segments, start=1):
        text = seg.text.strip()
        plain_lines.append(text)
        srt_blocks.append(_format_srt_block(idx, seg.start, seg.end, text))

    return "\n".join(plain_lines), "\n\n".join(srt_blocks)


def _format_srt_block(index: int, start: float, end: float, text: str) -> str:
    """Format a single SRT subtitle block."""
    return f"{index}\n{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}\n{text}"


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp: HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def generate_srt(segments) -> str:
    """
    Generate an SRT subtitle string from a list of segment objects.
    Each segment must have .start, .end, and .text attributes.
    """
    blocks = [
        _format_srt_block(i + 1, seg.start, seg.end, seg.text.strip())
        for i, seg in enumerate(segments)
    ]
    return "\n\n".join(blocks)


def download_youtube_audio(url: str, output_dir: str) -> str:
    """
    Download audio from a YouTube URL using yt-dlp.

    Args:
        url:        YouTube video URL.
        output_dir: Directory to save the downloaded audio.

    Returns:
        Path to the downloaded .wav file.

    Raises:
        ValueError:  If URL is not a valid YouTube link.
        RuntimeError: If download fails.
    """
    if not _is_valid_youtube_url(url):
        raise ValueError("The URL provided does not appear to be a valid YouTube link.")

    import yt_dlp  # imported here to keep startup fast

    output_template = os.path.join(output_dir, "yt_audio.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    wav_path = os.path.join(output_dir, "yt_audio.wav")
    if not os.path.exists(wav_path):
        raise RuntimeError("Audio file was not created after download.")

    return wav_path


def _is_valid_youtube_url(url: str) -> bool:
    """Return True if url looks like a YouTube video URL."""
    patterns = [
        r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+",
        r"(https?://)?(www\.)?youtube\.com/watch\?v=.+",
        r"(https?://)?youtu\.be/.+",
    ]
    return any(re.match(p, url.strip()) for p in patterns)


# ── Recording sample rate (shared constant) ─────────────────────────────────
_REC_SAMPLE_RATE = 16000
_REC_CHUNK_SIZE  = 1024   # frames per callback chunk


def _check_microphone() -> tuple[bool, str]:
    """
    Verify that at least one input (microphone) device is available.

    Returns:
        (ok: bool, message: str)
        ok=True  → microphone is ready
        ok=False → message explains the problem
    """
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        # Look for any device that has at least one input channel
        has_input = any(
            d.get("max_input_channels", 0) > 0
            for d in (devices if isinstance(devices, list) else [devices])
        )
        if not has_input:
            return False, "No microphone detected. Please connect a microphone and try again."
        return True, ""
    except Exception:
        return False, "Microphone access is unavailable. Please allow microphone permissions."


def record_audio_streaming(
    duration: int,
    progress_bar,
    status_text,
    level_bar,
    stop_flag: list,
    sample_rate: int = _REC_SAMPLE_RATE,
) -> str:
    """
    Record audio using sounddevice.InputStream (chunk-based, non-blocking).

    Reads audio in small chunks so the UI can:
      - display real-time audio level
      - update an accurate progress bar
      - respond to the user pressing Stop

    Args:
        duration:    Maximum recording length in seconds.
        progress_bar: st.progress() element.
        status_text:  st.empty() element for percentage text.
        level_bar:    st.empty() element for audio level bar.
        stop_flag:    Single-element list [False]; set to [True] to stop early.
        sample_rate:  Audio sample rate in Hz.

    Returns:
        Path to the saved .wav file.

    Raises:
        RuntimeError: If the stream cannot be opened or audio saving fails.
    """
    import numpy as np
    import sounddevice as sd
    import soundfile as sf

    total_frames  = int(duration * sample_rate)
    recorded      = []          # list of numpy chunks
    frames_done   = 0

    def _callback(indata, frames, time_info, status):
        """Called by sounddevice for each chunk; appends data to buffer."""
        recorded.append(indata.copy())

    try:
        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=_REC_CHUNK_SIZE,
            callback=_callback,
        )
    except Exception as exc:
        raise RuntimeError(f"Could not open microphone stream: {exc}") from exc

    with stream:
        while frames_done < total_frames and not stop_flag[0]:
            time.sleep(_REC_CHUNK_SIZE / sample_rate)  # wait for one chunk

            # Accumulate frames captured so far
            frames_done = sum(len(c) for c in recorded)

            # ── Progress (capped at 100 %) ────────────────────────────
            pct = min(int(frames_done / total_frames * 100), 100)
            progress_bar.progress(pct)
            elapsed  = frames_done / sample_rate
            status_text.markdown(
                f"**🔴 Recording… {elapsed:.1f}s / {duration}s &nbsp;|&nbsp; {pct}%**"
            )

            # ── Audio level meter ─────────────────────────────────────
            if recorded:
                last_chunk = recorded[-1]
                rms = float(np.sqrt(np.mean(last_chunk ** 2)))
                # Scale RMS (typical speech ~0.02–0.3) to 0–100
                level_pct = min(int(rms * 400), 100)
                filled  = "█" * (level_pct // 5)
                empty   = "░" * (20 - level_pct // 5)
                level_bar.markdown(
                    f"**Audio Level** &nbsp; `{filled}{empty}` &nbsp; {level_pct}%"
                )

    # Combine all chunks into a single numpy array
    if not recorded:
        raise RuntimeError("No audio was captured. The microphone may have been silent.")

    audio_data = np.concatenate(recorded, axis=0)

    # Save to a temporary WAV file
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio_data, sample_rate)
    return tmp.name


def convert_to_wav(input_path: str) -> str:
    """
    Convert an uploaded audio/video file to WAV using pydub + ffmpeg.

    Args:
        input_path: Path to the source audio/video file.

    Returns:
        Path to the converted .wav file.
    """
    from pydub import AudioSegment

    ext = os.path.splitext(input_path)[1].lower().lstrip(".")
    audio = AudioSegment.from_file(input_path, format=ext if ext != "mp4" else "mp4")
    wav_path = input_path.rsplit(".", 1)[0] + "_converted.wav"
    audio.export(wav_path, format="wav")
    return wav_path


# ═══════════════════════════════════════════════════════════════════════════════
# REUSABLE UI HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def show_transcript_results(plain: str, srt: str, key_prefix: str):
    """Display transcript text and SRT download buttons."""
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown("#### 📄 Transcript")
    st.markdown(f'<div class="transcript-box">{plain}</div>', unsafe_allow_html=True)

    st.markdown("")  # spacer
    col_a, col_b, _ = st.columns([1, 1, 3])
    with col_a:
        st.download_button(
            label="⬇ Download transcript.txt",
            data=plain,
            file_name="transcript.txt",
            mime="text/plain",
            key=f"{key_prefix}_txt",
        )
    with col_b:
        st.download_button(
            label="⬇ Download subtitles.srt",
            data=srt,
            file_name="subtitles.srt",
            mime="text/plain",
            key=f"{key_prefix}_srt",
        )


def run_transcription_with_progress(audio_path: str, language: str | None) -> tuple[str, str]:
    """Run transcription while showing a progress bar in Streamlit."""
    progress_bar = st.progress(0)
    status_msg = st.empty()

    status_msg.info("🔄 Loading model…")
    progress_bar.progress(15)
    load_model()  # warm-up / cache hit

    status_msg.info("🔄 Processing audio…")
    progress_bar.progress(40)
    time.sleep(0.3)  # gives the progress UI time to render

    status_msg.info("🔄 Generating transcript…")
    progress_bar.progress(70)

    plain, srt = transcribe_audio(audio_path, language)

    progress_bar.progress(100)
    status_msg.success("✅ Transcription complete!")

    return plain, srt


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════════════════════════════

def page_home():
    st.markdown('<p class="hero-title">AI Transcription Tool</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-subtitle">Fast, accurate speech-to-text powered by Faster-Whisper</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card-grid">

          <div class="feat-card">
            <span class="feat-icon">📁</span>
            <div class="feat-title">Audio File</div>
            <div class="feat-desc">
              Upload MP3, WAV, M4A, or MP4 files.<br>
              Get a plain transcript and downloadable SRT subtitles instantly.
            </div>
          </div>

          <div class="feat-card">
            <span class="feat-icon">🎬</span>
            <div class="feat-title">YouTube Video</div>
            <div class="feat-desc">
              Paste any YouTube URL.<br>
              The audio is extracted automatically and transcribed in seconds.
            </div>
          </div>

          <div class="feat-card">
            <span class="feat-icon">🎙</span>
            <div class="feat-title">Record Audio</div>
            <div class="feat-desc">
              Record directly from your microphone.<br>
              Choose duration and language, then get your transcript live.
            </div>
          </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;color:#555;font-size:13px;'>"
        "Powered by <b>Faster-Whisper</b> · CPU inference · int8 quantization"
        "</p>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: AUDIO FILE TRANSCRIPTION
# ═══════════════════════════════════════════════════════════════════════════════

SUPPORTED_FORMATS = ["mp3", "wav", "m4a", "mp4"]

def page_transcribe_audio():
    st.markdown('<p class="section-header">📁 Audio / Video Transcription</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Upload an audio or video file and receive a full transcript with subtitle export.</p>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Choose a file",
        type=SUPPORTED_FORMATS,
        help="Supported: MP3, WAV, M4A, MP4",
    )

    language = st.selectbox(
        "Language",
        ["Auto-detect", "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko", "ar", "hi"],
        help="Select the spoken language or let the model auto-detect it.",
        key="af_lang",
    )

    if uploaded and st.button("▶ Transcribe", key="af_btn", type="primary"):
        try:
            suffix = f".{uploaded.name.rsplit('.', 1)[-1].lower()}"

            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name

            # Convert non-WAV files
            if suffix != ".wav":
                with st.spinner("Converting audio format…"):
                    audio_path = convert_to_wav(tmp_path)
            else:
                audio_path = tmp_path

            plain, srt = run_transcription_with_progress(audio_path, language)
            show_transcript_results(plain, srt, key_prefix="af")

        except FileNotFoundError:
            st.error("⚠️ A required audio processing dependency is missing (ffmpeg / pydub).")
        except RuntimeError as e:
            st.error(f"⚠️ Model inference failed. Please try again. ({e})")
        except Exception:
            st.error("⚠️ An unexpected error occurred while processing the audio.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: YOUTUBE TRANSCRIPTION
# ═══════════════════════════════════════════════════════════════════════════════

def page_youtube():
    st.markdown('<p class="section-header">🎬 YouTube Video Transcription</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Paste a YouTube link below — the audio is automatically extracted and transcribed.</p>',
        unsafe_allow_html=True,
    )

    yt_url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        key="yt_url",
    )

    language = st.selectbox(
        "Language",
        ["Auto-detect", "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko", "ar", "hi"],
        key="yt_lang",
    )

    if yt_url and st.button("▶ Transcribe", key="yt_btn", type="primary"):
        if not _is_valid_youtube_url(yt_url):
            st.error("⚠️ That doesn't look like a valid YouTube URL. Please check and try again.")
            return

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                progress_bar = st.progress(0)
                status_msg = st.empty()

                status_msg.info("📥 Downloading audio from YouTube…")
                progress_bar.progress(20)

                audio_path = download_youtube_audio(yt_url, tmpdir)

                status_msg.info("🔄 Loading model…")
                progress_bar.progress(45)
                load_model()

                status_msg.info("🔄 Generating transcript…")
                progress_bar.progress(70)

                plain, srt = transcribe_audio(audio_path, language)

                progress_bar.progress(100)
                status_msg.success("✅ Transcription complete!")

            show_transcript_results(plain, srt, key_prefix="yt")

        except ValueError as e:
            st.error(f"⚠️ Invalid YouTube URL: {e}")
        except RuntimeError as e:
            st.error(f"⚠️ Could not process the video. It may be private or geo-restricted. ({e})")
        except Exception:
            st.error("⚠️ An unexpected error occurred. Please check the URL and try again.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: RECORD AUDIO
# ═══════════════════════════════════════════════════════════════════════════════

LANGUAGE_OPTIONS = {
    "Auto-detect": None,
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar",
    "Hindi": "hi",
}

def page_record_audio():
    st.markdown('<p class="section-header">🎙 Record & Transcribe</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-sub">Record directly from your microphone and receive a transcript instantly.</p>',
        unsafe_allow_html=True,
    )

    # ── Duration / Language controls ─────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        duration = st.slider(
            "Recording duration (seconds)",
            min_value=5,
            max_value=120,
            value=30,
            step=5,
            key="rec_dur",
        )
    with col2:
        lang_label = st.selectbox(
            "Spoken language",
            list(LANGUAGE_OPTIONS.keys()),
            key="rec_lang",
        )

    language = LANGUAGE_OPTIONS[lang_label]

    # ── Session-state flags ───────────────────────────────────────────────────
    # rec_active : True while recording is in progress
    # rec_stop   : set to True when user presses Stop
    if "rec_active" not in st.session_state:
        st.session_state["rec_active"] = False
    if "rec_stop" not in st.session_state:
        st.session_state["rec_stop"] = False

    # ── Microphone check ─────────────────────────────────────────────────────
    # Verify mic availability BEFORE showing the Start button
    mic_ok, mic_msg = _check_microphone()
    if not mic_ok:
        st.warning(f"⚠️ {mic_msg}")
        return  # stop rendering — nothing to record with

    st.info(
        f"🎙 Ready to record **{duration} seconds** of audio. "
        "Ensure your microphone is connected and permissions are granted."
    )

    # ── Button row: Start / Stop ──────────────────────────────────────────────
    btn_col1, btn_col2, _ = st.columns([1, 1, 4])
    with btn_col1:
        start_pressed = st.button(
            "⏺ Start Recording",
            key="rec_start_btn",
            type="primary",
            disabled=st.session_state["rec_active"],
        )
    with btn_col2:
        stop_pressed = st.button(
            "⏹ Stop Recording",
            key="rec_stop_btn",
            disabled=not st.session_state["rec_active"],
        )

    # Handle Stop request — set flag so the recording loop exits
    if stop_pressed and st.session_state["rec_active"]:
        st.session_state["rec_stop"] = True

    # ── Recording workflow ────────────────────────────────────────────────────
    if start_pressed and not st.session_state["rec_active"]:
        st.session_state["rec_active"] = True
        st.session_state["rec_stop"]   = False

        try:
            # UI elements that will be updated during recording
            progress_bar = st.progress(0)
            status_text  = st.empty()
            level_bar    = st.empty()

            status_text.markdown("**🔴 Recording started — speak now…**")

            # stop_flag is a mutable container so the callback can signal stop
            stop_flag = [False]

            # Watch session_state["rec_stop"] from the main thread
            # (sounddevice callback runs in a background thread, so we poll
            #  the flag list instead of session_state directly)
            import threading

            def _watch_stop():
                """Background watcher: copies session_state stop flag → stop_flag[0]."""
                while not stop_flag[0]:
                    if st.session_state.get("rec_stop", False):
                        stop_flag[0] = True
                        break
                    time.sleep(0.1)

            watcher = threading.Thread(target=_watch_stop, daemon=True)
            watcher.start()

            # ── Stream and record ─────────────────────────────────────
            audio_path = record_audio_streaming(
                duration=duration,
                progress_bar=progress_bar,
                status_text=status_text,
                level_bar=level_bar,
                stop_flag=stop_flag,
            )

            # Recording finished (naturally or via Stop)
            stop_flag[0] = True  # ensure watcher thread exits
            progress_bar.progress(100)
            status_text.success("✅ Recording complete — transcribing now…")
            level_bar.empty()

            # ── Transcription ─────────────────────────────────────────
            plain, srt = run_transcription_with_progress(audio_path, language)

            # Clean up temp WAV
            try:
                os.unlink(audio_path)
            except OSError:
                pass

            show_transcript_results(plain, srt, key_prefix="rec")

        except ImportError:
            st.error(
                "⚠️ Recording dependencies are missing. "
                "Please run: `pip install sounddevice soundfile numpy`"
            )
        except RuntimeError as exc:
            st.error(f"⚠️ Recording failed: {exc}")
        except Exception:
            st.error(
                "⚠️ Recording failed. Please check your microphone and try again."
            )
        finally:
            # Always reset state so Start button re-enables
            st.session_state["rec_active"] = False
            st.session_state["rec_stop"]   = False


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(
            "<h2 style='font-size:20px;font-weight:700;margin-bottom:4px;'>🎙 AI Transcribe</h2>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:12px;color:#555;margin-bottom:24px;'>Powered by Faster-Whisper</p>",
            unsafe_allow_html=True,
        )

        menu = st.radio(
            "Navigation",
            options=[
                "🏠  Home",
                "📁  Transcribe Audio",
                "🎬  YouTube",
                "🎙  Record Audio",
            ],
            label_visibility="collapsed",
        )

        st.markdown('<hr style="border-color:#2a2a2a;margin-top:32px;">', unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:11px;color:#444;'>"
            "Model: <b>Whisper Base</b><br>"
            "Device: CPU · int8"
            "</p>",
            unsafe_allow_html=True,
        )

    return menu


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    menu = render_sidebar()

    if menu == "🏠  Home":
        page_home()
    elif menu == "📁  Transcribe Audio":
        page_transcribe_audio()
    elif menu == "🎬  YouTube":
        page_youtube()
    elif menu == "🎙  Record Audio":
        page_record_audio()


if __name__ == "__main__":
    main()

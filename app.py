import streamlit as st
import whisper
import tempfile
import time

st.set_page_config(page_title="Whisper Audio Transcriber", layout="centered")

st.title("🎤 Audio to Text Converter (Whisper AI)")
st.markdown("---")

# Load model
@st.cache_resource
def load_model():
    model = whisper.load_model("small")
    return model

model = load_model()

uploaded_file = st.file_uploader(
    "Upload Audio File",
    type=["mp3", "wav", "m4a", "mp4"]
)

if uploaded_file:

    st.audio(uploaded_file)

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(uploaded_file.read())
        temp_path = temp_audio.name

    if st.button("Transcribe Audio"):

        progress_bar = st.progress(0)
        status_text = st.empty()

        with st.spinner("Transcribing... Please wait"):

            # Fake progress while whisper runs
            for i in range(0, 90, 10):
                status_text.text(f"Processing... {i}%")
                progress_bar.progress(i)
                time.sleep(0.2)

            # Run whisper transcription
            result = model.transcribe(temp_path)

            progress_bar.progress(100)
            status_text.text("Processing... 100%")

        text = result["text"]
        language = result["language"]

        st.success("✅ Transcription Complete")

        st.markdown(f"**Detected Language:** `{language.upper()}`")

        st.text_area(
            "Transcribed Text",
            value=text,
            height=300
        )

        st.download_button(
            "Download Transcript",
            text,
            file_name="transcript.txt"
        )
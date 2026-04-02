import streamlit as st
import os
import tempfile
from pathlib import Path

from pdfapp import PDFToAudiobook, AudiobookConfig

st.set_page_config(page_title="PDF to Audiobook", page_icon="🎧", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0f0f0f;
    color: #f0ede6;
}
h1, h2, h3 { font-family: 'Syne', sans-serif; font-weight: 800; }
.stButton>button {
    background: #e8ff47;
    color: #0f0f0f;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    border: none;
    border-radius: 4px;
    padding: 0.6rem 2rem;
    font-size: 1rem;
    width: 100%;
    cursor: pointer;
}
.stButton>button:hover { background: #d4eb30; }
.stSelectbox label, .stSlider label, .stTextInput label, .stNumberInput label {
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
.block-container { padding-top: 2rem; max-width: 720px; }
audio { width: 100%; margin-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🎧 PDF to Audiobook")
st.markdown("<p style='color:#888; font-family:DM Mono,monospace; font-size:0.85rem;'>Upload a PDF. Get an audiobook.</p>", unsafe_allow_html=True)

st.divider()

uploaded = st.file_uploader("Upload PDF", type=["pdf"])

col1, col2 = st.columns(2)
with col1:
    engine = st.selectbox("TTS Engine", ["pyttsx3", "gtts", "edge-tts"],
                          help="pyttsx3=offline, gtts=Google, edge-tts=best quality")
with col2:
    fmt = st.selectbox("Output Format", ["wav", "mp3"])

col3, col4 = st.columns(2)
with col3:
    lang = st.text_input("Language Code", value="en", help="e.g. en, hi, fr")
with col4:
    voice = st.text_input("Voice (optional)", placeholder="e.g. en-US-JennyNeural")

col5, col6 = st.columns(2)
with col5:
    start_page = st.number_input("Start Page", min_value=1, value=1)
with col6:
    end_page = st.number_input("End Page (0 = all)", min_value=0, value=0)

col7, col8 = st.columns(2)
with col7:
    rate = st.slider("Speech Rate (pyttsx3)", 80, 300, 150)
with col8:
    volume = st.slider("Volume (pyttsx3)", 0.0, 1.0, 1.0, step=0.1)

no_merge = st.checkbox("Keep chapters as separate files")

st.divider()

if st.button("🎙️ Convert to Audiobook"):
    if not uploaded:
        st.error("Upload a PDF first.")
    else:
        tmpdir = tempfile.mkdtemp()
        pdf_path = os.path.join(tmpdir, uploaded.name)
        with open(pdf_path, "wb") as f:
            f.write(uploaded.read())

        output_dir = os.path.join(tmpdir, "output")

        config = AudiobookConfig(
            input_pdf=pdf_path,
            output_dir=output_dir,
            tts_engine=engine,
            language=lang,
            voice=voice if voice.strip() else None,
            rate=rate,
            volume=volume,
            merge_output=not no_merge,
            start_page=int(start_page),
            end_page=int(end_page) if end_page > 0 else None,
            output_format=fmt,
        )

        with st.spinner("Converting... this may take a few minutes."):
            try:
                converter = PDFToAudiobook(config)
                final_path = converter.convert()

                with open(final_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()

                st.success("✅ Done!")
                st.audio(audio_bytes, format=f"audio/{fmt}")
                st.download_button(
                    label="⬇️ Download Audiobook",
                    data=audio_bytes,
                    file_name=Path(final_path).name,
                    mime=f"audio/{fmt}"
                )
            except Exception as e:
                st.error(f"Error: {e}")
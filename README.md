# 📖 PDF to Audiobook Converter

Convert any PDF into a high-quality audiobook with a single command.  
Supports **offline** and **online** TTS engines, chapter detection, and audio merging.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔊 **3 TTS Engines** | pyttsx3 (offline), gTTS (Google), edge-tts (Microsoft) |
| 📚 **Auto Chapter Detection** | Detects Chapter/Section headings automatically |
| 🧹 **Smart Text Cleaning** | Removes headers, page numbers, hyphenation artifacts |
| 🔗 **Audio Merging** | Merges all chapters into one single audiobook file |
| 🌍 **Multi-language** | Supports 40+ languages via gTTS / edge-tts |
| ⚙️ **Configurable** | Control speed, voice, page range, chunk size |
| 🖥️ **CLI + Python API** | Use as a command-line tool or import in your code |

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/pdf-to-audiobook.git
cd pdf-to-audiobook
pip install -r requirements.txt
```

> **FFmpeg is required** for audio merging/conversion:
> - Ubuntu/Debian: `sudo apt install ffmpeg`
> - macOS: `brew install ffmpeg`
> - Windows: [Download FFmpeg](https://ffmpeg.org/download.html)

### 2. Convert a PDF

```bash
# Offline (no internet needed)
python pdf_to_audiobook.py mybook.pdf

# Google TTS (internet required)
python pdf_to_audiobook.py mybook.pdf --engine gtts --lang en

# Microsoft Edge TTS (best voice quality)
python pdf_to_audiobook.py mybook.pdf --engine edge-tts --voice en-US-JennyNeural
```

Output will be saved to `output_audio/mybook_audiobook.mp3`.

---

## 🛠️ CLI Reference

```
usage: pdf_to_audiobook.py [-h] [--engine {pyttsx3,gtts,edge-tts}]
                            [--output OUTPUT] [--format {mp3,wav}]
                            [--lang LANG] [--voice VOICE]
                            [--rate RATE] [--volume VOLUME]
                            [--start START] [--end END]
                            [--no-merge] [--list-voices]
                            [input_pdf]
```

| Argument | Default | Description |
|---|---|---|
| `input_pdf` | — | Path to the PDF file |
| `--engine` | `pyttsx3` | TTS engine: `pyttsx3`, `gtts`, `edge-tts` |
| `--output` | `output_audio` | Output directory |
| `--format` | `mp3` | Output audio format: `mp3` or `wav` |
| `--lang` | `en` | Language code (e.g. `en`, `hi`, `fr`) |
| `--voice` | auto | Voice ID or name (engine-specific) |
| `--rate` | `150` | Speech rate in words/min (pyttsx3 only) |
| `--volume` | `1.0` | Volume 0.0–1.0 (pyttsx3 only) |
| `--start` | `1` | Start page number |
| `--end` | last | End page number |
| `--no-merge` | off | Keep chapters as separate audio files |
| `--list-voices` | — | List all available pyttsx3 voices |

### Examples

```bash
# Convert pages 10–80 only
python pdf_to_audiobook.py textbook.pdf --start 10 --end 80

# Hindi language with Google TTS
python pdf_to_audiobook.py hindi_book.pdf --engine gtts --lang hi

# List available voices (pyttsx3)
python pdf_to_audiobook.py --list-voices

# Slow narration, high volume, WAV output
python pdf_to_audiobook.py novel.pdf --rate 120 --volume 0.9 --format wav

# Keep chapters separate (don't merge)
python pdf_to_audiobook.py book.pdf --engine edge-tts --no-merge
```

---

## 🐍 Python API

```python
from pdf_to_audiobook import PDFToAudiobook, AudiobookConfig

config = AudiobookConfig(
    input_pdf="mybook.pdf",
    output_dir="output_audio",
    tts_engine="edge-tts",           # pyttsx3 | gtts | edge-tts
    language="en",
    voice="en-US-GuyNeural",         # Edge TTS voice
    merge_output=True,
    start_page=1,
    end_page=100,
    output_format="mp3",
)

converter = PDFToAudiobook(config)
output_path = converter.convert()
print(f"Audiobook saved to: {output_path}")
```

---

## 🎙️ TTS Engine Comparison

| Engine | Internet | Quality | Speed | Languages | Notes |
|---|---|---|---|---|---|
| **pyttsx3** | ❌ Offline | ⭐⭐ | ⚡ Fast | System voices | Best for privacy |
| **gTTS** | ✅ Required | ⭐⭐⭐ | Medium | 40+ | Free, Google voices |
| **edge-tts** | ✅ Required | ⭐⭐⭐⭐⭐ | Medium | 70+ | Best quality, free |

### Recommended Edge TTS Voices

```
en-US-JennyNeural       # Female, clear American English
en-US-GuyNeural         # Male, clear American English
en-GB-SoniaNeural       # Female, British English
en-IN-NeerjaNeural      # Female, Indian English
hi-IN-SwaraNeural       # Hindi female
fr-FR-DeniseNeural      # French female
```

---

## 📁 Project Structure

```
pdf-to-audiobook/
├── pdf_to_audiobook.py   # Main script (all logic here)
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── LICENSE               # MIT License
└── output_audio/         # Generated audiobook files (git-ignored)
    ├── chunks/           # Intermediate chapter audio files
    └── mybook_audiobook.mp3
```

---

## 🐛 Troubleshooting

**`No module named 'pdfplumber'`**  
→ Run `pip install pdfplumber`

**`FileNotFoundError: ffmpeg`**  
→ Install FFmpeg (see Quick Start above)

**Edge TTS fails silently**  
→ Check your internet connection; edge-tts requires internet.

**Text extraction is empty/garbled**  
→ Your PDF may be scanned (image-based). Install OCR support:  
```bash
pip install pytesseract pdf2image
sudo apt install tesseract-ocr   # Ubuntu
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

```bash
git checkout -b feature/my-feature
git commit -m "Add my feature"
git push origin feature/my-feature
```

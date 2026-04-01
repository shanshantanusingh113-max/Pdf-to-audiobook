"""
PDF to Audiobook Converter
==========================
Converts PDF files into audio files using text-to-speech.
Supports multiple TTS engines: pyttsx3 (offline), gTTS (Google), edge-tts (Microsoft).
"""

import os
import re
import sys
import argparse
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# PDF extraction
try:
    import pdfplumber
    PDF_ENGINE = "pdfplumber"
except ImportError:
    try:
        from pypdf import PdfReader
        PDF_ENGINE = "pypdf"
    except ImportError:
        PDF_ENGINE = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Data Model
# ─────────────────────────────────────────────

@dataclass
class AudiobookConfig:
    """Configuration for the audiobook generation."""
    input_pdf: str
    output_dir: str = "output_audio"
    tts_engine: str = "pyttsx3"          # pyttsx3 | gtts | edge-tts
    language: str = "en"                  # Language code (e.g., en, hi, fr)
    voice: Optional[str] = None           # Voice ID / name (engine-specific)
    rate: int = 150                        # Speech rate (words per minute)
    volume: float = 1.0                   # Volume 0.0–1.0
    chunk_size: int = 5000                # Characters per audio chunk
    merge_output: bool = True             # Merge all chunks into one file
    start_page: int = 1
    end_page: Optional[int] = None
    skip_headers: bool = True             # Remove repeated header/footer text
    output_format: str = "mp3"           # mp3 | wav


@dataclass
class Chapter:
    """Represents a chapter / section extracted from the PDF."""
    title: str
    text: str
    page_start: int
    page_end: int
    index: int = 0


# ─────────────────────────────────────────────
# PDF Text Extractor
# ─────────────────────────────────────────────

class PDFExtractor:
    """Extracts and cleans text from PDF files."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self._validate()

    def _validate(self):
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        if PDF_ENGINE is None:
            raise ImportError("Install pdfplumber or pypdf: pip install pdfplumber")

    def extract_pages(self, start: int = 1, end: Optional[int] = None) -> list[dict]:
        """Extract text from each page. Returns list of {page_num, text}."""
        pages = []
        if PDF_ENGINE == "pdfplumber":
            pages = self._extract_pdfplumber(start, end)
        else:
            pages = self._extract_pypdf(start, end)
        return pages

    def _extract_pdfplumber(self, start, end):
        pages = []
        with pdfplumber.open(self.pdf_path) as pdf:
            total = len(pdf.pages)
            end = min(end or total, total)
            log.info(f"PDF has {total} pages. Extracting pages {start}–{end}.")
            for i in range(start - 1, end):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                pages.append({"page_num": i + 1, "text": text})
        return pages

    def _extract_pypdf(self, start, end):
        from pypdf import PdfReader
        pages = []
        reader = PdfReader(self.pdf_path)
        total = len(reader.pages)
        end = min(end or total, total)
        log.info(f"PDF has {total} pages. Extracting pages {start}–{end}.")
        for i in range(start - 1, end):
            text = reader.pages[i].extract_text() or ""
            pages.append({"page_num": i + 1, "text": text})
        return pages

    def extract_metadata(self) -> dict:
        """Return PDF metadata (title, author, etc.)."""
        if PDF_ENGINE == "pdfplumber":
            with pdfplumber.open(self.pdf_path) as pdf:
                return pdf.metadata or {}
        else:
            from pypdf import PdfReader
            reader = PdfReader(self.pdf_path)
            meta = reader.metadata or {}
            return {k.lstrip("/"): v for k, v in meta.items()}


# ─────────────────────────────────────────────
# Text Cleaner
# ─────────────────────────────────────────────

class TextCleaner:
    """Cleans extracted PDF text for better TTS output."""

    # Common ligatures / encoding artifacts
    REPLACEMENTS = [
        (r'ﬁ', 'fi'), (r'ﬂ', 'fl'), (r'ﬀ', 'ff'), (r'ﬃ', 'ffi'), (r'ﬄ', 'ffl'),
        (r'\u2018|\u2019', "'"),   # curly single quotes
        (r'\u201c|\u201d', '"'),   # curly double quotes
        (r'\u2013|\u2014', '-'),   # en/em dash
        (r'\u2026', '...'),        # ellipsis
        (r'\xa0', ' '),            # non-breaking space
    ]

    def clean(self, text: str, skip_headers: bool = True) -> str:
        """Apply all cleaning steps."""
        text = self._fix_encoding(text)
        text = self._remove_urls(text)
        text = self._remove_page_numbers(text)
        if skip_headers:
            text = self._remove_short_lines(text)
        text = self._fix_hyphenation(text)
        text = self._normalize_whitespace(text)
        return text.strip()

    def _fix_encoding(self, text: str) -> str:
        for pattern, replacement in self.REPLACEMENTS:
            text = re.sub(pattern, replacement, text)
        return text

    def _remove_urls(self, text: str) -> str:
        return re.sub(r'https?://\S+|www\.\S+', '', text)

    def _remove_page_numbers(self, text: str) -> str:
        # Lines that are just a number (page numbers)
        return re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    def _remove_short_lines(self, text: str, min_words: int = 3) -> str:
        """Remove header/footer lines (very short isolated lines)."""
        lines = text.split('\n')
        cleaned = []
        for line in lines:
            words = line.split()
            if len(words) >= min_words or len(cleaned) == 0:
                cleaned.append(line)
            elif line.strip() == '':
                cleaned.append(line)
        return '\n'.join(cleaned)

    def _fix_hyphenation(self, text: str) -> str:
        """Re-join words broken across lines with hyphens."""
        return re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text


# ─────────────────────────────────────────────
# Chapter Detector
# ─────────────────────────────────────────────

class ChapterDetector:
    """Splits text into chapters based on heading patterns."""

    HEADING_PATTERNS = [
        r'^(Chapter\s+\d+[\.:]\s*.+)$',
        r'^(CHAPTER\s+\d+[\.:]\s*.+)$',
        r'^(\d+\.\s+[A-Z][^\n]{5,50})$',
        r'^(Part\s+[IVX]+[\.:]\s*.+)$',
        r'^(Section\s+\d+[\.:]\s*.+)$',
    ]

    def detect(self, pages: list[dict]) -> list[Chapter]:
        """Try to split pages into chapters. Falls back to single chapter."""
        full_text = '\n'.join(p['text'] for p in pages)
        chapters = self._split_by_headings(full_text, pages)
        if len(chapters) <= 1:
            chapters = self._split_by_pages(pages, chunk_pages=20)
        log.info(f"Detected {len(chapters)} chapter(s).")
        return chapters

    def _split_by_headings(self, text: str, pages: list[dict]) -> list[Chapter]:
        combined_pattern = '|'.join(f'({p})' for p in self.HEADING_PATTERNS)
        regex = re.compile(combined_pattern, re.MULTILINE)
        splits = list(regex.finditer(text))
        if not splits:
            return []

        chapters = []
        for idx, match in enumerate(splits):
            title = match.group().strip()
            start_pos = match.end()
            end_pos = splits[idx + 1].start() if idx + 1 < len(splits) else len(text)
            body = text[start_pos:end_pos].strip()
            chapters.append(Chapter(
                title=title, text=body,
                page_start=1, page_end=len(pages), index=idx
            ))
        return chapters

    def _split_by_pages(self, pages: list[dict], chunk_pages: int = 20) -> list[Chapter]:
        chapters = []
        for i in range(0, len(pages), chunk_pages):
            batch = pages[i:i + chunk_pages]
            text = '\n'.join(p['text'] for p in batch)
            chapters.append(Chapter(
                title=f"Section {i // chunk_pages + 1}",
                text=text,
                page_start=batch[0]['page_num'],
                page_end=batch[-1]['page_num'],
                index=i // chunk_pages
            ))
        return chapters


# ─────────────────────────────────────────────
# TTS Engines
# ─────────────────────────────────────────────

class TTSEngine:
    """Base class for TTS engines."""

    def synthesize(self, text: str, output_path: str, config: AudiobookConfig):
        raise NotImplementedError

    def _ensure_dir(self, path: str):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)


class Pyttsx3Engine(TTSEngine):
    """Offline TTS using pyttsx3."""

    def synthesize(self, text: str, output_path: str, config: AudiobookConfig):
        try:
            import pyttsx3
        except ImportError:
            raise ImportError("Install pyttsx3: pip install pyttsx3")

        self._ensure_dir(output_path)
        engine = pyttsx3.init()
        engine.setProperty('rate', config.rate)
        engine.setProperty('volume', config.volume)

        if config.voice:
            engine.setProperty('voice', config.voice)

        # pyttsx3 saves as wav natively; convert to mp3 if needed
        wav_path = output_path.replace('.mp3', '.wav')
        engine.save_to_file(text, wav_path)
        engine.runAndWait()

        if config.output_format == 'mp3' and wav_path != output_path:
            self._wav_to_mp3(wav_path, output_path)
            os.remove(wav_path)

    def _wav_to_mp3(self, wav_path: str, mp3_path: str):
        try:
            from pydub import AudioSegment
            AudioSegment.from_wav(wav_path).export(mp3_path, format='mp3')
        except ImportError:
            log.warning("pydub not installed. Saving as WAV instead.")
            import shutil
            shutil.copy(wav_path, mp3_path.replace('.mp3', '.wav'))

    def list_voices(self):
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        return [(v.id, v.name, v.languages) for v in voices]


class GTTSEngine(TTSEngine):
    """Online TTS using Google Text-to-Speech."""

    def synthesize(self, text: str, output_path: str, config: AudiobookConfig):
        try:
            from gtts import gTTS
        except ImportError:
            raise ImportError("Install gTTS: pip install gtts")

        self._ensure_dir(output_path)
        tts = gTTS(text=text, lang=config.language, slow=False)
        tts.save(output_path)
        log.debug(f"Saved: {output_path}")


class EdgeTTSEngine(TTSEngine):
    """Online TTS using Microsoft Edge TTS (high quality, free)."""

    def synthesize(self, text: str, output_path: str, config: AudiobookConfig):
        try:
            import edge_tts
            import asyncio
        except ImportError:
            raise ImportError("Install edge-tts: pip install edge-tts")

        self._ensure_dir(output_path)
        voice = config.voice or "en-US-JennyNeural"

        async def _run():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        import asyncio
        asyncio.run(_run())
        log.debug(f"Saved: {output_path}")


def get_tts_engine(name: str) -> TTSEngine:
    engines = {
        'pyttsx3': Pyttsx3Engine,
        'gtts': GTTSEngine,
        'edge-tts': EdgeTTSEngine,
    }
    if name not in engines:
        raise ValueError(f"Unknown TTS engine: {name}. Choose: {list(engines)}")
    return engines[name]()


# ─────────────────────────────────────────────
# Audio Merger
# ─────────────────────────────────────────────

class AudioMerger:
    """Merges multiple audio chunks into a single audiobook file."""

    def merge(self, audio_files: list[str], output_path: str, fmt: str = 'mp3'):
        try:
            from pydub import AudioSegment
        except ImportError:
            log.warning("pydub not installed. Skipping merge. Install: pip install pydub")
            return

        log.info(f"Merging {len(audio_files)} audio chunks…")
        combined = AudioSegment.empty()
        silence = AudioSegment.silent(duration=800)  # 0.8 s pause between chapters

        for path in audio_files:
            if os.path.exists(path):
                seg = AudioSegment.from_file(path, format=fmt)
                combined += seg + silence

        combined.export(output_path, format=fmt)
        log.info(f"Merged audiobook saved to: {output_path}")


# ─────────────────────────────────────────────
# Main Converter
# ─────────────────────────────────────────────

class PDFToAudiobook:
    """Orchestrates the full PDF → Audiobook pipeline."""

    def __init__(self, config: AudiobookConfig):
        self.config = config
        self.extractor = PDFExtractor(config.input_pdf)
        self.cleaner = TextCleaner()
        self.chapter_detector = ChapterDetector()
        self.tts = get_tts_engine(config.tts_engine)
        self.merger = AudioMerger()
        os.makedirs(config.output_dir, exist_ok=True)

    def convert(self) -> str:
        """Run the full conversion pipeline. Returns path to final audio file."""
        log.info("=" * 60)
        log.info(f"PDF  : {self.config.input_pdf}")
        log.info(f"TTS  : {self.config.tts_engine}")
        log.info(f"Out  : {self.config.output_dir}")
        log.info("=" * 60)

        # Step 1: Extract pages
        pages = self.extractor.extract_pages(
            start=self.config.start_page,
            end=self.config.end_page
        )

        # Step 2: Clean text
        for p in pages:
            p['text'] = self.cleaner.clean(p['text'], self.config.skip_headers)

        # Step 3: Detect chapters
        chapters = self.chapter_detector.detect(pages)

        # Step 4: Synthesize each chapter
        audio_files = []
        for ch in chapters:
            files = self._synthesize_chapter(ch)
            audio_files.extend(files)

        # Step 5: Optionally merge
        pdf_stem = Path(self.config.input_pdf).stem
        final_path = os.path.join(self.config.output_dir, f"{pdf_stem}_audiobook.{self.config.output_format}")

        if self.config.merge_output and len(audio_files) > 1:
            self.merger.merge(audio_files, final_path, self.config.output_format)
        elif audio_files:
            import shutil
            shutil.copy(audio_files[0], final_path)

        log.info(f"\n✅ Audiobook created: {final_path}")
        return final_path

    def _synthesize_chapter(self, chapter: Chapter) -> list[str]:
        """Synthesize one chapter, splitting into chunks if needed."""
        chunks = self._chunk_text(chapter.text, self.config.chunk_size)
        audio_files = []
        safe_title = re.sub(r'[^\w\s-]', '', chapter.title)[:40].strip().replace(' ', '_')

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            filename = f"ch{chapter.index:03d}_{safe_title}_part{i:02d}.{self.config.output_format}"
            out_path = os.path.join(self.config.output_dir, "chunks", filename)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            log.info(f"  Synthesizing: {filename} ({len(chunk)} chars)")
            try:
                self.tts.synthesize(chunk, out_path, self.config)
                audio_files.append(out_path)
            except Exception as e:
                log.error(f"  TTS failed for {filename}: {e}")

        return audio_files

    @staticmethod
    def _chunk_text(text: str, size: int) -> list[str]:
        """Split text into chunks at sentence boundaries."""
        if len(text) <= size:
            return [text]

        chunks = []
        while text:
            if len(text) <= size:
                chunks.append(text)
                break
            cut = size
            # Try to cut at sentence end
            for sep in ['. ', '! ', '? ', '\n\n', '\n']:
                pos = text.rfind(sep, 0, size)
                if pos != -1:
                    cut = pos + len(sep)
                    break
            chunks.append(text[:cut])
            text = text[cut:]
        return chunks


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="📖 PDF to Audiobook Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pdf_to_audiobook.py book.pdf
  python pdf_to_audiobook.py book.pdf --engine gtts --lang en
  python pdf_to_audiobook.py book.pdf --engine edge-tts --voice en-US-GuyNeural
  python pdf_to_audiobook.py book.pdf --start 5 --end 50 --output ./audio
  python pdf_to_audiobook.py --list-voices
        """
    )
    p.add_argument('input_pdf', nargs='?', help='Path to the PDF file')
    p.add_argument('--engine', choices=['pyttsx3', 'gtts', 'edge-tts'], default='pyttsx3',
                   help='TTS engine (default: pyttsx3)')
    p.add_argument('--output', default='output_audio', help='Output directory')
    p.add_argument('--format', choices=['mp3', 'wav'], default='mp3', help='Audio format')
    p.add_argument('--lang', default='en', help='Language code (e.g., en, hi, fr)')
    p.add_argument('--voice', help='Voice ID/name (engine-specific)')
    p.add_argument('--rate', type=int, default=150, help='Speech rate (words/min, pyttsx3 only)')
    p.add_argument('--volume', type=float, default=1.0, help='Volume 0.0–1.0 (pyttsx3 only)')
    p.add_argument('--start', type=int, default=1, help='Start page')
    p.add_argument('--end', type=int, default=None, help='End page')
    p.add_argument('--no-merge', action='store_true', help='Keep chapters as separate files')
    p.add_argument('--list-voices', action='store_true', help='List available pyttsx3 voices')
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.list_voices:
        engine = Pyttsx3Engine()
        voices = engine.list_voices()
        print(f"\n{'ID':<60} {'Name':<30} Languages")
        print("-" * 100)
        for vid, name, langs in voices:
            print(f"{vid:<60} {name:<30} {langs}")
        return

    if not args.input_pdf:
        parser.print_help()
        sys.exit(1)

    config = AudiobookConfig(
        input_pdf=args.input_pdf,
        output_dir=args.output,
        tts_engine=args.engine,
        language=args.lang,
        voice=args.voice,
        rate=args.rate,
        volume=args.volume,
        merge_output=not args.no_merge,
        start_page=args.start,
        end_page=args.end,
        output_format=args.format,
    )

    converter = PDFToAudiobook(config)
    converter.convert()


if __name__ == '__main__':
    main()

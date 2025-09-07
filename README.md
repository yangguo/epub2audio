EPUB to MP3 (gTTS)

Convert an EPUB ebook into an MP3 audiobook using the free Google Text-to-Speech service (via `gTTS`). Produces a folder of per-chapter MP3 files and a simple `playlist.m3u` in reading order.

Requirements
- Python 3.9+
- `pip install -r requirements.txt`
- Internet connection (gTTS calls an online service)

Optional
- `ffmpeg` is NOT required. Tags are added with `mutagen` only.

Usage
```
python epub2audio.py path/to/book.epub \
  --lang en \
  --tld com \
  --artist "Author Name"
```

Key options
- `--outdir`: Output dir (default: `<epubname>_audio`)
- `--lang`: Language code (e.g., `en`, `es`, `de`)
- `--tld`: Accent via top-level domain (e.g., `com`, `co.uk`, `com.au`)
- `--slow`: Slower speech
- `--min-chapter-chars`: Skip very short documents (default 200)
- `--start`, `--limit`: Render a subset of chapters
- `--album`, `--artist`: ID3 tags for the generated MP3s

What it does
- Parse the EPUB in spine order
- Extract readable text from each HTML document
- Skip short/non-content docs (e.g., ToC, colophon)
- Generate `NNN - Chapter Title.mp3` per chapter with ID3 tags
- Create a `playlist.m3u` in the output directory

Examples
- Basic:
```
python epub2audio.py diary1.epub
```

- UK accent, slower, custom artist:
```
python epub2audio.py diary1.epub --tld co.uk --slow --artist "Anonymous"
```

Split a single-file book by headings (h1 or h2 or h3):
```
python epub2audio.py diary1.epub --split-on h1,h2,h3
```

Notes
- gTTS is a free online TTS; usage is subject to Google’s service behavior and rate limits.
- Chapter titles are guessed from the HTML `<title>` or the first heading.
- If you rerun the script, existing chapter MP3s are skipped.

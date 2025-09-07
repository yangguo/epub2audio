EPUB to MP3 (gTTS / edge-tts)

Convert an EPUB ebook into an MP3 audiobook using free TTS engines: Google Text-to-Speech (`gTTS`) or Microsoft Edge TTS (`edge-tts`). Produces a folder of per-chapter MP3 files and a simple `playlist.m3u` in reading order.

Requirements
- Python 3.9+
- `pip install -r requirements.txt`
- Internet connection (both gTTS and edge-tts call online services)

Optional
- `ffmpeg` is NOT required. Tags are added with `mutagen` only.

Usage
```
python epub2audio.py path/to/book.epub \
  --engine gtts \
  --lang en \
  --tld com \
  --artist "Author Name"
```

Key options
- `--outdir`: Output dir (default: `<epubname>_audio`)
- `--engine gtts|edge`: Pick the TTS backend
- gTTS: `--lang`, `--tld`, `--slow`
- edge-tts: `--voice`, `--rate`, `--volume`, `--pitch`
- `--min-chapter-chars`: Skip very short documents (default 200)
- `--start`, `--limit`: Render a subset of chapters
- `--album`, `--artist`: ID3 tags for the generated MP3s
- `--jobs N`: Parallel chapter synthesis (e.g., 4)
- `--max-retries`, `--retry-wait`: Network retry control

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

Use edge-tts with a neural voice (often faster):
```
python epub2audio.py diary1.epub --engine edge --voice en-US-JennyNeural --jobs 4
```

Speed tips
- Use `--split-on h1,h2,h3` if the book is a single large HTML file.
- Run parallel chapters with `--jobs 4` (or more) to overlap network requests.
- Re-runs skip existing MP3s; you can process in batches with `--start`/`--limit`.

Notes
- gTTS and edge-tts are free online TTS; usage is subject to service behavior and rate limits.
- Chapter titles are guessed from the HTML `<title>` or the first heading.
- If you rerun the script, existing chapter MP3s are skipped.

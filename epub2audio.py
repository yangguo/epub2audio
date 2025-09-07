#!/usr/bin/env python3
import argparse
import os
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT
from gtts import gTTS
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TALB, TPE1, TRCK


def sanitize_filename(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    return name[:150] or "untitled"


def html_to_text(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def guess_title(item) -> str:
    # Try to extract a reasonable title per document
    try:
        soup = BeautifulSoup(item.get_content(), "html.parser")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        # Fallback: first heading
        for hn in ["h1", "h2", "h3"]:
            h = soup.find(hn)
            if h and h.get_text(strip=True):
                return h.get_text(strip=True)
    except Exception:
        pass
    # Fallback to file name
    return Path(item.file_name).stem.replace("_", " ")


def extract_chapters(epub_path: Path, split_on: list[str] | None = None):
    book = epub.read_epub(str(epub_path))

    # Build spine order list of document file names
    spine_order = []
    for idref, _ in book.spine:
        try:
            item = book.get_item_with_id(idref)
            if item and getattr(item, 'get_type', lambda: None)() == ITEM_DOCUMENT:
                spine_order.append(item.file_name)
        except Exception:
            continue

    # Map file_name -> item for documents
    docs = {i.file_name: i for i in book.get_items_of_type(ITEM_DOCUMENT)}

    chapters = []
    seen = set()
    order = 0
    for fname in spine_order:
        item = docs.get(fname)
        if not item or fname in seen:
            continue
        seen.add(fname)

        if split_on:
            from bs4.element import Tag

            soup = BeautifulSoup(item.get_content(), "html.parser")
            headings = soup.find_all(split_on)

            if headings:
                for i, h in enumerate(headings, start=1):
                    # Collect siblings until next heading
                    buf = []
                    for sib in h.next_siblings:
                        if isinstance(sib, Tag) and sib.name in split_on:
                            break
                        buf.append(str(sib))
                    section_html = ("".join(buf)).encode("utf-8")
                    text = html_to_text(section_html)
                    if not text:
                        continue
                    title = h.get_text(strip=True) or f"Section {i}"
                    chapters.append({
                        "order": order,
                        "title": title,
                        "text": text,
                    })
                    order += 1
                # If we created sections for this item, continue to next item
                if order > 0 and chapters and chapters[-1]["title"]:
                    continue

        # Fallback: treat the whole document as one chapter
        title = guess_title(item)
        text = html_to_text(item.get_content())
        chapters.append({
            "order": order,
            "title": title,
            "text": text,
        })
        order += 1

    # Fallback: if spine not found, iterate documents directly
    if not chapters:
        for order, item in enumerate(docs.values()):
            chapters.append({
                "order": order,
                "title": guess_title(item),
                "text": html_to_text(item.get_content()),
            })

    return chapters


def write_id3_tags(mp3_path: Path, title: str, album: str, artist: str, track_number: int):
    try:
        tags = ID3()
        tags.add(TIT2(encoding=3, text=title))
        tags.add(TALB(encoding=3, text=album))
        tags.add(TPE1(encoding=3, text=artist))
        tags.add(TRCK(encoding=3, text=str(track_number)))
        tags.save(str(mp3_path))
    except Exception:
        # Best-effort; ignore tag failures
        pass


def synthesize_gtts(text: str, out_path: Path, lang: str, tld: str, slow: bool):
    tts = gTTS(text=text, lang=lang, tld=tld, slow=slow)
    tts.save(str(out_path))


def build_playlist(out_dir: Path, entries):
    m3u = out_dir / "playlist.m3u"
    with m3u.open("w", encoding="utf-8") as f:
        for p in entries:
            f.write(p.name + "\n")


def main():
    parser = argparse.ArgumentParser(description="Convert an EPUB to an MP3 audiobook using free TTS (gTTS)")
    parser.add_argument("epub", type=Path, help="Path to the .epub file")
    parser.add_argument("--outdir", type=Path, default=None, help="Output directory (default: <epubname>_audio)")
    parser.add_argument("--lang", default="en", help="gTTS language code, e.g., en, en-uk, es, de")
    parser.add_argument("--tld", default="com", help="gTTS top-level-domain for accent (e.g., com, co.uk, com.au, co.in)")
    parser.add_argument("--slow", action="store_true", help="Speak more slowly")
    parser.add_argument("--min-chapter-chars", type=int, default=200, help="Skip chapters shorter than this length")
    parser.add_argument("--split-on", default=None, help="Comma-separated headings to split on, e.g., 'h1,h2,h3'")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of chapters to render")
    parser.add_argument("--start", type=int, default=0, help="Start from chapter index (0-based)")
    parser.add_argument("--album", default=None, help="Album name for ID3 tags (default: EPUB title or filename)")
    parser.add_argument("--artist", default="Unknown", help="Artist/Author for ID3 tags")

    args = parser.parse_args()

    epub_path = args.epub
    if not epub_path.exists():
        print(f"EPUB not found: {epub_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = args.outdir or epub_path.with_suffix("").name + "_audio"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading EPUB: {epub_path}")
    split_on = None
    if args.split_on:
        split_on = [h.strip().lower() for h in args.split_on.split(",") if h.strip()]

    chapters = extract_chapters(epub_path, split_on=split_on)
    if not chapters:
        print("No chapters found.", file=sys.stderr)
        sys.exit(2)

    # Determine album title
    album = args.album or epub_path.stem

    # Filter and slice chapters
    chapters = [c for c in chapters if len(c["text"]) >= args.min_chapter_chars]
    chapters = chapters[args.start:]
    if args.limit is not None:
        chapters = chapters[: args.limit]

    if not chapters:
        print("No chapters to render after filtering.", file=sys.stderr)
        sys.exit(3)

    print(f"Found {len(chapters)} chapter(s) to render.")
    written = []
    total = len(chapters)
    for idx, ch in enumerate(chapters, start=1):
        title = ch["title"] or f"Chapter {idx}"
        safe_title = sanitize_filename(title)
        filename = f"{idx:03d} - {safe_title}.mp3"
        out_path = out_dir / filename

        # Skip if already exists
        if out_path.exists():
            print(f"[{idx}/{total}] Exists, skipping: {filename}")
            written.append(out_path)
            continue

        print(f"[{idx}/{total}] Synthesizing: {filename}")
        try:
            synthesize_gtts(ch["text"], out_path, lang=args.lang, tld=args.tld, slow=args.slow)
            write_id3_tags(out_path, title=title, album=album, artist=args.artist, track_number=idx)
            written.append(out_path)
        except Exception as e:
            print(f"Failed chapter '{title}': {e}", file=sys.stderr)

    if written:
        build_playlist(out_dir, written)
        print(f"\nDone. Wrote {len(written)} MP3 file(s) to: {out_dir}")
        print("Playlist:", out_dir / "playlist.m3u")
    else:
        print("No MP3s were written.", file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()

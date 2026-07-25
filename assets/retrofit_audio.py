#!/usr/bin/env python3
"""Retrofit lesson HTML files with <audio> players from assets/audio/manifest.json.

Idempotent: strips previously injected audio-block / audio-disclaimer nodes first.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "assets" / "audio" / "manifest.json"
LESSONS = ROOT / "lessons"
AUDIO_REL = "../assets/audio"

DISCLAIMER_HTML = """\
      <div class="audio-disclaimer" role="note">
        <strong>Audio:</strong> Machine-generated Kannada (edge-tts · kn-IN-SapnaNeural).
        Helpful for rhythm and recognition — may not perfectly match native Bengaluru pronunciation.
        Prefer what you hear from neighbours when the two differ.
      </div>
"""


def load_index(entries: list) -> dict[str, dict]:
    """Map normalized roman → preferred entry.

    Preference: exact roman key. For collisions, keep both via type-specific maps.
    """
    by_exact: dict[str, dict] = {}
    by_norm: dict[str, dict] = {}
    words_by_norm: dict[str, dict] = {}
    sents_by_norm: dict[str, dict] = {}

    def norms(roman: str) -> list[str]:
        r = re.sub(r"\s+", " ", roman).strip()
        out = {r.lower(), r.lower().rstrip("?.! ").strip()}
        # without final period
        out.add(r.lower().rstrip(".").strip())
        return [x for x in out if x]

    for e in entries:
        for n in norms(e["roman"]):
            by_exact[e["roman"].lower()] = e
            by_norm[n] = e
            if e["type"] == "word":
                words_by_norm[n] = e
            else:
                sents_by_norm[n] = e
    return {
        "exact": by_exact,
        "norm": by_norm,
        "words": words_by_norm,
        "sents": sents_by_norm,
    }


def lookup(index: dict, text: str, prefer: str = "any") -> dict | None:
    t = re.sub(r"\s+", " ", text).strip()
    # strip leading/trailing ellipsis templates: "… rupayi" → "rupayi"
    t_clean = re.sub(r"^[\s.…]+", "", t)
    t_clean = re.sub(r"[\s.…]+$", "", t_clean).strip()
    keys = []
    for candidate in (t, t_clean):
        if not candidate:
            continue
        keys.extend(
            [
                candidate.lower(),
                candidate.lower().rstrip("?.! ").strip(),
                candidate.lower().rstrip(".").strip(),
            ]
        )
    # de-dupe preserve order
    seen = set()
    uniq = []
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            uniq.append(k)
    keys = uniq
    pools = []
    if prefer == "word":
        pools = [index["words"], index["norm"], index["sents"]]
    elif prefer == "sentence":
        pools = [index["sents"], index["norm"], index["words"]]
    else:
        pools = [index["exact"], index["sents"], index["words"], index["norm"]]
    for pool in pools:
        for k in keys:
            if k in pool:
                return pool[k]
    return None


def audio_html(entry: dict) -> str:
    slug = entry["slug"]
    if entry["type"] == "word":
        src = f"{AUDIO_REL}/{slug}.mp3"
        return (
            f'<div class="audio-block" data-slug="{slug}">'
            f'<audio controls preload="none" src="{src}"></audio>'
            f"</div>"
        )
    slow = f"{AUDIO_REL}/{slug}_slow.mp3"
    nat = f"{AUDIO_REL}/{slug}_nat.mp3"
    return (
        f'<div class="audio-block" data-slug="{slug}">'
        f'<span class="audio-pair"><span class="audio-label">slow</span>'
        f'<audio controls preload="none" src="{slow}"></audio></span>'
        f'<span class="audio-pair"><span class="audio-label">natural</span>'
        f'<audio controls preload="none" src="{nat}"></audio></span>'
        f"</div>"
    )


def strip_previous(html: str) -> str:
    html = re.sub(
        r'\s*<div class="audio-disclaimer"[^>]*>.*?</div>\s*',
        "\n",
        html,
        flags=re.S,
    )
    html = re.sub(
        r'\s*<div class="audio-block"[^>]*>.*?</div>\s*',
        "\n",
        html,
        flags=re.S,
    )
    return html


def inject_after_match(html: str, pattern: str, replacer) -> str:
    """Call replacer(match) -> full replacement string including original."""

    def _sub(m):
        return replacer(m)

    return re.sub(pattern, _sub, html, flags=re.S)


def process_lesson(path: Path, index: dict) -> dict:
    html = path.read_text(encoding="utf-8")
    html = strip_previous(html)
    stats = {"phrase": 0, "vocab": 0, "dialogue": 0, "missing": []}

    # Insert disclaimer after course-header (or after lede / first win)
    if 'class="audio-disclaimer"' not in html:
        if re.search(r"</header>\s*", html):
            html = re.sub(
                r"(</header>\s*)",
                r"\1" + DISCLAIMER_HTML + "\n",
                html,
                count=1,
            )
        else:
            html = DISCLAIMER_HTML + html

    # Phrase cards: <p class="kn">...</p>
    def phrase_repl(m):
        full = m.group(0)
        inner = re.sub(r"<[^>]+>", "", m.group(1))
        inner = re.sub(r"\s+", " ", inner).strip()
        parts = re.split(r"\s*·\s*", inner)
        blocks = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # split short A / B
            subparts = (
                [p.strip() for p in part.split(" / ")]
                if (" / " in part and len(part) < 48)
                else [part]
            )
            for sp in subparts:
                if not sp or sp in ("…", "..."):
                    continue
                prefer = "sentence" if (" " in sp or sp.endswith("?")) else "word"
                # for "Sari · Beda" each is word
                e = lookup(index, sp, prefer=prefer)
                if not e and prefer == "sentence":
                    e = lookup(index, sp, prefer="word")
                if e:
                    blocks.append(audio_html(e))
                    stats["phrase"] += 1
                else:
                    stats["missing"].append(("phrase", sp))
        if not blocks:
            return full
        return full + "\n        " + "\n        ".join(blocks)

    html = inject_after_match(html, r'<p class="kn">(.*?)</p>', phrase_repl)

    # Vocab / num / dir: <span class="kn">...</span>
    # Avoid double-injecting if already followed by audio-block (shouldn't after strip)
    def vocab_repl(m):
        full = m.group(0)
        # only act when this span is a direct kn cell (not nested weirdness)
        inner = re.sub(r"<[^>]+>", "", m.group(1))
        inner = re.sub(r"\s+", " ", inner).strip()
        if not inner or "…" in inner or "..." in inner:
            return full
        parts = re.split(r"\s*[·/]\s*", inner)
        blocks = []
        for sp in parts:
            sp = sp.strip()
            if not sp:
                continue
            e = lookup(index, sp, prefer="word")
            if not e:
                e = lookup(index, sp, prefer="sentence")
            if e:
                blocks.append(audio_html(e))
                stats["vocab"] += 1
            else:
                stats["missing"].append(("vocab", sp))
        if not blocks:
            return full
        # keep span inline; put audio after the span (may sit inside grid cell)
        return full + "".join(blocks)

    html = inject_after_match(html, r'<span class="kn">(.*?)</span>', vocab_repl)

    # Dialogue lines
    def line_repl(m):
        full = m.group(0)
        inner = re.sub(r"<[^>]+>", "", m.group(1))
        inner = re.sub(r"\s+", " ", inner).strip()
        if not inner:
            return full
        e = lookup(index, inner, prefer="sentence")
        if not e:
            # try cleaned ellipsis
            cleaned = inner.replace("…", ".").replace("...", ".")
            cleaned = re.sub(r"\s*\.\s*", ". ", cleaned).strip(" .")
            e = lookup(index, cleaned, prefer="sentence")
            if not e:
                e = lookup(index, cleaned, prefer="word")
        if not e:
            stats["missing"].append(("dialogue", inner))
            return full
        stats["dialogue"] += 1
        return full + "\n        " + audio_html(e)

    html = inject_after_match(html, r'<span class="line">(.*?)</span>', line_repl)

    path.write_text(html, encoding="utf-8")
    return stats


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    index = load_index(data["entries"])
    total_missing = []
    for path in sorted(LESSONS.glob("*.html")):
        stats = process_lesson(path, index)
        print(
            f"{path.name}: phrase={stats['phrase']} vocab={stats['vocab']} "
            f"dialogue={stats['dialogue']} missing={len(stats['missing'])}"
        )
        for kind, text in stats["missing"]:
            print(f"  MISSING [{kind}] {text}")
            total_missing.append((path.name, kind, text))
    print(f"\nTotal missing attachments: {len(total_missing)}")


if __name__ == "__main__":
    main()

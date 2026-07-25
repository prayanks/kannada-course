#!/usr/bin/env python3
"""Generate Kannada audio clips from assets/audio/manifest.json via edge-tts.

Idempotent: skips files that already exist unless --force.
Words  → <slug>.mp3 at natural speed
Sentences → <slug>_slow.mp3 (-35%) and <slug>_nat.mp3 (natural)

Usage:
  python3 assets/generate_audio.py
  python3 assets/generate_audio.py --force
  python3 assets/generate_audio.py --only namaskaara,hegiddiri
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).resolve().parent / "audio" / "manifest.json"
OUT_DIR = Path(__file__).resolve().parent / "audio"

# Prefer Hermes venv edge-tts if present
CANDIDATE_EDGE = [
    Path.home() / ".hermes/hermes-agent/venv/bin/edge-tts",
    Path(shutil.which("edge-tts") or ""),
]


def find_edge_tts() -> str:
    for p in CANDIDATE_EDGE:
        if p and p.exists():
            return str(p)
    # try module
    return sys.executable  # fallback used with -m


async def synth_one(
    text: str,
    voice: str,
    rate: str,
    dest: Path,
    semaphore: asyncio.Semaphore,
) -> tuple[Path, str]:
    """Return (dest, status) status in ok|skip|error:..."""
    if dest.exists() and dest.stat().st_size > 0 and not FORCE:
        return dest, "skip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    if tmp.exists():
        tmp.unlink()

    edge = find_edge_tts()
    async with semaphore:
        try:
            # Use edge_tts Python API when available for cleaner control
            try:
                import edge_tts  # type: ignore
            except ImportError:
                # subprocess fallback
                import os

                env = os.environ.copy()
                cmd = [
                    edge if edge.endswith("edge-tts") else sys.executable,
                ]
                if not edge.endswith("edge-tts"):
                    cmd += ["-m", "edge_tts"]
                else:
                    cmd = [edge]
                cmd += [
                    "--voice",
                    voice,
                    "--rate",
                    rate,
                    "--text",
                    text,
                    "--write-media",
                    str(tmp),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, err = await proc.communicate()
                if proc.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
                    if tmp.exists():
                        tmp.unlink()
                    return dest, f"error: {err.decode()[:200]}"
                tmp.replace(dest)
                return dest, "ok"

            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(str(tmp))
            if not tmp.exists() or tmp.stat().st_size == 0:
                if tmp.exists():
                    tmp.unlink()
                return dest, "error: empty output"
            tmp.replace(dest)
            return dest, "ok"
        except Exception as e:
            if tmp.exists():
                tmp.unlink()
            return dest, f"error: {e}"


FORCE = False


async def run(only: set[str] | None, concurrency: int) -> int:
    global FORCE
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    voice = data["tts"]["voice"]
    rates = data["tts"]["rates"]
    entries = data["entries"]

    jobs: list[tuple[str, str, str, Path]] = []  # text, voice, rate, dest
    for e in entries:
        if only and e["slug"] not in only and e["roman"].lower() not in only:
            continue
        kn = e["kannada"]
        if e["type"] == "word":
            jobs.append((kn, voice, rates.get("word", "+0%"), OUT_DIR / e["files"][0]))
        else:
            jobs.append(
                (kn, voice, rates.get("sentence_slow", "-35%"), OUT_DIR / e["files"][0])
            )
            jobs.append(
                (kn, voice, rates.get("sentence_nat", "+0%"), OUT_DIR / e["files"][1])
            )

    print(f"Jobs: {len(jobs)}  voice={voice}  out={OUT_DIR}")
    sem = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(*[synth_one(t, v, r, d, sem) for t, v, r, d in jobs])

    ok = skip = err = 0
    errors = []
    for dest, status in results:
        if status == "ok":
            ok += 1
        elif status == "skip":
            skip += 1
        else:
            err += 1
            errors.append((dest.name, status))

    print(f"Done: ok={ok} skip={skip} err={err}")
    for name, status in errors[:30]:
        print(f"  FAIL {name}: {status}")
    return 1 if err else 0


def main() -> None:
    global FORCE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    ap.add_argument("--only", type=str, default="", help="Comma-separated slugs to generate")
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()
    FORCE = args.force
    only = {s.strip().lower() for s in args.only.split(",") if s.strip()} or None

    # Ensure edge_tts importable: prefer hermes venv
    hermes_py = Path.home() / ".hermes/hermes-agent/venv/bin/python"
    if hermes_py.exists() and Path(sys.executable) != hermes_py:
        # re-exec under hermes venv so edge_tts imports cleanly
        import os

        os.execv(
            str(hermes_py),
            [str(hermes_py), str(Path(__file__).resolve()), *sys.argv[1:]],
        )

    if not MANIFEST.exists():
        print(f"Missing manifest: {MANIFEST}", file=sys.stderr)
        print("Run: python3 assets/build_manifest.py", file=sys.stderr)
        sys.exit(2)

    raise SystemExit(asyncio.run(run(only, args.concurrency)))


if __name__ == "__main__":
    main()

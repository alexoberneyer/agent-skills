#!/usr/bin/env python3
"""Transcribe Apple Voice Memos that sync from iPhone and Apple Watch.

Standard library only. Borrows local transcription from the video skill
(ffmpeg and mlx-audio). Progress goes to stderr, results to stdout.

Usage:
    memos.py [--last N | --since YYYY-MM-DD] [--language LANG] [--model REPO]
             [--dir DIR] [--dry-run]

Without --last or --since it takes the memos added since the previous run and
remembers them. The first run takes only the newest memo.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path

_VIDEO = Path(__file__).resolve().parents[2] / "video" / "scripts" / "video.py"
_spec = importlib.util.spec_from_file_location("video", _VIDEO)
video = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(video)
Fail, log = video.Fail, video.log

RECORDINGS = Path.home() / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
AUDIO_SUFFIXES = {".m4a", ".qta"}
FULL_DISK_ACCESS = (
    "macOS blocks the Voice Memos folder. Open System Settings > Privacy & Security > "
    "Full Disk Access, add the terminal app that runs this (Ghostty, Terminal, iTerm), "
    "restart that app and run again."
)


def state_file() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / "voice-memos" / "seen.json"


def load_seen(path: Path) -> set[str] | None:
    """Names of memos already handled, or None before the first run."""
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return None


def save_seen(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(seen), indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def list_memos(folder: Path) -> list[Path]:
    """Audio files in the folder, oldest first."""
    try:
        files = [p for p in folder.iterdir() if p.suffix.lower() in AUDIO_SUFFIXES and p.is_file()]
    except PermissionError as error:
        raise Fail(FULL_DISK_ACCESS) from error
    except FileNotFoundError as error:
        raise Fail(f"{folder} does not exist. Turn on Voice Memos under iCloud in System Settings.") from error
    return sorted(files, key=lambda p: (p.stat().st_mtime, p.name))


def select(memos: list[Path], seen: set[str] | None, last: int | None = None,
           since: dt.date | None = None) -> list[Path]:
    if last:
        return memos[-last:]
    if since:
        return [m for m in memos if dt.date.fromtimestamp(m.stat().st_mtime) >= since]
    if seen is None:
        return memos[-1:]
    return [m for m in memos if m.name not in seen]


def probe(path: Path) -> tuple[str, float | None]:
    """Local recording time and duration in seconds, from the file's metadata."""
    try:
        data = json.loads(video.run(["ffprobe", "-v", "error", "-show_entries",
                                     "format=duration:format_tags=creation_time",
                                     "-of", "json", str(path)]))
    except (Fail, ValueError):
        data = {}
    fields = data.get("format") or {}
    try:
        when = dt.datetime.fromisoformat(fields["tags"]["creation_time"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        when = dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc)
    seconds = float(fields["duration"]) if fields.get("duration") else None
    return when.astimezone().strftime("%Y-%m-%d %H:%M"), seconds


def transcribe_memo(memo: Path, args: argparse.Namespace) -> dict:
    key = re.sub(r"[^A-Za-z0-9_-]+", "_", memo.stem)
    work = Path(tempfile.gettempdir()) / "voice-memos" / key
    work.mkdir(parents=True, exist_ok=True)
    vtt, source = video.transcribe_audio(memo, work / "local", args.language, args.model)
    text = video.vtt_to_text(vtt.read_text(encoding="utf-8"))
    transcript = work / "transcript.txt"
    transcript.write_text(text + "\n", encoding="utf-8")
    words = len(re.sub(r"^\[[\d:]+\] ", "", text, flags=re.MULTILINE).split())
    return {"source": source, "words": words, "transcript": transcript}


def transcribe_memos(args: argparse.Namespace) -> None:
    video.need("ffprobe")
    folder = Path(args.dir).expanduser()
    memos = list_memos(folder)
    if not memos:
        print(f"no voice memos in {folder}")
        return
    path = state_file()
    seen = load_seen(path)
    chosen = select(memos, seen, args.last, args.since)
    if not chosen:
        print("no new voice memos since the last run")
        return
    if seen is None:
        older = len(memos) - 1
        if older and not (args.last or args.since):
            log(f"first run: taking the newest memo and skipping {older} older "
                f"{'memo' if older == 1 else 'memos'}. Use --last N or --since for those.")
        seen = {m.name for m in memos if m not in chosen}
    if not args.dry_run:
        video.need_local()
    for memo in chosen:
        when, seconds = probe(memo)
        print(f"memo: {memo.name}")
        print(f"recorded: {when}")
        if seconds:
            print(f"duration: {video.clock(seconds)}")
        if not args.dry_run:
            for name, value in transcribe_memo(memo, args).items():
                print(f"{name}: {value}")
            seen.add(memo.name)
            save_seen(path, seen)
        print(flush=True)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Transcribe Apple Voice Memos synced to this Mac.")
    pick = root.add_mutually_exclusive_group()
    pick.add_argument("--last", type=int, metavar="N", help="the newest N memos, handled before or not")
    pick.add_argument("--since", type=dt.date.fromisoformat, metavar="YYYY-MM-DD",
                      help="memos whose file date is on or after this day")
    root.add_argument("--language",
                      help="spoken language, e.g. ja. Only needed outside Parakeet's 25 languages")
    root.add_argument("--model", help=f"Hugging Face model for mlx-audio (default: {video.PARAKEET})")
    root.add_argument("--dir", default=str(RECORDINGS),
                      help="folder to read (default: the Voice Memos sync folder)")
    root.add_argument("--dry-run", action="store_true",
                      help="list the memos without transcribing or remembering them")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.last is not None and args.last < 1:
        log("error: --last must be 1 or more")
        return 1
    try:
        transcribe_memos(args)
    except Fail as error:
        log(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

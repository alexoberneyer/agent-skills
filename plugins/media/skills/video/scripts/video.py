#!/usr/bin/env python3
"""Download a video, or build a transcript to summarize it.

Standard library only. Shells out to yt-dlp and ffmpeg, and to mlx-audio (run
through uvx) for videos without captions. Progress goes to stderr, results to
stdout.

Usage:
    video.py download URL --name NAME [--dir DIR] [--section START-END]
                                      [--max-mb N] [--item N]
    video.py transcript URL [--language LANG] [--force-local]
                            [--work-dir DIR] [--model REPO] [--item N]

Both commands accept --cookies-from-browser BROWSER for login-walled posts.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

MLX_AUDIO = "mlx-audio==0.5.3"
PARAKEET = "mlx-community/parakeet-tdt-0.6b-v3"
WHISPER = "mlx-community/whisper-large-v3-turbo-asr-fp16"
MODEL_SIZES = {PARAKEET: "2.4 GB", WHISPER: "1.5 GB"}
# The languages Parakeet v3 transcribes, from its model card. Whisper takes the rest.
PARAKEET_LANGUAGES = frozenset(
    "bg cs da de el en es et fi fr hr hu it lt lv mt nl pl pt ro ru sk sl sv uk".split()
)
AUDIO_KBPS = 128
INSTALL = {
    "yt-dlp": "brew install yt-dlp",
    "ffmpeg": "brew install ffmpeg",
    "ffprobe": "brew install ffmpeg",
    "uvx": "brew install uv",
}
PLACEHOLDER_EXT = re.compile(
    r"\.(?:<[^>]*>|\[[^\]]*\]|\{[^}]*\}|ext(?:ension)?|file-?(?:extension|ending)"
    r"|mp4|m4v|mov|mkv|webm)$",
    re.IGNORECASE,
)
SECTION = re.compile(r"^\d[\d:.]*-(?:\d[\d:.]*|inf)$")
CUE_TIMING = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})[.,]\d{3}\s+-->")
LOGIN_HINT = re.compile(
    r"sign in|log ?in|cookies|authenticat|age.restricted|nsfw|private", re.IGNORECASE
)


class Fail(Exception):
    """An expected failure with a message for the user."""


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def need(*tools: str) -> None:
    missing = [tool for tool in tools if shutil.which(tool) is None]
    if missing:
        hints = ", ".join(sorted({INSTALL[tool] for tool in missing}))
        raise Fail(f"missing {', '.join(missing)}. Install with: {hints}")


def run(cmd: list[str]) -> str:
    log("$ " + shlex.join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-8:])
        message = f"{cmd[0]} exited with {proc.returncode}:\n{tail}"
        if cmd[0] == "yt-dlp" and LOGIN_HINT.search(tail):
            message += "\nThe site may need a login. Retry with --cookies-from-browser <browser>."
        raise Fail(message)
    return proc.stdout


def ytdlp(args: argparse.Namespace, *extra: str) -> list[str]:
    cmd = ["yt-dlp", "--no-warnings", *extra]
    if args.cookies_from_browser:
        cmd += ["--cookies-from-browser", args.cookies_from_browser]
    return cmd


def clock(seconds: float) -> str:
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


# --- download -----------------------------------------------------------------


def normalize_name(name: str) -> str:
    stem = PLACEHOLDER_EXT.sub("", Path(name.strip()).name)
    if stem in {"", ".", ".."}:
        raise Fail(f"invalid --name: {name!r}")
    return stem


def target_video_kbps(max_mb: float, seconds: float, audio_kbps: int = AUDIO_KBPS) -> int:
    total_kbps = max_mb * 8 * 1024 * 1024 / 1000 / seconds * 0.95
    return int(total_kbps - audio_kbps)


def shrink(path: Path, max_mb: float) -> None:
    limit = max_mb * 1024 * 1024
    if path.stat().st_size <= limit:
        return
    need("ffprobe")
    probe = ["ffprobe", "-v", "error", "-show_entries", "format=duration"]
    seconds = float(run(probe + ["-of", "default=nw=1:nk=1", str(path)]).strip())
    kbps = target_video_kbps(max_mb, seconds)
    tmp = path.with_name(f"{path.stem}.shrinking.mp4")
    for _ in range(3):
        if kbps < 150:
            break
        log(f"re-encoding to fit {max_mb:g} MB (video {kbps} kbit/s)")
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
            "-c:v", "libx264", "-preset", "medium",
            "-b:v", f"{kbps}k", "-maxrate", f"{kbps}k", "-bufsize", f"{kbps * 2}k",
            "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", "-movflags", "+faststart", str(tmp),
        ])
        size = tmp.stat().st_size
        if size <= limit:
            tmp.replace(path)
            return
        kbps = int(kbps * limit / size * 0.95)
    tmp.unlink(missing_ok=True)
    raise Fail(
        f"could not fit {seconds:.0f} s of video into {max_mb:g} MB. "
        f"The full-size file is still at {path}. Try --section or a larger --max-mb."
    )


def download(args: argparse.Namespace) -> None:
    need("yt-dlp", "ffmpeg")
    name = normalize_name(args.name)
    folder = Path(args.dir).expanduser()
    folder.mkdir(parents=True, exist_ok=True)
    taken = sorted(p for p in folder.iterdir() if p.name.split(".")[0] == name)
    if taken:
        raise Fail(f"{taken[0]} already exists. Pick another --name.")
    cmd = ytdlp(
        args,
        "--no-playlist", "--playlist-items", str(args.item),
        "-f", "bv*+ba/b", "-S", "vcodec:h264,res,acodec:aac",
        "--merge-output-format", "mp4", "--remux-video", "mp4",
        "-o", str(folder / f"{name}.%(ext)s"),
        "--print", "after_move:filepath", "--no-simulate",
    )
    if args.section:
        if not SECTION.match(args.section):
            raise Fail(f"--section must look like 0-75 or 1:30-2:45, got {args.section!r}")
        cmd += ["--download-sections", f"*{args.section}", "--force-keyframes-at-cuts"]
    path = Path(run(cmd + [args.url]).strip().splitlines()[-1])
    if args.max_mb:
        shrink(path, args.max_mb)
    print(f"saved: {path}")
    print(f"size_mb: {path.stat().st_size / 1024 / 1024:.1f}")


# --- local transcription --------------------------------------------------------


def pick_model(language: str | None, override: str | None = None) -> str:
    """Parakeet for its languages and for unknown ones, Whisper for everything else."""
    if override:
        return override
    base = language.split("-")[0].lower() if language else None
    return WHISPER if base and base not in PARAKEET_LANGUAGES else PARAKEET


def hub_cached(model: str) -> bool:
    home = Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface")
    hub = Path(os.environ.get("HF_HUB_CACHE") or home / "hub")
    return (hub / f"models--{model.replace('/', '--')}").is_dir()


def need_local() -> None:
    if sys.platform != "darwin" or platform.machine() != "arm64":
        raise Fail("local transcription runs mlx-audio, which needs a Mac with Apple silicon")
    need("ffmpeg", "uvx")


def transcribe_audio(audio: Path, out: Path, language: str | None = None,
                     model: str | None = None) -> tuple[Path, str]:
    """Transcribe any audio file ffmpeg reads into <out>.vtt. Returns (vtt, source)."""
    need_local()
    chosen = pick_model(language, model)
    wav = out.parent / f"{out.name}.wav"
    vtt = out.parent / f"{out.name}.vtt"
    vtt.unlink(missing_ok=True)
    cmd = ["uvx", "--from", MLX_AUDIO, "mlx_audio.stt.generate", "--model", chosen,
           "--audio", str(wav), "--output-path", str(out), "--format", "vtt"]
    if "parakeet" in chosen:
        # The default 30 s chunks split words at the boundaries and garble names.
        cmd += ["--chunk-duration", "120"]
    elif language:
        cmd += ["--language", language.split("-")[0].lower()]
    if not hub_cached(chosen):
        log(f"downloading {chosen} once ({MODEL_SIZES.get(chosen, 'size unknown')}) from Hugging Face")
    try:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(audio),
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)])
        run(cmd)
    finally:
        wav.unlink(missing_ok=True)
    if not vtt.is_file():
        raise Fail("mlx-audio finished but wrote no transcript")
    return vtt, f"mlx-audio ({chosen})"


# --- transcript ---------------------------------------------------------------


def pick_captions(info: dict, language: str | None = None) -> tuple[str, bool] | None:
    """Choose a caption track: (name, automatic) or None when there is nothing usable."""
    manual = {k: v for k, v in (info.get("subtitles") or {}).items() if v and k != "live_chat"}
    auto = {k: v for k, v in (info.get("automatic_captions") or {}).items() if v}
    spoken = language or info.get("language")
    base = spoken.split("-")[0] if spoken else None
    english = ["en", "en-US", "en-GB"]
    steps = [
        (manual, [spoken, base]),
        (auto, [f"{spoken}-orig" if spoken else None, f"{base}-orig" if base else None]),
        (auto, sorted(k for k in auto if k.endswith("-orig"))),
        (auto, [spoken, base]),
        (manual, english),
        (auto, english),
        (manual, sorted(manual)),
    ]
    for tracks, names in steps:
        found = next((n for n in names if n and n in tracks), None)
        if found:
            return found, tracks is auto
    return None


def vtt_to_text(vtt: str) -> str:
    """Flatten WebVTT into one paragraph per minute, dropping rolling-caption repeats."""
    lines = vtt.splitlines()
    paragraphs: list[tuple[int, list[str]]] = []
    recent: deque = deque(maxlen=3)
    start = None
    for index, raw in enumerate(lines):
        line = raw.strip()
        timing = CUE_TIMING.match(line)
        if timing:
            hours, minutes, seconds = timing.groups()
            start = int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)
            continue
        cue_id = index + 1 < len(lines) and CUE_TIMING.match(lines[index + 1].strip())
        if start is None or not line or cue_id:
            continue
        text = " ".join(html.unescape(re.sub(r"<[^>]+>", "", line)).split())
        if not text or text in recent:
            continue
        recent.append(text)
        minute = start // 60
        if not paragraphs or paragraphs[-1][0] != minute:
            paragraphs.append((minute, []))
        paragraphs[-1][1].append(text)
    return "\n\n".join(f"[{clock(m * 60)}] {' '.join(texts)}" for m, texts in paragraphs)


def fetch_info(args: argparse.Namespace) -> dict:
    cmd = ytdlp(args, "--no-playlist", "--playlist-items", str(args.item),
                "--dump-single-json", "--skip-download", args.url)
    info = json.loads(run(cmd))
    if info.get("_type") == "playlist":
        entries = [entry for entry in info.get("entries") or [] if entry]
        if not entries:
            raise Fail("no video found at that URL")
        info = entries[0]
    return info


def download_captions(args, info_path: Path, work: Path, track: str, automatic: bool):
    for old in work.glob("captions.*"):
        old.unlink()
    cmd = ytdlp(
        args, "--load-info-json", str(info_path), "--skip-download",
        "--write-auto-subs" if automatic else "--write-subs", "--sub-langs", track,
        "--sub-format", "vtt/best", "-o", str(work / "captions.%(ext)s"),
    )
    if shutil.which("ffmpeg"):
        cmd += ["--convert-subs", "vtt"]
    try:
        run(cmd)
    except Fail as error:
        log(f"captions failed, transcribing instead: {error}")
        return None
    return next(iter(sorted(work.glob("captions*.vtt"))), None)


def transcribe(args, info: dict, info_path: Path, work: Path) -> tuple[Path, str]:
    need_local()
    for old in work.glob("audio.*"):
        old.unlink()
    run(ytdlp(args, "--load-info-json", str(info_path), "-f", "ba/b",
              "-o", str(work / "audio.%(ext)s")))
    audio = next(iter(work.glob("audio.*")), None)
    if audio is None:
        raise Fail("yt-dlp finished but saved no audio")
    try:
        return transcribe_audio(audio, work / "local", args.language or info.get("language"), args.model)
    finally:
        audio.unlink(missing_ok=True)


def transcript(args: argparse.Namespace) -> None:
    need("yt-dlp")
    info = fetch_info(args)
    key = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{info.get('extractor_key', 'video')}-{info.get('id', 'unknown')}")
    work = Path(args.work_dir).expanduser() if args.work_dir else Path(tempfile.gettempdir()) / "video-skill" / key
    work.mkdir(parents=True, exist_ok=True)
    info_path = work / "info.json"
    info_path.write_text(json.dumps(info), encoding="utf-8")

    vtt = source = None
    track = None if args.force_local else pick_captions(info, args.language)
    if track:
        vtt = download_captions(args, info_path, work, *track)
        source = f"captions ({'auto' if track[1] else 'manual'}, {track[0]})"
    if vtt is None:
        vtt, source = transcribe(args, info, info_path, work)

    text = vtt_to_text(vtt.read_text(encoding="utf-8"))
    transcript_path = work / "transcript.txt"
    transcript_path.write_text(text + "\n", encoding="utf-8")
    description_path = work / "description.txt"
    description_path.write_text(info.get("description") or "", encoding="utf-8")

    words = len(re.sub(r"^\[[\d:]+\] ", "", text, flags=re.MULTILINE).split())
    duration = info.get("duration")
    date = info.get("upload_date") or ""
    fields = {
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "upload_date": f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else None,
        "duration": clock(duration) if duration else None,
        "url": info.get("webpage_url") or args.url,
        "timestamp_link": (
            f"https://www.youtube.com/watch?v={info.get('id')}&t=<seconds>s"
            if info.get("extractor_key") == "Youtube" else None
        ),
        "transcript_source": source,
        "words": words,
        "words_per_minute": round(words / (duration / 60)) if duration else None,
        "transcript": transcript_path,
        "description": description_path,
    }
    for name, value in fields.items():
        if value is not None:
            print(f"{name}: {value}")
    chapters = info.get("chapters") or []
    if chapters:
        print("chapters:")
        for chapter in chapters:
            print(f"  {clock(chapter['start_time'])} {chapter.get('title', '')}")


# --- cli ----------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("url")
    common.add_argument("--item", type=int, default=1,
                        help="which video of a post with several (default: 1)")
    common.add_argument("--cookies-from-browser", metavar="BROWSER",
                        help="use this browser's login, e.g. chrome, safari, firefox")

    root = argparse.ArgumentParser(description="Download a video or build its transcript.")
    commands = root.add_subparsers(dest="command", required=True)

    down = commands.add_parser("download", parents=[common], help="save the video as mp4")
    down.add_argument("--name", required=True,
                      help="file name, placeholder extensions like name.<ext> are stripped")
    down.add_argument("--dir", default="~/Downloads", help="target folder (default: ~/Downloads)")
    down.add_argument("--section", help="keep only START-END, e.g. 0-75 or 1:30-2:45")
    down.add_argument("--max-mb", type=float, help="re-encode when the file is larger than this")
    down.set_defaults(func=download)

    text = commands.add_parser("transcript", parents=[common],
                               help="build a transcript from captions or local transcription")
    text.add_argument("--language",
                      help="spoken language, e.g. en or de (default: what the site reports, else detect)")
    text.add_argument("--force-local", "--force-whisper", dest="force_local", action="store_true",
                      help="transcribe locally even when captions exist")
    text.add_argument("--work-dir", help="where to keep the files (default: a temp folder per video)")
    text.add_argument("--model",
                      help=f"Hugging Face model for mlx-audio (default: {PARAKEET}, "
                           f"or {WHISPER} for languages Parakeet lacks)")
    text.set_defaults(func=transcript)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        args.func(args)
    except Fail as error:
        log(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

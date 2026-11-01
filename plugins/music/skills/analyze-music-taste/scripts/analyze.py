#!/usr/bin/env python3
"""Offline listening-history analyzer. Python 3.10+, standard library only."""
import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

UTC = timezone.utc
WINDOWS = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
HISTORY_PREFIXES = ("streaminghistory", "streaming_history_audio", "endsong_")


def parse_datetime(value):
    if not value or not isinstance(value, str):
        raise ValueError("Missing timestamp")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    # Spotify's endTime field omits the timezone but represents UTC.
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


def history_files(paths):
    files = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_dir():
            files += [p for p in path.rglob("*.json")
                      if p.name.lower().startswith(HISTORY_PREFIXES)]
        elif path.suffix.lower() == ".json":
            files.append(path)
        else:
            raise ValueError(f"Expected JSON history file or directory: {path}")
    return sorted(set(files))


def normalize_play(record, min_ms):
    if not isinstance(record, dict):
        return None
    if record.get("spotify_episode_uri") or record.get("episode_name"):
        return None
    artist = record.get("master_metadata_album_artist_name") or record.get("artistName")
    track = record.get("master_metadata_track_name") or record.get("trackName")
    ms = record.get("ms_played", record.get("msPlayed", 0))
    if not isinstance(artist, str) or not artist.strip() or not isinstance(track, str) or not track.strip():
        return None
    if not isinstance(ms, (int, float)) or isinstance(ms, bool) or ms < min_ms:
        return None
    try:
        when = parse_datetime(record.get("ts") or record.get("endTime"))
    except ValueError:
        return None
    return (when, artist.strip(), track.strip(), int(ms))


def read_plays(paths, min_ms=30000):
    plays, prev_file_keys, duplicate_count, ignored = [], set(), 0, 0
    files = history_files(paths)
    for path in files:
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list):
            raise ValueError(f"Expected JSON list in {path.name}")
        this_file_keys = set()
        for raw in rows:
            play = normalize_play(raw, min_ms)
            if play is None:
                ignored += 1
                continue
            key = (play[0], play[1].casefold(), play[2].casefold(), play[3])
            if key in prev_file_keys:
                duplicate_count += 1
                continue
            plays.append(play)
            this_file_keys.add(key)
        prev_file_keys |= this_file_keys
    return plays, [p.name for p in files], ignored, duplicate_count


def read_library(path):
    if path is None:
        return [], None
    path = Path(path).expanduser()
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        artists = []
        for row in rows:
            name = row.get("Artist Name(s)") or row.get("Artist Name") or row.get("artist")
            if name:
                artists.extend(a.strip() for a in name.split(";") if a.strip())
        return artists, path.name
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("tracks"), list):
        raise ValueError("Library JSON must contain a 'tracks' list (YourLibrary.json)")
    artists = []
    for track in data["tracks"]:
        if not isinstance(track, dict):
            continue
        artist = track.get("artist")
        if isinstance(artist, dict):
            artist = artist.get("name")
        if isinstance(artist, str) and artist.strip():
            artists.append(artist.strip())
    return artists, path.name


def aggregate(plays):
    stats, tracks, total_ms = {}, set(), 0
    for _, artist, track, ms in plays:
        key = artist.casefold()
        if key not in stats:
            stats[key] = {"name": artist, "play_count": 0, "ms_played": 0}
        stats[key]["play_count"] += 1
        stats[key]["ms_played"] += ms
        tracks.add((key, track.casefold()))
        total_ms += ms
    ranked = sorted(stats.values(), key=lambda x: (-x["ms_played"], -x["play_count"], x["name"].casefold()))
    for i, artist in enumerate(ranked, 1):
        artist["rank"] = i
    return {"play_count": len(plays), "listen_minutes": round(total_ms / 60000, 2),
            "artist_count": len(stats), "track_count": len(tracks), "artists": ranked}


def saved_stats(names):
    counts, labels = defaultdict(int), {}
    for name in names:
        key = name.casefold()
        counts[key] += 1
        labels.setdefault(key, name)
    artists = [{"name": labels[k], "saved_tracks": count} for k, count in counts.items()]
    artists.sort(key=lambda x: (-x["saved_tracks"], x["name"].casefold()))
    for i, artist in enumerate(artists, 1):
        artist["rank"] = i
    return {"saved_tracks": len(names), "artist_count": len(artists), "artists": artists}


def build_profile(plays, saved_names, now, source_files=None, library_file=None, ignored=0, duplicates=0):
    now = now.astimezone(UTC)
    usable = [p for p in plays if p[0] <= now]
    ordered = sorted(usable, key=lambda x: x[0])
    windows = {"overall": aggregate(usable)}
    for name, days in WINDOWS.items():
        cutoff = now - timedelta(days=days)
        windows[name] = aggregate([p for p in usable if cutoff <= p[0] <= now])
        windows[name]["period_start_utc"] = cutoff.isoformat()
    warnings = ["Listening history may have gaps; a zero-play window is not proof of no listening.",
                "Plays shorter than the configured threshold are excluded; minutes reflect observed plays only."]
    if not source_files:
        warnings.append("No play history supplied: recent and overall listening metrics are unavailable.")
    if not usable and not saved_names:
        warnings.append("No usable music data was found.")
    if ordered and (now - ordered[-1][0]) > timedelta(days=7):
        warnings.append("The newest observed play is more than seven days old; recent windows may be stale.")
    return {"schema_version": 1, "generated_at_utc": now.isoformat(),
            "method": "offline_user_export", "windows": windows,
            "saved_library": saved_stats(saved_names),
            "provenance": {"history_files": source_files or [], "library_file": library_file,
                           "ignored_records": ignored, "overlap_duplicates_removed": duplicates,
                           "first_observed_play_utc": ordered[0][0].isoformat() if ordered else None,
                           "last_observed_play_utc": ordered[-1][0].isoformat() if ordered else None,
                           "coverage": "unknown; observed plays only"},
            "warnings": warnings}


def markdown_report(profile):
    lines = ["# Music taste report", "", f"Generated (UTC): {profile['generated_at_utc']}", "",
             "This reflects observed exports, not a guaranteed complete listening history.", ""]
    for label in ("overall", "90d", "30d", "7d", "1d"):
        window = profile["windows"][label]
        lines += [f"## {label} (observed)",
                  f"{window['play_count']} plays, {window['listen_minutes']:.1f} minutes, "
                  f"{window['artist_count']} artists", ""]
        lines += [f"- {x['name']}: {x['play_count']} plays, {x['ms_played'] / 60000:.1f} min"
                  for x in window["artists"][:10]] or ["No observed plays"]
        lines += [""]
    saved = profile["saved_library"]
    lines += ["## Saved library", f"{saved['saved_tracks']} saved-track entries", ""]
    lines += [f"- {x['name']}: {x['saved_tracks']} saved tracks" for x in saved["artists"][:10]]
    lines += ["", "## Data caveats", ""] + [f"- {w}" for w in profile["warnings"]]
    return "\n".join(lines) + "\n"


def private_write(path, content):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".music-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(content)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", nargs="*", default=[], help="Spotify history JSON files or directory")
    parser.add_argument("--library", help="YourLibrary.json or exported liked-song CSV")
    parser.add_argument("--output", required=True, help="Private taste-profile.json output")
    parser.add_argument("--report", help="Optional human-readable Markdown report")
    parser.add_argument("--now", help="Reference ISO timestamp (default current UTC)")
    parser.add_argument("--min-ms", type=int, default=30000, help="Minimum milliseconds per play")
    args = parser.parse_args()
    if not args.history and not args.library:
        parser.error("Provide --history and/or --library")
    if args.min_ms < 0:
        parser.error("--min-ms must be nonnegative")
    now = parse_datetime(args.now) if args.now else datetime.now(UTC)
    plays, files, ignored, duplicates = read_plays(args.history, args.min_ms)
    saved, library_file = read_library(args.library)
    profile = build_profile(plays, saved, now, files, library_file, ignored, duplicates)
    private_write(args.output, json.dumps(profile, ensure_ascii=False, indent=2) + "\n")
    if args.report:
        private_write(args.report, markdown_report(profile))
    print(f"Wrote {args.output}: {len(plays)} observed plays, {len(saved)} saved-track entries")
    print("Coverage: unknown; no personal data uploaded by this script")


if __name__ == "__main__":
    main()

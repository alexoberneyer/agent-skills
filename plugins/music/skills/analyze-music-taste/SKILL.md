---
name: analyze-music-taste
description: Analyze the user's personal music listening history and saved songs from a user-provided Spotify data export (including extended streaming history, basic StreamingHistory JSON, or Liked Songs CSV). Use for questions about favorite artists, listening habits, trends, changes over the last 1/7/30/90 days, or creating a private taste profile for another skill. Do not treat saved songs as timestamped listening history.
---

# Analyze music taste

Analyze music preferences using a local, user-supplied export. Never presume access to an account. No Spotify API, developer credentials, scraping, or automated export download is required.

## Inputs and execution

1. Identify a user's `StreamingHistory*.json`, `Streaming_History_Audio*.json`, or `endsong_*.json` files, optionally `YourLibrary.json` or a saved-songs CSV. A directory is supported, but only history-named JSON files inside it are read. Do not inspect unrelated account-export files; extended exports can include IP addresses and device information.
2. Resolve the loaded `SKILL.md` to an absolute path and run the adjacent `scripts/analyze.py` with Python 3.10+ (standard library only). Use, for example:

```bash
python3 "<skill-dir>/scripts/analyze.py" \
  --history "$HOME/Downloads/Spotify Extended Streaming History" \
  --library "$HOME/Downloads/YourLibrary.json" \
  --output "$HOME/.local/share/music/taste-profile.json" \
  --report "$HOME/.local/share/music/taste-report.md"
```

`--history` or `--library` may be omitted, but not both. With only saved songs, skip time-window conclusions. `--now 2026-11-01T10:00:00+00:00` allows reproducible comparisons. A play must reach 30 seconds by default (`--min-ms` overrides). All time windows are rolling UTC durations ending at `--now` (1/7/30/90 days), not calendar-month or local-midnight bins.

3. Read the private generated report and profile, and explain the strongest observed long-term and recent patterns. Compare windows using plays **and** time, acknowledging small samples. Never infer personality, mood, diagnosis, or genre from an artist name alone.

## Data contract and safety

The output `taste-profile.json` has `schema_version: 1`, `generated_at_utc`, `windows` (`overall`, `1d`, `7d`, `30d`, `90d`), and `saved_library`. Each window lists ranked artists (`name`, `play_count`, `ms_played`, `rank`); saved artists list `saved_tracks` and `rank`. The event-discovery skill reads this contract without coupling to the analyzer's code or export format. `overall` means **all available observed plays**, not necessarily lifetime listening. Spotify exports do not supply reliable genre tags; never manufacture them.

Output files are written with private permissions outside the public repository. The script emits aggregated track/artist data only; it never copies username, IP address, country, or device metadata. History coverage is unverified even when a period has zero plays; report source gaps and stale exports explicitly. Keep personal exports, profile, and reports out of public Git commits, logs, fixtures, and third-party services. Do not send raw history to a hosted service unless explicitly authorized.

## Verify

Check that the expected source files were found, the reference time and windows make sense, and metrics reflect actual observed evidence. Show top artists, meaningful changes, sparse windows, and explicit limitations. Recommend an updated export or another consented listening-history source when recent periods lack coverage. Do not claim continuous synchronization; this skill is offline and on demand.

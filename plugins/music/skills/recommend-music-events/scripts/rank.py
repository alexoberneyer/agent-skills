#!/usr/bin/env python3
"""Rank sourced events against a versioned offline music taste profile."""
import argparse
import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

UTC = timezone.utc
WEIGHTS = (("overall", 0.45), ("90d", 0.20), ("30d", 0.25), ("saved_library", 0.10))


def parse_timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Event start must be an ISO timestamp with timezone")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Event start must include an explicit timezone offset")
    return parsed.astimezone(UTC)


def valid_link(value):
    if not isinstance(value, str):
        return False
    parts = urlparse(value)
    return parts.scheme in ("https", "http") and bool(parts.netloc)


def artist_affinities(profile):
    if profile.get("schema_version") != 1:
        raise ValueError("Expected taste-profile schema_version 1")
    weighted, total_weights, evidence = {}, 0.0, {}
    for window, weight in WEIGHTS:
        section = profile.get("saved_library", {}) if window == "saved_library" else profile.get("windows", {}).get(window, {})
        artists = section.get("artists", [])
        if not artists:
            continue
        total_weights += weight
        for artist in artists:
            if not isinstance(artist, dict) or not isinstance(artist.get("name"), str):
                continue
            name = artist["name"].strip().casefold()
            rank = artist.get("rank", 0)
            if not name or not isinstance(rank, int) or rank < 1:
                continue
            weighted[name] = weighted.get(name, 0.0) + weight / math.sqrt(rank)
            evidence.setdefault(name, []).append(window)
    return {k: v / total_weights for k, v in weighted.items()} if total_weights else {}, evidence


def rank_events(profile, events, city, now, days=90, max_distance_km=None, include_unmatched=False, limit=30):
    if days < 1 or limit < 1:
        raise ValueError("days and limit must be positive")
    if max_distance_km is not None and max_distance_km < 0:
        raise ValueError("max_distance_km must be nonnegative")
    now = now.astimezone(UTC)
    affinity, evidence = artist_affinities(profile)
    seen, ranked = set(), []
    rejected = {"invalid": 0, "outside_dates": 0, "outside_area": 0, "duplicate": 0, "unmatched": 0}
    for event in events:
        if not isinstance(event, dict):
            rejected["invalid"] += 1
            continue
        try:
            start = parse_timestamp(event.get("start"))
        except (ValueError, TypeError):
            rejected["invalid"] += 1
            continue
        title, place, event_city = event.get("title"), event.get("venue"), event.get("city")
        artists = event.get("artists", [])
        url = event.get("url") or event.get("source_url")
        if not all(isinstance(x, str) and x.strip() for x in (title, place, event_city)) or \
                not isinstance(artists, list) or not all(isinstance(a, str) for a in artists) or not valid_link(url):
            rejected["invalid"] += 1
            continue
        if start < now or start > now + timedelta(days=days):
            rejected["outside_dates"] += 1
            continue
        dist = event.get("distance_km")
        if dist is not None and (not isinstance(dist, (float, int)) or isinstance(dist, bool) or not math.isfinite(dist) or dist < 0):
            rejected["invalid"] += 1
            continue
        local = event_city.strip().casefold() == city.strip().casefold()
        if (not local and (dist is None or max_distance_km is None)) or \
                (max_distance_km is not None and dist is not None and dist > max_distance_km):
            rejected["outside_area"] += 1
            continue
        key = (start.isoformat(), title.strip().casefold(), place.strip().casefold(), event_city.strip().casefold())
        if key in seen:
            rejected["duplicate"] += 1
            continue
        seen.add(key)
        matches = []
        for artist in artists:
            norm = artist.strip().casefold()
            if norm in affinity and norm not in {m["name"].casefold() for m in matches}:
                matches.append({"name": artist.strip(), "affinity": round(affinity[norm], 4),
                                "evidence_windows": evidence[norm]})
        matches.sort(key=lambda x: -x["affinity"])
        if not matches and not include_unmatched:
            rejected["unmatched"] += 1
            continue
        # Highest affinity is the main signal; secondary lineup artists add a small boost.
        strength = matches[0]["affinity"] if matches else 0.0
        strength += min(0.15, sum(m["affinity"] for m in matches[1:]) * 0.10)
        ranked.append({"title": title.strip(), "start": start.isoformat(),
                       "venue": place.strip(), "city": event_city.strip(), "artists": artists,
                       "distance_km": dist, "distance_verified": dist is not None,
                       "url": url, "source": event.get("source") or "source not specified",
                       "score": round(min(100, strength * 100), 2),
                       "match_type": "direct_artist" if matches else "unmatched_exploration",
                       "matched_artists": matches})
    ranked.sort(key=lambda e: (-e["score"], e["start"], e["distance_km"] if e["distance_km"] is not None else float("inf")))
    warnings = ["Events must be verified against their linked primary listing before booking.",
                "Only exact artist-name overlap is scored; musical similarity and genres are not inferred."]
    if any(x["distance_km"] is None for x in ranked):
        warnings.append("Some event distances are unknown: same-city filtering does not enforce a radius or travel time.")
    if not ranked:
        warnings.append("No matching events found in the supplied sources; this is not evidence that none exist.")
    if include_unmatched:
        warnings.append("Unmatched exploration events have score 0: no taste similarity has been demonstrated.")
    return {"schema_version": 1, "generated_at_utc": now.isoformat(),
            "taste_profile_generated_at_utc": profile.get("generated_at_utc"),
            "city": city, "horizon_days": days, "max_distance_km": max_distance_km,
            "events_supplied": len(events), "recommendations": ranked[:limit],
            "excluded_counts": rejected, "warnings": warnings}


def markdown_report(result):
    lines = ["# Music event recommendations", "", f"City: {result['city']}",
             f"Horizon: {result['horizon_days']} days", "",
             "Sources are not exhaustive; check original event pages before booking.", ""]
    for index, event in enumerate(result["recommendations"], 1):
        names = ", ".join(x["name"] for x in event["matched_artists"]) or "No direct artist match"
        distance = f"{event['distance_km']} km" if event["distance_km"] is not None else "distance unknown"
        lines += [f"## {index}. {event['title']} ({event['score']:.1f})", "",
                  f"- When: {event['start']} UTC", f"- Where: {event['venue']}, {event['city']} ({distance})",
                  f"- Match: {names}", f"- Source: {event['source']}", f"- Event: {event['url']}", ""]
    if not result["recommendations"]:
        lines += ["No events matched the supplied source records and filters.", ""]
    lines += ["## Caveats", ""] + [f"- {w}" for w in result["warnings"]]
    return "\n".join(lines) + "\n"


def private_write(path, content):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp = tempfile.mkstemp(prefix=".events-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="Private taste-profile.json from analyze-music-taste")
    parser.add_argument("--events", required=True, help="Source-backed events JSON list or {events: [...]}" )
    parser.add_argument("--city", required=True, help="Target city; nearby towns need known distances")
    parser.add_argument("--output", required=True, help="Private ranked result JSON")
    parser.add_argument("--report", help="Optional Markdown recommendations")
    parser.add_argument("--now", help="ISO timestamp to anchor recommendations")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--max-distance-km", type=float)
    parser.add_argument("--include-unmatched", action="store_true")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()
    profile = json.loads(Path(args.profile).expanduser().read_text(encoding="utf-8"))
    raw_events = json.loads(Path(args.events).expanduser().read_text(encoding="utf-8"))
    events = raw_events.get("events") if isinstance(raw_events, dict) else raw_events
    if not isinstance(events, list):
        parser.error("Events must be a JSON array or an object with an events array")
    now = parse_timestamp(args.now) if args.now else datetime.now(UTC)
    results = rank_events(profile, events, args.city, now, args.days, args.max_distance_km,
                          args.include_unmatched, args.limit)
    private_write(args.output, json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    if args.report:
        private_write(args.report, markdown_report(results))
    print(f"Wrote {args.output}: {len(results['recommendations'])} recommendations "
          f"from {results['events_supplied']} sourced events")


if __name__ == "__main__":
    main()

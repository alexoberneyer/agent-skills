# Candidate event JSON contract (v1)

Supply a JSON array (or `{ "events": [...] }`) using genuine source-backed event listings. Times must be ISO 8601 with a timezone offset, e.g. `2026-11-20T22:00:00+01:00`.

```json
[
  {
    "title": "Example Club Night (fictional fixture)",
    "start": "2026-11-20T22:00:00+01:00",
    "venue": "Example Venue",
    "city": "Berlin",
    "artists": ["Sample DJ", "Sample Producer"],
    "url": "https://example.org/events/example",
    "source": "Example venue website",
    "distance_km": null
  }
]
```

- `title`, `start`, `venue`, `city`, `artists`, and a valid http(s) `url` (or `source_url`) are required. Even if the lineup is unknown, supply `artists: []` and do not claim a taste match.
- `distance_km` is optional and must come from a genuine route/geographic source. The script never invents distance from city names or postal codes.
- Use official artist names where possible, not search keywords. Exact normalized (trim/case-insensitive) matching avoids uncontrolled fuzzy false positives.
- An `id` can be included, but duplicates are removed by title, date, venue, and city.
- Results explain their source, direct artist overlap, and any gaps. No artist similarity from model speculation.

# Event discovery sources and limits

Use current, verifiable listings rather than an embedded or remembered event catalog. Cross-check dates, venues, lineups, ticket links, and cancellations:

- Primary sources: venue and promoter event calendars, artist's official tour dates, festival lineups and organizers.
- Electronic music and club nights: https://ra.co/ (Resident Advisor); data coverage and programmatic access vary.
- Concert tracking: https://www.bandsintown.com/ and https://www.songkick.com/; do not assume public API access.
- General public concert listings: https://www.ticketmaster.com/; its Discovery API may be available with credentials and applicable terms.
- Other local listings: https://www.jambase.com/ where supported.

Each candidate must retain its source URL, a timezone-aware start, and verified venue/city. Search coverage is inevitably incomplete. Some festivals and underground club nights may not publish lineups or be indexed. Respect robots.txt, terms, and rate limits; do not bypass logins or scrape restricted pages. Changes and cancellations occur after collection, so require rechecking the source before travel or purchase.

Do not invoke a nonexistent source integration. If no live search access is available, accept a manually supplied JSON list and clearly label the result as matching provided candidates only.

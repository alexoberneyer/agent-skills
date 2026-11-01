# Import and provenance notes

Official data description: https://support.spotify.com/us/article/understanding-your-data/

- Extended history commonly uses `ts`, `ms_played`, `master_metadata_album_artist_name`, `master_metadata_track_name`, and optional `spotify_episode_uri`.
- Basic account history commonly uses `endTime`, `msPlayed`, `artistName`, and `trackName`.
- Your Library JSON contains `tracks` entries with `artist`, `track`, and `uri`; user-exported CSV may contain `Artist Name(s)`.
- `endTime` is in UTC even though it does not include a timezone offset; `ts` is usually explicit UTC.
- The basic history export can cover only a recent period. A user's extended history request can cover the lifetime of their account. Neither assures every play is present.
- Saved songs are a snapshot: saving a track is not evidence of playback at any particular date.
- Basic history may not distinguish audio from podcasts reliably; the extended format includes episode fields used to exclude them. Disclose this caveat.
- Spotify Platform restrictions: https://developer.spotify.com/policy. Do not wire in Spotify Web API access or train models on platform content. This implementation parses files voluntarily supplied by the user; verify applicable terms before widening integrations.

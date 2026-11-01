"""Offline fixtures only; no user's private data or network needed."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / 'plugins/music/skills/analyze-music-taste/scripts/analyze.py'
RANKER = ROOT / 'plugins/music/skills/recommend-music-events/scripts/rank.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analyze = load(ANALYZER, 'analyze_music')
rank = load(RANKER, 'rank_music')
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


class MusicAnalyzeTests(unittest.TestCase):
    def test_time_windows_are_rolling_and_overall_only_observed(self):
        plays = [(NOW - timedelta(hours=6), 'Alpha', 'One', 60000),
                 (NOW - timedelta(days=5), 'Beta', 'Two', 120000),
                 (NOW - timedelta(days=50), 'Alpha', 'Three', 90000),
                 (NOW - timedelta(days=120), 'Gamma', 'Four', 200000)]
        data = analyze.build_profile(plays, ['Alpha', 'Delta'], NOW, ['synthetic.json'], 'library.json')
        self.assertEqual([data['windows'][k]['play_count'] for k in ('1d','7d','30d','90d','overall')], [1,2,2,3,4])
        self.assertEqual(data['windows']['overall']['artists'][0]['name'], 'Gamma')
        self.assertEqual(data['saved_library']['saved_tracks'], 2)
        self.assertEqual(data['provenance']['coverage'], 'unknown; observed plays only')

    def test_extended_history_skips_podcasts_and_tiny_skips(self):
        rows = [dict(ts='2026-10-31T08:00:00Z', ms_played=180000,
                     master_metadata_album_artist_name='Alpha', master_metadata_track_name='One',
                     ip_addr_decrypted='private', username='private'),
                dict(ts='2026-10-31T10:00:00Z', ms_played=300000,
                     episode_name='Podcast', master_metadata_album_artist_name='Alpha',
                     master_metadata_track_name='Episode'),
                dict(ts='2026-10-31T12:00:00Z', ms_played=5000,
                     master_metadata_album_artist_name='Beta', master_metadata_track_name='Skipped')]
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'endsong_0.json'
            p.write_text(json.dumps(rows))
            plays, sources, ignored, duplicates = analyze.read_plays([p])
        self.assertEqual((len(plays), ignored, duplicates), (1,2,0))
        self.assertEqual(sources, ['endsong_0.json'])
        self.assertNotIn('private', json.dumps(analyze.build_profile(plays, [], NOW)))

    def test_basic_history_utc_and_overlap_dedup(self):
        row = {'endTime':'2026-10-31 20:30', 'artistName':'Alpha','trackName':'One','msPlayed':100000}
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p/'StreamingHistory0.json').write_text(json.dumps([row]))
            (p/'StreamingHistory1.json').write_text(json.dumps([row]))
            (p/'unrelated-account-data.json').write_text(json.dumps([row]))
            plays, sources, _, dup = analyze.read_plays([p])
        self.assertEqual((len(plays), dup, len(sources)), (1,1,2))
        self.assertEqual(plays[0][0], datetime(2026,10,31,20,30,tzinfo=timezone.utc))

    def test_library_only_has_no_fabricated_plays(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'YourLibrary.json'
            path.write_text(json.dumps({'tracks':[{'artist':'Alpha','track':'One'},
                                                       {'artist':'Alpha','track':'Two'}, {'artist':'Beta','track':'Three'}]}))
            names, _ = analyze.read_library(path)
        data = analyze.build_profile([], names, NOW)
        self.assertEqual(data['windows']['30d']['play_count'], 0)
        self.assertEqual(data['saved_library']['artists'][0]['saved_tracks'], 2)
        self.assertTrue(any('No play history' in x for x in data['warnings']))

    def test_csv_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'liked.csv'
            path.write_text('Artist Name(s),Track Name\nAlpha,One\nBeta; Gamma,Two\n')
            names, _ = analyze.read_library(path)
        self.assertEqual(names, ['Alpha','Beta','Gamma'])

    def test_cli_private_files_and_integration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root/'StreamingHistory0.json'
            history.write_text(json.dumps([{'endTime':'2026-10-31 20:30', 'artistName':'Alpha',
                                             'trackName':'One','msPlayed':180000}]))
            profile, report = root/'private-profile.json', root/'private-report.md'
            subprocess.run([sys.executable,str(ANALYZER),'--history',str(history),
                            '--output',str(profile),'--report',str(report), '--now', NOW.isoformat()],
                           check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(profile.read_text())['windows']['1d']['play_count'], 1)
            self.assertIn('Music taste report',report.read_text())
            if os.name == 'posix':
                self.assertEqual(profile.stat().st_mode & 0o777, 0o600)
            events = root/'events.json'
            events.write_text(json.dumps([{'title':'Alpha night','start':'2026-11-20T20:00:00+01:00',
                        'venue':'Example Venue','city':'Berlin','artists':['Alpha'],
                        'url':'https://example.org/fictional', 'source':'synthetic test'}]))
            ranked = root/'ranked.json'
            subprocess.run([sys.executable,str(RANKER),'--profile',str(profile),
                            '--events',str(events),'--city','Berlin','--output',str(ranked),
                            '--now',NOW.isoformat()],check=True,capture_output=True,text=True)
            result = json.loads(ranked.read_text())
            self.assertEqual(result['recommendations'][0]['matched_artists'][0]['name'],'Alpha')


class MusicRankingTests(unittest.TestCase):
    def setUp(self):
        plays = [(NOW-timedelta(days=5), 'Alpha','One',300000),
                 (NOW-timedelta(days=10), 'Beta','Two',120000)]
        self.profile = analyze.build_profile(plays, ['Alpha','Beta'], NOW, ['synthetic.json'])
        self.template = {'title':'Test Show','start':'2026-11-20T20:00:00+01:00',
                         'venue':'Example Hall','city':'Berlin','artists':['Alpha'],
                         'url':'https://example.org/fictional','source':'fixture'}

    def test_known_artist_ranks_above_other_artist(self):
        other = dict(self.template,title='Other Show',artists=['Beta'])
        result = rank.rank_events(self.profile,[other,self.template],'Berlin',NOW)
        self.assertEqual(result['recommendations'][0]['title'],'Test Show')
        self.assertTrue(result['recommendations'][0]['score']>result['recommendations'][1]['score'])

    def test_unknown_artist_needs_opt_in(self):
        event = dict(self.template, artists=['Unheard'])
        self.assertEqual(rank.rank_events(self.profile,[event],'Berlin',NOW)['recommendations'],[])
        result = rank.rank_events(self.profile,[event],'Berlin',NOW,include_unmatched=True)
        self.assertEqual(result['recommendations'][0]['score'],0)
        self.assertEqual(result['recommendations'][0]['match_type'],'unmatched_exploration')

    def test_timezone_and_bad_or_past_events(self):
        bad = dict(self.template,start='2026-11-20T20:00:00')
        old = dict(self.template,start='2026-10-20T20:00:00+02:00')
        result = rank.rank_events(self.profile,[bad,old,self.template],'Berlin',NOW)
        self.assertEqual(result['excluded_counts']['invalid'],1)
        self.assertEqual(result['excluded_counts']['outside_dates'],1)
        self.assertEqual(len(result['recommendations']),1)

    def test_duplicate_and_city_and_radius(self):
        distant = dict(self.template,title='Outside city',city='Potsdam',distance_km=50)
        nearby = dict(self.template,title='Near by',city='Potsdam',distance_km=20)
        result = rank.rank_events(self.profile,[self.template,self.template,distant,nearby],
                                  'Berlin',NOW,max_distance_km=30)
        self.assertEqual(result['excluded_counts']['duplicate'],1)
        self.assertEqual(result['excluded_counts']['outside_area'],1)
        self.assertEqual(len(result['recommendations']),2)
        self.assertTrue(any('distance' in x.lower() for x in result['warnings']))

    def test_missing_source_link_and_invalid_distance_rejected(self):
        invalid = dict(self.template,url='not-a-link')
        negative = dict(self.template,title='Negative',distance_km=-1)
        result = rank.rank_events(self.profile,[invalid,negative],'Berlin',NOW)
        self.assertEqual(result['excluded_counts']['invalid'],2)


if __name__ == '__main__':
    unittest.main()

from pathlib import Path
import importlib.util
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/media/skills/video/scripts/video.py'
spec = importlib.util.spec_from_file_location('video', SCRIPT)
video = importlib.util.module_from_spec(spec)
spec.loader.exec_module(video)

ROLLING = """WEBVTT
Kind: captions
Language: en

00:00:00.160 --> 00:00:02.869 align:start position:0%

welcome<00:00:00.480><c> to</c><00:00:00.640><c> the</c><00:00:00.800><c> talk</c>

00:00:02.869 --> 00:00:02.879 align:start position:0%
welcome to the talk


00:00:02.879 --> 00:00:05.000 align:start position:0%
welcome to the talk
harnesses<00:00:03.000><c> matter</c>

00:01:00.000 --> 00:01:02.000
harnesses matter
Q&amp;A starts now
"""

NUMBERED = """WEBVTT

1
01:02:03.000 --> 01:02:05.000
yes

2
01:02:10.000 --> 01:02:12.000
one

3
01:02:20.000 --> 01:02:22.000
two

4
01:02:30.000 --> 01:02:32.000
three

5
01:02:40.000 --> 01:02:42.000
yes
42
"""

class NameTest(unittest.TestCase):
    def test_placeholder_extensions_are_stripped(self):
        cases = {
            'naval-stress.<ext>': 'naval-stress', 'glick-defense.[extension]': 'glick-defense',
            'ai-art.extension': 'ai-art', 'cold-calling.<file-ending>': 'cold-calling',
            'clavicular.mp4': 'clavicular', 'uncle-bob-ai-coding': 'uncle-bob-ai-coding',
            'talk-v1.2': 'talk-v1.2', '../escape.<ext>': 'escape',
        }
        for given, expected in cases.items():
            self.assertEqual(video.normalize_name(given), expected, given)
        with self.assertRaises(video.Fail):
            video.normalize_name('.<ext>')

class CaptionChoiceTest(unittest.TestCase):
    def test_manual_in_spoken_language_wins(self):
        info = {'language': 'de', 'subtitles': {'en': [{}], 'de': [{}]}, 'automatic_captions': {'de-orig': [{}]}}
        self.assertEqual(video.pick_captions(info), ('de', False))

    def test_original_auto_track_beats_translations(self):
        info = {'automatic_captions': {'af': [{}], 'en': [{}], 'en-orig': [{}]}}
        self.assertEqual(video.pick_captions(info), ('en-orig', True))

    def test_live_chat_and_empty_tracks_mean_whisper(self):
        self.assertIsNone(video.pick_captions({'subtitles': {'live_chat': [{}]}, 'automatic_captions': {'en': []}}))
        self.assertIsNone(video.pick_captions({}))

class VttTest(unittest.TestCase):
    def test_rolling_captions_collapse_into_minute_paragraphs(self):
        self.assertEqual(video.vtt_to_text(ROLLING), '[0:00] welcome to the talk harnesses matter\n\n[1:00] Q&A starts now')

    def test_cue_numbers_hours_and_later_repeats(self):
        self.assertEqual(video.vtt_to_text(NUMBERED), '[1:02:00] yes one two three yes 42')

class HelpersTest(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(video.clock(59), '0:59')
        self.assertEqual(video.clock(3723), '1:02:03')

    def test_bitrate_leaves_room_for_audio_and_container(self):
        self.assertEqual(video.target_video_kbps(100, 60), 13153)

    def test_section_format(self):
        for ok in ['0-75', '1:30-2:45', '90-inf']:
            self.assertRegex(ok, video.SECTION)
        for bad in ['75', 'start-end', '-10']:
            self.assertNotRegex(bad, video.SECTION)

if __name__ == '__main__':
    unittest.main()

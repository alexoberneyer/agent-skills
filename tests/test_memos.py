from pathlib import Path
from unittest import mock
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/media/skills/voice-memos/scripts/memos.py'
spec = importlib.util.spec_from_file_location('memos', SCRIPT)
memos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memos)

def touch(folder, name, day):
    path = folder / name
    path.write_bytes(b'')
    stamp = dt.datetime(2026, 9, day, 12).timestamp()
    os.utime(path, (stamp, stamp))
    return path

class SelectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name)
        self.a = touch(folder, 'a.m4a', 1)
        self.b = touch(folder, 'b.qta', 3)
        self.c = touch(folder, 'c.m4a', 2)
        touch(folder, 'CloudRecordings.db', 4)
        self.found = memos.list_memos(folder)

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_audio_oldest_first(self):
        self.assertEqual(self.found, [self.a, self.c, self.b])

    def test_first_run_takes_the_newest_only(self):
        self.assertEqual(memos.select(self.found, None), [self.b])

    def test_later_runs_take_what_was_not_handled(self):
        self.assertEqual(memos.select(self.found, {'a.m4a', 'b.qta'}), [self.c])

    def test_last_and_since_ignore_what_was_handled(self):
        everything = {'a.m4a', 'b.qta', 'c.m4a'}
        self.assertEqual(memos.select(self.found, everything, last=2), [self.c, self.b])
        self.assertEqual(memos.select(self.found, everything, since=dt.date(2026, 9, 2)), [self.c, self.b])

class FolderTest(unittest.TestCase):
    def test_blocked_folder_points_at_the_mirror(self):
        with mock.patch.object(Path, 'iterdir', side_effect=PermissionError(1, 'Operation not permitted')):
            with self.assertRaisesRegex(memos.Fail, 'mirror'):
                memos.list_memos(Path('/blocked'))

    def test_missing_mirror_points_at_the_readme(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(memos.Fail, 'README'):
                memos.list_memos(Path(d) / 'missing')

    def test_reads_the_mirror_by_default(self):
        self.assertEqual(memos.parser().parse_args([]).dir, str(memos.MIRROR))

class RunTest(unittest.TestCase):
    def test_remembers_memos_across_runs(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / 'recordings'
            folder.mkdir()
            touch(folder, 'old.m4a', 1)
            touch(folder, 'new.m4a', 2)
            state = Path(d) / 'state' / 'voice-memos' / 'seen.json'
            done = []

            def fake_transcribe(memo, args):
                done.append(memo.name)
                return {'source': 'test', 'words': 1, 'transcript': 'x'}

            def run(*extra):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    return memos.main(['--dir', str(folder), *extra])

            with mock.patch.dict(os.environ, {'XDG_STATE_HOME': str(Path(d) / 'state')}), \
                 mock.patch.object(memos, 'transcribe_memo', fake_transcribe), \
                 mock.patch.object(memos, 'probe', lambda path: ('2026-09-02 12:00', 60.0)), \
                 mock.patch.object(memos.video, 'need', lambda *tools: None), \
                 mock.patch.object(memos.video, 'need_local', lambda: None):
                self.assertEqual(run('--dry-run'), 0)
                self.assertFalse(state.exists())
                self.assertEqual(run(), 0)
                self.assertEqual(done, ['new.m4a'])
                self.assertEqual(json.loads(state.read_text()), ['new.m4a', 'old.m4a'])
                touch(folder, 'newer.m4a', 3)
                self.assertEqual(run(), 0)
                self.assertEqual(run(), 0)
                self.assertEqual(done, ['new.m4a', 'newer.m4a'])
                self.assertEqual(run('--last', '1'), 0)
                self.assertEqual(done, ['new.m4a', 'newer.m4a', 'newer.m4a'])

if __name__ == '__main__':
    unittest.main()

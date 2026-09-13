from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

INSTALLER = Path(__file__).resolve().parents[1] / 'install.sh'

class InstallTest(unittest.TestCase):
    def test_spaces_idempotence_and_conflict_preservation(self):
        with tempfile.TemporaryDirectory(prefix='skill install ') as d:
            root = Path(d) / 'source'; root.mkdir()
            shutil.copy2(INSTALLER, root / 'install.sh')
            source = root / 'plugins/writing/skills/example'; source.mkdir(parents=True)
            (source / 'SKILL.md').write_text('example')
            home = Path(d) / 'home'
            def run():
                return subprocess.run(['bash', str(root / 'install.sh')], env={**os.environ, 'HOME': str(home)}, capture_output=True, text=True)
            self.assertEqual(run().returncode, 0)
            dest = home / '.agents/skills/example'
            self.assertEqual(dest.resolve(), source.resolve())
            self.assertEqual(run().returncode, 0)
            dest.unlink(); dest.write_text('user content')
            self.assertEqual(run().returncode, 1)
            self.assertEqual(dest.read_text(), 'user content')
            dest.unlink(); dest.symlink_to(Path(d) / 'missing')
            self.assertEqual(run().returncode, 1)
            self.assertEqual(os.readlink(dest), str(Path(d) / 'missing'))

if __name__ == '__main__':
    unittest.main()

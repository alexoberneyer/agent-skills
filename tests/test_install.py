from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest

INSTALLER = Path(__file__).resolve().parents[1] / 'install.sh'

class InstallTest(unittest.TestCase):
    def test_tutor_installs_with_license_and_matching_plugin_metadata(self):
        source = INSTALLER.parent / 'plugins/learning'
        marketplace = json.loads((INSTALLER.parent / '.claude-plugin/marketplace.json').read_text())
        entry = next(plugin for plugin in marketplace['plugins'] if plugin['name'] == 'learning')
        metadata = json.loads((source / '.claude-plugin/plugin.json').read_text())
        self.assertEqual(entry['version'], metadata['version'])
        self.assertEqual(entry['description'], metadata['description'])
        self.assertFalse((source / 'commands/tutor.md').exists())
        with tempfile.TemporaryDirectory(prefix='tutor install ') as d:
            root = Path(d) / 'public checkout'
            root.mkdir()
            shutil.copy2(INSTALLER, root / 'install.sh')
            shutil.copytree(source, root / 'plugins/learning')
            home = Path(d) / 'home'
            for _ in range(2):
                result = subprocess.run(['bash', str(root / 'install.sh')],
                                        env={**os.environ, 'HOME': str(home)}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            installed = home / '.agents/skills/tutor'
            self.assertEqual(installed.resolve(), (root / 'plugins/learning/skills/tutor').resolve())
            instructions = (installed / 'SKILL.md').read_text()
            self.assertTrue(instructions.startswith('---\nname: tutor\n'))
            for invocation in ('/learning:tutor', '/skill:tutor', '$tutor'):
                self.assertIn(invocation, instructions)
            self.assertIn('Copyright (c) 2026 Jane Street Group, LLC',
                          (installed / 'LICENSE.upstream').read_text())
            self.assertFalse((home / '.claude/commands/tutor.md').exists())
            self.assertFalse((home / '.local/bin/tutor').exists())

    def test_daily_report_installs_as_one_self_contained_skill(self):
        with tempfile.TemporaryDirectory(prefix='daily report install ') as d:
            root = Path(d) / 'public checkout'
            root.mkdir()
            shutil.copy2(INSTALLER, root / 'install.sh')
            skill = root / 'plugins/context/skills/daily-report'
            shutil.copytree(INSTALLER.parent / 'plugins/context/skills/daily-report', skill,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            home = Path(d) / 'home'
            result = subprocess.run(['bash', str(root / 'install.sh')],
                                    env={**os.environ, 'HOME': str(home)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            installed = home / '.agents/skills/daily-report'
            self.assertEqual(installed.resolve(), skill.resolve())
            self.assertTrue((installed / 'scripts/report.py').is_file())
            self.assertTrue((installed / 'assets/template.html').is_file())
            instructions = (installed / 'SKILL.md').read_text()
            for invocation in ('/context:daily-report', '/skill:daily-report', '$daily-report'):
                self.assertIn(invocation, instructions)
            self.assertFalse((home / '.claude/skills/daily-report').exists())
            self.assertFalse((home / '.local/bin/daily-report').exists())

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

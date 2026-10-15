"""Exercise launch compatibility with inert stand-ins, never vehicle programs."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = json.loads((ROOT / 'docs/path-migration.json').read_text(encoding='utf-8'))


class CompatibilityTests(unittest.TestCase):
    def test_python_context_arguments_and_exit_status(self):
        for old, entry in MANIFEST['compatibility'].items():
            if not old.endswith('.py'):
                continue
            with self.subTest(old=old), tempfile.TemporaryDirectory() as temp:
                fixture = Path(temp)
                wrapper = fixture / old
                target = fixture / entry['target']
                wrapper.parent.mkdir(parents=True, exist_ok=True)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / old, wrapper)
                (target.parent / '_mira_test_import.py').write_text('VALUE = 42\n')
                target.write_text(
                    'from pathlib import Path\nimport json,sys\n'
                    'from _mira_test_import import VALUE\n'
                    'print(json.dumps([str(Path(__file__).resolve()),sys.argv[1:],VALUE]))\n'
                    'raise SystemExit(17)\n', encoding='utf-8')
                run = subprocess.run([sys.executable, str(wrapper), 'argument with spaces', 'ä'],
                                     capture_output=True, text=True, encoding='utf-8')
                self.assertEqual(run.returncode, 17, run.stderr)
                result = json.loads(run.stdout)
                expected = target if entry['context'] == 'canonical' else wrapper
                self.assertEqual(Path(result[0]), expected.resolve())
                self.assertEqual(result[1:], [['argument with spaces', 'ä'], 42])

    def test_legacy_private_data_context(self):
        old = 'scripts/read_from_canbus.py'
        target_name = MANIFEST['compatibility'][old]['target']
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp)
            wrapper, target = fixture / old, fixture / target_name
            wrapper.parent.mkdir(parents=True)
            target.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / old, wrapper)
            (wrapper.parent / 'hudiy_api').mkdir()
            (wrapper.parent / 'hudiy_api/private-marker').write_text('private')
            (wrapper.parent / 'features.conf').write_text('local-settings')
            target.write_text(
                'from pathlib import Path\n'
                'base = Path(__file__).resolve().parent\n'
                'assert (base / "features.conf").read_text() == "local-settings"\n'
                'assert (base / "hudiy_api/private-marker").read_text() == "private"\n')
            run = subprocess.run([sys.executable, str(wrapper)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_shell_wrappers_forward_arguments(self):
        # bash is optional on Windows; the Pi check does not execute any shell wrapper.
        bash = shutil.which('bash')
        if not bash:
            self.skipTest('bash unavailable on this host')
        for old, entry in MANIFEST['compatibility'].items():
            if old.endswith('.py'):
                continue
            with self.subTest(old=old), tempfile.TemporaryDirectory() as temp:
                fixture = Path(temp)
                wrapper, target = fixture / old, fixture / entry['target']
                wrapper.parent.mkdir(parents=True, exist_ok=True)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / old, wrapper)
                target.write_text('test "$#" = 2 && test "$1" = "one two" && test "$2" = "three" || exit 18\nexit 17\n')
                run = subprocess.run([bash, str(wrapper), 'one two', 'three'], capture_output=True, text=True)
                self.assertEqual(run.returncode, 17, run.stderr)

    def test_launcher_splash_resource_relation(self):
        folder = ROOT / 'platform/launcher' / '..' / 'boot/mira-animation/theme'
        self.assertTrue((folder / 'frame-0.png').is_file())
        self.assertTrue((folder / 'frame-155.png').is_file())
        ast.parse((ROOT / 'platform/boot/mira-animation/install.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

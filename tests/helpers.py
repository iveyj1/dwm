#!/usr/bin/env python3
"""Headless hardware helper tests. Never invoke actual hardware commands."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Helpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.env = dict(os.environ, PATH=str(self.base), OUT=str(self.base / 'out'))
        (self.base / 'grep').symlink_to(shutil.which('grep'))
        self.mock('brightnessctl', 'case $1 in\n'
                  'get) printf "%s" "${CUR:-50}";;\n'
                  'max) printf "%s" "${MAX:-100}";;\n'
                  'set) printf "%s" "$2" > "$OUT";;\nesac')

    def mock(self, name, body):
        file = self.base / name
        file.write_text('#!/bin/sh\n' + body + '\n')
        file.chmod(0o755)

    def run_helper(self, helper, **env):
        return subprocess.run(['/bin/sh', str(ROOT / helper)], text=True,
                              capture_output=True, timeout=5, env=dict(self.env, **env))

    def test_brightness_curve(self):
        for cur, step in [('0', '5'), ('50', '5'), ('100', '15')]:
            for helper, expected in [('brightness-up', f'+{step}%'),
                                     ('brightness-down', f'{step}%-')]:
                result = self.run_helper(helper, CUR=cur)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((self.base / 'out').read_text(), expected)

    def test_invalid_brightness(self):
        for helper in ('brightness-up', 'brightness-down'):
            for env in ({'MAX': '0'}, {'MAX': 'bad'}, {'CUR': '-1'}):
                self.assertNotEqual(self.run_helper(helper, **env).returncode, 0)
                self.assertFalse((self.base / 'out').exists())

    def test_suspend(self):
        self.mock('loginctl', 'if [ "$1" = --version ]; then printf "elogind 255\\n"; '
                  'else printf "loginctl %s" "$*" > "$OUT"; exit 7; fi')
        self.mock('systemctl', 'printf "systemctl %s" "$*" > "$OUT"; exit 7')
        result = self.run_helper('dwm-suspend')
        self.assertEqual(result.returncode, 7)  # No retry after denial.
        backend = 'systemctl' if Path('/run/systemd/system').is_dir() else 'loginctl'
        self.assertEqual((self.base / 'out').read_text(), backend + ' suspend')

    def test_no_suspend_backend(self):
        self.mock('loginctl', 'printf "systemd 255\\n"')
        result = self.run_helper('dwm-suspend')
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.base / 'out').exists())

    def test_screenshots(self):
        self.mock('scrot', 'printf "%s" "$*" > "$OUT"')
        for helper, expected in [('dwm-screenshot', '-s'), ('dwm-screenshot-full', '')]:
            self.assertNotIn('/tmp/scrot', (ROOT / helper).read_text())
            result = self.run_helper(helper)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((self.base / 'out').read_text(), expected)


if __name__ == '__main__':
    unittest.main()

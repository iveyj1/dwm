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
        for command in ('grep', 'awk'):
            (self.base / command).symlink_to(shutil.which(command))
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

    def brightness(self, direction, cur, maximum):
        (self.base / 'out').unlink(missing_ok=True)
        result = self.run_helper('brightness-' + direction,
                                 CUR=str(cur), MAX=str(maximum))
        self.assertEqual(result.returncode, 0, result.stderr)
        return int((self.base / 'out').read_text())

    def test_brightness_curve(self):
        # 1000 and 4000 are no longer rungs; arbitrary values snap to a
        # strictly lower/higher rung, with endpoint clamping.
        for cur, down, up in [(0, 1, 1), (1, 1, 2000), (500, 1, 2000),
                              (1000, 1, 2000), (1999, 1, 2000),
                              (2000, 1, 8000), (2001, 2000, 8000),
                              (3000, 2000, 8000), (4000, 2000, 8000),
                              (7999, 2000, 8000), (8000, 2000, 16000),
                              (8001, 8000, 16000),
                              (64000, 32000, 96000), (96000, 64000, 96000)]:
            with self.subTest(cur=cur):
                self.assertEqual(self.brightness('down', cur, 96000), down)
                self.assertEqual(self.brightness('up', cur, 96000), up)

    def test_brightness_ladder(self):
        for maximum in (1, 2, 100, 1000, 1999, 2000, 2001, 3000, 4000,
                        7999, 8000, 8001, 16000, 32000, 64000, 96000):
            levels = sorted({1, maximum} | {
                level for level in (2000, 8000, 16000, 32000, 64000)
                if level < maximum
            })
            # Every rung is reachable in both directions, including both endpoints.
            for i, cur in enumerate(levels):
                with self.subTest(maximum=maximum, cur=cur):
                    self.assertEqual(self.brightness('up', cur, maximum),
                                     levels[min(i + 1, len(levels) - 1)])
                    self.assertEqual(self.brightness('down', cur, maximum),
                                     levels[max(i - 1, 0)])
            for direction in ('up', 'down'):
                self.assertEqual(self.brightness(direction, 0, maximum), 1)
                self.assertEqual(self.brightness(direction, maximum + 1, maximum),
                                 maximum)

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

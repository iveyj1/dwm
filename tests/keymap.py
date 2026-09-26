#!/usr/bin/env python3
"""Exercise help without X or launching real applications."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Keymap(unittest.TestCase):
    def run_menu(self, selection='', lines=None):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            for name, script in {
                'dmenu-font': 'printf "%s\\n" "$@" > "$CAPTURE/args"\n'
                              'cat > "$CAPTURE/entries"\n'
                              'printf "%s\\n" "$SELECTION"\n',
                'dmenu_run': 'echo launcher > "$CAPTURE/action"\n',
                'pcmanfm': 'echo files > "$CAPTURE/action"\n',
                'brave-browser': 'echo browser > "$CAPTURE/action"\n',
            }.items():
                executable = tmp / name
                executable.write_text('#!/bin/sh\n' + script)
                executable.chmod(0o755)
            env = dict(os.environ, PATH=f'{tmp}:/usr/bin:/bin',
                       CAPTURE=directory, SELECTION=selection)
            env.pop('DWM_KEYMAP_LINES', None)
            if lines is not None:
                env['DWM_KEYMAP_LINES'] = lines
            subprocess.run(['/bin/sh', str(ROOT / 'dwm-keymap')],
                           env=env, check=True)
            return {name: (tmp / name).read_text() if (tmp / name).exists() else ''
                    for name in ('args', 'entries', 'action')}

    def test_geometry_and_entries(self):
        result = self.run_menu()
        args = result['args'].splitlines()
        self.assertNotIn('-c', args)
        self.assertIn('-i', args)
        self.assertEqual(args[args.index('-l') + 1], '12')
        for text in ('Super+Shift+P', 'Super+Shift+E', 'Super+B              toggle bar',
                     'Copy mode: W/E/B', 'Ctrl+Shift+NumLock', 'dwm intercepts'):
            self.assertIn(text, result['entries'])
        for stale in ('Super+P ', 'also toggles bar', 'also opens browser', 'Super+E '):
            self.assertNotIn(stale, result['entries'])
        self.assertEqual(result['action'], '')

    def test_launchable_entries(self):
        entries = self.run_menu()['entries'].splitlines()
        for label, action in [('application launcher', 'launcher'),
                              ('file manager', 'files'),
                              ('browser', 'browser')]:
            entry = next(line for line in entries if line.endswith(label))
            self.assertEqual(self.run_menu(entry)['action'].strip(), action)
        entry = next(line for line in entries if line.endswith('toggle bar'))
        self.assertEqual(self.run_menu(entry)['action'], '')

    def test_row_override(self):
        for value, expected in [('8', '8'), ('invalid', '12'), ('0', '12')]:
            args = self.run_menu(lines=value)['args'].splitlines()
            self.assertEqual(args[args.index('-l') + 1], expected)


if __name__ == '__main__':
    unittest.main()

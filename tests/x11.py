#!/usr/bin/env python3
"""Optional end-to-end desktop tests on an isolated, automatically allocated Xvfb.
Run from any directory: python3 dwm/tests/x11.py
Requires built sibling st-reflow/dmenu/dwmblocks, Xvfb, libXtst and xclip.
Never connects to the user's DISPLAY; commands that touch hardware are mocked.
"""
import ctypes as C
import ctypes.util
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess as S
import sys
import tempfile
import time
import tty

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]


def wait(fn, message, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = fn()
        if result:
            return result
        time.sleep(.025)
    raise AssertionError(message)


class Attributes(C.Structure):
    _fields_ = [(s, C.c_int) for s in ('x', 'y', 'width', 'height', 'border_width', 'depth')] + [
        ('visual', C.c_void_p), ('root', C.c_ulong), ('class_', C.c_int),
        ('bit_gravity', C.c_int), ('win_gravity', C.c_int), ('backing_store', C.c_int),
        ('backing_planes', C.c_ulong), ('backing_pixel', C.c_ulong), ('save_under', C.c_int),
        ('colormap', C.c_ulong), ('map_installed', C.c_int), ('map_state', C.c_int),
        ('all_event_masks', C.c_long), ('your_event_mask', C.c_long),
        ('do_not_propagate_mask', C.c_long), ('override_redirect', C.c_int), ('screen', C.c_void_p)]


class X:
    def __init__(self, display):
        self.lib = C.CDLL(ctypes.util.find_library('X11'))
        self.xt = C.CDLL(ctypes.util.find_library('Xtst'))
        def bind(lib, name, args, result=C.c_int):
            f = getattr(lib, name)
            f.argtypes, f.restype = args, result
            return f
        D, W, I, P = C.c_void_p, C.c_ulong, C.c_int, C.c_void_p
        self.open = bind(self.lib, 'XOpenDisplay', [C.c_char_p], D)
        self.d = self.open(display.encode())
        if not self.d:
            raise RuntimeError('cannot connect to isolated display')
        self.root = bind(self.lib, 'XDefaultRootWindow', [D], W)(self.d)
        self.sync = bind(self.lib, 'XSync', [D, I])
        self.flush = bind(self.lib, 'XFlush', [D])
        self.atom = bind(self.lib, 'XInternAtom', [D, C.c_char_p, I], W)
        self.prop = bind(self.lib, 'XGetWindowProperty', [D,W,W,C.c_long,C.c_long,I,W,P,P,P,P,P])
        self.free = bind(self.lib, 'XFree', [P])
        self.attr = bind(self.lib, 'XGetWindowAttributes', [D,W,P])
        self.tree = bind(self.lib, 'XQueryTree', [D,W,P,P,P,P])
        self.keycode = bind(self.lib, 'XKeysymToKeycode', [D,W], C.c_uint)
        self.keysym = bind(self.lib, 'XStringToKeysym', [C.c_char_p], W)
        self.fakekey = bind(self.xt, 'XTestFakeKeyEvent', [D,C.c_uint,I,W])
        self.fakemotion = bind(self.xt, 'XTestFakeMotionEvent', [D,I,I,I,W])
        self.fakebutton = bind(self.xt, 'XTestFakeButtonEvent', [D,C.c_uint,I,W])
        self.create = bind(self.lib, 'XCreateSimpleWindow', [D,W,I,I,C.c_uint,C.c_uint,C.c_uint,W,W], W)
        self.map = bind(self.lib, 'XMapWindow', [D,W])
        self.destroy = bind(self.lib, 'XDestroyWindow', [D,W])
        self.store = bind(self.lib, 'XStoreName', [D,W,C.c_char_p])
        self.classhint = bind(self.lib, 'XSetClassHint', [D,W,P])
        self.owner = bind(self.lib, 'XGetSelectionOwner', [D,W], W)
        self.close = bind(self.lib, 'XCloseDisplay', [D])

    def property(self, w, name):
        kind, fmt, n, rem = C.c_ulong(), C.c_int(), C.c_ulong(), C.c_ulong()
        data = C.c_void_p()
        self.prop(self.d, w, self.atom(self.d, name.encode(), 0), 0, 65536, 0, 0,
                  C.byref(kind), C.byref(fmt), C.byref(n), C.byref(rem), C.byref(data))
        if not data.value:
            return []
        try:
            if fmt.value == 32:
                return list(C.cast(data, C.POINTER(C.c_ulong))[:n.value])
            return C.string_at(data, n.value)
        finally:
            self.free(data)

    def clients(self):
        return self.property(self.root, '_NET_CLIENT_LIST')

    def attributes(self, w):
        a = Attributes()
        assert self.attr(self.d, w, C.byref(a))
        return a

    def children(self):
        r, p, n = C.c_ulong(), C.c_ulong(), C.c_uint()
        children = C.POINTER(C.c_ulong)()
        self.tree(self.d, self.root, C.byref(r), C.byref(p), C.byref(children), C.byref(n))
        result = list(children[:n.value])
        if children:
            self.free(children)
        return result

    def key(self, name, down):
        code = self.keycode(self.d, self.keysym(name.encode()))
        assert code, name
        self.fakekey(self.d, code, down, 0)
        self.sync(self.d, 0)

    def chord(self, name, *mods):
        for mod in mods:
            self.key(mod, 1)
        self.key(name, 1)
        self.key(name, 0)
        for mod in reversed(mods):
            self.key(mod, 0)
        time.sleep(.045)

    def text(self, text):
        for ch in text:
            self.chord(ch.lower() if ch.isupper() else ch,
                       *(['Shift_L'] if ch.isupper() else []))

    def mouse(self, x, y, button=None, down=1):
        self.fakemotion(self.d, 0, int(x), int(y), 0)
        if button:
            self.fakebutton(self.d, button, down, 0)
        self.sync(self.d, 0)
        time.sleep(.04)

    def window(self, title):
        class Hint(C.Structure):
            _fields_ = [('name', C.c_char_p), ('class_', C.c_char_p)]
        w = self.create(self.d, self.root, 40, 60, 320, 200, 0, 0, 0)
        hint = Hint(b'review-fixture', b'ReviewFixture')
        self.classhint(self.d, w, C.byref(hint))
        self.store(self.d, w, title.encode())
        return w


def window_fixture(path, rapid=False):
    x = X(os.environ['DISPLAY'])
    if rapid:
        splash = x.window('review splash')
        x.map(x.d, splash)
        x.sync(x.d, 0)
        time.sleep(.04)
        x.destroy(x.d, splash)
    w = x.window('review GUI')
    x.map(x.d, w)
    x.sync(x.d, 0)
    Path(str(path) + '.pid').write_text(str(os.getpid()))
    Path(path).write_text(str(w))
    while True:
        time.sleep(10)


def terminal_fixture(directory):
    directory = Path(directory)
    tty.setraw(0)
    fd = os.open(directory / 'control', os.O_RDWR | os.O_NONBLOCK)
    (directory / 'ready').write_text('ready')
    os.write(1, b'one two three four\r\n')
    children = []
    buffer = b''
    while True:
        ready, _, _ = select.select([0, fd], [], [])
        if 0 in ready:
            data = os.read(0, 4096)
            if not data:
                return
            with (directory / 'input').open('ab') as out:
                out.write(data)
        if fd in ready:
            buffer += os.read(fd, 65536)
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                cmd = json.loads(line)
                if cmd[0] == 'write':
                    os.write(1, cmd[1].encode())
                elif cmd[0] == 'spawn':
                    children.append(S.Popen([sys.executable, str(HERE), '--window-fixture', cmd[1], 'rapid']))
                elif cmd[0] == 'kill':
                    for child in children:
                        child.terminate()
                        child.wait(timeout=3)
                    children.clear()
                (directory / 'size').write_text(json.dumps(list(os.get_terminal_size(0))))
                (directory / 'ack').write_text(str(cmd[-1]))


def integration():
    for name in ('Xvfb', 'xclip'):
        if not shutil.which(name):
            raise SystemExit(f'missing dependency: {name}')
    binaries = {name: ROOT / repo / name for name, repo in
                [('dwm','dwm'), ('dmenu','dmenu'), ('st','st-reflow'), ('dwmblocks','dwmblocks')]}
    for binary in binaries.values():
        if not binary.exists():
            raise SystemExit(f'build first: {binary}')
    processes, logs, results = [], [], []
    with tempfile.TemporaryDirectory(prefix='suckless-x11-') as directory:
        tmp = Path(directory)
        env = dict(os.environ)
        env.update(HOME=str(tmp), XDG_CONFIG_HOME=str(tmp / 'config'),
                   XDG_CACHE_HOME=str(tmp / 'cache'), SHELL='/bin/sh', LC_ALL='C.UTF-8')
        bindir = tmp / 'bin'
        bindir.mkdir()
        env['PATH'] = ':'.join([str(bindir), str(ROOT / 'dmenu'), str(ROOT / 'st-reflow'), '/usr/bin', '/bin'])
        def launch(argv, **kw):
            log = (tmp / f'process-{len(processes)}.log').open('wb')
            logs.append(log)
            p = S.Popen(list(map(str, argv)), env=env, stdout=log, stderr=log,
                        start_new_session=True, **kw)
            processes.append(p)
            return p
        def script(name, content):
            p = bindir / name
            p.write_text(content)
            p.chmod(0o755)
        def check(name, fn):
            fn()
            results.append(name)
            print('PASS', name, flush=True)
        try:
            r, w = os.pipe()
            server = launch(['Xvfb', '-displayfd', str(w), '-screen', '0', '1024x768x24', '-nolisten', 'tcp'], pass_fds=(w,))
            os.close(w)
            assert select.select([r], [], [], 5)[0], 'Xvfb startup timeout'
            display = ':' + os.read(r, 32).decode().strip()
            os.close(r)
            assert display != ':', 'Xvfb failed'
            env['DISPLAY'] = display
            x = X(display)
            print('Isolated display', display, flush=True)
            script('dmenu-font', '#!' + sys.executable + '\nimport os,sys,json\n'
                   + f'open({str(tmp / "menu-args")!r},"w").write(json.dumps(sys.argv[1:]))\n'
                   + f'os.execv({str(binaries["dmenu"])!r},["dmenu"]+sys.argv[1:])\n')
            script('st', '#!/bin/sh\n' + f'test ! -f "{tmp}/fail-st" || exit 1\nexec "{binaries["st"]}" "$@"\n')
            wm = launch([binaries['dwm'], '-fn', 'monospace:size=10'])
            wait(lambda: x.property(x.root, '_NET_SUPPORTING_WM_CHECK'), 'dwm startup')
            assert wm.poll() is None

            def menu_visible():
                return any(b'dmenu' in x.property(w, 'WM_CLASS') for w in x.children()
                           if x.attributes(w).map_state == 2)

            def test_prefill():
                p = S.Popen([str(binaries['dmenu']), '-it', 'existing tag', '-p', 'Rename'],
                            env=env, stdin=S.DEVNULL, stdout=S.PIPE, stderr=S.PIPE, start_new_session=True)
                processes.append(p)
                wait(menu_visible, 'dmenu map')
                x.chord('Return')
                out, err = p.communicate(timeout=3)
                assert p.returncode == 0 and out == b'existing tag\n', (out, err)
            check('dmenu accepts initial text through real keyboard input', test_prefill)

            def rename(value, expected):
                (tmp / 'menu-args').unlink(missing_ok=True)
                x.chord('n', 'Super_L')
                wait(lambda: (tmp / 'menu-args').exists() and menu_visible(), 'rename prompt')
                args = json.loads((tmp / 'menu-args').read_text())
                assert args[args.index('-it') + 1] == expected, args
                if value is None:
                    x.chord('Escape')
                else:
                    x.chord('u', 'Control_L')
                    x.text(value)
                    x.chord('Return')
                wait(lambda: not menu_visible(), 'rename exit')
                time.sleep(.08)
            def test_rename():
                rename('work', '1')
                rename('', 'work')
                rename(None, '1')
            check('dwm rename prefill, round trip, blank default and cancellation', test_rename)

            fixture = tmp / 'terminal'
            fixture.mkdir()
            os.mkfifo(fixture / 'control')
            term = launch([binaries['st'], '-f', 'monospace:size=12', '-T', 'review terminal',
                           '-e', sys.executable, HERE, '--terminal-fixture', fixture])
            wait(lambda: (fixture / 'ready').exists(), 'terminal fixture startup')
            tw = wait(lambda: next((w for w in x.clients() if x.property(w, '_NET_WM_PID') == [term.pid]), 0), 'terminal managed')
            control = os.open(fixture / 'control', os.O_WRONLY)
            sequence = 0
            def command(*args):
                nonlocal sequence
                sequence += 1
                os.write(control, (json.dumps([*args, sequence]) + '\n').encode())
                wait(lambda: (fixture / 'ack').exists() and (fixture / 'ack').read_text() == str(sequence), 'fixture ack')
                time.sleep(.09)
            def clipboard():
                return S.check_output(['xclip', '-selection', 'clipboard', '-o'], env=env, timeout=3).decode()
            def mode():
                x.chord('Escape', 'Alt_L')
            def test_count():
                mode()
                x.text('gg03Wvey')
                assert clipboard() == 'four', clipboard()
            check('st 3W survives actual Shift events and visual yank', test_count)

            def test_copy_commands():
                def fresh(text):
                    command('write', '\033[2J\033[3J\033[H' + text)
                    mode()
                    x.text('gg')
                fresh('one two three four five six')
                x.text('2y2w')
                assert clipboard() == 'one two three four ', clipboard()
                fresh('one,two,three')
                x.text('vt'); x.chord('comma'); x.chord('semicolon'); x.text('y')
                assert clipboard() == 'one,two', clipboard()
                fresh('one,two,three')
                x.chord('4', 'Shift_L'); x.text('yF'); x.chord('comma')
                assert clipboard() == ',three', clipboard()
                text = 'alpha catfirst\r\nbeta catsecond\r\ngamma catthird'
                fresh(text)
                x.chord('slash'); x.text('cat'); x.chord('Return')
                x.text('2nNY')
                assert clipboard() == 'catsecond', clipboard()
                fresh(text)
                x.chord('slash', 'Shift_L'); x.text('cat'); x.chord('Return')
                x.text('nNnY')
                assert clipboard() == 'catsecond', clipboard()
                fresh(text)
                x.text('v'); x.chord('slash'); x.text('cat'); x.chord('Return')
                x.text('ny')
                assert clipboard() == 'alpha catfirst\nbeta c', clipboard()
                fresh('one  \r\n  two  \r\nthree')
                x.text('2'); x.chord('y', 'Control_L')
                assert clipboard() == 'one\n  two', clipboard()
                fresh('one  ')
                x.text('v'); x.chord('4', 'Shift_L'); x.chord('c', 'Control_L', 'Shift_L')
                assert clipboard() == 'one  ', clipboard()
                fresh('cancelled prompt')
                x.chord('slash'); x.text('absent'); x.chord('Escape'); x.text('Y')
                assert clipboard() == 'cancelled prompt', clipboard()
            check('operator counts, character-find/repeat, global/visual search and yank aliases', test_copy_commands)

            def test_stream():
                command('write', '\033[2J\033[3J\033[H' + ''.join(f'row {i:03}\r\n' for i in range(100)))
                mode()
                x.text('10gg0v')
                x.chord('4', 'Shift_L')
                command('write', ''.join(f'new {i:03}\r\n' for i in range(15)) + '\033[6n')
                wait(lambda: (fixture / 'input').exists() and b'R' in (fixture / 'input').read_bytes(), 'terminal CPR reply')
                x.text('y')
                assert clipboard() == 'row 009', clipboard()
            check('streaming selection and terminal queries preserve selected history', test_stream)

            def selection(name, text):
                old = x.owner(x.d, x.atom(x.d, name.upper().encode(), 0))
                p = S.Popen(['xclip', '-quiet', '-selection', name, '-i'], env=env,
                            stdin=S.PIPE, stdout=S.DEVNULL, stderr=S.DEVNULL, start_new_session=True)
                processes.append(p)
                p.stdin.write(text.encode()); p.stdin.close()
                wait(lambda: x.owner(x.d, x.atom(x.d, name.upper().encode(), 0)) not in (0, old), 'clipboard owner')
            def test_paste():
                selection('primary', 'PRIMARY_MARK')
                selection('clipboard', 'CLIPBOARD_MARK')
                mode()
                before = (fixture / 'input').read_bytes()
                a = x.attributes(tw)
                x.mouse(a.x + 100, a.y + 100, 2, 1)
                x.mouse(a.x + 100, a.y + 100, 2, 0)
                x.chord('v', 'Control_L', 'Shift_L')
                time.sleep(.2)
                assert (fixture / 'input').read_bytes() == before
                x.chord('Escape')
                x.chord('v', 'Control_L', 'Shift_L')
                wait(lambda: b'CLIPBOARD_MARK' in (fixture / 'input').read_bytes(), 'ordinary paste')
            check('copy mode rejects middle/keyboard paste; normal paste still reaches PTY', test_paste)

            def test_mouse():
                command('write', '\033[2J\033[3J\033[Habcdef\r\n')
                mode()
                # The anysize patch publishes 1-pixel increments, not glyph size.
                # Read PTY dimensions from the fixture and account for centered padding.
                cols, rows = json.loads((fixture / 'size').read_text())
                a = x.attributes(tw)
                cw, ch = a.width // cols, a.height // rows
                left = a.x + a.border_width + (a.width - cols*cw) // 2
                top = a.y + a.border_width + (a.height - rows*ch) // 2
                x.mouse(left + 1.5*cw, top + .5*ch, 1, 1)
                x.mouse(left + 3.5*cw, top + .5*ch)
                x.mouse(left + 3.5*cw, top + .5*ch, 1, 0)
                x.text('y')
                assert clipboard() == 'bcd', clipboard()
            check('real mouse drag in copy mode creates characterwise selection', test_mouse)

            def test_alternate():
                command('write', '\033[?1049h\033[2J\033[Halternate words\r\n')
                mode()
                x.text('gg0v')
                x.chord('4', 'Shift_L')
                x.text('y')
                assert clipboard() == 'alternate words', clipboard()
                command('write', '\033[?1049l')
            check('alternate-screen copy mode selects live rows, not normal-screen history', test_alternate)

            def test_copyout():
                command('write', '\033[2J\033[3J\033[H$ run\r\nolder output\r\n$ run\r\nnewer output\r\n$ ')
                for older, expected in ((False, 'newer output\n'), (True, 'older output\n')):
                    x.chord('o', 'Alt_L')
                    wait(menu_visible, 'command-output menu')
                    if older:
                        x.chord('Down')
                    x.chord('Return')
                    wait(lambda: not menu_visible(), 'command-output menu exit')
                    wait(lambda: clipboard() == expected, 'individual command output copied')
                before = clipboard()
                x.chord('o', 'Alt_L')
                wait(menu_visible, 'command-output cancellation menu')
                x.chord('Escape')
                wait(lambda: not menu_visible(), 'cancelled command-output menu exit')
                time.sleep(.15)
                assert clipboard() == before, 'cancellation changed clipboard'
            check('Alt+o copies individual duplicate-command output and preserves clipboard on cancel', test_copyout)

            def test_pathcopy():
                longpath = '/tmp/' + 'a'*180 + '/file'
                command('write', '\033[2J\033[3J\033[H~/.bashrc\r\n"/tmp/my file"\r\n' + longpath + '\r\n')
                x.chord('p', 'Alt_L')
                wait(menu_visible, 'path-copy menu')
                x.chord('Return')
                wait(lambda: not menu_visible(), 'path-copy menu exit')
                wait(lambda: clipboard() == longpath, 'soft-wrapped path copied literally')
                x.chord('p', 'Alt_L')
                wait(menu_visible, 'quoted-path menu')
                x.text('my'); x.chord('space'); x.text('file'); x.chord('Return')
                wait(lambda: not menu_visible(), 'quoted-path menu exit')
                wait(lambda: clipboard() == '/tmp/my file', 'quoted path copied without quotes')
                x.chord('p', 'Alt_L')
                wait(menu_visible, 'path-copy cancellation menu')
                x.chord('Escape')
                wait(lambda: not menu_visible(), 'path-copy cancelled')
                time.sleep(.15)
                assert clipboard() == '/tmp/my file'
            check('Alt+p copies soft-wrapped/quoted paths and preserves clipboard on cancel', test_pathcopy)

            def test_swallow():
                for i in range(6):
                    registry = tmp / f'gui-{i}'
                    command('spawn', str(registry))
                    gw = int(wait(lambda: registry.read_text() if registry.exists() else '', 'GUI startup'))
                    wait(lambda: gw in x.clients() and tw not in x.clients(), 'GUI swallowed')
                    assert x.attributes(tw).map_state == 0, 'hidden terminal still mapped'
                    x.chord('2', 'Super_L')
                    assert x.attributes(tw).map_state == 0
                    assert x.attributes(gw).x < 0
                    x.chord('1', 'Super_L')
                    command('kill')
                    wait(lambda: tw in x.clients() and x.attributes(tw).map_state == 2, 'terminal restored')
                    assert x.property(tw, 'WM_STATE')[0] == 1
                assert wm.poll() is None
            check('six rapid splash/main GUI swallow cycles restore terminal without orphan windows', test_swallow)

            def ordinary_window(name):
                path = tmp / name
                p = launch([sys.executable, HERE, '--window-fixture', path])
                w = int(wait(lambda: path.read_text() if path.exists() else '', 'ordinary GUI'))
                wait(lambda: w in x.clients(), 'ordinary GUI managed')
                return p, w
            def test_spawn():
                S.run([str(ROOT / 'dwm/dwm-spawn'), '4', '/bin/true'], env=env, check=True)
                (tmp / 'fail-st').touch()
                x.chord('s', 'Super_L', 'Shift_L')
                time.sleep(.15)
                p, w = ordinary_window('unrelated')
                assert x.attributes(w).x >= 0, 'unrelated GUI inherited pending tag'
                assert x.attributes(w).height > 600, 'unrelated GUI inherited floating geometry'
                p.terminate(); p.wait(timeout=3)
                (tmp / 'fail-st').unlink()
                path = tmp / 'targeted'
                S.run([str(ROOT / 'dwm/dwm-spawn'), '4', sys.executable, str(HERE), '--window-fixture', str(path)], env=env, check=True)
                w = int(wait(lambda: path.read_text() if path.exists() else '', 'targeted GUI'))
                wait(lambda: w in x.clients(), 'targeted GUI managed')
                assert x.attributes(w).x < 0
                x.chord('4', 'Super_L')
                assert x.attributes(w).x >= 0
                x.chord('1', 'Super_L')
                os.kill(int(Path(str(path) + '.pid').read_text()), signal.SIGTERM)
                wait(lambda: w not in x.clients(), 'targeted GUI closed')
            check('failed tag/floating requests do not leak; PID-targeted spawn reaches tag 4', test_spawn)

            def test_resize():
                command('write', '\033[2J\033[3J\033[H' + ('x'*115 + '\r\n')*2500)
                def rss():
                    pages = int(Path(f'/proc/{term.pid}/statm').read_text().split()[1])
                    return pages * os.sysconf('SC_PAGE_SIZE')
                baseline = None
                samples = []
                original = x.attributes(tw).width
                for i in range(10):
                    p, w = ordinary_window(f'tile-{i}')
                    wait(lambda: x.attributes(tw).width < original, 'terminal tiled narrower')
                    time.sleep(.12)
                    p.terminate(); p.wait(timeout=3)
                    wait(lambda: x.attributes(tw).width == original, 'terminal width restored')
                    time.sleep(.12)
                    samples.append(rss())
                    if i == 1:
                        baseline = samples[-1]
                assert max(samples[2:]) - baseline < 2*1024*1024, samples
                print('  RSS after warmup:', [n//1024 for n in samples[1:]], 'KiB', flush=True)
            check('full-history terminal RSS remains bounded over ten real tiling cycles', test_resize)

            def test_status():
                counter = tmp / 'polls'
                counter.touch()
                script('date', f'#!/bin/sh\necho date >> "{counter}"\necho CLOCK\n')
                script('wpctl', f'#!/bin/sh\necho "$1" >> "{counter}"\necho "Volume: 0.50"\n')
                for name in ('top', 'free', 'dwmblocks-wifi', 'dwmblocks-charge-rate'):
                    script(name, '#!/bin/sh\nexit 0\n')
                blocks = launch([binaries['dwmblocks']])
                script('pkill', '#!' + sys.executable + f'\nimport os,signal\nos.kill({blocks.pid},signal.SIGRTMIN+10)\n')
                wait(lambda: b'CLOCK' in x.property(x.root, 'WM_NAME'), 'status root name')
                initial = counter.read_text().splitlines()
                assert initial.count('get-volume') == 1
                blocks.send_signal(signal.SIGRTMIN + 10)
                wait(lambda: counter.read_text().splitlines().count('get-volume') >= 2, 'signal refresh')
                assert counter.read_text().splitlines().count('date') == 1, 'signal advanced interval clock'
                x.chord('F2', 'Super_L')
                wait(lambda: counter.read_text().splitlines().count('get-volume') >= 3, 'volume-key refresh')
                assert 'set-volume' in counter.read_text()
                start = time.monotonic()
                blocks.terminate(); blocks.wait(timeout=1)
                assert time.monotonic() - start < .5
            check('real dwmblocks signal/key refresh, unchanged interval tick and prompt termination', test_status)

            def test_interrupted_status():
                # Force refresh signals to land while unrelated commands are
                # blocked on pipe reads, not only while the main loop sleeps.
                script('top', f"#!/bin/sh\ntouch '{tmp}/slow-command-ready'\nsleep 0.25\nprintf 'Cpu 12 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\\n'\n")
                script('dwmblocks-charge-rate', "#!/bin/sh\nsleep 0.25\nprintf 'POWER 8W\\n'\n")
                x.store(x.d, x.root, b'')
                x.sync(x.d, 0)
                blocks = launch([binaries['dwmblocks']])
                wait(lambda: (tmp / 'slow-command-ready').exists(), 'delayed command startup')
                end = time.monotonic() + 1.2
                published = []
                while time.monotonic() < end:
                    assert blocks.poll() is None
                    blocks.send_signal(signal.SIGRTMIN + 10)
                    time.sleep(.015)
                    status = x.property(x.root, 'WM_NAME')
                    if status:
                        published.append(status)
                        assert b'CPU 12%' in status and b'POWER 8W' in status, status
                assert published, 'no status was published during signal burst'
                blocks.terminate(); blocks.wait(timeout=2)
            check('CPU/power fields survive refresh signals during delayed command output', test_interrupted_status)
            os.close(control)
            assert server.poll() is None and wm.poll() is None and term.poll() is None
            print(f'All {len(results)} X11 integration checks passed.', flush=True)
        except BaseException:
            for log in logs:
                log.flush()
                text = Path(log.name).read_text(errors='replace')
                if text:
                    print(f'--- {Path(log.name).name} ---\n{text[-6000:]}', file=sys.stderr)
            raise
        finally:
            # dwm creates separate sessions for launched fixture clients.
            for pidfile in tmp.glob('*.pid'):
                try:
                    pid = int(pidfile.read_text())
                    args = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
                    # A completed fixture's PID could have been reused. Validate
                    # both the executable script and this private registry path.
                    if str(HERE).encode() in args and str(pidfile)[:-4].encode() in args:
                        os.kill(pid, signal.SIGTERM)
                except (ProcessLookupError, FileNotFoundError):
                    pass
            # Kill only groups created above, never real desktop processes.
            for p in reversed(processes):
                if p.poll() is None:
                    try:
                        os.killpg(p.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            for p in reversed(processes):
                try:
                    p.wait(timeout=2)
                except S.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait(timeout=2)
            for log in logs:
                log.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--terminal-fixture':
        terminal_fixture(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == '--window-fixture':
        window_fixture(sys.argv[2], len(sys.argv) > 3)
    else:
        integration()

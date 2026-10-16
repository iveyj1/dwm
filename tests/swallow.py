#!/usr/bin/env python3
"""Regression tests for delayed swallow UnmapNotify events (no X server)."""
from pathlib import Path
import subprocess
import tempfile
import unittest

class Swallow(unittest.TestCase):
    def test_hidden_terminal_maprequest(self):
        source = (Path(__file__).resolve().parents[1] / 'dwm.c').read_text()
        start = source.index('\nvoid\nmaprequest(XEvent *e)')
        end = source.index('\nvoid\nmonocle', start)
        code = r'''
#include <assert.h>
#include <X11/Xlib.h>
static Display *dpy;
static int managed;
int XGetWindowAttributes(Display *d, Window w, XWindowAttributes *a) {
    (void)d; a->override_redirect = w == 99; return 1;
}
static int swallowingclient(Window w) { return w == 42; }
static int wintoclient(Window w) { return w == 43; }
static void manage(Window w, XWindowAttributes *a) { (void)w; (void)a; managed++; }
'''
        code += source[start:end]
        code += r'''
int main(void) {
    XEvent e = {0};
    e.xmaprequest.window = 42; maprequest(&e); assert(managed == 0);
    e.xmaprequest.window = 43; maprequest(&e); assert(managed == 0);
    e.xmaprequest.window = 99; maprequest(&e); assert(managed == 0);
    e.xmaprequest.window = 44; maprequest(&e); assert(managed == 1);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.c'
            path.write_text(code)
            binary = Path(tmp) / 'test'
            subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_unmap_ordering(self):
        source = (Path(__file__).resolve().parents[1] / 'dwm.c').read_text()
        start = source.index('\nvoid\nunmapnotify(XEvent *e)')
        end = source.index('\nvoid\nupdatebars', start)
        code = r'''
#include <assert.h>
#include <X11/Xlib.h>
#define WithdrawnState 0
typedef struct Client Client;
struct Client { Window win; unsigned int ignoreunmap; Client *swallowing; };
static Client terminal = {42, 0, 0}, app = {43, 0, &terminal};
static Client *active = &app;
static int removed, withdrawn;
static Client *wintoclient(Window w) { return active->win == w ? active : 0; }
static Client *swallowingclient(Window w) {
    return active->swallowing && active->swallowing->win == w ? active : 0;
}
static void unmanage(Client *c, int destroyed) { (void)c; (void)destroyed; removed++; }
static void setclientstate(Client *c, int state) { (void)c; (void)state; withdrawn++; }
'''
        code += source[start:end]
        code += r'''
int main(void) {
    XEvent e = {0};
    e.xunmap.window = 42;
    /* Root duplicate must not consume the expected window notification. */
    terminal.ignoreunmap = 1;
    e.xunmap.event = 1;
    unmapnotify(&e);
    assert(terminal.ignoreunmap == 1);
    e.xunmap.event = 42;
    unmapnotify(&e);
    assert(terminal.ignoreunmap == 0 && removed == 0);
    /* Restore before the expected hide notification is dispatched. */
    terminal.ignoreunmap = 1;
    active = &terminal;
    unmapnotify(&e);
    assert(terminal.ignoreunmap == 0 && removed == 0);
    e.xunmap.event = 1;
    unmapnotify(&e);
    assert(removed == 0);
    /* Genuine later client unmap still works. */
    e.xunmap.event = 42;
    unmapnotify(&e);
    assert(removed == 1);
    /* Synthetic withdrawal to root must still be processed. */
    e.xunmap.event = 1;
    e.xunmap.send_event = True;
    unmapnotify(&e);
    assert(withdrawn == 1);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.c'
            path.write_text(code)
            binary = Path(tmp) / 'test'
            subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(path), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

if __name__ == '__main__':
    unittest.main()

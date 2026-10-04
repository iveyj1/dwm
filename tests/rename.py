#!/usr/bin/env python3
"""Headless tests of the actual asynchronous rename pipe consumer."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Rename(unittest.TestCase):
    def test_pipe(self):
        source = (ROOT / 'dwm.c').read_text()
        start = source.index('\nvoid\nreadtagname(void)')
        end = source.index('\nClient *\nnexttiled', start)
        code = r'''
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#define LENGTH(a) (sizeof(a) / sizeof((a)[0]))
#define MAX_TAGLEN 16
static int tagnamefd = -1, tagnamedone, draws;
static unsigned int tagnamemask;
static size_t tagnamelen;
static char tagnamebuf[MAX_TAGLEN];
static char tags[3][MAX_TAGLEN] = { "1", "2", "3" };
static void drawbars(void) { draws++; }
'''
        code += source[start:end]
        code += r'''
static int begin(unsigned int mask) {
    int fd[2];
    assert(pipe(fd) == 0);
    assert(fcntl(fd[0], F_SETFL, O_NONBLOCK) == 0);
    tagnamefd = fd[0];
    tagnamemask = mask;
    tagnamelen = tagnamedone = 0;
    return fd[1];
}
int main(void) {
    int w = begin(1U << 1);
    /* No output yet: return immediately, leaving rename pending. */
    readtagname();
    assert(tagnamefd >= 0 && draws == 0);
    assert(write(w, "wo", 2) == 2);
    readtagname();
    assert(write(w, "rk\n", 3) == 3);
    readtagname();
    assert(draws == 0);
    close(w); readtagname();
    assert(tagnamefd == -1 && draws == 1);
    assert(!strcmp(tags[0], "1") && !strcmp(tags[1], "work"));
    /* Escape/failed exec produces EOF without a line. */
    w = begin(2); close(w); readtagname();
    assert(draws == 1 && !strcmp(tags[1], "work"));
    /* Incomplete output must not rename. */
    w = begin(2); assert(write(w, "bad", 3) == 3);
    readtagname(); close(w); readtagname();
    assert(draws == 1);
    /* Long names are drained and bounded, even across reads. */
    w = begin(5);
    for (int i = 0; i < 8; i++) {
        assert(write(w, "abcdefghijklmnop", 16) == 16);
        readtagname();
    }
    assert(write(w, "\n", 1) == 1);
    readtagname(); close(w); readtagname();
    assert(draws == 2 && strlen(tags[0]) == MAX_TAGLEN - 1);
    assert(!strcmp(tags[0], tags[2]) && !strcmp(tags[1], "work"));
    /* Enter on an empty prompt retains the previous empty-name behavior. */
    w = begin(1); assert(write(w, "\n", 1) == 1);
    readtagname(); close(w); readtagname();
    assert(draws == 3 && !strcmp(tags[0], ""));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'rename.c').write_text(code)
            subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            str(path / 'rename.c'), '-o', str(path / 'rename')],
                           check=True)
            subprocess.run([str(path / 'rename')], check=True, timeout=5)


if __name__ == '__main__':
    unittest.main()

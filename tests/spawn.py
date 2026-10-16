#!/usr/bin/env python3
"""Exercise the real pending-request code with a synthetic process tree/clock."""
from pathlib import Path
import subprocess
import tempfile
import unittest

class Spawn(unittest.TestCase):
    def test_matching(self):
        source = (Path(__file__).resolve().parents[1] / 'dwm.c').read_text()
        start = source.index('\nstatic void\nrecordspawn(')
        end = source.index('\nstatic pid_t\nspawnpid(', start)
        code = r'''
#include <assert.h>
#include <stddef.h>
#include <sys/types.h>
#include <time.h>
#define LENGTH(a) (sizeof(a) / sizeof((a)[0]))
typedef struct { int unused; } FloatingWindow;
typedef struct {
    pid_t pid;
    unsigned int tags;
    const FloatingWindow *floating;
    time_t created;
} PendingSpawn;
static PendingSpawn pendingspawns[16];
static time_t now = 100;
static time_t spawnnow(void) { return now; }
static int isdescprocess(pid_t parent, pid_t child) {
    return parent == 123 && child == 456;
}
'''
        code += source[start:end]
        code += r'''
int main(void) {
    PendingSpawn result;
    FloatingWindow fw = {0};
    recordspawn(123, 4, &fw);
    assert(!matchspawn(0, &result));
    assert(!matchspawn(999, &result));
    assert(matchspawn(456, &result));
    assert(result.tags == 4 && result.floating == &fw);
    assert(!matchspawn(456, &result));
    recordspawn(321, 8, 0);
    assert(matchspawn(321, &result) && result.tags == 8);
    recordspawn(-1, 8, 0);
    recordspawn(0, 8, 0);
    assert(!matchspawn(321, &result));
    recordspawn(123, 2, 0);
    now += 30;
    assert(!matchspawn(123, &result));
    assert(!matchspawn(456, &result));
    /* Concurrent unrelated requests retain their individual attributes. */
    recordspawn(111, 1, 0);
    recordspawn(222, 2, &fw);
    assert(matchspawn(222, &result) && result.tags == 2 && result.floating == &fw);
    assert(matchspawn(111, &result) && result.tags == 1 && !result.floating);
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

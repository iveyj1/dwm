#!/usr/bin/env python3
"""Exercise shortcut process management without touching the X server."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

HELPER = Path(__file__).resolve().parents[1] / "dwm-redshift"

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    fake = root / "redshift"
    fake.write_text("""#!/usr/bin/env python3
import os, signal, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
with Path(os.environ['EVENTS']).open('a') as out:
    out.write(' '.join(sys.argv[1:]) + '\\n')
while True:
    time.sleep(0.01)
""")
    fake.chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp}:{HELPER.parent}:{os.environ['PATH']}",
               XDG_RUNTIME_DIR=tmp, DISPLAY=":test", EVENTS=str(root / "events"))

    def run(action):
        subprocess.run([str(HELPER), action], env=env, check=True, timeout=10)

    def wait_events(count):
        for _ in range(200):
            if (root / "events").exists():
                lines = (root / "events").read_text().splitlines()
                if len(lines) == count:
                    assert all(line == "-l 42:-84 -t 5000:3000" for line in lines)
                    return
            time.sleep(0.01)
        raise AssertionError("Redshift did not start")

    try:
        run("stop")  # No instance is harmless.
        children = [subprocess.Popen([str(HELPER), "start"], env=env) for _ in range(8)]
        assert all(child.wait(timeout=10) == 0 for child in children)
        wait_events(1)
        state = next((root / "dwm-process").glob("*.json"))
        run("stop")
        assert not state.exists()
        run("stop")
        # A stale record must never signal an unrelated process.
        state.write_text(json.dumps([os.getpid(), "stale-start-time"]))
        run("stop")
        assert not state.exists()
        run("start")
        wait_events(2)
        # Names and displays isolate instances; argv is passed without shell parsing.
        manager = str(HELPER.parent / "dwm-process")
        other_env = dict(env, DISPLAY=":other")
        sleeper = ["python3", "-c", "import time; time.sleep(60)"]
        try:
            subprocess.run([manager, "start", "other/name", "--", *sleeper],
                           env=env, check=True)
            subprocess.run([manager, "start", "redshift", "--", *sleeper],
                           env=other_env, check=True)
            assert len(list((root / "dwm-process").glob("*.json"))) == 3
            # An already running name ignores even an invalid replacement command.
            subprocess.run([manager, "start", "other/name", "--", "/nonexistent"],
                           env=env, check=True)
            run("stop")
            assert len(list((root / "dwm-process").glob("*.json"))) == 2
        finally:
            for _ in range(2):
                subprocess.run([manager, "stop", "other/name"], env=env, check=True)
                subprocess.run([manager, "stop", "redshift"], env=other_env, check=True)
        assert not list((root / "dwm-process").glob("*.json"))
    finally:
        run("stop")
print("process/redshift: concurrent start, repeated stop, isolation, restart, stale PID: passed")

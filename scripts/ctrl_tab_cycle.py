#!/usr/bin/env python3
"""Switch to the last tab once, then cycle forward on rapid Ctrl+Tab presses."""

import fcntl
import os
from pathlib import Path
import subprocess
import sys
import time

# Key-repeat normally starts after roughly half a second. This allows both a
# repeated physical key and another Ctrl+Tab press while Ctrl remains held.
REPEAT_WINDOW_SECONDS = 0.8


def state_file() -> Path:
    # KITTY_LISTEN_ON is a newly-created fd for every helper invocation, so it
    # cannot identify a sequence. KITTY_PID is inherited from the kitty window
    # that launched us and stays constant for the lifetime of that instance.
    instance = os.environ.get("KITTY_PID", "unknown")
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
    return runtime_dir / f"kitty-ctrl-tab-{instance}.state"


def main() -> None:
    if sys.argv[1:] == ["next"]:
        action = "next_tab"
    else:
        path = state_file()
        now = time.monotonic()

        with path.open("a+") as state:
            fcntl.flock(state.fileno(), fcntl.LOCK_EX)
            state.seek(0)
            try:
                previous = float(state.read().strip())
            except ValueError:
                previous = 0.0

            action = "next_tab" if now - previous < REPEAT_WINDOW_SECONDS else "goto_tab"
            state.seek(0)
            state.truncate()
            state.write(str(now))
            state.flush()

    command = ["kitten", "@", "--no-response"]
    window_id = os.environ.get("KITTY_WINDOW_ID")
    if window_id:
        command.extend(["--match", f"id:{window_id}"])
    command.extend(["action", action])
    if action == "goto_tab":
        command.append("-1")
    # Kitty passes background helpers a private remote-control fd, such as
    # KITTY_LISTEN_ON=fd:3. Keep it open for the kitten subprocess.
    listen_on = os.environ.get("KITTY_LISTEN_ON", "")
    pass_fds = ()
    if listen_on.startswith("fd:"):
        try:
            pass_fds = (int(listen_on[3:]),)
        except ValueError:
            pass
    subprocess.run(command, check=False, pass_fds=pass_fds)


if __name__ == "__main__":
    main()

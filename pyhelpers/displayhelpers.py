"""Which X display an emulator window should open on.

Non-headless runs are for the user to watch: the emulator has to appear on the
same X session app.py is running in -- the xfce/RDP desktop reachable on port
33891 -- not on a private Xvfb the user can't see. app.py inherits that display
(currently ":20.0", from xorgxrdp), so helpers running inside the runner just
need to honour os.environ["DISPLAY"].

The fallback only matters when a helper is exercised from a bare shell with no
DISPLAY set. Hardcoding one (basiliskhelpers pins ":14") goes stale as soon as
the RDP session is recycled -- /tmp/.X11-unix is full of dead sockets from old
sessions -- so find the live xrdp X server instead.
"""

import os
import re
import subprocess


def resolve_display(explicit=None):
    """Return the display emulator windows should open on.

    explicit wins; then the ambient DISPLAY; then the running xrdp session.
    """
    if explicit:
        return explicit
    if os.environ.get("DISPLAY"):
        return os.environ["DISPLAY"]
    return find_rdp_display() or ":20"


def find_rdp_display():
    """Find the live xorgxrdp session's display, e.g. ':20'.

    Prefers an Xorg started with an xrdp config; falls back to the
    highest-numbered live Xorg. Returns None if nothing is running.
    """
    try:
        ps = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    except Exception:
        return None

    candidates = []
    for line in ps.splitlines():
        if "Xorg" not in line:
            continue
        m = re.search(r"Xorg\s+(:\d+)", line)
        if not m:
            continue
        disp = m.group(1)
        # xorgxrdp sessions carry an xrdp-ish config/logfile on the cmdline.
        is_rdp = "xrdp" in line or "xorg.conf" in line
        candidates.append((is_rdp, int(disp[1:]), disp))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]

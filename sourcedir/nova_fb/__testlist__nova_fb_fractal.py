import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Same shape as __testlist__nova_fb_spritecursor.py -- a bare SIMH script
# poked into memory and run, boot_rdos False, "binary" pointing at this
# project's own bin/dgnova-fb build (the shared dgnova has no FB device).
#
# demo/fractal.ini (gen_fractal.py) is a title card in char mode (the
# built-in ROM, "vga" style 8x25 text) followed by a classic 8-bit-demo AND
# fractal -- SET (x,y) iff (x+t) AND y != 0, the Sierpinski gasket out of
# Pascal's triangle mod 2, redrawn from scratch every frame with t advancing.
# It scrolls, IT NEVER HALTS -- same as modeswitch.ini -- so there is no
# "HALT instruction" or fixed frame count to wait for: the program is
# genuinely in continuous motion (~100+ frames/sec on this host) until
# something stops the simulator. See gen_fractal.py for why the AND test in
# particular: no multiply, one ALC instruction to test each pixel, exactly
# what a Nova (and the home-computer BASICs this effect comes from) can do
# fast.
#
# The live sink and monitor are the same deal as sprite_cursor: the PNGs are
# the assertion (verify_fractal.py, independent of the simulator, checking
# whatever frames happened to land rather than assuming a specific count),
# the monitor is only the view, and require_success=False keeps a headless
# container running this unchanged. NOT keep_open on the monitor, though --
# see "THE HANDOVER" at the bottom for why that's pause_on's job here, not a
# flag on the monitor.

CONFIG = {
    "parent": "nova fb sprite cursor",
    "projdir": "nova_fb",
    "instance_name": "nova1",
    "function": "and_fractal",
    "simh_binary": "bin/dgnova-fb",
    "live_sink": "/dev/shm/novafb-fractal",
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
            "simh_binary_path": "{simh_binary}",
            "out_dir": {
                "_rel": "output"
            }
        }
    },
    "steps": [
        {
            "action": "test_start_novafb_monitor",
            "param": {
                "name": "novafb_monitor",
                "live_path": "{live_sink}",
                "scale": 0,
                "require_success": False,
                "keep_open": False
            },
            "subaction": ""
        },
        {
            "action": "test_startnovasimh",
            "param": {
                "name": "nova1",
                "binary": "{projbasedir}{projdir}/{simh_binary}",
                "script_path": "{projbasedir}{projdir}/demo/fractal.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False,
                "live_path": "{live_sink}"
            },
            "subaction": ""
        },
        # No successphrase to wait for -- the program never prints to the
        # console once it starts scrolling, by design (nothing here touches
        # TTO). This only catches a script that failed to load: a bad "d"
        # line fails synchronously, before "go" is even reached, so it is
        # already in the buffer by the time test_startnovasimh returns.
        {
            "action": "test_novascreensearch",
            "param": {
                "name": "nova1",
                "failphrase": "Invalid argument",
                "timeout": 5,
                "require_success": False
            },
            "subaction": ""
        },
        # The whole point: let it actually scroll for a few seconds before
        # anything checks it. Motion, not a snapshot, is the thing being
        # tested. nova1 is left running through every step below -- none of
        # them need it stopped, only some frames already on disk.
        {
            "action": "test_wait_for_seconds",
            "param": {
                "seconds": 3,
                "reason": "let the AND-scroll run so multiple frames land "
                          "in output/ and the live sink before checking them"
            },
            "subaction": ""
        },
        # --- show it in the report -------------------------------------------
        # Title card plus the first few scroll frames -- a fixed, small glob
        # rather than "the last one", since the exact frame count depends on
        # host speed and is not something to assume here.
        {
            "action": "test_attach_screenshot",
            "param": {
                "image_path": "{projbasedir}{projdir}/output/fractal000[1-4].png",
                "name": "fb",
                "scale": 2
            },
            "subaction": ""
        },
        # --- assert on the pixels, not just the console ---------------------
        {
            "action": "test_hostbuild",
            "param": {
                "command": "python3 verify_fractal.py",
                "cwd": "{projbasedir}{projdir}",
                "timeout": 120
            },
            "subaction": ""
        },
        # --- assert the live sink shows what the PNGs assert ----------------
        # Its own separate simulator instance (see verify_live.py), unrelated
        # to nova1 -- doesn't care whether nova1 is still running.
        {
            "action": "test_hostbuild",
            "param": {
                "command": "python3 verify_live.py fractal",
                "cwd": "{projbasedir}{projdir}",
                "timeout": 120
            },
            "subaction": ""
        },
        # --- THE HANDOVER -----------------------------------------------------
        # Every automated check above already ran and passed. This is the
        # only step nova1 (and the monitor) needs to survive to: pause_on
        # turns teardown into a breakpoint that blocks until the live
        # instances actually exit, so someone reviewing interactively can
        # keep watching the scroll for as long as they want instead of it
        # being cut off at a fixed 3 seconds. A runner that doesn't honour
        # pause_on just runs this as an ordinary teardown -- the safe way to
        # degrade -- so headless/CI runs still complete on their own.
        {
            "action": "test_terminate_all",
            "param": {},
            "subaction": "",
            "pause_on": True
        },
    ],
}

PATHS = init_test_env(CONFIG, __name__)

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Framebuffer/sprite test for the custom Nova device on code 042.
#
# Unlike the nova_rdos tests this does NOT boot RDOS: each step runs a bare
# SIMH script that pokes a program into memory, runs it, and halts. So
# boot_rdos is False, and "binary" points at this project's own simulator
# build (bin/dgnova-fb) -- the shared disk_artifacts/bin/dgnova has no FB
# device and would fail every "set fb ..." line in the script.
#
# cwd is the project dir so the "set fb prefix=output/cursor" lines inside the
# demo scripts resolve relative to it.
#
# The console assertions prove the Nova program ran to completion; the PNG
# assertions (verify_frames.py, which exits non-zero on failure) prove what it
# actually drew. See BUILD.txt for the device programming model.
#
# The PNGs are the assertion; the monitor is the view. live_path turns on the
# card's shared-memory live sink and test_start_novafb_monitor opens a pygame
# window on it, so the run has a screen to watch instead of only stills to read
# afterwards. Nothing here depends on the window: the sink costs a memcpy per
# present, the viewer only reads it, and require_success=False lets a headless
# container (or one built before pygame was in requirements.txt) run the same
# testlist unchanged. The demos halt in milliseconds, so what you actually see
# is the final frame -- the window is worth more against the rdosdraw test,
# which drives RDOS interactively.

CONFIG = {
    "parent": "nova fb sprite cursor",
    "projdir": "nova_fb",
    "instance_name": "nova1",
    "function": "sprite_cursor",
    "simh_binary": "bin/dgnova-fb",
    # Per-run, not per-program: kept out of the generated demo/*.ini, which
    # run_demos.sh shares.
    "live_sink": "/dev/shm/novafb-spritecursor",
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
        # The viewer waits for the sink rather than creating it, so starting it
        # first means it is already up for frame 1 instead of catching the run
        # halfway.
        {
            "action": "test_start_novafb_monitor",
            "param": {
                "name": "novafb_monitor",
                "live_path": "{live_sink}",
                "scale": 0,
                "require_success": False,
                # Two demos that halt in milliseconds: without this the window
                # exists for the few seconds before teardown and is easy to
                # miss. Close it with Q.
                "keep_open": True
            },
            "subaction": ""
        },
        # --- 32x32 arrow from four 16x16 sprite units, SET op ---------------
        {
            "action": "test_startnovasimh",
            "param": {
                "name": "nova1",
                "binary": "{projbasedir}{projdir}/{simh_binary}",
                "script_path": "{projbasedir}{projdir}/demo/cursor.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False,
                "live_path": "{live_sink}"
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "name": "nova1",
                "successphrase": "HALT instruction",
                "failphrase": "Invalid argument",
                "timeout": 30,
                "require_success": True
            },
            "subaction": ""
        },
        # Two presents = two frames dumped; proves the cursor moved and the
        # second present happened rather than the program halting early.
        {
            "action": "test_novascreensearch",
            "param": {
                "name": "nova1",
                "successphrase": "FRAME:",
                "failphrase": "",
                "timeout": 5,
                "require_success": True
            },
            "subaction": ""
        },
        # --- same cursor, XOR op (visible over any background) --------------
        {
            "action": "test_startnovasimh",
            "param": {
                "name": "nova2",
                "binary": "{projbasedir}{projdir}/{simh_binary}",
                "script_path": "{projbasedir}{projdir}/demo/cursor_xor.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_rdos": False,
                "live_path": "{live_sink}"
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "name": "nova2",
                "successphrase": "HALT instruction",
                "failphrase": "Invalid argument",
                "timeout": 30,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_terminate_all",
            "param": {},
            "subaction": ""
        },
        # --- show the frames in the report ----------------------------------
        # Both cursor frames (moved position) and both ops, so the report shows
        # what was drawn rather than only that the pixel checks passed.
        {
            "action": "test_attach_screenshot",
            "param": {
                "image_path": "{projbasedir}{projdir}/output/cursor*.png",
                "name": "fb",
                "scale": 2
            },
            "subaction": ""
        },
        # --- assert on the pixels, not just the console ---------------------
        # verify_frames.py recomputes the expected composite independently and
        # diffs every pixel; it also asserts the sprite overlay did NOT damage
        # the framebuffer under the cursor's old position.
        {
            "action": "test_hostbuild",
            "param": {
                "command": "python3 verify_frames.py cursor cursor_xor",
                "cwd": "{projbasedir}{projdir}",
                "timeout": 120
            },
            "subaction": ""
        },
        # --- assert the live sink shows what the PNGs assert ----------------
        # The viewer above is for the human and is allowed to be absent; this
        # is the headless half, and it fails the run. It re-runs cursor.ini
        # with the sink on and diffs the sink's frame against that frame's PNG,
        # so a viewer can never quietly drift from what verify_frames.py
        # checked. No pygame, no X involved.
        {
            "action": "test_hostbuild",
            "param": {
                "command": "python3 verify_live.py cursor",
                "cwd": "{projbasedir}{projdir}",
                "timeout": 120
            },
            "subaction": ""
        },
    ],
}

PATHS = init_test_env(CONFIG, __name__)

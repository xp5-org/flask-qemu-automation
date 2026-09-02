import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Variant of "nova fb sprite cursor" (function sprite_cursor) that drives the
# framebuffer from REAL SOFTWARE UNDER RDOS instead of from the SIMH console.
#
# Yes, this works from RDOS. A Nova has no supervisor mode, so an ordinary user
# program can issue IOT to device 42 directly; and because the card never
# asserts Done and never interrupts, RDOS is undisturbed by it. The stock
# rdos_d31.dsk already carries the whole toolchain (ASM.SV, RLDR.SV, MAC.SV,
# EDIT.SV), so nothing extra had to be installed.
#
# rdos_d31_fb.dsk is a stock RDOS disk with FBDRAW.SR baked in (built by
# build_rdos_disk.py). This test does the assemble/link/run LIVE, the same way
# the nova_rdos FORTRAN variant does, so a broken toolchain path fails loudly
# rather than being assumed.
#
# FBDRAW.SR draws a filled 128x96 rectangle with word writes (the cheap path
# for solid fills) and overlays a 16x16 sprite cursor in XOR mode positioned to
# straddle the rectangle's corner -- so the one cursor is visible against both
# the white fill and the black background. See BUILD.txt.
#
# This is the variant the live view is actually FOR. live_path turns on the
# card's shared-memory sink and test_start_novafb_monitor opens a pygame window
# on it, so the card's output is on screen while the run happens rather than
# only in a PNG afterwards. The sprite_cursor variant halts in milliseconds and
# its window just shows the final frame; this one boots RDOS, assembles, links
# and runs -- a minute and a half of console work with the screen visible
# throughout, and the frame appearing at the moment FBDRAW presents it.
#
# The window is not an assertion and cannot fail the run: the sink costs a
# memcpy per present, the viewer only ever reads it, and require_success=False
# means a headless container runs this testlist exactly as it did before. The
# PNG assertions below are unchanged and remain the thing that passes or fails.

CONFIG = {
    "parent": "nova fb sprite cursor",
    "projdir": "nova_fb",
    "instance_name": "nova1",
    "function": "rdos_draw",
    "simh_binary": "bin/dgnova-fb",
    "disk_image": "rdos_d31_fb.dsk",
    # Per-run, not per-program, so it is injected around demo/rdos_fbdraw.ini
    # rather than written into it. A different sink path from the sprite_cursor
    # variant's, so the two can run at once without fighting over one window.
    "live_sink": "/dev/shm/novafb-rdosdraw",
    "projbasedir": "/testsrc/sourcedir/",
    "structure": {
        "project": {
            "_rel": "{projdir}",
            "simh_binary_path": "{simh_binary}",
            "disk_image_path": "{disk_image}",
            "out_dir": {
                "_rel": "output"
            }
        }
    },
    "steps": [
        # First, so the window is already up for the boot rather than catching
        # the run halfway: the viewer waits for the sink, it does not create it.
        {
            "action": "test_start_novafb_monitor",
            "param": {
                "name": "novafb_monitor",
                "live_path": "{live_sink}",
                "scale": 0,
                "require_success": False
            },
            "subaction": ""
        },
        # Boots RDOS off rdos_d31_fb.dsk. Unlike the sprite_cursor variant this
        # DOES drive the cold-boot prompts, so boot_rdos stays at its default.
        # The script sets the frame geometry and PNG prefix before booting.
        {
            "action": "test_startnovasimh",
            "param": {
                "name": "nova1",
                "binary": "{projbasedir}{projdir}/{simh_binary}",
                "script_path": "{projbasedir}{projdir}/demo/rdos_fbdraw.ini",
                "cwd": "{projbasedir}{projdir}",
                "boot_timeout": 40,
                "live_path": "{live_sink}"
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "name": "nova1",
                "successphrase": "NOVA RDOS Rev",
                "failphrase": "",
                "timeout": 10,
                "require_success": True
            },
            "subaction": ""
        },
        # --- assemble ------------------------------------------------------
        {
            "action": "test_sendnovacommand",
            "param": {
                "name": "nova1",
                "cmd_text": "ASM FBDRAW",
                "delay": 35
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "name": "nova1",
                "successphrase": "PROGRAM IS RELOCATABLE",
                "failphrase": "ASSEMBLY TERMINATED",
                "timeout": 30,
                "require_success": True
            },
            "subaction": ""
        },
        # --- link ----------------------------------------------------------
        {
            "action": "test_sendnovacommand",
            "param": {
                "name": "nova1",
                "cmd_text": "RLDR FBDRAW",
                "delay": 35
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "name": "nova1",
                "successphrase": "NMAX",
                "failphrase": "NO STARTING ADDRESS",
                "timeout": 30,
                "require_success": True
            },
            "subaction": ""
        },
        # --- run it: this is the step that actually touches device 042 ------
        {
            "action": "test_sendnovacommand",
            "param": {
                "name": "nova1",
                "cmd_text": "FBDRAW",
                "delay": 12
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "name": "nova1",
                "successphrase": "R",
                "failphrase": "ERROR",
                "timeout": 15,
                "require_success": True
            },
            "subaction": ""
        },
        {
            "action": "test_terminate_all",
            "param": {},
            "subaction": ""
        },
        # --- show the frame in the report -----------------------------------
        # The Nova has no VM framebuffer to screendump, so the card's PNG is
        # attached here instead; 2x so the 256x256 1-bit frame is legible.
        {
            "action": "test_attach_screenshot",
            "param": {
                "image_path": "{projbasedir}{projdir}/output/rdos0001.png",
                "name": "fb",
                "scale": 2
            },
            "subaction": ""
        },
        # --- assert on the pixels the RDOS program drew ---------------------
        {
            "action": "test_hostbuild",
            "param": {
                "command": "python3 verify_frames.py rdos",
                "cwd": "{projbasedir}{projdir}",
                "timeout": 120
            },
            "subaction": ""
        },
        # --- and that the sink agrees with the PNG the assertions checked ---
        # Headless (no pygame, no X): re-runs a demo with the sink on and diffs
        # its frame against that frame's PNG, so what the window shows can
        # never quietly drift from what verify_frames.py proved. It uses the
        # cursor demo rather than this test's own RDOS frame because that path
        # needs no interactive console driving.
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

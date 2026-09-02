import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
TESTSRC_HELPERDIR = "/testsrc/pyhelpers"
if TESTSRC_HELPERDIR not in sys.path:
    sys.path.insert(0, TESTSRC_HELPERDIR)

from apphelpers import init_test_env


# Character mode: the card GENERATES the frame from a text buffer and a font
# instead of showing what was written to the bitmap.
#
# ONE PROGRAM, THREE MODES. This used to be three separate SIMH scripts, each
# loading its own copy of the same loader with different data, each presenting
# one frame and halting -- a proof of concept that demonstrated char mode three
# times without ever SWITCHING a mode. demo/modeswitch.ini (gen_modeswitch.py)
# is the merged version: one Nova program, loaded once, that owns all three
# modes and switches between them on a character typed at the console.
#
#   1   80x25, nine dot cell, built-in ROM, line graphics
#   2   90x25, eight dot cell, built-in ROM
#   3   80x25, nine dot cell, the program's OWN font (CHARPTR)
#
# All three are 720x400, because the program cannot change that: WIDTH and
# HEIGHT are card settings, not registers on the text port, so the modes differ
# in exactly what a program can actually reach -- cell width, line graphics,
# and the font. Mode 2 is 90x25 (720/8) where the old text30.ini was 80x30 on a
# 640x480 card.
#
# THE PROGRAM NEVER HALTS. It presents mode 1, then waits on the console
# (device 10, TTI). Every "1"/"2"/"3" + RETURN repaints the text buffer and
# presents, so each switch is a new frame in the live sink AND a new
# output/modeswitch####.png. The steps below drive 2, 3, 1 and screenshot each,
# then hand the still-running program to the person watching.
#
# The screen and the keyboard are two windows on the same desktop:
#   test_start_novafb_monitor  the pygame window -- what the card presents
#   test_open_nova_terminal    an xterm on the SAME console this test drives,
#                              so the person can keep pressing 1/2/3 themselves
#
# The assertions are the PNGs: verify_frames.py recomputes each of the four
# frames from src/nova_charrom.h and the layouts in gen_modeswitch.py and diffs
# every pixel, so it never compares the simulator against itself. Frame 4 is
# mode 1 again, which is what proves a switch RESTORES a mode rather than
# leaving the wider screen's cells behind. The windows are the view, not the
# assertion -- require_success=False on both keeps a headless container running
# this unchanged. See BUILD.txt, CHARACTER MODE.

CONFIG = {
    "parent": "nova fb sprite cursor",
    "projdir": "nova_fb",
    "instance_name": "nova1",
    "function": "text_mode",
    "simh_binary": "bin/dgnova-fb",
    "projbasedir": "/testsrc/sourcedir/",
    # Its own sink, so this can run beside the other two variants.
    "live_sink": "/dev/shm/novafb-modeswitch",
    "console_sock": "/dev/shm/novafb-modeswitch.console",
    "description": "One Nova program with three character modes, switched "
                   "from the console; a screenshot per switch, then the "
                   "running program is handed to the person watching.",
    "tags": ["nova", "framebuffer", "character mode", "interactive", "tty"],
    "structure": {
        "project": {
            "_rel": "{projdir}",
            "out_dir": {
                "_rel": "output"
            },
            "simh_binary_path": "{simh_binary}"
        }
    },
    "steps": [
        {
            "action": "test_hostbuild",
            "param": {
                "command": "python3 gen_modeswitch.py && rm -f output/modeswitch*.png",
                "cwd": "{projbasedir}{projdir}",
                "timeout": 120
            },
            "subaction": "",
            "description": "Rebuild the demo from source and clear old frames, "
                           "so the frame numbers below mean this run's presents "
                           "and not a previous one's."
        },
        {
            "action": "test_start_novafb_monitor",
            "param": {
                "fps": "60",
                "keep_open": True,
                "live_path": "{live_sink}",
                "name": "novafb_monitor",
                "require_success": False,
                "scale": "0",
                "wait": "30"
            },
            "subaction": "",
            "description": "The card's output: a pygame window fed by the live "
                           "sink. Started first -- it waits for the sink rather "
                           "than creating it."
        },
        {
            "action": "test_startnovasimh",
            "param": {
                "binary": "{projbasedir}{projdir}/{simh_binary}",
                "boot_rdos": False,
                "cwd": "{projbasedir}{projdir}",
                "live_path": "{live_sink}",
                "name": "nova1",
                "script_path": "{projbasedir}{projdir}/demo/modeswitch.ini"
            },
            "subaction": "",
            "description": "One instance for the whole test now -- the program "
                           "stays up and switches modes, so there is nothing "
                           "for a second or third simulator to do."
        },
        # The old version fired "go" three times because the FIRST send always
        # landed before SIMH switched its console into run mode and was
        # discarded. Waiting for the program's own prompt is the same fix
        # without the guesswork: it cannot appear until the program is running
        # and reading the console, so a send after it is a send that lands.
        {
            "action": "test_novascreensearch",
            "param": {
                "failphrase": "Invalid argument",
                "name": "nova1",
                "require_success": True,
                "successphrase": "mode> ",
                "timeout": 30
            },
            "subaction": "",
            "description": "The program has started, presented mode 1 and is "
                           "waiting for a key."
        },
        {
            "action": "test_attach_screenshot",
            "param": {
                "image_path": "{projbasedir}{projdir}/output/modeswitch0001.png",
                "name": "mode1",
                "scale": 1
            },
            "subaction": "",
            "description": "Mode 1 as loaded: 80x25, nine dot cell, built-in ROM."
        },
        {
            "action": "test_open_nova_terminal",
            "param": {
                "banner": "Nova console. Press 1, 2 or 3 then RETURN to switch "
                          "the framebuffer's mode. Ctrl-E then 'quit' ends the "
                          "run; Ctrl-] closes this window only.",
                "geometry": "100x24+0+430",
                "instance": "nova1",
                "keep_open": True,
                "name": "nova_terminal",
                "require_success": False,
                "sock_path": "{console_sock}",
                "title": "Nova console - nova_fb mode switch",
                "wait": 30
            },
            "subaction": "",
            "description": "The card's input: an xterm sharing THIS console, so "
                           "the sends below appear in it and the person watching "
                           "can type into the same program."
        },
        # --- mode 2 -------------------------------------------------------
        {
            "action": "test_sendnovacommand",
            "param": {
                "name": "nova1",
                "cmd_text": "2",
                "delay": 0.5
            },
            "subaction": "",
            "description": "Exactly what a person pressing 2 and RETURN sends."
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "failphrase": "expected 1, 2 or 3",
                "name": "nova1",
                "require_success": True,
                "successphrase": "presenting mode 2",
                "timeout": 15
            },
            "subaction": "",
            "description": "The program says this only after SHOWMODE presented, "
                           "so the PNG the next step attaches already exists."
        },
        {
            "action": "test_attach_screenshot",
            "param": {
                "image_path": "{projbasedir}{projdir}/output/modeswitch0002.png",
                "name": "mode2",
                "scale": 1
            },
            "subaction": "",
            "description": "Mode 2: 90x25, eight dot cell, same ROM, same 720x400."
        },
        # --- mode 3 -------------------------------------------------------
        {
            "action": "test_sendnovacommand",
            "param": {
                "name": "nova1",
                "cmd_text": "3",
                "delay": 0.5
            },
            "subaction": ""
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "failphrase": "expected 1, 2 or 3",
                "name": "nova1",
                "require_success": True,
                "successphrase": "presenting mode 3",
                "timeout": 15
            },
            "subaction": ""
        },
        {
            "action": "test_attach_screenshot",
            "param": {
                "image_path": "{projbasedir}{projdir}/output/modeswitch0003.png",
                "name": "mode3",
                "scale": 1
            },
            "subaction": "",
            "description": "Mode 3: the program's own thickened font, via CHARPTR."
        },
        # --- back to mode 1 ----------------------------------------------
        {
            "action": "test_sendnovacommand",
            "param": {
                "name": "nova1",
                "cmd_text": "1",
                "delay": 0.5
            },
            "subaction": "",
            "description": "Back to the mode it started in: the frame this "
                           "produces has to match frame 1 pixel for pixel, "
                           "which is the real test of a mode SWITCH."
        },
        {
            "action": "test_novascreensearch",
            "param": {
                "failphrase": "expected 1, 2 or 3",
                "name": "nova1",
                "require_success": True,
                "successphrase": "presenting mode 1",
                "timeout": 15
            },
            "subaction": ""
        },
        {
            "action": "test_attach_screenshot",
            "param": {
                "image_path": "{projbasedir}{projdir}/output/modeswitch0004.png",
                "name": "mode1again",
                "scale": 1
            },
            "subaction": "",
            "description": "Mode 1 again, after two switches -- verify_frames "
                           "diffs this against the same recomputed frame as 0001."
        },
        # Verified while the program is still running: the frames are files on
        # disk, and nothing here touches the simulator, so this does not have
        # to wait for a teardown that now happens only when the person watching
        # is finished.
        {
            "action": "test_hostbuild",
            "param": {
                "command": "python3 verify_frames.py modeswitch",
                "cwd": "{projbasedir}{projdir}",
                "timeout": 120
            },
            "subaction": "",
            "description": "Recomputes all four frames from the ROM and the "
                           "layouts and diffs every pixel."
        },
        {
            "action": "test_terminate_all",
            "param": {},
            "subaction": "",
            "pause_on": True,
            "description": "THE HANDOVER. pause_on makes this a breakpoint: the "
                           "run blocks here with the program still up, so the "
                           "terminal and the framebuffer window stay live and "
                           "the person watching can keep switching modes. Ctrl-E "
                           "then 'quit' in the terminal ends the simulator and "
                           "releases the run. On a runner without pause_on it is "
                           "an ordinary teardown step, which is the safe way to "
                           "degrade."
        }
    ],
    "test_start_novafb_monitor.keep_open": "",
    "test_start_novafb_monitor.live_path": "",
    "test_start_novafb_monitor.name": "",
    "test_start_novafb_monitor.require_success": "",
    "test_start_novafb_monitor.scale": "",
    "test_start_novafb_monitor.fps": "",
    "test_start_novafb_monitor.title": "",
    "test_start_novafb_monitor.wait": "",
    "test_open_nova_terminal.banner": "",
    "test_open_nova_terminal.font_size": "",
    "test_open_nova_terminal.geometry": "",
    "test_open_nova_terminal.instance": "",
    "test_open_nova_terminal.keep_open": "",
    "test_open_nova_terminal.name": "",
    "test_open_nova_terminal.require_success": "",
    "test_open_nova_terminal.sock_path": "",
    "test_open_nova_terminal.title": "",
    "test_open_nova_terminal.wait": "",
    "test_startnovasimh.binary": "",
    "test_startnovasimh.boot_rdos": "",
    "test_startnovasimh.cwd": "",
    "test_startnovasimh.live_path": "",
    "test_startnovasimh.name": "",
    "test_startnovasimh.script_path": "",
    "test_startnovasimh.boot_timeout": "",
    "test_startnovasimh.disk_image_path": "",
    "test_startnovasimh.memory": "",
    "test_sendnovacommand.cmd_text": "",
    "test_sendnovacommand.name": "",
    "test_sendnovacommand.delay": "",
    "test_novascreensearch.failphrase": "",
    "test_novascreensearch.name": "",
    "test_novascreensearch.require_success": "",
    "test_novascreensearch.successphrase": "",
    "test_novascreensearch.timeout": "",
    "test_attach_screenshot.image_path": "",
    "test_attach_screenshot.name": "",
    "test_attach_screenshot.scale": "",
    "test_hostbuild.command": "",
    "test_hostbuild.cwd": "",
    "test_hostbuild.timeout": "",
}

PATHS = init_test_env(CONFIG, __name__)
